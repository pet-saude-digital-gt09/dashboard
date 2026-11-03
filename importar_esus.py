# importar_esus.py
# Importa os arquivos exportados pelo e-SUS APS (.esus) para o site:
#   - Ficha de Cadastro Individual: cria um usuário para cada cidadão novo (login = CPF, senha = 4 primeiros dígitos
#     do CPF) e detecta mudanças nos dados de quem já está no site
#   - Ficha de Vacinação: registra as vacinas no Cartão Vacinal e detecta registros que parecem corrigidos no e-SUS
#
# Mudanças em dados que já estão no site nunca são gravadas sem revisão: o script lista as alterações pendentes e
# só as aplica quando você pede. Todo valor substituído fica guardado na tabela historico_alteracoes.
#
# Uso:
#   python importar_esus.py <pasta>                       importa o que é novo e lista as alterações pendentes
#   python importar_esus.py <pasta> --aplicar [CPF ...]   grava as alterações pendentes (de todos ou dos CPFs informados)
#   python importar_esus.py <pasta> --rejeitar [CPF ...]  descarta as alterações pendentes, mantendo o site como está
import argparse
import glob
import os
import re
import struct
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

from app import cpf_valido, cpf_br, data_br, get_db_connection

# --- Leitor do formato Thrift (TBinaryProtocol), usado nos arquivos .esus ---
T_STOP, T_BOOL, T_BYTE, T_DOUBLE, T_I16, T_I32, T_I64 = 0, 2, 3, 4, 6, 8, 10
T_STRING, T_STRUCT, T_MAP, T_SET, T_LIST = 11, 12, 13, 14, 15
FORMATOS = {T_BOOL: '?', T_BYTE: 'b', T_DOUBLE: 'd', T_I16: 'h', T_I32: 'i', T_I64: 'q'}


class LeitorThrift:
    """Lê uma struct Thrift sem precisar do schema: devolve um dicionário {id_do_campo: valor}."""

    def __init__(self, dados):
        self.dados = dados
        self.pos = 0

    def _ler(self, formato):
        valor, = struct.unpack_from('>' + formato, self.dados, self.pos)
        self.pos += struct.calcsize(formato)
        return valor

    def ler_valor(self, tipo):
        if tipo in FORMATOS:
            return self._ler(FORMATOS[tipo])
        if tipo == T_STRING:
            tamanho = self._ler('i')
            if self.pos + tamanho > len(self.dados):
                raise ValueError('arquivo truncado')
            self.pos += tamanho
            return self.dados[self.pos - tamanho:self.pos]
        if tipo == T_STRUCT:
            return self.ler_struct()
        if tipo in (T_LIST, T_SET):
            tipo_item, quantidade = self._ler('b'), self._ler('i')
            return [self.ler_valor(tipo_item) for _ in range(quantidade)]
        if tipo == T_MAP:
            tipo_chave, tipo_valor, quantidade = self._ler('b'), self._ler('b'), self._ler('i')
            return {self.ler_valor(tipo_chave): self.ler_valor(tipo_valor) for _ in range(quantidade)}
        raise ValueError(f'tipo Thrift desconhecido: {tipo}')

    def ler_struct(self):
        campos = {}
        while True:
            tipo = self._ler('b')
            if tipo == T_STOP:
                return campos
            id_campo = self._ler('h')
            campos[id_campo] = self.ler_valor(tipo)


def ler_arquivo_esus(caminho):
    """Lê um arquivo .esus e devolve (identificador da ficha, tipo do dado, ficha já decodificada)."""
    with open(caminho, 'rb') as arquivo:
        transporte = LeitorThrift(arquivo.read()).ler_struct()

    # DadoTransporte: 1 = uuidDadoSerializado, 2 = tipoDadoSerializado, 7 = dadoSerializado (a ficha, também em Thrift)
    return transporte[1].decode('utf-8'), transporte.get(2), LeitorThrift(transporte[7]).ler_struct()


# --- Datas e nomes ---
def epoch_ms_para_data(milissegundos):
    """Converte uma data do e-SUS (nascimento, dose transcrita) para 'AAAA-MM-DD'.

    A meia-noite local de qualquer fuso do Brasil cai entre 02h e 05h UTC, então a data em UTC é a correta.
    (Usa timedelta porque datetime.fromtimestamp falha no Windows para datas anteriores a 1970.)
    """
    return (datetime(1970, 1, 1) + timedelta(milliseconds=milissegundos)).date().isoformat()


def data_do_atendimento(milissegundos):
    """Converte a data e hora de um atendimento para 'AAAA-MM-DD' no horário de Brasília (UTC-3)."""
    return epoch_ms_para_data(milissegundos - 3 * 60 * 60 * 1000)


PARTICULAS = {'da', 'das', 'de', 'do', 'dos', 'e'}


def formatar_nome(nome):
    """Converte nomes em CAIXA ALTA para 'Maria das Graças', mantendo como está o que já vier formatado."""
    nome = ' '.join(nome.split())
    if not nome.isupper():
        return nome
    palavras = nome.lower().split()
    return ' '.join(p if i > 0 and p in PARTICULAS else p.capitalize() for i, p in enumerate(palavras))


# --- Ficha de Cadastro Individual (layout e-SUS APS) ---
TIPO_CADASTRO_INDIVIDUAL = 2
SEXOS = {0: 'Masculino', 1: 'Feminino'}  # 4 = Ignorado (fica em branco)


def extrair_cadastro_individual(ficha):
    """Retorna os dados do cidadão de uma Ficha de Cadastro Individual (None nos campos não informados)."""
    # CadastroIndividual: 1 = condicoesDeSaude, 4 = fichaAtualizada, 5 = identificacaoUsuarioCidadao, 13 = headerTransport
    condicoes = ficha.get(1, {})
    identificacao = ficha.get(5, {})
    cabecalho = ficha.get(13, {})

    # CondicoesDeSaude: 17 = statusTemDiabetes, 20 = statusTemHipertensaoArterial (ausentes = não informado)
    grupo_risco = None
    if 17 in condicoes or 20 in condicoes:
        riscos = [risco for campo, risco in ((20, 'Hipertenso'), (17, 'Diabético')) if condicoes.get(campo)]
        grupo_risco = ','.join(riscos) or 'Sem comorbidade'

    # IdentificacaoUsuarioCidadao: 3 = dataNascimentoCidadao, 8 = nomeCidadao, 16 = sexoCidadao, 26 = cpfCidadao
    nascimento = identificacao.get(3)
    return {
        'cpf': identificacao.get(26, b'').decode('utf-8'),
        'nome': formatar_nome(identificacao.get(8, b'').decode('utf-8')),
        'data_nascimento': epoch_ms_para_data(nascimento) if nascimento is not None else None,
        'sexo': SEXOS.get(identificacao.get(16)),
        'grupo_risco': grupo_risco,
        # Usados para escolher a ficha mais recente quando o mesmo cidadão aparece mais de uma vez
        'data_ficha': cabecalho.get(5, 0),
        'atualizada': bool(ficha.get(4)),
    }


# --- Ficha de Vacinação (vem dentro do registro de atendimento do PEC) ---
TIPO_REGISTRO_ATENDIMENTO = 9

# Códigos de imunobiológico do e-SUS (dicionário LEDI), agrupados pelo nome usado no CALENDARIO_VACINAL do site
VACINAS_DO_SITE = {
    'BCG': (15,),
    'Hepatite B': (9,),
    'Hepatite A': (55, 83, 35),
    'Pentavalente (DTP/Hib/HepB)': (42,),
    'Poliomielite (VIP/VOP)': (22, 28),
    'Pneumocócica 10V': (26,),
    'Pneumocócica 23V': (21,),
    'Rotavírus': (45, 65),
    'Meningocócica C': (41,),
    'Meningocócica ACWY': (74,),
    'Febre Amarela': (14,),
    'Tríplice Viral (SCR)': (24,),
    'Tetraviral (SCRV)': (56, 73),
    'Varicela': (34,),
    'DTP (Reforço)': (46,),
    'Dupla Adulto (dT)': (25,),
    'DTPA (Gestante)': (57,),
    'HPV': (60, 67, 93),
    'Influenza (Gripe)': (33, 64, 77, 110, 117),
    'Covid-19': (85, 86, 87, 88, 89, 97, 98, 99, 102, 103, 105, 112, 114),
    'Herpes Zóster': (76, 101),
}
IMUNOBIOLOGICOS = {codigo: nome for nome, codigos in VACINAS_DO_SITE.items() for codigo in codigos}

# Códigos de dose do e-SUS (dicionário LEDI) -> rótulo usado no calendário do site
DOSES = {
    1: '1ª Dose', 2: '2ª Dose', 3: '3ª Dose', 6: 'Reforço 1', 7: 'Reforço 2', 39: 'Reforço 3',
    8: 'Dose', 9: 'Dose Única', 38: 'Reforço', 36: 'Dose Inicial', 37: 'Dose Adicional', 10: 'Revacinação',
}

# Doses que o calendário do site chama de outro jeito
DOSES_NO_CALENDARIO = {
    ('Hepatite B', 'Dose'): 'Ao Nascer',
    ('Tríplice Viral (SCR)', 'Dose'): '1ª Dose',  # adultos de 30 a 59 anos tomam uma dose só
    ('Influenza (Gripe)', 'Dose'): 'Dose Anual',
    ('Influenza (Gripe)', 'Dose Única'): 'Dose Anual',
    ('Covid-19', 'Dose'): 'Dose Anual',
    ('Covid-19', 'Dose Única'): 'Dose Anual',
}

# Doses que podem se repetir ao longo da vida: a mesma dose em outra data é uma nova aplicação, não uma correção
DOSES_REPETIVEIS = {'Dose', 'Dose Anual', 'Dose Adicional', 'Revacinação'}
VACINAS_COM_REFORCO_PERIODICO = {'Dupla Adulto (dT)', 'DTPA (Gestante)'}


def extrair_vacinacao(uuid, registro):
    """Lê a ficha de vacinação de um registro de atendimento.

    Devolve {'uuid', 'inicio' (data e hora do atendimento), 'vacinas': [(cpf, código do imunobiológico, código da dose, data)]}.
    """
    ficha = {'uuid': uuid, 'inicio': 0, 'vacinas': []}
    # Registro de atendimento: 19 = ficha de vacinação; ficha de vacinação: 4 = uma vacinação por cidadão
    for vacinacao in registro[19].get(4, []):
        # Vacinação: 11 = vacinas, 12 = data e hora do início do atendimento, 14 = CPF do cidadão
        cpf = vacinacao.get(14, b'').decode('utf-8')
        ficha['inicio'] = max(ficha['inicio'], vacinacao[12])
        data_atendimento = data_do_atendimento(vacinacao[12])

        for vacina in vacinacao.get(11, []):
            # Vacina: 1 = imunobiológico, 3 = dose, 7 = é transcrição de caderneta, 8 = data da dose transcrita
            data = epoch_ms_para_data(vacina[8]) if vacina.get(7) else data_atendimento
            ficha['vacinas'].append((cpf, vacina.get(1), vacina.get(3), data))
    return ficha


def buscar_registro_corrigido(conn, cpf, vacina, dose, data):
    """Procura no site o registro que a vacina nova provavelmente corrige: a mesma dose em outra data
    (se for uma dose que só se toma uma vez) ou outra dose da mesma vacina no mesmo dia."""
    dose_unica_na_vida = dose not in DOSES_REPETIVEIS and not (dose == 'Reforço' and vacina in VACINAS_COM_REFORCO_PERIODICO)
    if dose_unica_na_vida:
        mesma_dose = conn.execute(
            'SELECT * FROM vacinas_aplicadas WHERE cpf_usuario = ? AND vacina = ? AND dose = ? AND data_aplicacao <> ?',
            (cpf, vacina, dose, data)
        ).fetchone()
        if mesma_dose:
            return mesma_dose
    return conn.execute(
        'SELECT * FROM vacinas_aplicadas WHERE cpf_usuario = ? AND vacina = ? AND data_aplicacao = ? AND dose <> ?',
        (cpf, vacina, data, dose)
    ).fetchone()


# --- Controle da importação no banco ---
# Como cada alteração em um dado que já está no site é mostrada e contada, conforme a decisão tomada para o CPF
ROTULOS = {None: '[PENDENTE]  ', 'aplicar': '[ALTERADO]  ', 'rejeitar': '[REJEITADO] '}
RESUMOS = {None: 'alteração(ões) pendente(s)', 'aplicar': 'alteração(ões) aplicada(s)', 'rejeitar': 'alteração(ões) rejeitada(s)'}


def preparar_banco(conn):
    """Cria as tabelas de controle da importação, caso o banco ainda não as tenha."""
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS esus_fichas_processadas (
            uuid TEXT PRIMARY KEY,
            situacao TEXT NOT NULL,
            processada_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS historico_alteracoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cpf_usuario TEXT NOT NULL,
            campo TEXT NOT NULL,
            valor_anterior TEXT,
            valor_novo TEXT,
            ficha_esus TEXT,
            alterado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')


def marcar_processadas(conn, uuids, situacao):
    """Registra as fichas como resolvidas, para que não sejam reavaliadas se forem importadas de novo."""
    conn.executemany('INSERT OR REPLACE INTO esus_fichas_processadas (uuid, situacao) VALUES (?, ?)',
                     [(uuid, situacao) for uuid in uuids])


def registrar_historico(conn, cpf, campo, anterior, novo, uuid):
    conn.execute(
        'INSERT INTO historico_alteracoes (cpf_usuario, campo, valor_anterior, valor_novo, ficha_esus) VALUES (?, ?, ?, ?, ?)',
        (cpf, campo, anterior, novo, uuid)
    )


# --- Gravação no banco do site ---
CAMPOS_CADASTRO = {'nome': 'Nome', 'data_nascimento': 'Data de nascimento', 'sexo': 'Sexo', 'grupo_risco': 'Grupo de risco'}


def normalizar(valor):
    """Prepara um valor para comparação: ignora maiúsculas, espaços extras e a ordem dos itens do grupo de risco."""
    return sorted(' '.join(str(valor or '').split()).casefold().split(','))


def exibir(campo, valor):
    return data_br(valor) if campo == 'data_nascimento' else valor


def importar_cadastros(conn, cadastros, decidir, resumo):
    """Cria os usuários novos e trata as diferenças entre o e-SUS e os dados de quem já está no site."""
    for cpf, fichas in cadastros.items():
        cidadao = max(fichas, key=lambda c: (c['data_ficha'], c['atualizada']))  # vale a ficha mais recente
        uuids = [c['uuid'] for c in fichas]
        usuario = conn.execute('SELECT * FROM usuarios WHERE cpf = ?', (cpf,)).fetchone()

        if usuario is None:
            grupo_risco = cidadao['grupo_risco'] or 'Sem comorbidade'
            conn.execute(
                """INSERT INTO usuarios (cpf, nome, senha_hash, grupo_risco, data_nascimento, sexo)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (cpf, cidadao['nome'], generate_password_hash(cpf[:4]), grupo_risco,
                 cidadao['data_nascimento'], cidadao['sexo'])
            )
            marcar_processadas(conn, uuids, 'usuário criado')
            resumo['usuário(s) criado(s)'] += 1
            print(f'[CRIADO]    {cpf_br(cpf)} - {cidadao["nome"]} ({grupo_risco})')
            continue

        # Valor vazio no e-SUS nunca apaga o que está no site
        diferencas = [(campo, usuario[campo], cidadao[campo]) for campo in CAMPOS_CADASTRO
                      if cidadao[campo] and normalizar(cidadao[campo]) != normalizar(usuario[campo])]
        if not diferencas:
            marcar_processadas(conn, uuids, 'sem alterações')
            continue

        acao = decidir(cpf)
        for campo, atual, novo in diferencas:
            if acao == 'aplicar':
                conn.execute(f'UPDATE usuarios SET {campo} = ? WHERE cpf = ?', (novo, cpf))
                registrar_historico(conn, cpf, CAMPOS_CADASTRO[campo], atual, novo, cidadao['uuid'])
            print(f'{ROTULOS[acao]}{cpf_br(cpf)} - {usuario["nome"]}: {CAMPOS_CADASTRO[campo]}: '
                  f'"{exibir(campo, atual)}" (site) → "{exibir(campo, novo)}" (e-SUS)')
        resumo[RESUMOS[acao]] += len(diferencas)
        if acao is not None:
            marcar_processadas(conn, uuids, 'alterações aplicadas' if acao == 'aplicar' else 'alterações rejeitadas')


def importar_vacinas(conn, fichas, decidir, resumo):
    """Registra as vacinas novas no Cartão Vacinal e trata os registros que parecem corrigidos no e-SUS."""
    novas = Counter()
    sem_usuario, desconhecidas = set(), set()

    for ficha in sorted(fichas, key=lambda f: f['inicio']):  # as mais recentes por último, como correções das anteriores
        resolvida = True
        for cpf, codigo_vacina, codigo_dose, data in ficha['vacinas']:
            usuario = conn.execute('SELECT nome FROM usuarios WHERE cpf = ?', (cpf,)).fetchone()
            vacina, dose = IMUNOBIOLOGICOS.get(codigo_vacina), DOSES.get(codigo_dose)
            # Fichas com vacinas que não puderam ser gravadas ficam para a próxima execução
            if usuario is None:
                sem_usuario.add(cpf)
                resolvida = False
                continue
            if vacina is None or dose is None:
                desconhecidas.add((codigo_vacina, codigo_dose))
                resolvida = False
                continue
            dose = DOSES_NO_CALENDARIO.get((vacina, dose), dose)

            ja_registrada = conn.execute(
                'SELECT id FROM vacinas_aplicadas WHERE cpf_usuario = ? AND vacina = ? AND dose = ? AND data_aplicacao = ?',
                (cpf, vacina, dose, data)
            ).fetchone()
            if ja_registrada:
                continue

            anterior = buscar_registro_corrigido(conn, cpf, vacina, dose, data)
            if anterior is None:
                conn.execute(
                    'INSERT INTO vacinas_aplicadas (cpf_usuario, vacina, dose, data_aplicacao) VALUES (?, ?, ?, ?)',
                    (cpf, vacina, dose, data)
                )
                novas[cpf] += 1
                continue

            acao = decidir(cpf)
            if acao == 'aplicar':
                conn.execute('UPDATE vacinas_aplicadas SET dose = ?, data_aplicacao = ? WHERE id = ?',
                             (dose, data, anterior['id']))
                registrar_historico(conn, cpf, f'Vacina {vacina}', f'{anterior["dose"]} em {anterior["data_aplicacao"]}',
                                    f'{dose} em {data}', ficha['uuid'])
            elif acao is None:
                resolvida = False
            print(f'{ROTULOS[acao]}{cpf_br(cpf)} - {usuario["nome"]}: {vacina}: '
                  f'"{anterior["dose"]} em {data_br(anterior["data_aplicacao"])}" (site) → "{dose} em {data_br(data)}" (e-SUS)')
            resumo[RESUMOS[acao]] += 1

        if resolvida:
            marcar_processadas(conn, [ficha['uuid']], 'vacinas gravadas')

    for cpf, quantidade in novas.items():
        nome = conn.execute('SELECT nome FROM usuarios WHERE cpf = ?', (cpf,)).fetchone()['nome']
        print(f'[VACINAS]   {cpf_br(cpf)} - {nome}: {quantidade} nova(s)')
    resumo['vacina(s) nova(s)'] += sum(novas.values())
    for cpf in sorted(sem_usuario):
        print(f'[SEM USUÁRIO] {cpf_br(cpf) or "CPF não informado"}: vacinas ignoradas, o cidadão não tem cadastro no site')
    for codigo_vacina, codigo_dose in sorted(desconhecidas, key=str):
        print(f'[DESCONHECIDA] imunobiológico {codigo_vacina}, dose {codigo_dose}: '
              'sem correspondência em VACINAS_DO_SITE/DOSES, vacina ignorada')


def main():
    parser = argparse.ArgumentParser(description='Importa para o site os arquivos .esus exportados pelo e-SUS APS.')
    parser.add_argument('pasta', help='pasta com os arquivos .esus')
    parser.add_argument('--aplicar', nargs='*', metavar='CPF',
                        help='grava as alterações pendentes (de todos, ou só dos CPFs informados)')
    parser.add_argument('--rejeitar', nargs='*', metavar='CPF',
                        help='descarta as alterações pendentes e mantém o site como está (de todos, ou só dos CPFs informados)')
    args = parser.parse_args()

    def ler_cpfs(lista):
        if lista is None:
            return None
        cpfs = {re.sub(r'[^0-9]', '', cpf) for cpf in lista}
        invalidos = sorted(cpf for cpf in cpfs if not cpf_valido(cpf))
        if invalidos:
            parser.error(f'CPF inválido: {", ".join(invalidos)} (a pasta deve vir antes de --aplicar/--rejeitar)')
        return cpfs

    aplicar, rejeitar = ler_cpfs(args.aplicar), ler_cpfs(args.rejeitar)

    def decidir(cpf):
        """O que fazer com as alterações de um CPF: 'rejeitar', 'aplicar' ou None (deixar pendente)."""
        if rejeitar is not None and (not rejeitar or cpf in rejeitar):
            return 'rejeitar'
        if aplicar is not None and (not aplicar or cpf in aplicar):
            return 'aplicar'
        return None

    arquivos = sorted(glob.glob(os.path.join(args.pasta, '*.esus')))
    if not arquivos:
        sys.exit(f'Nenhum arquivo .esus encontrado em: {args.pasta}')

    conn = get_db_connection()
    preparar_banco(conn)
    processadas = {linha['uuid'] for linha in conn.execute('SELECT uuid FROM esus_fichas_processadas')}

    # 1. Lê as fichas que ainda não foram processadas
    cadastros = defaultdict(list)
    vacinacoes = []
    ja_processadas = outras_fichas = 0
    for caminho in arquivos:
        try:
            uuid, tipo, ficha = ler_arquivo_esus(caminho)
            if uuid in processadas:
                ja_processadas += 1
            elif tipo == TIPO_CADASTRO_INDIVIDUAL:
                cidadao = extrair_cadastro_individual(ficha)
                if cpf_valido(cidadao['cpf']):
                    cadastros[cidadao['cpf']].append(dict(cidadao, uuid=uuid))
                else:
                    print(f'[SEM CPF]   {cidadao["nome"]}: CPF ausente ou inválido, não é possível criar o login')
            elif tipo == TIPO_REGISTRO_ATENDIMENTO and 19 in ficha:  # 19 = ficha de vacinação
                vacinacoes.append(extrair_vacinacao(uuid, ficha))
            else:
                outras_fichas += 1
        except (ValueError, KeyError, struct.error, UnicodeDecodeError) as e:
            print(f'[ERRO]      {os.path.basename(caminho)}: arquivo inválido ({e})')

    # 2. Grava no banco do site (usuários primeiro, para que as vacinas de quem acabou de ser criado entrem também)
    resumo = Counter()
    importar_cadastros(conn, cadastros, decidir, resumo)
    importar_vacinas(conn, vacinacoes, decidir, resumo)
    conn.commit()
    conn.close()

    print(f'\n{len(arquivos)} arquivo(s) lido(s): {sum(map(len, cadastros.values()))} ficha(s) de cadastro e '
          f'{len(vacinacoes)} de vacinação a processar, {ja_processadas} já processada(s) antes, '
          f'{outras_fichas} de outro tipo ignorada(s).')
    print(', '.join(f'{quantidade} {descricao}' for descricao, quantidade in resumo.items() if quantidade)
          or 'Nada novo para gravar no site.')
    if resumo['usuário(s) criado(s)']:
        print('Login dos novos usuários: CPF | Senha inicial: 4 primeiros dígitos do CPF.')
    if resumo[RESUMOS[None]]:
        print('\nAs alterações pendentes NÃO foram gravadas. Confira cada uma e rode de novo com:\n'
              '  --aplicar CPF ...   para gravar no site (o valor anterior fica em historico_alteracoes)\n'
              '  --rejeitar CPF ...  para manter o site como está\n'
              'Sem CPFs, a opção vale para todas as pendências.')


if __name__ == '__main__':
    main()

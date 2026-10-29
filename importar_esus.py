# importar_esus.py
# Importa os cidadãos das Fichas de Cadastro Individual exportadas pelo e-SUS APS (.esus)
# e cria um usuário no site para cada um (login = CPF, senha = 4 primeiros dígitos do CPF).
#
# Uso: python importar_esus.py "C:\caminho\da\pasta\com\arquivos"
import glob
import os
import struct
import sys
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

from app import cpf_valido, cpf_br, get_db_connection

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


# --- Interpretação da Ficha de Cadastro Individual (layout e-SUS APS) ---
TIPO_CADASTRO_INDIVIDUAL = 2
SEXOS = {0: 'Masculino', 1: 'Feminino'}  # 4 = Ignorado (fica em branco)
PARTICULAS = {'da', 'das', 'de', 'do', 'dos', 'e'}


def epoch_ms_para_data(milissegundos):
    """Converte o timestamp do e-SUS para 'AAAA-MM-DD'.

    A meia-noite local de qualquer fuso do Brasil cai entre 02h e 05h UTC, então a data em UTC é a correta.
    (Usa timedelta porque datetime.fromtimestamp falha no Windows para datas anteriores a 1970.)
    """
    return (datetime(1970, 1, 1) + timedelta(milliseconds=milissegundos)).date().isoformat()


def formatar_nome(nome):
    """Converte nomes em CAIXA ALTA para 'Maria das Graças', mantendo como está o que já vier formatado."""
    nome = ' '.join(nome.split())
    if not nome.isupper():
        return nome
    palavras = nome.lower().split()
    return ' '.join(p if i > 0 and p in PARTICULAS else p.capitalize() for i, p in enumerate(palavras))


def ler_cadastro_individual(caminho):
    """Retorna os dados do cidadão de um arquivo .esus, ou None se não for uma Ficha de Cadastro Individual."""
    with open(caminho, 'rb') as arquivo:
        transporte = LeitorThrift(arquivo.read()).ler_struct()

    # DadoTransporte: 2 = tipoDadoSerializado, 7 = dadoSerializado (a ficha, também em Thrift)
    if transporte.get(2) != TIPO_CADASTRO_INDIVIDUAL:
        return None
    ficha = LeitorThrift(transporte[7]).ler_struct()

    # CadastroIndividual: 1 = condicoesDeSaude, 4 = fichaAtualizada, 5 = identificacaoUsuarioCidadao, 13 = headerTransport
    condicoes = ficha.get(1, {})
    identificacao = ficha.get(5, {})
    cabecalho = ficha.get(13, {})

    # CondicoesDeSaude: 17 = statusTemDiabetes, 20 = statusTemHipertensaoArterial
    riscos = []
    if condicoes.get(20):
        riscos.append('Hipertenso')
    if condicoes.get(17):
        riscos.append('Diabético')

    # IdentificacaoUsuarioCidadao: 3 = dataNascimentoCidadao, 8 = nomeCidadao, 16 = sexoCidadao, 26 = cpfCidadao
    nascimento = identificacao.get(3)
    return {
        'cpf': identificacao.get(26, b'').decode('utf-8'),
        'nome': formatar_nome(identificacao.get(8, b'').decode('utf-8')),
        'data_nascimento': epoch_ms_para_data(nascimento) if nascimento is not None else None,
        'sexo': SEXOS.get(identificacao.get(16)),
        'grupo_risco': ','.join(riscos) or 'Sem comorbidade',
        # Usados para escolher a ficha mais recente quando o mesmo cidadão aparece mais de uma vez
        'data_ficha': cabecalho.get(5, 0),
        'atualizada': bool(ficha.get(4)),
    }


def main():
    if len(sys.argv) != 2:
        print('Uso: python importar_esus.py <pasta com os arquivos .esus>')
        sys.exit(1)

    arquivos = sorted(glob.glob(os.path.join(sys.argv[1], '*.esus')))
    if not arquivos:
        print(f'Nenhum arquivo .esus encontrado em: {sys.argv[1]}')
        sys.exit(1)

    # 1. Lê as fichas, guardando só a mais recente de cada CPF
    cadastros = {}
    outras_fichas = 0
    for caminho in arquivos:
        try:
            cidadao = ler_cadastro_individual(caminho)
        except (ValueError, KeyError, struct.error, UnicodeDecodeError) as e:
            print(f'[ERRO]      {os.path.basename(caminho)}: arquivo inválido ({e})')
            continue

        if cidadao is None:
            outras_fichas += 1
            continue
        if not cpf_valido(cidadao['cpf']):
            print(f'[SEM CPF]   {cidadao["nome"]}: CPF ausente ou inválido, não é possível criar o login')
            continue

        anterior = cadastros.get(cidadao['cpf'])
        if anterior is None or (cidadao['data_ficha'], cidadao['atualizada']) >= (anterior['data_ficha'], anterior['atualizada']):
            cadastros[cidadao['cpf']] = cidadao

    # 2. Cria os usuários no banco do site
    conn = get_db_connection()
    criados = 0
    for cpf, cidadao in cadastros.items():
        if conn.execute('SELECT cpf FROM usuarios WHERE cpf = ?', (cpf,)).fetchone():
            print(f'[JÁ EXISTE] {cpf_br(cpf)} - {cidadao["nome"]}')
            continue

        conn.execute(
            """INSERT INTO usuarios (cpf, nome, senha_hash, grupo_risco, data_nascimento, sexo)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (cpf, cidadao['nome'], generate_password_hash(cpf[:4]), cidadao['grupo_risco'],
             cidadao['data_nascimento'], cidadao['sexo'])
        )
        criados += 1
        print(f'[CRIADO]    {cpf_br(cpf)} - {cidadao["nome"]} ({cidadao["grupo_risco"]})')

    conn.commit()
    conn.close()

    print(f'\n{len(arquivos)} arquivo(s) lido(s): {len(cadastros)} cidadão(s) com cadastro individual, '
          f'{outras_fichas} ficha(s) de outro tipo ignorada(s).')
    print(f'{criados} usuário(s) criado(s). Login: CPF | Senha inicial: 4 primeiros dígitos do CPF.')


if __name__ == '__main__':
    main()

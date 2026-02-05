from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
import sqlite3
import re
from werkzeug.security import check_password_hash, generate_password_hash # Importa o verificador de senha

app = Flask(__name__)
app.config['SECRET_KEY'] = 'uma-chave-secreta-muito-forte'

DICAS_SAUDE = {
    'Hipertenso': [
        'Não espere sentir sintomas; a pressão alta geralmente não apresenta sinais visíveis.',
        'Fique atento, pois pressão 14 por 9 (ou superior) já é considerada pressão alta.',
        'Diminua o consumo de sal e utilize temperos naturais para dar sabor à comida.',
        'A pressão alta não tem cura, mas tem controle, por isso é fundamental seguir o tratamento continuamente.',
        'Dor na nuca, tontura ou visão embaçada? Pode ser pressão altíssima. Procure um médico.',
        'O controle da pressão é vital para evitar AVC (derrame), infarto e problemas nos rins.',
        'Controle o peso, uma vez que a obesidade é uma das principais causas da pressão alta.',
        'A falta de atividade física piora a pressão, portanto, mexa-se.',
        'Pare de fumar, pois o cigarro aumenta a pressão arterial.',
        'Controle o estresse emocional, pois ele eleva a sua pressão.'

        ],
    'Diabético': [
        'Examine seus pés todos os dias. Procure cortes, bolhas ou rachaduras.',
        'Fique atento a sintomas como tremedeira, suor frio ou tontura; isso pode indicar açúcar baixo.',
        'Não pule refeições. Comer nos horários certos evita o açúcar baixo (hipoglicemia).',
        'Meça seu açúcar no sangue (glicemia) regularmente, várias vezes ao dia.',
        'Não interrompa o tratamento e tome seus medicamentos todos os dias, exatamente como o médico receitou.',
        'Faça os exames de urina e sangue. Cuidar do rim hoje evita a hemodiálise amanhã.',
        'Pare de fumar, pois o cigarro piora a circulação e aumenta drasticamente o risco de amputação.',
        'Mantenha o peso controlado, pois o sobrepeso é um risco enorme para o diabetes.',
        'Fuja do sedentarismo, pois a atividade física é essencial para o controle da doença.'
    ],
    'Geral': [
        'Beba pelo menos 2 litros de água por dia.',
        'Mantenha uma rotina de sono regular, dormindo de 7 a 8 horas por noite.'
    ]
}

DETALHES_GRUPOS = {
    'homem': {
        'titulo': 'Saúde do Homem',
        'icone': '👨',
        'desc': 'Cuidar de si é um ato de responsabilidade, força e proteção para você e sua família.',
        'secoes': [
            {
                'titulo': '🛡️ Prevenção e Exames',
                'itens': [
                    'Acesso: Procure a unidade de saúde mesmo sem estar doente. Agende consultas preventivas de 1 a 2 vezes por ano.',
                    'Câncer de Próstata: Converse sobre exames a partir dos 50 anos (ou 45 se houver fatores de risco na família).',
                    'Doenças Crônicas: Monitore pressão e glicemia regularmente para prevenir hipertensão e diabetes.'
                ]
            },
            {
                'titulo': '❤️ Saúde Sexual e Reprodutiva',
                'itens': [
                    'Sinal de Alerta: A disfunção erétil pode ser um sinal de problemas cardíacos. Não ignore.',
                    'Proteção: Use preservativo em todas as relações sexuais e faça testes regulares de ISTs.'
                ]
            },
            {
                'titulo': '👶 Paternidade Ativa',
                'itens': [
                    'Pré-Natal do Parceiro: Acompanhe as consultas da gestante e participe das decisões.',
                    'Dia a Dia: Dividir tarefas como banho e troca de fraldas fortalece o vínculo com a criança.'
                ]
            }
        ]
    },
    'mulher': {
        'titulo': 'Saúde da Mulher',
        'icone': '👩',
        'desc': 'Atenção integral em todas as fases da vida, garantindo autonomia, prevenção de doenças e direitos.',
        'secoes': [
            {
                'titulo': '🌸 Prevenção',
                'itens': [
                    'Preventivo (Papanicolau): Indicado para mulheres de 25 a 64 anos. Deve ser feito anualmente ou conforme orientação.',
                    'Sinais de Alerta: Procure atendimento se houver lesões, verrugas ou corrimento com odor forte.'
                ]
            },
            {
                'titulo': '💊 Planejamento Reprodutivo',
                'itens': [
                    'Métodos Gratuitos: O SUS oferece DIU de cobre (dura 10 anos), pílulas, injeções e preservativos.',
                    'DIU de Cobre: Alta eficácia (mais de 99%), sem hormônios e pode ser usado por quem nunca engravidou.',
                    'Direito de Escolha: Laqueadura tubária permitida para maiores de 21 anos ou com dois filhos vivos.'
                ]
            },
            {
                'titulo': '🤰 Maternidade e Direitos',
                'itens': [
                    'Pré-Natal: Iniciar cedo para garantir o desenvolvimento saudável. Direito a acompanhante no parto.',
                    'Violência: Em caso de violência sexual ou doméstica, o atendimento é prioritário e não exige agendamento.'
                ]
            }
        ]
    },
    'idoso': {
        'titulo': 'Saúde da Pessoa Idosa',
        'icone': '👴',
        'desc': 'Envelhecimento ativo e saudável. O foco é manter a independência, a autonomia e a segurança no dia a dia.',
        'secoes': [
            {
                'titulo': '🏠 Prevenção de Quedas',
                'itens': [
                    'Casa Segura: Retire tapetes soltos, fios do chão e instale corrimãos nas escadas.',
                    'Calçados: Use sapatos fechados, firmes e com solado antiderrapante. Evite chinelos soltos.',
                    'Iluminação: Mantenha a casa bem iluminada, especialmente o caminho para o banheiro à noite.'
                ]
            },
            {
                'titulo': '💊 Uso de Medicamentos',
                'itens': [
                    'Organização: Mantenha na embalagem original e verifique a validade com frequência.',
                    'Armazenamento: Não guarde remédios na porta da geladeira nem junto com produtos de limpeza.'
                ]
            },
            {
                'titulo': '⚖️ Direitos',
                'itens': [
                    'Identificação: Para garantir direitos de idoso (60+), basta apresentar documento oficial com foto.',
                    'Denúncia: Em caso de violência ou negligência, disque 100.'
                ]
            }
        ]
    },
    'crianca': {
        'titulo': 'Saúde da Criança',
        'icone': '👶',
        'desc': 'Os primeiros anos definem o futuro. Garanta um ambiente saudável, seguro e estimulante.',
        'secoes': [
            {
                'titulo': '🧪 Triagem Neonatal',
                'itens': [
                    'Teste do Pezinho: Realizado entre o 3º e 5º dia de vida. Detecta doenças graves.',
                    'Outros Testes: Exija os testes do Olhinho (visão), Orelhinha (audição) e Coraçãozinho na maternidade.'
                ]
            },
            {
                'titulo': '🚩 Sinais de Alerta',
                'itens': [
                    'Visão: Atenção se a criança aproxima muito os objetos ou tem dificuldade de focar.',
                    'Audição: Atenção se a criança não reage a barulhos fortes ou demora para falar.',
                    'Motor: Atraso para rolar, engatinhar ou andar exige avaliação médica.'
                ]
            },
            {
                'titulo': '🍼 Nutrição e Vacinas',
                'itens': [
                    'Leite Materno: Exclusivo até os 6 meses e complementar até os 2 anos ou mais.',
                    'Vacinação: Direito fundamental da criança. Mantenha a caderneta sempre atualizada.'
                ]
            }
        ]
    },
    'adolescente': {
        'titulo': 'Saúde do Adolescente',
        'icone': '👱',
        'desc': 'Fase de transformações. Você tem direito a sigilo médico e orientações sobre seu corpo e mente.',
        'secoes': [
            {
                'titulo': '🔒 Seus Direitos',
                'itens': [
                    'Sigilo: O que você conversa com o profissional de saúde é confidencial. Você pode ser atendido sozinho.',
                    'Dúvidas: Pergunte sem vergonha sobre mudanças no corpo, sexualidade e sentimentos.'
                ]
            },
            {
                'titulo': '🧠 Saúde Mental',
                'itens': [
                    'Emoções: É normal sentir ansiedade. Se o sofrimento for grande, procure a UBS.',
                    'Sono: Tente dormir entre 8 e 10 horas por noite. Evite telas antes de dormir.'
                ]
            },
            {
                'titulo': '⚠️ Cuidados',
                'itens': [
                    'Sexualidade: Use camisinha em todas as relações para prevenir gravidez e ISTs.',
                    'Internet: Cuidado com a exposição. Não envie fotos íntimas e peça ajuda se sofrer violência online.'
                ]
            }
        ]
    }
}


def is_cpf_valido(cpf: str) -> bool:
    """Valida um CPF brasileiro."""
    
    # 1. Remove caracteres não numéricos
    cpf_numeros = re.sub(r'[^0-9]', '', cpf)

    # 2. Verifica se tem 11 dígitos
    if len(cpf_numeros) != 11:
        return False

    # 3. Verifica se todos os dígitos são iguais (ex: 111.111.111-11)
    if cpf_numeros == cpf_numeros[0] * 11:
        return False

    # 4. Cálculo do primeiro dígito verificador (dv1)
    soma = 0
    for i in range(9):
        soma += int(cpf_numeros[i]) * (10 - i)
    
    dv1 = (soma * 10) % 11
    if dv1 == 10:
        dv1 = 0
    
    if dv1 != int(cpf_numeros[9]):
        return False

    # 5. Cálculo do segundo dígito verificador (dv2)
    soma = 0
    for i in range(10):
        soma += int(cpf_numeros[i]) * (11 - i)
    
    dv2 = (soma * 10) % 11
    if dv2 == 10:
        dv2 = 0

    if dv2 != int(cpf_numeros[10]):
        return False
        
    # Se passou por todas as verificações
    return True


# --- FUNÇÃO DE CONEXÃO COM O BANCO ---
def get_db_connection():
    """Cria uma conexão com o banco de dados SQLite."""
    conn = sqlite3.connect('saude.db')
    # Isso faz a conexão retornar os dados como dicionários (útil!)
    conn.row_factory = sqlite3.Row 
    return conn

# --- Controle de Login (Decorator) ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'cpf_logado' not in session:
            flash('Você precisa estar logado para ver esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- ROTAS DA APLICAÇÃO (Atualizadas) ---

@app.route('/')
def index():
    """Página Inicial (Landing Page)."""
    # Se já estiver logado, manda direto para a área interna
    if 'cpf_logado' in session:
        return redirect(url_for('home'))
    
    # Se não, renderiza a página de apresentação
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Tela de Login (Agora usa o banco de dados)."""
    if request.method == 'POST':
        cpf_bruto = request.form['cpf']
        cpf = re.sub(r'[^0-9]', '', cpf_bruto)
        senha = request.form['senha']
        
        # 1. Conecta ao banco e busca o usuário
        conn = get_db_connection()
        usuario_db = conn.execute('SELECT * FROM usuarios WHERE cpf = ?', (cpf,)).fetchone()
        conn.close()

        # 2. Verifica se o usuário existe e se a senha está correta
        if usuario_db and check_password_hash(usuario_db['senha_hash'], senha):
            # Salva dados na sessão
            session['cpf_logado'] = usuario_db['cpf']
            session['nome_usuario'] = usuario_db['nome']
            # Divide os grupos de risco (ex: "Hipertenso,Diabético")
            session['grupo_risco'] = usuario_db['grupo_risco'].split(',') if usuario_db['grupo_risco'] else []
            
            flash(f'Login efetuado com sucesso! Bem-vindo(a), {usuario_db["nome"]}.', 'success')
            return redirect(url_for('home'))
        else:
            flash('CPF ou senha incorretos.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear() # Limpa toda a sessão
    flash('Você saiu do sistema.', 'info')
    return redirect(url_for('index'))

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    """Tela de Cadastro de Novo Usuário."""
    
    if request.method == 'POST':
        # 1. Coletar dados do formulário
        nome = request.form['nome']
        cpf_bruto = request.form['cpf']
        cpf = re.sub(r'[^0-9]', '', cpf_bruto)
        senha = request.form['senha']
        confirmar_senha = request.form['confirmar_senha']
        # .strip() remove espaços em branco antes e depois

        lista_riscos = request.form.getlist('grupo_risco')
        
        opcoes_doencas = ['Hipertenso', 'Diabético']
        tem_doenca = any(item in lista_riscos for item in opcoes_doencas)
        
        if tem_doenca and "Sem comorbidade" in lista_riscos:
            lista_riscos.remove("Sem comorbidade")
        # # Lógica inteligente: Se marcou "Hipertenso" E "Sem comorbidade", 
        # # removemos o "Sem comorbidade" para não ficar contraditório.
        # if len(lista_riscos) > 1 and "Sem comorbidade" in lista_riscos:
        #     lista_riscos.remove("Sem comorbidade")
        
        # # Se o usuário não marcou nada, definimos como "Sem comorbidade"
        if not lista_riscos:
             lista_riscos = ["Sem comorbidade"]

        # Transformamos a lista em uma string separada por vírgulas para o Banco de Dados
        # Ex: ['Hipertenso', 'Diabético'] vira "Hipertenso,Diabético"
        grupo_risco_str = ",".join(lista_riscos)
        # 2. Validações
        if not all([nome, cpf, senha, confirmar_senha]):
            flash('Por favor, preencha todos os campos obrigatórios.', 'danger')
            return redirect(url_for('cadastro'))

        if senha != confirmar_senha:
            flash('As senhas não coincidem. Tente novamente.', 'danger')
            return redirect(url_for('cadastro'))
            
        if len(cpf) != 11 or not cpf.isdigit():
            flash('CPF inválido. Deve conter 11 números.', 'danger')
            return redirect(url_for('cadastro'))

        conn = get_db_connection()
        usuario_existente = conn.execute('SELECT cpf FROM usuarios WHERE cpf = ?', (cpf,)).fetchone()

        if usuario_existente:
            flash('Este CPF já está cadastrado no sistema.', 'danger')
            conn.close()
            return redirect(url_for('cadastro'))
        
        # 3. Se tudo estiver OK, insere no banco
        senha_hash = generate_password_hash(senha)
        
        try:
            conn.execute(
                "INSERT INTO usuarios (cpf, nome, senha_hash, grupo_risco) VALUES (?, ?, ?, ?)",
                (cpf, nome, senha_hash, grupo_risco_str)
            )
            conn.commit()
            flash(f'Usuário {nome} cadastrado com sucesso! Faça o login.', 'success')
        except Exception as e:
            conn.rollback() # Desfaz a operação em caso de erro
            flash(f'Erro ao cadastrar: {e}', 'danger')
        finally:
            conn.close()
            
        return redirect(url_for('login'))

    # Se o método for GET, apenas mostra a página de cadastro
    return render_template('cadastro.html')

@app.route('/home')
@login_required
def home():
    """Tela Principal (Hall / Dashboard)."""
    
    # Dados dos Cards Giratórios
    cards_info = [
        {
            'titulo': 'Saúde do Homem',
            'slug': 'homem',
            'icone': '👨',
            'front_color': '#e3f2fd', # Azul claro
            'texto': 'Realize check-ups anuais. A prevenção contra o câncer de próstata e doenças cardiovasculares começa aos 40 anos.'
        },
        {
            'titulo': 'Saúde da Mulher',
            'slug': 'mulher',
            'icone': '👩',
            'front_color': '#fce4ec', # Rosa claro
            'texto': 'O preventivo e a mamografia são essenciais. Mantenha seus exames em dia para prevenir câncer de colo de útero e mama.'
        },
        {
            'titulo': 'Saúde do Idoso',
            'slug': 'idoso',
            'icone': '👴',
            'front_color': '#fff3e0', # Laranja claro
            'texto': 'Atenção à prevenção de quedas, vacinação contra gripe e controle da pressão arterial. Hidratação é fundamental!'
        },
        {
            'titulo': 'Saúde da Criança',
            'slug': 'crianca',
            'icone': '👶',
            'front_color': '#e8f5e9', # Verde claro
            'texto': 'Mantenha a carteira de vacinação atualizada. O acompanhamento do crescimento e desenvolvimento é vital.'
        },
        {
            'titulo': 'Saúde do Adolescente',
            'slug': 'adolescente',
            'icone': '👱',
            'front_color': '#f3e5f5', # Roxo claro
            'texto': 'Foco na saúde mental, prevenção de ISTs e prática de esportes. É o momento de criar hábitos para a vida toda.'
        }
    ]

    return render_template('home.html', cards_info=cards_info)

@app.route('/saude/<grupo>')
@login_required
def detalhes_saude(grupo):
    # Busca as informações no dicionário
    dados = DETALHES_GRUPOS.get(grupo)
    
    if not dados:
        flash('Página não encontrada.', 'danger')
        return redirect(url_for('home'))
        
    return render_template('detalhes_saude.html', dados=dados)

@app.route('/orientacoes')
@login_required
def orientacoes():
    """Tela de Orientações (Antiga lógica da Home)."""
    grupos = session.get('grupo_risco', [])
    dicas = DICAS_SAUDE['Geral'].copy()
    
    for grupo in grupos:
        if grupo in DICAS_SAUDE:
            dicas.extend(DICAS_SAUDE[grupo])
            
    # Note que agora renderiza 'orientacoes.html'
    return render_template('orientacoes.html', dicas=dicas, grupos_de_risco=grupos)

@app.route('/cronograma')
@login_required
def cronograma():
    conn = get_db_connection()
    especialidade_selecionada = request.args.get('especialidade')

    if especialidade_selecionada:
        # Consulta com ordenação lógica dos dias da semana
        medicos = conn.execute('''
            SELECT * FROM medicos 
            WHERE especialidade = ? 
            ORDER BY CASE dia
                WHEN 'Segunda-feira' THEN 1
                WHEN 'Terça-feira' THEN 2
                WHEN 'Quarta-feira' THEN 3
                WHEN 'Quinta-feira' THEN 4
                WHEN 'Sexta-feira' THEN 5
                ELSE 6
            END, horario ASC
        ''', (especialidade_selecionada,)).fetchall()
        
        conn.close()
        return render_template('cronograma_detalhes.html', 
                               medicos=medicos, 
                               especialidade=especialidade_selecionada)
    
    # Busca todas as especialidades únicas para mostrar no menu inicial
    especialidades = conn.execute('SELECT DISTINCT especialidade FROM medicos').fetchall()
    conn.close()
    return render_template('cronograma.html', especialidades=especialidades)

@app.route('/lembretes')
@login_required
def lembretes():
    """Tela de Lembretes (Usa o main.js e localStorage)."""
    return render_template('lembretes.html')

@app.route('/api/lembretes')
@login_required
def api_get_lembretes():
    """Busca os lembretes do usuário logado no banco."""
    cpf = session['cpf_logado']
    
    conn = get_db_connection()
    lembretes_db = conn.execute(
        'SELECT * FROM lembretes WHERE cpf_usuario = ? ORDER BY horario', (cpf,)
    ).fetchall()
    conn.close()
    
    # Converte os dados do banco para uma lista de dicionários
    lembretes_lista = [dict(row) for row in lembretes_db]
    return jsonify(lembretes_lista)


@app.route('/api/lembretes/add', methods=['POST'])
@login_required
def api_add_lembrete():
    """Adiciona um novo lembrete no banco."""
    cpf = session['cpf_logado']
    dados = request.json # Pega os dados enviados pelo JavaScript
    
    nome = dados['nome']
    horario = dados['horario']
    
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO lembretes (cpf_usuario, nome_remedio, horario) VALUES (?, ?, ?)',
        (cpf, nome, horario)
    )
    conn.commit()
    
    # Retorna o lembrete recém-criado com seu novo ID
    novo_lembrete_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.close()
    
    return jsonify({
        'id': novo_lembrete_id,
        'nome_remedio': nome,
        'horario': horario
    }), 201 # 201 = "Created"


@app.route('/api/lembretes/delete', methods=['POST'])
@login_required
def api_delete_lembrete():
    """Deleta um lembrete do banco."""
    cpf = session['cpf_logado']
    dados = request.json
    lembrete_id = dados['id']
    
    conn = get_db_connection()
    # Garante que o usuário só pode deletar seus próprios lembretes
    conn.execute(
        'DELETE FROM lembretes WHERE id = ? AND cpf_usuario = ?',
        (lembrete_id, cpf)
    )
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Lembrete deletado com sucesso'}), 200

if __name__ == '__main__':
    app.run(debug=True)
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
import sqlite3
import re
from datetime import date, timedelta
from werkzeug.security import check_password_hash, generate_password_hash # Importa o verificador de senha

app = Flask(__name__)
app.config['SECRET_KEY'] = 'uma-chave-secreta-muito-forte'

def cpf_valido(cpf):
    """Valida um CPF pelo algoritmo dos dígitos verificadores."""
    if len(cpf) != 11 or not cpf.isdigit() or cpf == cpf[0] * 11:
        return False

    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = (soma * 10) % 11
    digito1 = resto if resto < 10 else 0
    if digito1 != int(cpf[9]):
        return False

    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = (soma * 10) % 11
    digito2 = resto if resto < 10 else 0
    return digito2 == int(cpf[10])

@app.template_filter('data_br')
def data_br(data_iso):
    """Converte data 'AAAA-MM-DD' para 'DD/MM/AAAA'."""
    try:
        ano, mes, dia = data_iso.split('-')
        return f'{dia}/{mes}/{ano}'
    except (ValueError, AttributeError):
        return data_iso

@app.template_filter('cpf_br')
def cpf_br(cpf):
    """Formata um CPF de 11 dígitos como 'XXX.XXX.XXX-XX'."""
    if cpf and len(cpf) == 11 and cpf.isdigit():
        return f'{cpf[0:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:11]}'
    return cpf

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


CONTATOS_EXTERNOS = [
    {
        'categoria': 'Secretaria Municipal de Saúde',
        'icone': '🏢',
        'unidades': [
            {
                'nome': 'Secretaria Municipal de Saúde',
                'endereco': 'Av. Júlia Freire, S/Nº - Torre',
                'contatos': [
                    {'setor': 'Ouvidoria', 'ramal': '3213-7530 / 3213-7531 / 3213-7948 / 3213-7949'},
                    {'setor': 'Recepção', 'ramal': '3213-7792'},
                    {'setor': 'Serviço Social', 'ramal': '3213-7541'},
                ]
            }
        ]
    },
    {
        'categoria': 'CAPS (Centro de Atenção Psicossocial)',
        'icone': '🧠',
        'unidades': [
            {
                'nome': 'CAPS Cirandar',
                'endereco': 'Rua Gouveia Nobrega, S/Nº - Roger',
                'contatos': [
                    {'setor': 'Recepção', 'ramal': '3213-7614'},
                ]
            },
            {
                'nome': 'CAPS - Caminhar',
                'endereco': 'Rua Paulino Santos Coelho, S/Nº - Cidade Universitária',
                'contatos': [
                    {'setor': 'Recepção', 'ramal': '3213-7615'},
                    {'setor': 'Serviço Social', 'ramal': '3213-7753'},
                    {'setor': 'Direção', 'ramal': '3213-7624'},
                    {'setor': 'Enfermagem', 'ramal': '3213-7752'},
                ]
            },
            {
                'nome': 'CAPS AD - David Capistrano da Costa Filho',
                'endereco': 'Rua Prof° Álvaro Carvalho, S/Nº - Tambauzinho',
                'contatos': [
                    {'setor': 'Recepção', 'ramal': '3213-7616'},
                ]
            },
            {
                'nome': 'CAPS - Gutemberg Botelho',
                'endereco': 'Av. Minas Gerais, Nº 409 - Bairro dos Estados',
                'contatos': [
                    {'setor': 'Recepção', 'ramal': '3213-7617'},
                ]
            },
            {
                'nome': 'CAPS - Unidade de Acolhimento Infanto Juvenil (UAI)',
                'endereco': 'Rua Gouveia Nobrega, S/Nº - Roger',
                'contatos': [
                    {'setor': 'Sala 3 - Equipe Multiprofissional', 'ramal': '3213-7618'},
                ]
            },
        ]
    },
    {
        'categoria': 'Cartão SUS',
        'icone': '💳',
        'unidades': [
            {
                'nome': 'Cartão SUS',
                'endereco': 'Av. Rui Barbosa, S/Nº - Torre',
                'contatos': [
                    {'setor': 'Recepção', 'ramal': '3213-7637'},
                ]
            }
        ]
    },
    {
        'categoria': 'Centro de Doenças Raras',
        'icone': '🧬',
        'unidades': [
            {
                'nome': 'Centro de Doenças Raras',
                'endereco': 'Rua Esmeraldo Gomes Vieira, S/Nº - Bancários',
                'contatos': [
                    {'setor': 'Recepção', 'ramal': '3213-7620'},
                    {'setor': 'Serviço Social', 'ramal': '3213-7784'},
                    {'setor': 'Regulação', 'ramal': '3213-7875'},
                ]
            }
        ]
    },
]

CALENDARIO_VACINAL = {
    'crianca': {
        'titulo': 'Criança (0 a 9 anos)',
        'vacinas': [
            {'nome': 'BCG', 'doses': ['Dose Única']},
            {'nome': 'Hepatite B', 'doses': ['Ao Nascer']},
            {'nome': 'Pentavalente (DTP/Hib/HepB)', 'doses': ['1ª Dose', '2ª Dose', '3ª Dose']},
            {'nome': 'Poliomielite (VIP/VOP)', 'doses': ['1ª Dose', '2ª Dose', '3ª Dose', 'Reforço 1', 'Reforço 2']},
            {'nome': 'Pneumocócica 10V', 'doses': ['1ª Dose', '2ª Dose', 'Reforço']},
            {'nome': 'Rotavírus', 'doses': ['1ª Dose', '2ª Dose']},
            {'nome': 'Meningocócica C', 'doses': ['1ª Dose', '2ª Dose', 'Reforço']},
            {'nome': 'Febre Amarela', 'doses': ['Dose', 'Reforço']},  # 9 meses e reforço aos 4 anos
            {'nome': 'Tríplice Viral (SCR)', 'doses': ['1ª Dose']},  # a 2ª dose vem na Tetraviral
            {'nome': 'Tetraviral (SCRV)', 'doses': ['Dose Única']},  # 15 meses
            {'nome': 'Varicela', 'doses': ['2ª Dose']},  # aos 4 anos; a 1ª dose vem na Tetraviral
            {'nome': 'DTP (Reforço)', 'doses': ['Reforço 1', 'Reforço 2']},
            {'nome': 'Hepatite A', 'doses': ['Dose Única']},
            {'nome': 'Influenza (Gripe)', 'doses': ['Dose Anual']},
        ]
    },
    'adolescente': {
        'titulo': 'Adolescente (10 a 19 anos)',
        'vacinas': [
            {'nome': 'Dupla Adulto (dT)', 'doses': ['Reforço']},
            {'nome': 'HPV', 'doses': ['1ª Dose', '2ª Dose']},
            {'nome': 'Meningocócica ACWY', 'doses': ['Reforço']},
            {'nome': 'Febre Amarela', 'doses': ['Dose Única']},
            {'nome': 'Tríplice Viral (SCR)', 'doses': ['1ª Dose', '2ª Dose']},
            {'nome': 'Hepatite B', 'doses': ['1ª Dose', '2ª Dose', '3ª Dose']},
        ]
    },
    'adulto': {
        'titulo': 'Adulto (20 a 59 anos)',
        'vacinas': [
            {'nome': 'Hepatite B', 'doses': ['1ª Dose', '2ª Dose', '3ª Dose']},
            {'nome': 'Febre Amarela', 'doses': ['Dose Única']},
            {'nome': 'Tríplice Viral (SCR)', 'doses': ['1ª Dose', '2ª Dose']},
            {'nome': 'Dupla Adulto (dT)', 'doses': ['1ª Dose', '2ª Dose', '3ª Dose', 'Reforço']},
            {'nome': 'DTPA (Gestante)', 'doses': ['1ª Dose', '2ª Dose', '3ª Dose', 'Reforço'], 'apenas_sexo': 'Feminino'},
        ]
    },
    'idoso': {
        'titulo': 'Idoso (60 anos ou mais)',
        'vacinas': [
            {'nome': 'Influenza (Gripe)', 'doses': ['Dose Anual']},
            {'nome': 'Pneumocócica 23V', 'doses': ['Dose Única']},
            {'nome': 'Hepatite B', 'doses': ['1ª Dose', '2ª Dose', '3ª Dose']},
            {'nome': 'Dupla Adulto (dT)', 'doses': ['1ª Dose', '2ª Dose', '3ª Dose', 'Reforço']},
            {'nome': 'Covid-19', 'doses': ['Dose Anual']},
            {'nome': 'Herpes Zóster', 'doses': ['1ª Dose', '2ª Dose']},
        ]
    },
}


def calcular_idade(data_nascimento_str):
    """Retorna (anos, meses, dias) de idade a partir de uma data 'AAAA-MM-DD'."""
    nascimento = date.fromisoformat(data_nascimento_str)
    hoje = date.today()

    anos = hoje.year - nascimento.year
    meses = hoje.month - nascimento.month
    dias = hoje.day - nascimento.day

    if dias < 0:
        meses -= 1
        mes_anterior = hoje.month - 1 if hoje.month > 1 else 12
        ano_mes_anterior = hoje.year if hoje.month > 1 else hoje.year - 1
        ultimo_dia_mes_anterior = (date(ano_mes_anterior, mes_anterior % 12 + 1, 1) - timedelta(days=1)).day
        dias += ultimo_dia_mes_anterior

    if meses < 0:
        anos -= 1
        meses += 12

    return anos, meses, dias


def faixa_etaria(anos):
    if anos <= 9:
        return 'crianca'
    elif anos <= 19:
        return 'adolescente'
    elif anos <= 59:
        return 'adulto'
    return 'idoso'


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
        data_nascimento = request.form.get('data_nascimento')
        sexo = request.form.get('sexo')
        cep = re.sub(r'[^0-9]', '', request.form.get('cep', ''))
        rua = request.form.get('rua')
        bairro = request.form.get('bairro')
        estado = request.form.get('estado')
        numero = request.form.get('numero')
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
        if not all([nome, cpf, senha, confirmar_senha, data_nascimento, sexo, cep, rua, bairro, estado, numero]):
            flash('Por favor, preencha todos os campos obrigatórios.', 'danger')
            return redirect(url_for('cadastro'))

        if sexo not in ('Masculino', 'Feminino', 'Transgênero'):
            flash('Sexo inválido.', 'danger')
            return redirect(url_for('cadastro'))

        if len(cep) != 8:
            flash('CEP inválido.', 'danger')
            return redirect(url_for('cadastro'))

        if senha != confirmar_senha:
            flash('As senhas não coincidem. Tente novamente.', 'danger')
            return redirect(url_for('cadastro'))

        if any(char.isdigit() for char in nome):
            flash('O nome não pode conter números.', 'danger')
            return redirect(url_for('cadastro'))

        if not cpf_valido(cpf):
            flash('CPF inválido.', 'danger')
            return redirect(url_for('cadastro'))

        try:
            data_nascimento_valida = date.fromisoformat(data_nascimento)
        except ValueError:
            flash('Data de nascimento inválida.', 'danger')
            return redirect(url_for('cadastro'))

        if data_nascimento_valida > date.today():
            flash('A data de nascimento não pode ser uma data futura.', 'danger')
            return redirect(url_for('cadastro'))

        if data_nascimento_valida < date.today() - timedelta(days=365 * 150):
            flash('A data precisa ser mais recente.', 'danger')
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
                """INSERT INTO usuarios
                   (cpf, nome, senha_hash, grupo_risco, data_nascimento, sexo, cep, rua, bairro, estado, numero)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (cpf, nome, senha_hash, grupo_risco_str, data_nascimento, sexo, cep, rua, bairro, estado, numero)
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
    data_min_nascimento = (date.today() - timedelta(days=365 * 150)).isoformat()
    data_max_nascimento = date.today().isoformat()
    return render_template('cadastro.html', data_min_nascimento=data_min_nascimento, data_max_nascimento=data_max_nascimento)

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

@app.route('/cartao_vacinal')
@login_required
def cartao_vacinal():
    """Cartão vacinal do usuário logado, com a caderneta correspondente à sua faixa etária."""
    cpf = session['cpf_logado']

    conn = get_db_connection()
    usuario = conn.execute('SELECT * FROM usuarios WHERE cpf = ?', (cpf,)).fetchone()
    # Ordenado por data para que, em doses repetidas (ex.: Dose Anual), a mais recente prevaleça
    aplicadas_db = conn.execute(
        'SELECT vacina, dose, data_aplicacao FROM vacinas_aplicadas WHERE cpf_usuario = ? ORDER BY data_aplicacao',
        (cpf,)
    ).fetchall()
    conn.close()

    idade_anos, idade_meses, idade_dias = calcular_idade(usuario['data_nascimento'])
    calendario_base = CALENDARIO_VACINAL[faixa_etaria(idade_anos)]
    vacinas_visiveis = [
        v for v in calendario_base['vacinas']
        if v.get('apenas_sexo') is None or v['apenas_sexo'] == usuario['sexo']
    ]
    calendario = {'titulo': calendario_base['titulo'], 'vacinas': vacinas_visiveis}
    aplicadas = {f"{a['vacina']}|{a['dose']}": a['data_aplicacao'] for a in aplicadas_db}

    # Vacinas registradas que não aparecem no calendário da faixa etária atual (ex.: as da infância de um adulto)
    doses_do_calendario = {f"{v['nome']}|{dose}" for v in vacinas_visiveis for dose in v['doses']}
    outras_vacinas = [dict(a) for a in aplicadas_db if f"{a['vacina']}|{a['dose']}" not in doses_do_calendario]

    return render_template('cartao_vacinal.html', usuario=usuario, calendario=calendario, aplicadas=aplicadas,
                           outras_vacinas=outras_vacinas,
                           idade_anos=idade_anos, idade_meses=idade_meses, idade_dias=idade_dias)

@app.route('/lembretes', methods=['GET', 'POST'])
@login_required
def lembretes():
    cpf = session['cpf_logado'] # Usando a chave correta da sua sessão
    
    if request.method == 'POST':
        # Captura os dados do formulário vistoso
        nome_remedio = request.form.get('nome_remedio')
        data_inicio = request.form.get('data_inicio')
        posologia = request.form.get('posologia')
        prescrito_por = request.form.get('prescrito_por')

        if nome_remedio and data_inicio and posologia and prescrito_por:
            data_limite = date.today() - timedelta(days=365 * 20)
            try:
                data_inicio_valida = date.fromisoformat(data_inicio)
                data_no_passado = data_inicio_valida < data_limite
                data_no_futuro = data_inicio_valida > date.today()
            except ValueError:
                data_no_passado = data_no_futuro = True

            if data_no_passado:
                flash('A data deve ser mais recente.', 'danger')
            elif data_no_futuro:
                flash('A data não pode ser uma data futura.', 'danger')
            elif any(char.isdigit() for char in prescrito_por):
                flash('O campo "Prescrito por" não pode conter números.', 'danger')
            else:
                nome_remedio = nome_remedio.strip()
                nome_remedio = nome_remedio[:1].upper() + nome_remedio[1:]

                conn = get_db_connection()
                conn.execute(
                    'INSERT INTO lembretes (cpf_usuario, nome_remedio, data_inicio, posologia, prescrito_por) VALUES (?, ?, ?, ?, ?)',
                    (cpf, nome_remedio, data_inicio, posologia, prescrito_por))
                conn.commit()
                conn.close()
                flash('Medicamento adicionado!', 'success')
        return redirect(url_for('lembretes'))

    # Listagem dos lembretes
    conn = get_db_connection()
    lembretes_db = conn.execute(
        'SELECT * FROM lembretes WHERE cpf_usuario = ? ORDER BY data_inicio DESC', (cpf,)
    ).fetchall()
    conn.close()

    data_min_tratamento = (date.today() - timedelta(days=365 * 20)).isoformat()
    data_max_tratamento = date.today().isoformat()
    return render_template('lembretes.html', lembretes=lembretes_db,
                            data_min_tratamento=data_min_tratamento, data_max_tratamento=data_max_tratamento)

@app.route('/remover_lembrete/<int:id>', methods=['POST'])
@login_required
def remover_lembrete(id):
    cpf = session['cpf_logado']
    conn = get_db_connection()
    conn.execute('DELETE FROM lembretes WHERE id = ? AND cpf_usuario = ?', (id, cpf))
    conn.commit()
    conn.close()
    return redirect(url_for('lembretes'))

@app.route('/api/lembretes')
@login_required
def api_get_lembretes():
    """Busca os lembretes do usuário logado no banco."""
    cpf = session['cpf_logado']
    
    conn = get_db_connection()
    lembretes_db = conn.execute(
        'SELECT * FROM lembretes WHERE cpf_usuario = ? ORDER BY data_inicio DESC', (cpf,)
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
    data_inicio = dados['data_inicio']
    posologia = dados['posologia']
    prescrito_por = dados['prescrito_por']

    conn = get_db_connection()
    conn.execute(
        'INSERT INTO lembretes (cpf_usuario, nome_remedio, data_inicio, posologia, prescrito_por) VALUES (?, ?, ?, ?, ?)',
        (cpf, nome, data_inicio, posologia, prescrito_por)
    )
    conn.commit()

    # Retorna o lembrete recém-criado com seu novo ID
    novo_lembrete_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.close()

    return jsonify({
        'id': novo_lembrete_id,
        'nome_remedio': nome,
        'data_inicio': data_inicio,
        'posologia': posologia,
        'prescrito_por': prescrito_por
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

@app.route('/contatos')
@login_required
def contatos_externos():
    """Tela de Contatos - Endereços e telefones da rede municipal de saúde."""
    return render_template('contatos.html', contatos=CONTATOS_EXTERNOS)

@app.route('/contato', methods=['GET', 'POST'])
def contato():
    """Página de Contato para feedback dos usuários."""
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        mensagem = request.form.get('mensagem')

        if not nome or not email or not mensagem:
            flash('Por favor, preencha todos os campos.', 'warning')
        else:
            try:
                conn = get_db_connection()
                conn.execute(
                    'INSERT INTO contatos (nome, email, mensagem) VALUES (?, ?, ?)',
                    (nome, email, mensagem)
                )
                conn.commit()
                conn.close()
                flash('Sua mensagem foi enviada com sucesso! Obrigado pelo feedback.', 'success')
                return redirect(url_for('home') if 'cpf_logado' in session else url_for('index'))
            except Exception as e:
                flash(f'Erro ao enviar mensagem: {e}', 'danger')

    return render_template('contato.html')

if __name__ == '__main__':
    app.run(debug=True)
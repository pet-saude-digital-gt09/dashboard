from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
import sqlite3
import re
from werkzeug.security import check_password_hash, generate_password_hash # Importa o verificador de senha

app = Flask(__name__)
app.config['SECRET_KEY'] = 'uma-chave-secreta-muito-forte'

DICAS_SAUDE = {
    'Hipertenso': [
        'Reduza o consumo de sal (sódio) nas refeições.',
        'Pratique atividade física regularmente, como caminhada, por 30 minutos por dia.',
        'Meça sua pressão arterial regularmente e mantenha um registro.'
    ],
    'Diabético': [
        'Monitore seus níveis de glicose no sangue conforme orientação médica.',
        'Prefira alimentos integrais, frutas e vegetais.',
        'Examine seus pés diariamente em busca de pequenos ferimentos.'
    ],
    'Geral': [
        'Beba pelo menos 2 litros de água por dia.',
        'Mantenha uma rotina de sono regular, dormindo de 7 a 8 horas por noite.'
    ]
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
    if 'cpf_logado' in session:
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Tela de Login (Agora usa o banco de dados)."""
    if request.method == 'POST':
        cpf = request.form['cpf']
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
    return redirect(url_for('login'))

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    """Tela de Cadastro de Novo Usuário."""
    
    if request.method == 'POST':
        # 1. Coletar dados do formulário
        nome = request.form['nome']
        cpf = request.form['cpf']
        senha = request.form['senha']
        confirmar_senha = request.form['confirmar_senha']
        # .strip() remove espaços em branco antes e depois
        grupo_risco = request.form['grupo_risco'].strip() 

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
                (cpf, nome, senha_hash, grupo_risco)
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
    """Tela de Orientação (Lógica de dicas permanece a mesma)."""
    grupos = session.get('grupo_risco', [])
    dicas = DICAS_SAUDE['Geral'].copy()
    
    for grupo in grupos:
        if grupo in DICAS_SAUDE:
            dicas.extend(DICAS_SAUDE[grupo])
            
    return render_template('home.html', dicas=dicas, grupos_de_risco=grupos)

@app.route('/cronograma')
@login_required
def cronograma():
    """Tela de Cronograma (Agora usa o banco de dados)."""
    conn = get_db_connection()
    # Busca todos os médicos no banco
    medicos_db = conn.execute('SELECT * FROM medicos ORDER BY dia, horario').fetchall()
    conn.close()
    
    # Envia os dados do banco para o template
    return render_template('cronograma.html', medicos=medicos_db)

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
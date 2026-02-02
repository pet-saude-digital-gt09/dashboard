# init_db.py
import sqlite3
from werkzeug.security import generate_password_hash

# Conecta ao banco (vai criar o arquivo saude.db se não existir)
conn = sqlite3.connect('saude.db')
cursor = conn.cursor()

print("Criando tabelas...")

# --- Tabela de Usuários ---
# (Vamos guardar a senha criptografada, não '123')
cursor.execute('''
CREATE TABLE IF NOT EXISTS usuarios (
    cpf TEXT PRIMARY KEY,
    nome TEXT NOT NULL,
    senha_hash TEXT NOT NULL,
    grupo_risco TEXT
)
''')

# --- Tabela de Médicos ---
cursor.execute(''' 
CREATE TABLE IF NOT EXISTS medicos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    medico TEXT NOT NULL,
    especialidade TEXT NOT NULL,
    dia TEXT NOT NULL,
    horario TEXT NOT NULL
)
''')

print("Criando tabela de lembretes...")

# --- Tabela de Lembretes ---
# 'cpf_usuario' é a chave estrangeira que liga o lembrete ao usuário
cursor.execute('''
CREATE TABLE IF NOT EXISTS lembretes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cpf_usuario TEXT NOT NULL,
    nome_remedio TEXT NOT NULL,
    horario TEXT NOT NULL,
    FOREIGN KEY (cpf_usuario) REFERENCES usuarios (cpf)
)
''')

print("Tabelas criadas. Inserindo dados iniciais...")

# --- Inserindo Usuários de Exemplo ---
# Criptografa a senha '123'
senha_hashed_admin = generate_password_hash('123')
senha_hashed_paciente = generate_password_hash('123')

try:
    cursor.execute(
        "INSERT INTO usuarios (cpf, nome, senha_hash, grupo_risco) VALUES (?, ?, ?, ?)",
        ('71192887417', 'Usuário Admin', senha_hashed_admin, 'Hipertenso')
    )
    cursor.execute(
        "INSERT INTO usuarios (cpf, nome, senha_hash, grupo_risco) VALUES (?, ?, ?, ?)",
        ('12345678900', 'Paciente Diabético', senha_hashed_paciente, 'Diabético')
    )
except sqlite3.IntegrityError:
    print("Usuários de exemplo já existem.")


# --- Inserindo Médicos de Exemplo ---
try:
    medicos_iniciais = [
        ('Dr. Ana Silva', 'Clínico Geral', 'Segunda-feira', '08:00 - 12:00'),
        ('Dr. Bruno Costa', 'Cardiologia', 'Terça-feira', '13:00 - 17:00'),
        ('Dra. Carla Dias', 'Endocrinologia', 'Quarta-feira', '09:00 - 13:00'),
        ('Dr. Ana Silva', 'Clínico Geral', 'Sexta-feira', '08:00 - 12:00'),
    ]
    cursor.executemany(
        "INSERT INTO medicos (medico, especialidade, dia, horario) VALUES (?, ?, ?, ?)",
        medicos_iniciais
    )
except sqlite3.IntegrityError:
     print("Dados de médicos já existem.")


# Salva as mudanças e fecha a conexão
conn.commit()
conn.close()

print("Banco de dados 'saude.db' inicializado com sucesso!")
# init_db.py
import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect('saude.db')
cursor = conn.cursor()

print("Limpando dados antigos e recriando tabelas...")
# Apagamos as tabelas para garantir que os nomes das colunas e dados antigos sumam
cursor.execute('DROP TABLE IF EXISTS medicos')
cursor.execute('DROP TABLE IF EXISTS usuarios')
cursor.execute('DROP TABLE IF EXISTS lembretes')
cursor.execute('DROP TABLE IF EXISTS contatos') # Nova tabela

# --- Tabela de Usuários ---
cursor.execute('''
CREATE TABLE usuarios (
    cpf TEXT PRIMARY KEY,
    nome TEXT NOT NULL,
    senha_hash TEXT NOT NULL,
    grupo_risco TEXT
)
''')

# --- Tabela de Médicos (Ajustada para os novos dados) ---
# Usaremos 'especialidade' para filtrar (Médico, Odonto, Enfermagem) 
# e 'medico' para descrever o serviço (Demanda Espontânea, etc)
cursor.execute(''' 
CREATE TABLE medicos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    medico TEXT NOT NULL,
    especialidade TEXT NOT NULL,
    dia TEXT NOT NULL,
    horario TEXT NOT NULL
)
''')

# --- Tabela de Lembretes ---
cursor.execute('''
CREATE TABLE lembretes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cpf_usuario TEXT NOT NULL,
    nome_remedio TEXT NOT NULL,
    horario TEXT NOT NULL,
    FOREIGN KEY (cpf_usuario) REFERENCES usuarios (cpf)
)
''')

# --- Nova Tabela de Contatos (Feedback) ---
cursor.execute('''
CREATE TABLE contatos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT NOT NULL,
    mensagem TEXT NOT NULL,
    data_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# --- Inserindo Usuários ---
senha_hashed = generate_password_hash('123')
cursor.execute("INSERT INTO usuarios VALUES (?, ?, ?, ?)", 
               ('71192887417', 'Usuário Admin', senha_hashed, 'Hipertenso'))

# --- Inserindo Dados Reais da USF TITO SILVA (Do PDF) ---
# Formato: (Serviço, Categoria/Especialidade, Dia, Horário)
dados_finais = [
    # ATENDIMENTO MÉDICO
    ('Demanda Espontânea', 'Atendimento Médico', 'Segunda-feira', '07h / 12h'),
    ('Pré-Natal / Distrito V', 'Atendimento Médico', 'Terça-feira', '07h / 12h'),
    ('Hipertenso e Diabético / Estudo', 'Atendimento Médico', 'Quarta-feira', '07h / 12h'),
    ('Demanda Espontânea / Visita', 'Atendimento Médico', 'Quinta-feira', '07h / 12h'),
    ('Demanda Espontânea / Equipe', 'Atendimento Médico', 'Sexta-feira', '07h / 12h'),
    
    # ATENDIMENTO ODONTOLÓGICO
    ('Demanda Espontânea', 'Atendimento Odontológico', 'Segunda-feira', '07h / 12h'),
    ('Pré-Natal / Visita', 'Atendimento Odontológico', 'Terça-feira', '07h / 12h'),
    ('PSE / Demanda Espontânea', 'Atendimento Odontológico', 'Quarta-feira', '07h / 12h'),
    ('Demanda Espontânea / Estudo', 'Atendimento Odontológico', 'Quinta-feira', '07h / 12h'),
    ('Demanda Espontânea / Equipe', 'Atendimento Odontológico', 'Sexta-feira', '07h / 12h'),
    
    # ATENDIMENTO ENFERMAGEM
    ('Hipertenso e Diabético / Visita', 'Atendimento Enfermagem', 'Segunda-feira', '07h / 12h'),
    ('Pré-Natal / Citológico', 'Atendimento Enfermagem', 'Terça-feira', '07h / 12h'),
    ('Puericultura / Citológico', 'Atendimento Enfermagem', 'Quarta-feira', '07h / 12h'),
    ('Puericultura / Visita', 'Atendimento Enfermagem', 'Quinta-feira', '07h / 12h'),
    ('Demanda Espontânea / Equipe', 'Atendimento Enfermagem', 'Sexta-feira', '07h / 12h')
]

cursor.executemany(
    "INSERT INTO medicos (medico, especialidade, dia, horario) VALUES (?, ?, ?, ?)",
    dados_finais
)

conn.commit()
conn.close()
print("Sucesso! Banco de dados atualizado com as informações da USF Tito Silva.")
import streamlit as st
from datetime import date
from utils import is_cpf_valido, calcular_idade_e_faixa_etaria

# --- Configurações Iniciais ---
st.set_page_config(
    page_title="Dashboard PET-Saúde",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.sidebar.title("🏥 PET Saúde - GT09")
st.sidebar.markdown("Gerencie seu histórico e vacinas.")

st.markdown("""
<style>
    /* ... (Seu CSS aqui) ... */
</style>
""", unsafe_allow_html=True)


# --- Inicialização do Estado da Sessão ---
if 'consultas' not in st.session_state:
    st.session_state['consultas'] = {}

# Controle de Login e Navegação
if 'usuarios' not in st.session_state:
    # DADO DE EXEMPLO (Atualizado com dados de paciente)
    admin_cpf = '71192887417'
    admin_nasc = date(2004, 5, 31)
    admin_idade, admin_faixa = calcular_idade_e_faixa_etaria(admin_nasc)
    
    st.session_state['usuarios'] = {
        admin_cpf: {
            'nome': 'Usuário Admin', 
            'senha': '123',
            'nascimento': admin_nasc,
            'idade': admin_idade,
            'faixa_etaria': admin_faixa,
            'cidade': 'Exemplo',
            'vacinas_tomadas': []
        }
    }
    # Inicializa consulta para o admin
    st.session_state['consultas'][admin_cpf] = []

if 'status_login' not in st.session_state:
    st.session_state['status_login'] = False
if 'pagina_atual' not in st.session_state:
    st.session_state['pagina_atual'] = 'login'


# --- FUNÇÕES DE TELA (Login e Cadastro de Usuário/Paciente) ---

def tela_login():
    """Tela principal de Login (CPF e Senha)."""
    
    st.header(" Login de Acesso")

    with st.form("form_login"):
        cpf_input = st.text_input("CPF (Login)", max_chars=11).strip()
        senha = st.text_input("Senha", type="password").strip()
        
        col_login, col_cadastro = st.columns([1, 1])
        
        login_btn = col_login.form_submit_button("Entrar")
        cadastro_btn = col_cadastro.form_submit_button("Novo Cadastro")

        if login_btn:
            if not cpf_input or not senha:
                st.error("Preencha o CPF e a senha.")
                return

            if cpf_input in st.session_state['usuarios']:
                usuario = st.session_state['usuarios'][cpf_input]
                
                if usuario['senha'] == senha:
                    st.session_state['status_login'] = True
                    st.session_state['cpf_logado'] = cpf_input
                    st.session_state['nome_usuario'] = usuario['nome']
                    st.session_state['pagina_atual'] = 'login' 
                    st.success(f"Login efetuado com sucesso! Bem-vindo(a), {usuario['nome']}.")
                    st.rerun() 
                else:
                    st.error("Senha incorreta.")
            else:
                st.error("CPF não encontrado ou não cadastrado.")
                
        if cadastro_btn:
            st.session_state['pagina_atual'] = 'cadastro'
            st.rerun()

def tela_cadastro_usuario():
    """Tela para criar um novo USUÁRIO/PACIENTE."""
    
    st.header("👤 Novo Cadastro")
    st.caption("Crie sua conta para acessar o sistema.")
    
    data_padrao = date.today().replace(year=date.today().year - 100)

    with st.form("form_cadastro_usuario"):
        st.subheader("Dados de Acesso")
        nome = st.text_input("Nome Completo").strip().title()
        cpf = st.text_input("CPF (apenas números)", max_chars=11).strip()
        senha = st.text_input("Defina uma Senha", type="password").strip()
        confirmar_senha = st.text_input("Confirme a Senha", type="password").strip()
        
        st.subheader("Dados do Paciente")
        data_nascimento = st.date_input(
            "Data de Nascimento", value=data_padrao, max_value=date.today(), format='DD/MM/YYYY'
            )
        cidade = st.text_input("Cidade de Residência").strip().title()
        
        col_submit, col_back = st.columns([1, 1])
        submit_btn = col_submit.form_submit_button("Cadastrar Usuário")
        voltar_btn = col_back.form_submit_button("Voltar para Login")

        if submit_btn:
            # Validações
            if not all([nome, cpf, senha, confirmar_senha, data_nascimento, cidade]):
                st.error("Por favor, preencha todos os campos.")
            elif not is_cpf_valido(cpf):
                st.error("CPF inválido. Verifique os dígitos.")
            elif senha != confirmar_senha:
                st.error("As senhas não coincidem.")
            elif data_nascimento == data_padrao:
                 st.error("Por favor, informe sua Data de Nascimento correta.")
            elif cpf in st.session_state['usuarios']:
                st.error("Este CPF (usuário) já está cadastrado no sistema.")
            else:
                # Calcula idade e faixa
                idade, faixa_etaria = calcular_idade_e_faixa_etaria(data_nascimento)
                
                # Adiciona novo usuário com todos os dados
                st.session_state['usuarios'][cpf] = {
                    'nome': nome,
                    'senha': senha,
                    'nascimento': data_nascimento,
                    'idade': idade,
                    'faixa_etaria': faixa_etaria,
                    'cidade': cidade,
                    'vacinas_tomadas': [] # Inicializa lista de vacinas
                }
                # Inicializa lista de consultas
                st.session_state['consultas'][cpf] = []
                
                st.success(f"Usuário {nome} cadastrado com sucesso!")
                st.info("Clique em 'Voltar para Login' para acessar o sistema.")
        
        if voltar_btn:
            st.session_state['pagina_atual'] = 'login'
            st.rerun()


# --- LÓGICA PRINCIPAL (ROTEADOR) ---
if st.session_state['status_login'] == False:
    if st.session_state['pagina_atual'] == 'login':
        tela_login()
    elif st.session_state['pagina_atual'] == 'cadastro':
        tela_cadastro_usuario()
else:
    # SE ESTIVER LOGADO
    st.sidebar.success(f"Logado como: {st.session_state.get('nome_usuario', 'Usuário')}")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state['status_login'] = False
        st.session_state['cpf_logado'] = None
        st.session_state['nome_usuario'] = None
        st.session_state['pagina_atual'] = 'login'
        st.rerun()

    # Página principal (home) pós-login
    st.header(f"Bem-vindo(a) ao PET-Saúde, {st.session_state.get('nome_usuario', 'Usuário')}!")
    st.markdown("Utilize o menu ao lado para navegar e gerenciar seu histórico de saúde.")
import streamlit as st
import pandas as pd
from utils import VACINAS_POR_GRUPO

st.set_page_config(
    page_title="Dashboard PET-Saúde",
    layout="wide",
    initial_sidebar_state="expanded"
)

def tela_visualizar_historico():
    """Interface para visualizar histórico e vacinas do usuário logado."""
    st.header("📋 Meu Histórico e Vacinação")
    
    selected_cpf = st.session_state.get('cpf_logado')
    
    if not selected_cpf or selected_cpf not in st.session_state['usuarios']:
        st.error("Faça login para ver seu histórico.")
        return
        
    # Busca os dados do usuário/paciente
    paciente = st.session_state['usuarios'][selected_cpf]

    st.subheader(f"Dados de **{paciente['nome']}**")
    st.info(f"Idade: **{paciente['idade']}** anos | Faixa Etária: **{paciente['faixa_etaria']}**")
    
    st.markdown("---")
    
    # Criação das abas
    tab_atendimentos, tab_vacinacao = st.tabs(["Histórico de Consultas", "Cartão de Vacina"])
    
    # Conteúdo da Aba 1: Atendimentos/Consultas
    with tab_atendimentos:
        st.subheader("📜 Histórico de Consultas")
        historico = st.session_state['consultas'].get(selected_cpf, [])

        if historico:
            df_consultas = pd.DataFrame(historico)
            df_consultas['data'] = pd.to_datetime(df_consultas['data']) 
            df_consultas['data'] = df_consultas['data'].dt.strftime('%d/%m/%Y')
            df_consultas = df_consultas.rename(columns={'data': 'Data', 'especialidade': 'Especialidade', 'observacoes': 'Observações'})
            df_consultas = df_consultas.sort_values(by='Data', ascending=False)
            
            st.dataframe(df_consultas, hide_index=True, use_container_width=True)
        else:
            st.info("Nenhuma consulta/atendimento registrado.")

    # Conteúdo da Aba 2: Cartão de Vacina
    with tab_vacinacao:
        st.subheader("💉 Status de Vacinação")
        faixa = paciente['faixa_etaria']
        vacinas_relevantes = VACINAS_POR_GRUPO.get(faixa, [])
        vacinas_tomadas_set = set(paciente['vacinas_tomadas'])
        
        dados_vacinas = []
        for vacina in vacinas_relevantes:
            status = "✅ APLICADA" if vacina in vacinas_tomadas_set else "❌ PENDENTE"
            dados_vacinas.append({"Vacina": vacina, "Status": status})

        if dados_vacinas:
            df_vacinas = pd.DataFrame(dados_vacinas)
            st.dataframe(df_vacinas, hide_index=True, use_container_width=True)
        else:
            st.write(f"Nenhuma vacina específica listada para a faixa '{faixa}'.")

# Verifica se o usuário está logado
if st.session_state.get('status_login', False):
    tela_visualizar_historico()
else:
    st.error("Faça login para acessar esta página.")
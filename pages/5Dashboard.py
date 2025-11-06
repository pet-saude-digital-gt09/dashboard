import streamlit as st
from utils import VACINAS_POR_GRUPO
import pandas as pd

st.set_page_config(
    page_title="Dashboard PET-Saúde",
    layout="wide",
    initial_sidebar_state="expanded"
)

def tela_dashboard():
    """
    Dashboard de Resumo Individual do Paciente (Usuário Logado).
    Apresenta métricas e status de saúde do paciente selecionado.
    """
    st.header("📋 Meu Resumo de Saúde")
    st.caption("Visualização rápida de métricas e status de consultas/vacinas.")
    st.markdown("---")

    # Pega o CPF do usuário logado
    selected_cpf = st.session_state.get('cpf_logado')

    if not selected_cpf or selected_cpf not in st.session_state['usuarios']:
        st.error("Não foi possível carregar os dados do usuário. Por favor, faça login novamente.")
        return
        
    # Busca os dados do usuário/paciente
    paciente = st.session_state['usuarios'][selected_cpf]
    historico = st.session_state['consultas'].get(selected_cpf, [])
    faixa = paciente['faixa_etaria']
    vacinas_relevantes = VACINAS_POR_GRUPO.get(faixa, [])
    vacinas_tomadas_set = set(paciente['vacinas_tomadas'])

    st.subheader(f"Resumo de **{paciente['nome']}**")
    st.info(f"Idade: **{paciente['idade']}** anos | Faixa Etária: **{paciente['faixa_etaria']}** | Cidade: **{paciente['cidade']}**")
    st.markdown("---")

    # 1. Indicadores Chave (Metrics)
    total_consultas = len(historico)
    vacinas_pendentes = len(vacinas_relevantes) - len([v for v in vacinas_relevantes if v in vacinas_tomadas_set])
    vacinas_aplicadas = len([v for v in vacinas_relevantes if v in vacinas_tomadas_set])
    
    col1, col2, col3 = st.columns(3)

    col1.metric("Consultas Registradas", total_consultas)
    col2.metric("Vacinas Aplicadas (Relevantes)", vacinas_aplicadas)
    col3.metric("Vacinas Pendentes (Relevantes)", vacinas_pendentes)
    
    st.markdown("---")

    # 2. Gráficos de Distribuição
    
    # 2.1. Gráfico de Distribuição de Vacinas (Aplicadas vs. Pendentes)
    st.subheader("Minha Cobertura Vacinal")
    
    dados_cobertura = pd.DataFrame({
        'Status': ['Aplicadas', 'Pendentes'],
        'Contagem': [vacinas_aplicadas, vacinas_pendentes]
    })
    
    if vacinas_aplicadas > 0 or vacinas_pendentes > 0:
        st.bar_chart(
            dados_cobertura,
            x='Status',
            y='Contagem',
            color='Status'
        )
    else:
        st.info("Nenhuma vacina relevante para esta faixa etária.")

    st.markdown("---")
    
    # 2.2. Resumo de Consultas Recentes
    st.subheader("Consultas por Especialidade")
    
    if historico:
        df_especialidades = pd.DataFrame(historico)['especialidade'].value_counts().reset_index()
        df_especialidades.columns = ['Especialidade', 'Contagem']
        
        st.bar_chart(
            df_especialidades,
            x='Especialidade',
            y='Contagem'
        )
        
        st.caption("Últimas 5 Consultas Detalhadas:")
        df_consultas = pd.DataFrame(historico)
        df_consultas['data'] = pd.to_datetime(df_consultas['data']) 
        df_consultas['data'] = df_consultas['data'].dt.strftime('%d/%m/%Y')
        df_consultas = df_consultas.rename(columns={'data': 'Data', 'especialidade': 'Especialidade', 'observacoes': 'Observações'})
        df_consultas = df_consultas.sort_values(by='Data', ascending=False)
        
        st.dataframe(df_consultas.head(5), hide_index=True, use_container_width=True)
    else:
        st.info("Nenhuma consulta registrada para exibir a distribuição por especialidade.")

    st.markdown("---")

    # 3. Resumo do Status Vacinal (Expander)
    st.subheader("Status Detalhado da Vacinação")
    
    if vacinas_relevantes:
        pendentes_list = [v for v in vacinas_relevantes if v not in vacinas_tomadas_set]
        
        if pendentes_list:
            st.warning(f"Atenção: Existem {vacinas_pendentes} vacinas pendentes para sua faixa etária ({faixa}).")
            
            with st.expander("Ver Vacinas Pendentes"):
                for v in pendentes_list:
                    st.markdown(f"- ❌ {v}")
        else:
            st.success(f"Excelente! Todas as {len(vacinas_relevantes)} vacinas relevantes para sua faixa ({faixa}) estão registradas como aplicadas.")

# Verifica se o usuário está logado para mostrar a tela
if st.session_state.get('status_login', False):
    tela_dashboard()
else:
    st.error("Faça login para acessar esta página.")
    # (Opcional) Redirecionar para o login
    # st.switch_page("login.py")
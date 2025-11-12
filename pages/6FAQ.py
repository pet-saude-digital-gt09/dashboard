import streamlit as st

st.set_page_config(
    page_title="Dashboard PET-Saúde",
    layout="wide",
    initial_sidebar_state="expanded"
)


def tela_faq():
    """
    Página de Dúvidas Frequentes (FAQ) sobre o Sistema e as Regras de Saúde.
    """
    st.header("❓ Dúvidas Frequentes (FAQ)")
    st.caption("Encontre aqui respostas para as questões mais comuns sobre o uso do sistema e a lógica de saúde.")
    st.markdown("---")

    # ----------------------------------------
    # SEÇÃO 1: SOBRE O SISTEMA E CADASTRO
    # ----------------------------------------
    st.subheader("1. Uso do Sistema")

    with st.expander("Como a idade e a faixa etária são calculadas?"):
        st.markdown(
            """
            A idade é calculada automaticamente com base na Data de Nascimento informada e a data de hoje. 
            A faixa etária é determinada com base na idade, conforme as diretrizes do Programa de Saúde:
            * **Recém-Nascido:** 0 a 1 ano
            * **Criança:** 2 a 9 anos
            * **Adolescentes e Jovens:** 10 a 24 anos
            * **Adulto:** 25 a 59 anos
            * **Idoso:** 60 anos ou mais
            """
        )

    with st.expander("Por que preciso informar a Cidade de Residência?"):
        st.markdown(
            """
            A Cidade de Residência é utilizada exclusivamente para fins de **gestão e planejamento (Dashboard)**. 
            Ao agregar os dados por cidade, a Unidade de Saúde pode identificar áreas com maior demanda 
            e otimizar a distribuição de recursos, mantendo a conformidade com a LGPD.
            """
        )

    with st.expander("O que devo fazer se o paciente estiver em uma faixa etária de transição?"):
        st.markdown(
            """
            O sistema faz uma classificação estrita. Se o paciente acabou de completar a idade de transição (ex: 10 anos, passando de Criança para Adolescente/Jovem), o sistema exibirá o calendário da nova faixa. O profissional deve sempre verificar se todas as doses da faixa etária anterior foram concluídas.
            """
        )
        
    st.markdown("---")

    # ----------------------------------------
    # SEÇÃO 2: SOBRE O CARTÃO DE VACINA
    # ----------------------------------------
    st.subheader("2. Vacinação")

    with st.expander("De onde vêm as vacinas sugeridas no Cartão de Vacina?"):
        st.markdown(
            """
            As vacinas sugeridas são baseadas nos esquemas vacinais do Calendário Vacinal do **Ministério da Saúde** e são filtradas pela faixa etária do paciente. Elas representam as vacinas que são tipicamente 
            necessárias para aquele grupo etário.
            """
        )

    with st.expander("O status [PENDENTE] significa que a vacina está atrasada?"):
        st.markdown(
            """
            O status **[PENDENTE]** significa apenas que a vacina é **relevante para a faixa etária do paciente e ainda não foi marcada como aplicada no sistema**. 
            Para saber se uma vacina está **atrasada**, o profissional de saúde deve cruzar esta informação 
            com a idade atual do paciente e o calendário oficial de doses (ex: "1ª dose aos 2 meses").
            """
        )

    with st.expander("Por que o nome da vacina aparece com detalhes da dose (ex: 'Penta - 2 meses')?"):
        st.markdown(
            """
            O sistema lista a dose específica (ex: 1ª, 2ª, reforço) para que o registro de vacinação seja o mais detalhado possível, auxiliando na conferência do calendário. Se a vacina for marcada como tomada, aquela dose específica será marcada como concluída.
            """
        )

    st.subheader("3. LGPD")

    with st.expander("Por que não vejo nomes ou CPFs no Dashboard?"):
        st.markdown(
            """
            Em cumprimento à **Lei Geral de Proteção de Dados (LGPD)**, o Dashboard exibe apenas dados **agregados e anonimizados** (como contagem de pacientes por cidade ou especialidade). Isso protege a privacidade de todos os pacientes.
            """
        )

tela_faq()
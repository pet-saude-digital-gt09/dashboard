# 🏥 Saúde em Dia - Sistema de Apoio ao Paciente

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python">
  <img alt="Flask" src="https://img.shields.io/badge/Flask-2.x-black?style=for-the-badge&logo=flask">
  <img alt="License" src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge">
</p>

> Aplicação web moderna para apoio ao paciente, focada em fornecer ferramentas essenciais de saúde, como orientações personalizadas, agendamentos e lembretes de medicação.

---

## Tabela de Conteúdos

* [✨ Funcionalidades](#-funcionalidades)
* [📸 Screenshots](#-screenshots)
* [💻 Tech Stack](#-tech-stack)
* [🚀 Começando](#-começando)
* [🗃️ Visualizando o Banco de Dados](#-visualizando-o-banco-de-dados)
* [📄 Licença](#-licença)

---

## ✨ Funcionalidades

* **🔐 Autenticação Segura:** Sistema de Login e Cadastro de pacientes com validação de CPF e senhas criptografadas.
* **💡 Orientação Personalizada:** Exibição de dicas de saúde com base no grupo de risco cadastrado pelo paciente (ex: Hipertenso, Diabético).
* **🗓️ Cronograma Médico:** Visualização clara da disponibilidade e horários dos profissionais de saúde na unidade.
* **⏰ Lembretes de Medicação:** Ferramenta para que o paciente cadastre e gerencie seus próprios lembretes de remédios (salvos por usuário no banco de dados).

---

## 📸 Screenshots

<table align="center">
  <tr>
    <td align="center"><strong>Tela de Login</strong></td>
    <td align="center"><strong>Tela de Orientação (Home)</strong></td>
  </tr>
  <tr>
    <td><img src="URL_DO_SCREENSHOT_LOGIN" width="400" alt="Screenshot da Tela de Login"></td>
    <td><img src="URL_DO_SCREENSHOT_HOME" width="400" alt="Screenshot da Tela de Orientação"></td>
  </tr>
  <tr>
    <td align="center"><strong>Cronograma Médico</strong></td>
    <td align="center"><strong>Lembretes de Medicação</strong></td>
  </tr>
  <tr>
    <td><img src="URL_DO_SCREENSHOT_CRONOGRAMA" width="400" alt="Screenshot do Cronograma Médico"></td>
    <td><img src="URL_DO_SCREENSHOT_LEMBRETES" width="400" alt="Screenshot dos Lembretes de Medicação"></td>
  </tr>
</table>

---

## 💻 Tech Stack

A tabela abaixo lista as principais tecnologias usadas no projeto:

| Categoria | Tecnologia |
| :--- | :--- |
| **Backend** | Python, Flask |
| **Frontend** | HTML, CSS, JavaScript |
| **Banco de Dados** | SQLite3 (nativo do Python) |
| **Ambiente** | `venv` (Gerenciamento de pacotes) |
| **Segurança** | Werkzeug (Hashing de senhas) |

---

## 🚀 Começando

Siga estas instruções para configurar e executar o projeto em seu ambiente local.

### Pré-requisitos

* Python 3.10 ou superior
* `git` (para clonar o projeto)

### Instalação

**1. Clone o repositório:**
```bash
git clone https://github.com/rhonnyesoaress/petsaude
cd petsaude

2. Crie e ative o ambiente virtual (venv):

    Isso isola as dependências do projeto e evita conflitos.

    No Windows:

    - python -m venv venv
    - .\venv\Scripts\activate

    No macOS ou Linux:

    - python3 -m venv venv
    - source venv/bin/activate

3. Instale as bibliotecas necessárias:

    O projeto é leve e requer apenas duas bibliotecas principais.

    - pip install Flask Werkzeug

    (O sqlite3, usado para o banco de dados, já vem com o Python).

4. Inicialize o Banco de Dados:

    Este passo deve ser executado apenas uma vez (ou sempre que o init_db.py for modificado).

    - python init_db.py

    Isso criará o arquivo saude.db com todas as tabelas (usuarios, medicos, lembretes).

5. Execute a Aplicação:


    - flask run OU python app.py

🗃️ Visualizando o Banco de Dados

Todos os dados são salvos no arquivo saude.db. A melhor forma de visualizá-los é usando uma extensão no VS Code.

Como visualizar: Extensão do VS Code (Recomendado)

    No VS Code, vá até a aba "Extensões" (Ctrl+Shift+X).

    Procure e instale a extensão "SQLite" (criada por alexcvzz).

    Se você usa Linux: Pode ser necessário instalar o sqlite3 no seu sistema com sudo apt install sqlite3.

    Reinicie o VS Code.

    Clique com o botão direito no arquivo saude.db no explorador de arquivos.

    Selecione "Open Database".

    Um novo painel "SQLITE EXPLORER" aparecerá na sua barra lateral, permitindo que você navegue e consulte as tabelas.
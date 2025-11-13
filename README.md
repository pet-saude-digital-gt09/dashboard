PET-Saúde - Sistema de Apoio ao Paciente

Este é um sistema web de apoio ao paciente, desenvolvido com Flask, focado em fornecer ferramentas diretas para o gerenciamento da saúde, como orientações personalizadas, cronogramas médicos e lembretes de medicação.

✨ Funcionalidades

    Autenticação: Sistema de login e cadastro de pacientes (com validação de CPF).

    Orientações de Saúde: Exibe dicas de saúde personalizadas com base no grupo de risco do paciente (ex: Hipertenso, Diabético).

    Cronograma Médico: Apresenta a disponibilidade e os horários dos médicos na unidade de saúde.

    Lembretes de Medicação: Permite ao paciente cadastrar e gerenciar seus próprios lembretes de remédios, que são salvos de forma segura no banco de dados e vinculados à sua conta.

🚀 Como Configurar e Executar

Siga estas instruções para configurar e executar o projeto em seu ambiente local.

1. Pré-requisitos

    Python 3.10+

    git (para clonar o repositório)

2. Configuração do Ambiente Virtual (Venv)

Primeiro, clone o repositório e acesse a pasta:
Bash

git clone https://github.com/rhonnyesoaress/petsaude
cd petsaude

Recomendamos o uso de um ambiente virtual (venv) para isolar as dependências do projeto.

No Windows:
Bash

# Criar o ambiente
python -m venv venv

# Ativar o ambiente
.\venv\Scripts\activate

No macOS ou Linux:
Bash

# Criar o ambiente
python3 -m venv venv

# Ativar o ambiente
source venv/bin/activate

3. Instalação das Bibliotecas

Com o venv ativado, instale as bibliotecas necessárias que estão listadas no requirements.txt. Este projeto utiliza apenas duas dependências principais:
Bash

pip install Flask Werkzeug

    Flask: O micro-framework web usado para construir a aplicação.

    Werkzeug: Usado pelo Flask para criptografar e verificar as senhas dos usuários.

(O sqlite3, usado para o banco de dados, já faz parte da biblioteca padrão do Python).

▶️ Como Executar a Aplicação

Com o ambiente configurado, siga estes dois passos:

1. Inicializar o Banco de Dados

Antes de executar a aplicação pela primeira vez, você precisa criar o banco de dados e as tabelas. Execute o script init_db.py uma única vez:
Bash

python init_db.py

Isso criará o arquivo saude.db na pasta do projeto, contendo as tabelas usuarios, medicos e lembretes.

2. Iniciar o Servidor Flask

Agora, inicie o servidor de desenvolvimento:
Bash

flask run

O servidor estará ativo e a aplicação pode ser acessada no seu navegador no endereço: http://127.0.0.1:5000

🗃️ Como Visualizar o Banco de Dados

Os dados (usuários, médicos, lembretes) são salvos no arquivo saude.db, que é um banco de dados SQLite. Você não pode abri-lo com um editor de texto.

A melhor forma de visualizar ou editar os dados é usando uma ferramenta de banco de dados.

Como abrir: Extensão do VS Code (Recomendado)

    No VS Code, vá até a aba "Extensões".

    Procure e instale a extensão "SQLite" (criada por alexcvzz).

    Importante (se você usa Linux): Esta extensão pode exigir que o sqlite3 esteja instalado no seu sistema. Se necessário, rode: sudo apt install sqlite3.

    Após a instalação, clique com o botão direito no arquivo saude.db no explorador de arquivos.

    Selecione "Open Database".

    Um novo painel "SQLITE EXPLORER" aparecerá na sua barra lateral, permitindo que você navegue pelas tabelas e veja todos os dados.
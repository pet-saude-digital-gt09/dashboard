// Espera o HTML da página ser totalmente carregado
document.addEventListener('DOMContentLoaded', function() {
    
    const formLembrete = document.getElementById('form-lembrete');
    const listaLembretes = document.getElementById('lista-lembretes');
    
    // Se não estamos na página de lembretes, não faz nada.
    if (!formLembrete) {
        return;
    }

    const remedioNomeInput = document.getElementById('remedio-nome');
    const remedioHorarioInput = document.getElementById('remedio-horario');

    // 1. Carrega os lembretes do banco assim que a página abre
    loadLembretes();

    // 2. O QUE FAZER QUANDO O FORMULÁRIO FOR ENVIADO
    formLembrete.addEventListener('submit', async function(e) {
        e.preventDefault(); // Impede que a página recarregue
        
        const nome = remedioNomeInput.value;
        const horario = remedioHorarioInput.value;

        if (nome && horario) {
            try {
                // Chama a API /api/lembretes/add
                const response = await fetch('/api/lembretes/add', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ nome: nome, horario: horario })
                });

                if (response.ok) {
                    const novoLembrete = await response.json();
                    // Adiciona o novo lembrete na lista visual
                    addLembreteNaTela(novoLembrete.nome_remedio, novoLembrete.horario, novoLembrete.id);
                    
                    // Limpa os campos do formulário
                    remedioNomeInput.value = '';
                    remedioHorarioInput.value = '';
                } else {
                    alert('Erro ao salvar lembrete.');
                }
            } catch (error) {
                console.error('Erro:', error);
            }
        }
    });

    // 3. O QUE FAZER QUANDO CLICAR NA LISTA (para remover)
    listaLembretes.addEventListener('click', async function(e) {
        // Verifica se o que foi clicado é um botão de remover
        if (e.target.classList.contains('btn-danger-sm')) {
            const li = e.target.parentElement;
            // Pega o ID que guardamos no elemento
            const lembreteId = li.dataset.id; 
            
            try {
                // Chama a API /api/lembretes/delete
                const response = await fetch('/api/lembretes/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id: lembreteId })
                });

                if (response.ok) {
                    // Remove o item da lista visual
                    li.remove();
                } else {
                    alert('Erro ao deletar lembrete.');
                }
            } catch (error) {
                console.error('Erro:', error);
            }
        }
    });

    // --- FUNÇÕES AUXILIARES ---

    /**
     * Adiciona o lembrete na lista visual (HTML)
     * Agora guarda o ID do banco no 'dataset' do elemento <li>
     */
    function addLembreteNaTela(nome, horario, id) {
        const li = document.createElement('li');
        // Adiciona o 'data-id' para sabermos qual lembrete deletar
        li.dataset.id = id; 
        
        li.innerHTML = `
            <span><strong>${nome}</strong></span>
            <span>${horario}</span>
            <button class="btn-danger-sm">Remover</button>
        `;
        listaLembretes.appendChild(li);
    }

    /**
     * Carrega os lembretes do usuário logado (do banco)
     */
    async function loadLembretes() {
        // Limpa a lista atual (remove o exemplo do HTML)
        listaLembretes.innerHTML = ''; 

        try {
            // Chama a API /api/lembretes
            const response = await fetch('/api/lembretes');
            if (response.ok) {
                const lembretes = await response.json();
                // Para cada lembrete que veio do banco, adiciona na tela
                lembretes.forEach(lembrete => {
                    addLembreteNaTela(lembrete.nome_remedio, lembrete.horario, lembrete.id);
                });
            }
        } catch (error) {
            console.error('Erro ao carregar lembretes:', error);
        }
    }
});
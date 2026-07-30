window.addEventListener('DOMContentLoaded', function () {
  const modal = document.getElementById('detail-modal');
  const modalCloseButtons = modal ? modal.querySelectorAll('[data-modal-close]') : [];
  const modalTitle = document.getElementById('modal-title');
  const modalBody = document.getElementById('modal-content');
  const modalMacrotema = document.getElementById('modal-macrotema');
  const modalMeta = document.getElementById('modal-meta');
  const toast = document.getElementById('realtime-toast');

  function setToast(message) {
    if (!toast) return;
    toast.textContent = message;
    toast.classList.remove('hidden');
    clearTimeout(window._realtimeToastTimeout);
    window._realtimeToastTimeout = setTimeout(() => toast.classList.add('hidden'), 3600);
  }

  function openModal() {
    document.body.classList.add('modal-open');
    modal.classList.remove('hidden');
    modal.setAttribute('aria-hidden', 'false');
  }

  function closeModal() {
    document.body.classList.remove('modal-open');
    modal.classList.add('hidden');
    modal.setAttribute('aria-hidden', 'true');
  }

  function renderDetail(data) {
    if (!modalTitle || !modalBody || !modalMacrotema || !modalMeta) return;
    modalTitle.textContent = data.titulo || 'Detalhes da proposição';
    modalMacrotema.classList.toggle('hidden', !data.macrotema?.nome);
    if (data.macrotema?.nome) {
      modalMacrotema.textContent = data.macrotema.nome;
      modalMacrotema.style.borderColor = data.macrotema.cor;
      modalMacrotema.style.color = data.macrotema.cor;
    }

    modalMeta.innerHTML = '';
    const metaLabels = [
      data.casa,
      data.status_tramitacao,
      data.prioridade_fnp,
      data.urgente ? 'Urgente' : null,
      data.aprovada ? 'Aprovada' : null,
      data.pauta ? 'Na pauta' : 'Sem pauta',
    ]
      .filter(Boolean)
      .map(value => `<span>${value}</span>`)
      .join('');
    modalMeta.innerHTML = metaLabels;

    modalBody.innerHTML = `
      <section>
        <h3>Resumo</h3>
        <p>${data.ementa_resumida || 'Sem resumo cadastrado.'}</p>
      </section>
      <section class="two-columns">
        <div>
          <h3>Próximos eventos</h3>
          <p>${data.proximos_eventos || 'Ainda sem eventos definidos.'}</p>
        </div>
        <div>
          <h3>Interlocutores</h3>
          <p>${data.interlocutores || 'Informação não disponível.'}</p>
        </div>
      </section>
      <section class="two-columns">
        <div>
          <h3>Última movimentação</h3>
          <p>${data.ultima_movimentacao || 'Sem movimentação registrada.'}</p>
        </div>
        <div>
          <h3>Tema</h3>
          <p>${data.tema || 'Indefinido'}</p>
        </div>
      </section>
      <section class="two-columns">
        <div>
          <h3>Posicionamento FNP</h3>
          <p>${data.posicionamento_fnp || '—'}</p>
        </div>
        <div>
          <h3>Ações de incidência</h3>
          <p>${data.acoes_incidencia || '—'}</p>
        </div>
      </section>
      <section>
        <h3>Riscos e oportunidades</h3>
        <p>${data.riscos_oportunidades || '—'}</p>
      </section>
    `;
  }

  function fetchProposicaoDetail(pk) {
    return fetch(`/legislativo/api/proposicao/${pk}/`)
      .then(response => {
        if (!response.ok) {
          throw new Error('Falha ao carregar detalhes.');
        }
        return response.json();
      });
  }

  function handleCardClick(event) {
    const anchor = event.target.closest('a[data-open-modal]');
    if (!anchor) return;
    event.preventDefault();
    const card = anchor.closest('.card');
    const pk = card?.dataset.proposicaoId;
    if (!pk) return;
    fetchProposicaoDetail(pk)
      .then(data => {
        renderDetail(data);
        openModal();
      })
      .catch(() => setToast('Erro ao carregar o detalhe da proposição.'));
  }

  function fetchStats() {
    const params = new URLSearchParams(window.location.search);
    fetch(`/legislativo/api/proposicoes/?${params.toString()}`)
      .then(response => response.json())
      .then(data => {
        document.getElementById('stats-total').textContent = data.counts.total;
        document.getElementById('stats-pauta').textContent = data.counts.pauta;
        document.getElementById('stats-urgentes').textContent = data.counts.urgentes;
        document.getElementById('stats-alta').textContent = data.counts.alta_prioridade;
        setToast('Painel atualizado com novos dados.');
      })
      .catch(() => setToast('Erro ao atualizar os dados em tempo real.'));
  }

  function initSse() {
    const params = new URLSearchParams(window.location.search);
    const source = new EventSource(`/legislativo/api/proposicao-sse/?${params.toString()}`);

    source.addEventListener('message', event => {
      try {
        const data = JSON.parse(event.data);
        document.getElementById('stats-total').textContent = data.counts.total;
        document.getElementById('stats-pauta').textContent = data.counts.pauta;
        document.getElementById('stats-urgentes').textContent = data.counts.urgentes;
        document.getElementById('stats-alta').textContent = data.counts.alta_prioridade;
      } catch (error) {
        console.error('SSE parse error', error);
      }
    });

    source.addEventListener('error', () => {
      source.close();
      setToast('Atualização em tempo real não disponível. Usando polling.');
      setInterval(fetchStats, realtimeInterval);
    });
  }

  if (modal) {
    modalCloseButtons.forEach(button => button.addEventListener('click', closeModal));
    modal.addEventListener('keydown', event => {
      if (event.key === 'Escape') {
        closeModal();
      }
    });
    document.addEventListener('click', handleCardClick);
  }

  let realtimeInterval = 20 * 1000;
  if (!window.location.pathname.includes('/participacoes/')) {
    if ('EventSource' in window) {
      initSse();
    } else {
      setInterval(fetchStats, realtimeInterval);
    }
  }

  console.log('Legislativo FNP pronto.');
});

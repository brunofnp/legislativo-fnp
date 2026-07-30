window.addEventListener('DOMContentLoaded', function () {
  const toast = document.getElementById('realtime-toast');

  function setToast(message) {
    if (!toast) return;
    toast.textContent = message;
    toast.classList.remove('hidden');
    clearTimeout(window._realtimeToastTimeout);
    window._realtimeToastTimeout = setTimeout(() => toast.classList.add('hidden'), 3600);
  }

  function applyCounts(data) {
    const total = document.getElementById('stats-total');
    const pauta = document.getElementById('stats-pauta');
    const urgentes = document.getElementById('stats-urgentes');
    const alta = document.getElementById('stats-alta');
    if (!total || !pauta || !urgentes || !alta) return;
    total.textContent = data.counts.total;
    pauta.textContent = data.counts.pauta;
    urgentes.textContent = data.counts.urgentes;
    alta.textContent = data.counts.alta_prioridade;
  }

  function fetchStats() {
    const params = new URLSearchParams(window.location.search);
    fetch(`/api/proposicoes/?${params.toString()}`)
      .then(response => response.json())
      .then(applyCounts)
      .catch(() => setToast('Erro ao atualizar os dados em tempo real.'));
  }

  function initSse() {
    const params = new URLSearchParams(window.location.search);
    const source = new EventSource(`/api/proposicao-sse/?${params.toString()}`);

    source.addEventListener('message', event => {
      try {
        const data = JSON.parse(event.data);
        applyCounts(data);
        if (data.updated) {
          setToast('Novas proposições foram atualizadas.');
        }
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

  let realtimeInterval = 20 * 1000;
  if (!window.location.pathname.includes('/participacoes/') && !window.location.pathname.includes('/proposicao/')) {
    if ('EventSource' in window) {
      initSse();
    } else {
      setInterval(fetchStats, realtimeInterval);
    }
  }

  console.log('Legislativo FNP pronto.');
});

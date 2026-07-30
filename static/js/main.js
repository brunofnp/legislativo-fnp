window.addEventListener('DOMContentLoaded', function () {
  const toast = document.getElementById('realtime-toast');

  function initTemaDropdown() {
    const dropdown = document.getElementById('tema-dropdown');
    const search = document.getElementById('tema-dropdown-search');
    if (!dropdown || !search) return;

    const options = dropdown.querySelectorAll('.tema-option');

    search.addEventListener('input', () => {
      const term = search.value.trim().toLowerCase();
      options.forEach(option => {
        const matches = option.textContent.toLowerCase().includes(term);
        option.classList.toggle('hidden', !matches);
      });
    });

    dropdown.addEventListener('toggle', () => {
      if (dropdown.open) {
        search.value = '';
        options.forEach(option => option.classList.remove('hidden'));
        setTimeout(() => search.focus(), 0);
      }
    });

    document.addEventListener('click', event => {
      if (dropdown.open && !dropdown.contains(event.target)) {
        dropdown.open = false;
      }
    });
  }

  initTemaDropdown();

  function initAppShell() {
    const shell = document.getElementById('app-shell');
    const collapseBtn = document.getElementById('sidebar-collapse-btn');
    const hamburger = document.getElementById('sidebar-hamburger');

    function applyCollapsed(collapsed) {
      if (!shell) return;
      shell.classList.toggle('sidebar-collapsed', collapsed);
      localStorage.setItem('fnp-sidebar-collapsed', collapsed ? '1' : '0');
    }

    if (shell) {
      applyCollapsed(localStorage.getItem('fnp-sidebar-collapsed') === '1');
    }

    function toggleCollapsed() {
      applyCollapsed(!shell.classList.contains('sidebar-collapsed'));
    }

    if (collapseBtn) collapseBtn.addEventListener('click', toggleCollapsed);
    if (hamburger) hamburger.addEventListener('click', toggleCollapsed);
  }

  initAppShell();

  function initThemeToggle() {
    const btn = document.getElementById('theme-toggle-btn');
    if (!btn) return;
    btn.addEventListener('click', () => {
      const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      if (isDark) {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('fnp-theme', 'light');
      } else {
        document.documentElement.setAttribute('data-theme', 'dark');
        localStorage.setItem('fnp-theme', 'dark');
      }
    });
  }

  initThemeToggle();

  function initFontSize() {
    const btn = document.getElementById('font-size-btn');
    if (!btn) return;
    const sizes = ['15px', '16px', '18px', '20px'];

    function currentIndex() {
      const stored = localStorage.getItem('fnp-font-size') || '16px';
      const idx = sizes.indexOf(stored);
      return idx === -1 ? 1 : idx;
    }

    btn.addEventListener('click', () => {
      const next = sizes[(currentIndex() + 1) % sizes.length];
      document.documentElement.style.fontSize = next;
      localStorage.setItem('fnp-font-size', next);
    });
  }

  initFontSize();

  function initDropdown(triggerId, dropdownId) {
    const trigger = document.getElementById(triggerId);
    const dropdown = document.getElementById(dropdownId);
    if (!trigger || !dropdown) return;

    trigger.addEventListener('click', event => {
      event.stopPropagation();
      dropdown.classList.toggle('open');
    });

    document.addEventListener('click', event => {
      if (dropdown.classList.contains('open') && !dropdown.contains(event.target) && event.target !== trigger) {
        dropdown.classList.remove('open');
      }
    });
  }

  initDropdown('notif-btn', 'notif-dropdown');

  function initSearchModal() {
    const modal = document.getElementById('search-modal');
    const trigger = document.getElementById('search-trigger');
    const backdrop = document.getElementById('search-modal-backdrop');
    const input = document.getElementById('search-modal-input');
    if (!modal || !input) return;

    function openModal() {
      modal.classList.remove('hidden');
      setTimeout(() => input.focus(), 0);
    }

    function closeModal() {
      modal.classList.add('hidden');
    }

    if (trigger) trigger.addEventListener('click', openModal);
    if (backdrop) backdrop.addEventListener('click', closeModal);

    document.addEventListener('keydown', event => {
      const isCtrlK = (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k';
      if (isCtrlK) {
        event.preventDefault();
        openModal();
      } else if (event.key === 'Escape' && !modal.classList.contains('hidden')) {
        closeModal();
      }
    });
  }

  initSearchModal();

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
    const relator = document.getElementById('stats-relator');
    if (!total || !pauta || !urgentes || !alta) return;
    total.textContent = data.counts.total;
    pauta.textContent = data.counts.pauta;
    urgentes.textContent = data.counts.urgentes;
    alta.textContent = data.counts.alta_prioridade;
    if (relator) {
      relator.textContent = data.counts.com_relator;
    }
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

window.addEventListener('DOMContentLoaded', function () {
  const toast = document.getElementById('realtime-toast');

  function initTemaDropdowns() {
    const dropdowns = document.querySelectorAll('.tema-dropdown');
    if (!dropdowns.length) return;

    dropdowns.forEach(dropdown => {
      const search = dropdown.querySelector('.tema-dropdown-search');
      const options = dropdown.querySelectorAll('.tema-option');
      if (!search) return;

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
    });

    document.addEventListener('click', event => {
      dropdowns.forEach(dropdown => {
        if (dropdown.open && !dropdown.contains(event.target)) {
          dropdown.open = false;
        }
      });
    });
  }

  initTemaDropdowns();

  function initSearchSuggestions() {
    const input = document.getElementById('search-input');
    const box = document.getElementById('search-suggestions');
    if (!input || !box) return;

    let debounceTimer;

    function hide() {
      box.classList.add('hidden');
      box.innerHTML = '';
    }

    function fetchSuggestions(term) {
      fetch(`/api/busca-sugestoes/?q=${encodeURIComponent(term)}`)
        .then(response => response.json())
        .then(data => {
          if (input.value.trim() !== term) return;
          if (!data.html) {
            hide();
            return;
          }
          box.innerHTML = data.html;
          box.classList.remove('hidden');
        })
        .catch(() => hide());
    }

    input.addEventListener('input', () => {
      const term = input.value.trim();
      clearTimeout(debounceTimer);
      if (term.length < 2) {
        hide();
        return;
      }
      debounceTimer = setTimeout(() => fetchSuggestions(term), 250);
    });

    input.addEventListener('keydown', event => {
      if (event.key === 'Escape') hide();
    });

    document.addEventListener('click', event => {
      if (!box.contains(event.target) && event.target !== input) {
        hide();
      }
    });
  }

  initSearchSuggestions();

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

  function initBackLinks() {
    const links = document.querySelectorAll('[data-back]');
    if (!links.length) return;
    const cameFromSameSite = document.referrer && document.referrer.startsWith(location.origin);
    if (!(window.history.length > 1 && cameFromSameSite)) return;
    links.forEach(link => {
      link.addEventListener('click', event => {
        event.preventDefault();
        window.history.back();
      });
    });
  }

  initBackLinks();

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

  function initStickyHeaderOffset() {
    const header = document.querySelector('.app-topbar') || document.querySelector('.site-header');
    if (!header) return;

    function updateOffset() {
      document.documentElement.style.setProperty('--header-height', header.offsetHeight + 'px');
    }

    updateOffset();
    if (window.ResizeObserver) {
      new ResizeObserver(updateOffset).observe(header);
    } else {
      window.addEventListener('resize', updateOffset);
    }
  }

  initStickyHeaderOffset();

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
  initDropdown('topbar-more-btn', 'topbar-more-panel');

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
      if (trigger) trigger.focus();
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

  function initForumReply() {
    const parentInput = document.getElementById('id_parent');
    const textoInput = document.getElementById('id_texto');
    const indicator = document.getElementById('comment-reply-indicator');
    const nomeEl = document.getElementById('comment-reply-nome');
    const cancelBtn = document.getElementById('comment-reply-cancel');
    const replyBtns = document.querySelectorAll('.comment-reply-btn');
    if (!parentInput || !textoInput || !replyBtns.length) return;

    replyBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        parentInput.value = btn.dataset.parentId;
        if (nomeEl) nomeEl.textContent = btn.dataset.parentNome;
        if (indicator) indicator.classList.remove('hidden');
        textoInput.focus();
        textoInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
      });
    });

    if (cancelBtn) {
      cancelBtn.addEventListener('click', () => {
        parentInput.value = '';
        if (indicator) indicator.classList.add('hidden');
      });
    }
  }

  initForumReply();

  function initComentariosVerMais() {
    const btn = document.getElementById('comments-ver-mais');
    if (!btn) return;

    btn.addEventListener('click', () => {
      document.querySelectorAll('.comment-extra').forEach(item => item.classList.remove('hidden'));
      btn.classList.add('hidden');
    });
  }

  initComentariosVerMais();

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

  function applyCards(sections) {
    if (!sections) return;
    const containerByKey = {
      urgentes: 'cards-urgentes',
      em_alta: 'cards-em-alta',
      todas: 'cards-todas',
    };
    Object.keys(containerByKey).forEach(key => {
      const container = document.getElementById(containerByKey[key]);
      if (container && sections[key] !== undefined) {
        container.innerHTML = sections[key];
      }
    });
  }

  function refreshCards() {
    const params = new URLSearchParams(window.location.search);
    fetch(`/api/proposicoes-cards/?${params.toString()}`)
      .then(response => response.json())
      .then(data => {
        applyCounts(data);
        applyCards(data.sections);
      })
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
          refreshCards();
        }
      } catch (error) {
        console.error('SSE parse error', error);
      }
    });

    source.addEventListener('error', () => {
      source.close();
      setToast('Atualização em tempo real não disponível. Usando polling.');
      setInterval(refreshCards, realtimeInterval);
    });
  }

  let realtimeInterval = 20 * 1000;
  if (!window.location.pathname.includes('/participacoes/') && !window.location.pathname.includes('/proposicao/')) {
    if ('EventSource' in window) {
      initSse();
    } else {
      setInterval(refreshCards, realtimeInterval);
    }
  }
});

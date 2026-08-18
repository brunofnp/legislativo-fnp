window.addEventListener('DOMContentLoaded', function () {
  const toast = document.getElementById('realtime-toast');

  // Cor do chip de macrotema é dinâmica (cadastrada por registro no Admin),
  // então não dá pra virar classe CSS fixa -- setar via element.style (JS)
  // em vez de atributo style="" no HTML evita precisar de 'unsafe-inline'
  // no style-src do CSP (CSP não restringe mudança de estilo via CSSOM).
  function initMacrotemaColors(root) {
    (root || document).querySelectorAll('[data-cor-macrotema]').forEach(chip => {
      const cor = chip.dataset.corMacrotema;
      if (!cor) return;
      chip.style.setProperty('color', cor);
      chip.style.setProperty('border-color', cor);
    });
  }

  initMacrotemaColors();

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
    // Digitar na busca vale como um filtro novo e independente -- substitui
    // (não soma a) qualquer tema/card de estatística já ativo na URL, daí
    // as chamadas abaixo usarem só `q`, nunca tema/filtro da página atual.
    const cardsGridExiste = !!document.getElementById('cards-todas');
    // Se a página já carregou com um filtro de verdade aplicado (veio de um
    // ?q=/?tema=/?filtro= submetido, não só digitação ao vivo), Urgentes/
    // Áreas de interesse/Em alta/Últimos acessados nem existem no DOM
    // (`{% if not filtro_ativo %}` no template) e o título da seção
    // consolidada ("Busca por X (N)") é só texto estático -- não dá pra
    // "desfazer" isso trocando só o conteúdo de #cards-todas via fetch, sem
    // duplicar em JS a lógica de montagem que já existe (e deveria
    // continuar existindo só) no template. Nesse caso, limpar a busca
    // navega pro link "Limpar filtro" de verdade (mesma URL que o próprio
    // servidor já usa), em vez de só ajustar pedaços incompletos via AJAX
    // (achado via captura de tela real, 2026-08-14 -- limpar o campo numa
    // página vinda de busca submetida deixava o título e as seções
    // originais sumidas mesmo com o "x" clicado).
    const limparFiltroLink = document.querySelector('.filtro-limpar-link');

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

    function fetchLivePreview(term) {
      if (!cardsGridExiste) return;
      fetch(`/api/proposicoes-cards/?q=${encodeURIComponent(term)}`)
        .then(response => response.json())
        .then(data => {
          if (input.value.trim() !== term) return;
          applyCounts(data);
          applyCards(data.sections);
        })
        .catch(() => {});
    }

    input.addEventListener('focus', () => {
      // Limpa o filtro anterior (tema/card de estatística) assim que o
      // usuário começa a digitar uma busca nova -- ver comentário acima.
      if (input.value.trim().length >= 2) {
        fetchLivePreview(input.value.trim());
      }
      // Em mobile o campo de busca fica abaixo dos cards de estatística --
      // sem subir a tela, a lista de sugestões nasce abaixo da dobra (e o
      // teclado virtual real reduz o espaço visível ainda mais). Achado da
      // auditoria mobile, 2026-08-13.
      if (window.innerWidth <= 900) {
        input.scrollIntoView({ block: 'start', behavior: 'smooth' });
      }
    });

    input.addEventListener('input', () => {
      const term = input.value.trim();
      clearTimeout(debounceTimer);
      if (term.length < 2) {
        hide();
        // Campo zerado (inclusive pelo "x" nativo do <input type="search">,
        // que dispara input normalmente) -- volta pros cards sem filtro
        // nenhum, em vez de deixar o preview anterior travado na tela até
        // a pessoa clicar em outro lugar ou recarregar a página (achado via
        // captura de tela real, 2026-08-14).
        if (term.length === 0) {
          if (limparFiltroLink) {
            window.location.href = limparFiltroLink.href;
          } else {
            fetchLivePreview('');
          }
        }
        return;
      }
      debounceTimer = setTimeout(() => {
        fetchSuggestions(term);
        fetchLivePreview(term);
      }, 250);
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
    if (!shell) return;

    // Modo "recolher" (desktop) -- sidebar permanente, só encolhe pra
    // ícone. Estado salvo entre sessões, é uma preferência de verdade.
    function applyCollapsed(collapsed) {
      shell.classList.toggle('sidebar-collapsed', collapsed);
      localStorage.setItem('fnp-sidebar-collapsed', collapsed ? '1' : '0');
    }

    applyCollapsed(localStorage.getItem('fnp-sidebar-collapsed') === '1');

    if (collapseBtn) {
      collapseBtn.addEventListener('click', () => {
        applyCollapsed(!shell.classList.contains('sidebar-collapsed'));
      });
    }

    // Modo gaveta (mobile, <900px) -- estado independente do "recolher"
    // de desktop; começa sempre fechado a cada carregamento de página (não
    // é uma preferência pra lembrar, é só "a gaveta está aberta agora").
    // Achado da auditoria mobile: antes os dois modos compartilhavam a
    // mesma classe/flag, então em mobile a gaveta nascia aberta cobrindo a
    // tela (com o próprio hambúrguer escondido atrás dela) sempre que a
    // preferência de desktop estivesse "não recolhida" (o padrão).
    const hamburger = document.getElementById('sidebar-hamburger');
    const closeBtn = document.getElementById('app-sidebar-close');
    const backdrop = document.getElementById('app-sidebar-backdrop');

    function setDrawerOpen(open) {
      shell.classList.toggle('sidebar-mobile-open', open);
      if (hamburger) hamburger.setAttribute('aria-expanded', open ? 'true' : 'false');
    }

    if (hamburger) {
      hamburger.setAttribute('aria-expanded', 'false');
      hamburger.addEventListener('click', () => {
        setDrawerOpen(!shell.classList.contains('sidebar-mobile-open'));
      });
    }
    if (closeBtn) closeBtn.addEventListener('click', () => setDrawerOpen(false));
    if (backdrop) backdrop.addEventListener('click', () => setDrawerOpen(false));

    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && shell.classList.contains('sidebar-mobile-open')) {
        setDrawerOpen(false);
      }
    });
  }

  initAppShell();

  function initBackNavigation() {
    // "Voltar" usava document.referrer + history.length -- heurística que
    // quebrava com facilidade (POST/redirect ao comentar cria uma entrada
    // extra no histórico, link direto/notificação sem referrer same-site
    // etc.), o que fazia o botão cair no fallback estático (sempre a home)
    // em vez de voltar pra página anterior de verdade. Uma pilha própria em
    // sessionStorage, empilhada a cada carregamento de página, é
    // determinística: "Ver mais comentários" não mexe nela (é só JS local,
    // sem navegação) e um recarregamento da mesma URL (ex.: após publicar
    // um comentário) não empilha duplicata.
    const STACK_KEY = 'fnp-nav-stack';
    const paginaAtual = window.location.pathname + window.location.search;

    let pilha;
    try {
      pilha = JSON.parse(sessionStorage.getItem(STACK_KEY) || '[]');
    } catch (error) {
      pilha = [];
    }
    if (pilha[pilha.length - 1] !== paginaAtual) {
      pilha.push(paginaAtual);
    }
    if (pilha.length > 20) pilha = pilha.slice(-20);
    sessionStorage.setItem(STACK_KEY, JSON.stringify(pilha));

    const links = document.querySelectorAll('[data-back]');
    if (!links.length) return;

    links.forEach(link => {
      link.addEventListener('click', event => {
        let atual;
        try {
          atual = JSON.parse(sessionStorage.getItem(STACK_KEY) || '[]');
        } catch (error) {
          atual = [];
        }
        atual.pop(); // remove a própria página atual do topo
        const destino = atual.pop(); // página anterior de fato
        if (destino) {
          sessionStorage.setItem(STACK_KEY, JSON.stringify(atual));
          event.preventDefault();
          window.location.href = destino;
        }
        // Pilha vazia (sessão nova, link direto/notificação): mantém o
        // href estático já presente no link (fallback pra home).
      });
    });
  }

  initBackNavigation();

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

  function initHelpModal() {
    const modal = document.getElementById('help-modal');
    const trigger = document.getElementById('page-help-btn');
    const backdrop = document.getElementById('help-modal-backdrop');
    const closeBtn = document.getElementById('help-modal-close');
    const okBtn = document.getElementById('help-modal-ok-btn');
    const tourBtn = document.getElementById('help-modal-tour-btn');
    if (!modal || !trigger) return;

    function openModal() {
      modal.classList.remove('hidden');
    }

    function closeModal() {
      modal.classList.add('hidden');
      trigger.focus();
    }

    trigger.addEventListener('click', openModal);
    if (backdrop) backdrop.addEventListener('click', closeModal);
    if (closeBtn) closeBtn.addEventListener('click', closeModal);
    if (okBtn) okBtn.addEventListener('click', closeModal);
    if (tourBtn) {
      tourBtn.addEventListener('click', () => {
        closeModal();
        if (window.iniciarTourFNP) window.iniciarTourFNP();
      });
    }

    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && !modal.classList.contains('hidden')) {
        closeModal();
      }
    });
  }

  initHelpModal();

  function initPrintDropdowns() {
    // <details> não fecha sozinho ao clicar fora -- mesmo tratamento já
    // usado no menu de editar avatar do perfil, generalizado aqui porque
    // pode existir 1 dropdown de impressão por card na grade (cards são
    // recriados via innerHTML no live-update por SSE, então delegação em
    // document em vez de listener por elemento).
    document.addEventListener('click', event => {
      document.querySelectorAll('.print-dropdown[open]').forEach(dropdown => {
        if (!dropdown.contains(event.target)) {
          dropdown.removeAttribute('open');
        }
      });
    });
  }

  initPrintDropdowns();

  function initPrintPersonalizado() {
    const modal = document.getElementById('print-personalizar-modal');
    if (!modal) return;
    const backdrop = document.getElementById('print-personalizar-backdrop');
    const closeBtn = document.getElementById('print-personalizar-close');
    const gerarBtn = document.getElementById('print-personalizar-gerar');
    let imprimirUrl = null;

    function openModal(url) {
      imprimirUrl = url;
      modal.classList.remove('hidden');
    }

    function closeModal() {
      modal.classList.add('hidden');
      imprimirUrl = null;
    }

    document.addEventListener('click', event => {
      const trigger = event.target.closest('.print-personalizada-btn');
      if (!trigger) return;
      const details = trigger.closest('details');
      if (details) details.removeAttribute('open');
      openModal(trigger.dataset.imprimirUrl);
    });

    if (backdrop) backdrop.addEventListener('click', closeModal);
    if (closeBtn) closeBtn.addEventListener('click', closeModal);
    if (gerarBtn) {
      gerarBtn.addEventListener('click', () => {
        if (!imprimirUrl) return;
        const secoes = Array.from(modal.querySelectorAll('input[name="secao"]:checked')).map(input => input.value);
        window.open(`${imprimirUrl}?formato=personalizada&secoes=${secoes.join(',')}`, '_blank');
        closeModal();
      });
    }

    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && !modal.classList.contains('hidden')) {
        closeModal();
      }
    });
  }

  initPrintPersonalizado();

  function initTour() {
    const modal = document.getElementById('tour-modal');
    if (!modal) return;

    const slides = Array.from(modal.querySelectorAll('.tour-modal-slide'));
    const progressBars = Array.from(modal.querySelectorAll('.tour-modal-progress-bar'));
    const stepCount = document.getElementById('tour-modal-step-count');
    const backdrop = document.getElementById('tour-modal-backdrop');
    const closeTextBtn = document.getElementById('tour-modal-close-text');
    const backBtn = document.getElementById('tour-modal-back');
    const nextBtn = document.getElementById('tour-modal-next');
    const naoMostrarCheckbox = document.getElementById('tour-modal-nao-mostrar');
    const TOTAL_STEPS = slides.length;
    const STORAGE_KEY = 'fnp-tour-visto';
    let passoAtual = 1;

    function mostrarPasso(passo) {
      passoAtual = passo;
      slides.forEach(slide => {
        slide.classList.toggle('hidden', Number(slide.dataset.tourStep) !== passo);
      });
      progressBars.forEach(bar => {
        bar.classList.toggle('active', Number(bar.dataset.progressStep) <= passo);
      });
      if (stepCount) stepCount.textContent = `${passo} de ${TOTAL_STEPS}`;
      if (backBtn) backBtn.disabled = passo === 1;
      if (nextBtn) nextBtn.textContent = passo === TOTAL_STEPS ? 'Concluir' : 'Próximo';
    }

    function abrirTour() {
      mostrarPasso(1);
      modal.classList.remove('hidden');
    }

    function fecharTour() {
      modal.classList.add('hidden');
      if (naoMostrarCheckbox && naoMostrarCheckbox.checked) {
        localStorage.setItem(STORAGE_KEY, '1');
      }
    }

    if (backdrop) backdrop.addEventListener('click', fecharTour);
    if (closeTextBtn) closeTextBtn.addEventListener('click', fecharTour);
    if (backBtn) backBtn.addEventListener('click', () => { if (passoAtual > 1) mostrarPasso(passoAtual - 1); });
    if (nextBtn) {
      nextBtn.addEventListener('click', () => {
        if (passoAtual < TOTAL_STEPS) {
          mostrarPasso(passoAtual + 1);
        } else {
          fecharTour();
        }
      });
    }

    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && !modal.classList.contains('hidden')) {
        fecharTour();
      }
    });

    // Exposto globalmente pro botão "Rever o tour" do modal de Ajuda
    // (initHelpModal acima) chamar de qualquer página autenticada.
    window.iniciarTourFNP = abrirTour;

    // Mostra sozinho só no primeiro acesso (Painel Geral) de quem nunca
    // viu ou desmarcou "Não mostrar novamente" da última vez.
    if (window.location.pathname === '/' && localStorage.getItem(STORAGE_KEY) !== '1') {
      abrirTour();
    }
  }

  initTour();

  function initBackToTop() {
    const btn = document.getElementById('back-to-top-btn');
    if (!btn) return;

    function checarScroll() {
      btn.classList.toggle('visible', window.scrollY > 500);
    }

    window.addEventListener('scroll', checarScroll, { passive: true });
    checarScroll();

    btn.addEventListener('click', () => {
      const reduzMovimento = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      window.scrollTo({ top: 0, behavior: reduzMovimento ? 'auto' : 'smooth' });
    });
  }

  initBackToTop();

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

  function initPreventDoubleSubmit() {
    // Sem isso, um duplo-clique no botão (ou conexão lenta) manda dois POSTs
    // antes do redirect da primeira resposta chegar -- cria dois comentários
    // e, junto, uma notificação duplicada pra cada participante da discussão.
    const form = document.getElementById('form-comentario');
    if (!form) return;
    form.addEventListener('submit', () => {
      const btn = form.querySelector('button[type="submit"]');
      if (btn) {
        btn.disabled = true;
        btn.textContent = 'Enviando...';
      }
    });
  }

  initPreventDoubleSubmit();

  function initComentariosVerMais() {
    const btn = document.getElementById('comments-ver-mais');
    if (!btn) return;

    btn.addEventListener('click', () => {
      document.querySelectorAll('.comment-extra').forEach(item => item.classList.remove('hidden'));
      btn.classList.add('hidden');
    });
  }

  initComentariosVerMais();

  function initPerfilAvatarEdit() {
    const menu = document.getElementById('perfil-avatar-menu');
    const fileInput = document.getElementById('id_foto');
    if (!menu || !fileInput) return;

    const clearCheckbox = document.getElementById('foto-clear_id');

    function atualizarPreview(arquivo) {
      const preview = document.getElementById('perfil-avatar-preview');
      if (!arquivo || !preview) return;
      const url = URL.createObjectURL(arquivo);
      if (preview.tagName === 'IMG') {
        preview.src = url;
      } else {
        const img = document.createElement('img');
        img.src = url;
        img.alt = '';
        img.className = preview.className.replace('perfil-avatar-fallback', '').trim();
        img.id = preview.id;
        preview.replaceWith(img);
      }
      if (clearCheckbox) clearCheckbox.checked = false;
    }

    menu.querySelectorAll('[data-avatar-action]').forEach(btn => {
      btn.addEventListener('click', () => {
        const action = btn.dataset.avatarAction;
        menu.open = false;
        if (action === 'remover') {
          if (clearCheckbox) clearCheckbox.checked = true;
        } else if (action === 'camera') {
          abrirCamera();
        } else {
          fileInput.click();
        }
      });
    });

    // <details> não fecha sozinho ao clicar fora -- só ao clicar de novo no
    // summary (mesmo comportamento já tratado pro .tema-dropdown).
    document.addEventListener('click', event => {
      if (menu.open && !menu.contains(event.target)) {
        menu.open = false;
      }
    });

    fileInput.addEventListener('change', () => {
      atualizarPreview(fileInput.files && fileInput.files[0]);
    });

    // ---- Captura por webcam (getUserMedia) ----
    // O atributo capture="..." do <input type="file"> só é respeitado por
    // navegador mobile (abre o app de câmera nativo); desktop ignora e cai
    // no seletor de arquivo comum, sem abrir webcam nenhuma. Pra "Abrir
    // câmera" funcionar de verdade em qualquer dispositivo, usa um <video>
    // ao vivo + captura de frame num <canvas> em vez do atributo.
    const cameraModal = document.getElementById('avatar-camera-modal');
    const cameraVideo = document.getElementById('avatar-camera-video');
    const cameraErro = document.getElementById('avatar-camera-erro');
    const cameraCapturar = document.getElementById('avatar-camera-capturar');
    const cameraCancelar = document.getElementById('avatar-camera-cancelar');
    const cameraBackdrop = document.getElementById('avatar-camera-modal-backdrop');
    let stream = null;

    function pararStream() {
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
        stream = null;
      }
    }

    function fecharCamera() {
      pararStream();
      if (cameraModal) cameraModal.classList.add('hidden');
    }

    async function abrirCamera() {
      if (!cameraModal || !cameraVideo || !navigator.mediaDevices) return;
      cameraModal.classList.remove('hidden');
      if (cameraErro) cameraErro.classList.add('hidden');
      cameraVideo.classList.remove('hidden');
      if (cameraCapturar) cameraCapturar.disabled = false;
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } });
        cameraVideo.srcObject = stream;
      } catch (error) {
        if (cameraErro) cameraErro.classList.remove('hidden');
        cameraVideo.classList.add('hidden');
        if (cameraCapturar) cameraCapturar.disabled = true;
      }
    }

    if (cameraCapturar) {
      cameraCapturar.addEventListener('click', () => {
        if (!stream || !cameraVideo.videoWidth) return;
        const canvas = document.createElement('canvas');
        canvas.width = cameraVideo.videoWidth;
        canvas.height = cameraVideo.videoHeight;
        const ctx = canvas.getContext('2d');
        // O <video> só é espelhado visualmente via CSS (transform) -- sem
        // desespelhar aqui a foto salva sairia com o texto/lado trocado.
        ctx.translate(canvas.width, 0);
        ctx.scale(-1, 1);
        ctx.drawImage(cameraVideo, 0, 0);
        canvas.toBlob(blob => {
          if (!blob) return;
          const arquivo = new File([blob], 'foto-camera.jpg', { type: 'image/jpeg' });
          const dataTransfer = new DataTransfer();
          dataTransfer.items.add(arquivo);
          fileInput.files = dataTransfer.files;
          atualizarPreview(arquivo);
          fecharCamera();
        }, 'image/jpeg', 0.92);
      });
    }

    if (cameraCancelar) cameraCancelar.addEventListener('click', fecharCamera);
    if (cameraBackdrop) cameraBackdrop.addEventListener('click', fecharCamera);
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && cameraModal && !cameraModal.classList.contains('hidden')) {
        fecharCamera();
      }
    });
  }

  initPerfilAvatarEdit();

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
        initMacrotemaColors(container);
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

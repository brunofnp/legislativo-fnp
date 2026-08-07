document.addEventListener('click', function (event) {
  var botao = event.target.closest('[data-fnp-action]');
  if (!botao) return;

  var form = document.getElementById('changelist-form');
  if (!form) return;

  var acao = botao.dataset.fnpAction;
  var pk = botao.dataset.fnpPk;

  form.querySelectorAll('input[name="_selected_action"]').forEach(function (checkbox) {
    checkbox.checked = checkbox.value === pk;
  });

  var selectAcao = form.querySelector('select[name="action"]');
  if (selectAcao) selectAcao.value = acao;

  form.requestSubmit ? form.requestSubmit() : form.submit();
});

// Confirmação antes de ação destrutiva (ex.: "Aprovar exclusão" na página
// do usuário) -- substitui onclick="return confirm(...)" inline, que a
// Content-Security-Policy (script-src sem 'unsafe-inline') bloquearia.
document.addEventListener('click', function (event) {
  var botao = event.target.closest('[data-confirm]');
  if (!botao) return;
  if (!confirm(botao.dataset.confirm)) {
    event.preventDefault();
  }
});

// Modal "Ajuda desta página" -- mesmo componente do site público
// (templates/_help_modal.html), sem o botão "Rever o tour" (o Admin não
// tem tour de onboarding).
document.addEventListener('DOMContentLoaded', function () {
  var modal = document.getElementById('help-modal');
  var trigger = document.getElementById('page-help-btn');
  if (!modal || !trigger) return;

  var backdrop = document.getElementById('help-modal-backdrop');
  var closeBtn = document.getElementById('help-modal-close');
  var okBtn = document.getElementById('help-modal-ok-btn');

  function abrir() {
    modal.classList.remove('hidden');
  }

  function fechar() {
    modal.classList.add('hidden');
    trigger.focus();
  }

  trigger.addEventListener('click', abrir);
  if (backdrop) backdrop.addEventListener('click', fechar);
  if (closeBtn) closeBtn.addEventListener('click', fechar);
  if (okBtn) okBtn.addEventListener('click', fechar);

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && !modal.classList.contains('hidden')) {
      fechar();
    }
  });
});

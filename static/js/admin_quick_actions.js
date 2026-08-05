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

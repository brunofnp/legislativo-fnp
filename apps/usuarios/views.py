from allauth.account.forms import ResetPasswordForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


@login_required
def definir_senha_social(request):
    """Sobrescreve account_set_password (allauth) pra contas sem senha local
    (login só via Google) -- sem isso, qualquer sessão autenticada (ex.:
    cookie sequestrado) conseguiria criar uma senha local nova sem precisar
    confirmar nada, virando uma porta dos fundos permanente de login. Em vez
    de reinventar verificação, reaproveita o fluxo de "Esqueci minha senha"
    do allauth (link por e-mail, token com expiração) já testado -- só quem
    tiver acesso à caixa de entrada cadastrada consegue de fato definir a
    senha, em account_reset_password_from_key."""

    if request.user.has_usable_password():
        return redirect('account_change_password')

    enviado = False
    if request.method == 'POST':
        form = ResetPasswordForm(data={'email': request.user.email})
        if form.is_valid():
            form.save(request)
            enviado = True

    return render(
        request,
        'account/definir_senha_social.html',
        {'page_title': 'Definir senha', 'enviado': enviado, 'mostrar_sidebar': True},
    )

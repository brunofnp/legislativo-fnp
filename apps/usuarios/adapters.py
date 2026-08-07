from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from .models import Perfil

DOMINIO_INSTITUCIONAL_FNP = 'fnp.org.br'


class GoogleAccountAdapter(DefaultSocialAccountAdapter):
    """Nome e sobrenome já são importados pelo comportamento padrão do allauth
    (DefaultSocialAccountAdapter.populate_user); aqui só cobrimos a foto de
    perfil, que não tem equivalente nativo no Usuario/Perfil."""

    def is_open_for_signup(self, request, sociallogin):
        """Cadastro novo via Google só é permitido pra e-mail institucional
        @fnp.org.br (equipe da FNP) -- município/entidade pública se
        cadastra pelo formulário normal (botão "Cadastre-se"), não pelo
        Google. Só afeta CADASTRO: quem já tem conta continua entrando
        normalmente, independente do domínio do e-mail (ver
        allauth.socialaccount.internal.flows.login._authenticate, que só
        chama is_open_for_signup pra sociallogin novo)."""
        email = (sociallogin.user.email or sociallogin.account.extra_data.get('email', '')).lower()
        if not email.endswith('@' + DOMINIO_INSTITUCIONAL_FNP):
            return False
        return super().is_open_for_signup(request, sociallogin)

    def save_user(self, request, sociallogin, form=None):
        usuario = super().save_user(request, sociallogin, form)
        foto_url = sociallogin.account.extra_data.get('picture', '')
        if foto_url:
            Perfil.objects.filter(usuario=usuario).update(foto_google_url=foto_url)
        return usuario

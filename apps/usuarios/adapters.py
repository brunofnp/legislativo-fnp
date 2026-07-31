from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from .models import Perfil


class GoogleAccountAdapter(DefaultSocialAccountAdapter):
    """Nome e sobrenome já são importados pelo comportamento padrão do allauth
    (DefaultSocialAccountAdapter.populate_user); aqui só cobrimos a foto de
    perfil, que não tem equivalente nativo no Usuario/Perfil."""

    def save_user(self, request, sociallogin, form=None):
        usuario = super().save_user(request, sociallogin, form)
        foto_url = sociallogin.account.extra_data.get('picture', '')
        if foto_url:
            Perfil.objects.filter(usuario=usuario).update(foto_google_url=foto_url)
        return usuario

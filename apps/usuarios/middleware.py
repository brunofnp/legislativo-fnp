from django.shortcuts import redirect
from django.urls import reverse

from .models import Perfil


class CadastroPendenteMiddleware:
    """Usuário autenticado cujo cadastro ainda não foi aprovado só acessa a
    página de aviso e o logout — equipe interna (is_staff) já entra aprovada
    automaticamente, ver signals.criar_perfil."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated and not user.is_staff:
            perfil = getattr(user, 'perfil', None)
            caminhos_liberados = (reverse('legislativo:cadastro_pendente'), reverse('account_logout'))
            if perfil and perfil.status_aprovacao != Perfil.APROVADO and request.path not in caminhos_liberados:
                return redirect('legislativo:cadastro_pendente')
        return self.get_response(request)

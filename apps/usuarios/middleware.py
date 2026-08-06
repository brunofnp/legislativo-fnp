from allauth.mfa.utils import is_mfa_enabled
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


class MFAObrigatorioStaffMiddleware:
    """Staff (is_staff=True — inclui Root e Administrador FNP) sem 2FA
    ativado só acessa a configuração de MFA, a reautenticação (exigida pelo
    allauth antes de mexer em segurança da conta) e o logout. Contas com
    acesso ao Admin são o alvo mais valioso num fórum de discussão política
    — ver auditoria de segurança em CLAUDE.md.

    Atenção no deploy: todo staff existente sem 2FA configurado fica
    bloqueado (redirecionado pra tela de ativação) no primeiro acesso
    depois que isso subir — avisar a equipe antes, não é silencioso."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated and user.is_staff and not is_mfa_enabled(user):
            caminhos_liberados = (
                reverse('mfa_index'),
                reverse('mfa_activate_totp'),
                reverse('mfa_view_recovery_codes'),
                reverse('mfa_download_recovery_codes'),
                reverse('mfa_generate_recovery_codes'),
                reverse('account_reauthenticate'),
                reverse('account_logout'),
            )
            if request.path not in caminhos_liberados:
                return redirect('mfa_index')
        return self.get_response(request)

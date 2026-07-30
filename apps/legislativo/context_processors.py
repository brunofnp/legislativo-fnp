import re


def _nome_a_partir_do_email(user):
    local = (user.email or user.username).split('@')[0]
    partes = [p.capitalize() for p in re.split(r'[._-]+', local) if p]
    return ' '.join(partes) or user.email


def notificacoes(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}

    nome = user.get_full_name().strip() or _nome_a_partir_do_email(user)

    return {
        'notificacoes_recentes': user.notificacoes.select_related('proposicao').order_by('-criado_em')[:8],
        'notificacoes_nao_lidas': user.notificacoes.filter(lida=False).count(),
        'usuario_display_name': nome,
    }

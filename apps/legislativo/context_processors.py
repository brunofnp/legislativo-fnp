def notificacoes(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}

    return {
        'notificacoes_recentes': user.notificacoes.select_related('proposicao').order_by('-criado_em')[:8],
        'notificacoes_nao_lidas': user.notificacoes.filter(lida=False).count(),
    }

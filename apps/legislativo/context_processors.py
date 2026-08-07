def notificacoes(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}

    return {
        'notificacoes_recentes': user.notificacoes.select_related('proposicao').order_by('-criado_em')[:8],
        'notificacoes_nao_lidas': user.notificacoes.filter(lida=False).count(),
        'usuario_display_name': user.get_display_name(),
        'usuario_avatar_url': user.get_avatar_url(),
    }


def ajuda_pagina(request):
    """Conteúdo do modal "Ajuda desta página" -- global (aplica em qualquer
    template renderizado, incluindo o Django Admin) porque é registrado nos
    TEMPLATES do settings.py, não anexado view a view."""
    from .ajuda_conteudo import ajuda_para_pagina

    url_name = getattr(request.resolver_match, 'url_name', None) if request.resolver_match else None
    return {'ajuda_pagina': ajuda_para_pagina(url_name)}

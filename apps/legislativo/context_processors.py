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


def acoes_legislativo(request):
    """Flags de navegação do cadastro/aprovação de proposições — exibe
    'Cadastrar' para a Equipe FNP e 'Pendentes (N)' para os aprovadores."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}

    from apps.proposicoes.models import Proposicao

    from .views import eh_aprovador, pode_cadastrar

    aprovador = eh_aprovador(user)
    return {
        'pode_cadastrar_proposicao': pode_cadastrar(user),
        'eh_aprovador_legislativo': aprovador,
        'proposicoes_pendentes_count': Proposicao.objects.pendentes().count() if aprovador else 0,
    }


def ajuda_pagina(request):
    """Conteúdo do modal "Ajuda desta página" -- global (aplica em qualquer
    template renderizado, incluindo o Django Admin) porque é registrado nos
    TEMPLATES do settings.py, não anexado view a view."""
    from .ajuda_conteudo import ajuda_para_pagina

    url_name = getattr(request.resolver_match, 'url_name', None) if request.resolver_match else None
    return {'ajuda_pagina': ajuda_para_pagina(url_name)}

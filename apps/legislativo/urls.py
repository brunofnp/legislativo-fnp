from django.urls import path

from .views import (
    FavoritosListView,
    HomeView,
    ParticipacaoListView,
    PerfilView,
    ProposicaoDetailView,
    api_busca_sugestoes,
    api_proposicao_detail,
    api_proposicao_sse,
    api_proposicoes,
    api_proposicoes_cards,
    cadastro_pendente,
    denunciar_comentario,
    exportar_meus_dados,
    ler_notificacao,
    marcar_notificacoes_lidas,
    politica_privacidade,
    solicitar_exclusao,
    toggle_favorito,
)

app_name = 'legislativo'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('proposicao/<int:pk>/', ProposicaoDetailView.as_view(), name='proposicao_detail'),
    path('proposicao/<int:pk>/favoritar/', toggle_favorito, name='toggle_favorito'),
    path('comentario/<int:pk>/denunciar/', denunciar_comentario, name='denunciar_comentario'),
    path('favoritos/', FavoritosListView.as_view(), name='favoritos_list'),
    path('participacoes/', ParticipacaoListView.as_view(), name='participacao_list'),
    path('perfil/', PerfilView.as_view(), name='perfil'),
    path('cadastro-pendente/', cadastro_pendente, name='cadastro_pendente'),
    path('politica-de-privacidade/', politica_privacidade, name='politica_privacidade'),
    path('conta/exportar-meus-dados/', exportar_meus_dados, name='exportar_meus_dados'),
    path('conta/solicitar-exclusao/', solicitar_exclusao, name='solicitar_exclusao'),
    path('notificacoes/<int:pk>/ler/', ler_notificacao, name='ler_notificacao'),
    path('notificacoes/marcar-lidas/', marcar_notificacoes_lidas, name='marcar_notificacoes_lidas'),
    path('api/proposicoes/', api_proposicoes, name='api_proposicoes'),
    path('api/busca-sugestoes/', api_busca_sugestoes, name='api_busca_sugestoes'),
    path('api/proposicoes-cards/', api_proposicoes_cards, name='api_proposicoes_cards'),
    path('api/proposicao/<int:pk>/', api_proposicao_detail, name='api_proposicao_detail'),
    path('api/proposicao-sse/', api_proposicao_sse, name='api_proposicao_sse'),
]

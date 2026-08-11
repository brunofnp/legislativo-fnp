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
    curtir_comentario,
    denunciar_comentario,
    excluir_comentario,
    ler_notificacao,
    marcar_notificacoes_lidas,
    politica_privacidade,
    solicitar_exclusao,
    toggle_favorito,
    usuario_publico,
)

app_name = 'legislativo'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('proposicao/<int:pk>/', ProposicaoDetailView.as_view(), name='proposicao_detail'),
    path('proposicao/<int:pk>/favoritar/', toggle_favorito, name='toggle_favorito'),
    path('comentario/<int:pk>/denunciar/', denunciar_comentario, name='denunciar_comentario'),
    path('comentario/<int:pk>/curtir/', curtir_comentario, name='curtir_comentario'),
    path('comentario/<int:pk>/excluir/', excluir_comentario, name='excluir_comentario'),
    path('favoritos/', FavoritosListView.as_view(), name='favoritos_list'),
    path('participacoes/', ParticipacaoListView.as_view(), name='participacao_list'),
    path('perfil/', PerfilView.as_view(), name='perfil'),
    path('usuario/<int:pk>/', usuario_publico, name='usuario_publico'),
    path('cadastro-pendente/', cadastro_pendente, name='cadastro_pendente'),
    path('politica-de-privacidade/', politica_privacidade, name='politica_privacidade'),
    path('conta/solicitar-exclusao/', solicitar_exclusao, name='solicitar_exclusao'),
    path('notificacoes/<int:pk>/ler/', ler_notificacao, name='ler_notificacao'),
    path('notificacoes/marcar-lidas/', marcar_notificacoes_lidas, name='marcar_notificacoes_lidas'),
    path('api/proposicoes/', api_proposicoes, name='api_proposicoes'),
    path('api/busca-sugestoes/', api_busca_sugestoes, name='api_busca_sugestoes'),
    path('api/proposicoes-cards/', api_proposicoes_cards, name='api_proposicoes_cards'),
    path('api/proposicao/<int:pk>/', api_proposicao_detail, name='api_proposicao_detail'),
    path('api/proposicao-sse/', api_proposicao_sse, name='api_proposicao_sse'),
]

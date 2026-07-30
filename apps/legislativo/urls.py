from django.urls import path

from .views import (
    FavoritosListView,
    HomeView,
    ParticipacaoListView,
    ProposicaoDetailView,
    api_proposicao_detail,
    api_proposicao_sse,
    api_proposicoes,
    ler_notificacao,
    marcar_notificacoes_lidas,
    toggle_favorito,
)

app_name = 'legislativo'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('proposicao/<int:pk>/', ProposicaoDetailView.as_view(), name='proposicao_detail'),
    path('proposicao/<int:pk>/favoritar/', toggle_favorito, name='toggle_favorito'),
    path('favoritos/', FavoritosListView.as_view(), name='favoritos_list'),
    path('participacoes/', ParticipacaoListView.as_view(), name='participacao_list'),
    path('notificacoes/<int:pk>/ler/', ler_notificacao, name='ler_notificacao'),
    path('notificacoes/marcar-lidas/', marcar_notificacoes_lidas, name='marcar_notificacoes_lidas'),
    path('api/proposicoes/', api_proposicoes, name='api_proposicoes'),
    path('api/proposicao/<int:pk>/', api_proposicao_detail, name='api_proposicao_detail'),
    path('api/proposicao-sse/', api_proposicao_sse, name='api_proposicao_sse'),
]

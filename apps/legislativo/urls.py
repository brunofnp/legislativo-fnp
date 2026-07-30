from django.urls import path

from .views import (
    HomeView,
    ParticipacaoListView,
    ProposicaoDetailView,
    api_proposicao_detail,
    api_proposicao_sse,
    api_proposicoes,
)

app_name = 'legislativo'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('proposicao/<int:pk>/', ProposicaoDetailView.as_view(), name='proposicao_detail'),
    path('participacoes/', ParticipacaoListView.as_view(), name='participacao_list'),
    path('api/proposicoes/', api_proposicoes, name='api_proposicoes'),
    path('api/proposicao/<int:pk>/', api_proposicao_detail, name='api_proposicao_detail'),
    path('api/proposicao-sse/', api_proposicao_sse, name='api_proposicao_sse'),
]

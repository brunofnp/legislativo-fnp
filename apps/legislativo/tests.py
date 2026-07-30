from django.test import RequestFactory, TestCase
from django.urls import reverse

from .models import Macrotema, Proposicao, Tema
from .views import HomeView


class ProposicaoModelTest(TestCase):
    def test_criar_proposicao_basica(self):
        proposicao = Proposicao.objects.create(
            titulo='Teste de proposição',
            casa='camara',
            status_tramitacao='Em tramitação',
        )
        self.assertEqual(proposicao.prioridade_fnp, 'normal')
        self.assertEqual(str(proposicao), 'Teste de proposição')


class HomeViewRegressionTest(TestCase):
    def setUp(self):
        macrotema = Macrotema.objects.create(nome='Infraestrutura', slug='infraestrutura', cor='#1A4B8F')
        tema = Tema.objects.create(nome='Transporte', slug='transporte', macrotema=macrotema)
        proposicao1 = Proposicao.objects.create(
            titulo='PL 1234/2025 - Financiamento do Transporte Público',
            casa='camara',
            status_tramitacao='Em tramitação',
            pauta=True,
            urgente=True,
            prioridade_fnp='alta',
            macrotema=macrotema,
            ementa_resumida='Projeto de lei que trata do financiamento do transporte público.',
        )
        proposicao1.temas.set([tema])
        proposicao2 = Proposicao.objects.create(
            titulo='PL 5678/2025 - Fortalecimento do Sistema Municipal',
            casa='senado',
            status_tramitacao='Aguardando parecer',
            pauta=False,
            urgente=False,
            prioridade_fnp='media',
            macrotema=macrotema,
            ementa_resumida='Projeto que visa ampliar a atuação dos municípios.',
        )
        proposicao2.temas.set([tema])

    def test_home_view_renders_briefing_cards_with_count_stats(self):
        request = RequestFactory().get(reverse('legislativo:home'))
        response = HomeView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('card-brief', content)
        self.assertIn('PL 1234/2025 - Financiamento do Transporte Público', content)
        self.assertIn('stats-total', content)
        self.assertIn('stats-pauta', content)

import json
import tempfile

from django.contrib.auth.models import Group
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.management import call_command
from django.test import RequestFactory, TestCase
from django.urls import reverse

from .models import EdicaoMeritoHistorico, Macrotema, Proposicao, Tema, Usuario
from .views import HomeView, PerfilView


def _request_with_session(path):
    request = RequestFactory().get(path)
    SessionMiddleware(lambda req: None).process_request(request)
    request.session.save()
    return request


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
        request = _request_with_session(reverse('legislativo:home'))
        response = HomeView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('card-brief', content)
        self.assertIn('PL 1234/2025 - Financiamento do Transporte Público', content)
        self.assertIn('stats-total', content)
        self.assertIn('stats-pauta', content)


class UsuarioDisplayNameTest(TestCase):
    def test_usa_nome_completo_quando_disponivel(self):
        usuario = Usuario.objects.create(
            username='bruno', email='bruno.marra@fnp.org.br', first_name='Bruno', last_name='Marra',
        )
        self.assertEqual(usuario.get_display_name(), 'Bruno Marra')

    def test_deriva_do_email_quando_sem_nome_cadastrado(self):
        usuario = Usuario.objects.create(username='joana.silva', email='joana.silva@fnp.org.br')
        self.assertEqual(usuario.get_display_name(), 'Joana Silva')


class PerfilSignalTest(TestCase):
    def test_novo_usuario_ganha_perfil_automaticamente(self):
        usuario = Usuario.objects.create(username='ana', email='ana@fnp.org.br')
        self.assertIsNotNone(usuario.perfil)


class PerfilViewTest(TestCase):
    def test_perfil_view_renderiza_dados_de_usuario_e_de_perfil(self):
        usuario = Usuario.objects.create(
            username='bruno', email='bruno.marra@fnp.org.br', first_name='Bruno', last_name='Marra',
        )
        usuario.perfil.telefone = '(61) 99999-0000'
        usuario.perfil.cargo = 'Coordenador'
        usuario.perfil.save()

        request = _request_with_session(reverse('legislativo:perfil'))
        request.user = usuario
        response = PerfilView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('(61) 99999-0000', content)
        self.assertIn('Coordenador', content)


class UsuarioGroupSignalTest(TestCase):
    def test_novo_usuario_entra_no_grupo_usuario(self):
        usuario = Usuario.objects.create(username='novo', email='novo@fnp.org.br')
        self.assertTrue(usuario.groups.filter(name='Usuário').exists())

    def test_superusuario_nao_entra_no_grupo_usuario(self):
        usuario = Usuario.objects.create(username='root2', email='root2@fnp.org.br', is_superuser=True)
        self.assertFalse(usuario.groups.filter(name='Usuário').exists())


class SetupRolesCommandTest(TestCase):
    def test_comando_e_idempotente_e_promove_root(self):
        Usuario.objects.create(username='bruno', email='bruno.marra@fnp.org.br')

        call_command('setup_roles')
        call_command('setup_roles')  # rodar duas vezes não deve duplicar grupo nem quebrar

        self.assertEqual(Group.objects.filter(name='Root').count(), 1)
        usuario = Usuario.objects.get(email='bruno.marra@fnp.org.br')
        self.assertTrue(usuario.is_superuser)
        self.assertTrue(usuario.is_staff)
        self.assertTrue(usuario.groups.filter(name='Root').exists())


class EdicaoMeritoHistoricoIngestTest(TestCase):
    def test_reingestao_com_campo_de_merito_alterado_grava_historico(self):
        registro = [{'Proposição': 'PL 999/2025', 'Casa': 'Camara', 'Posicionamento da FNP': 'Posição inicial'}]
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as arquivo:
            json.dump(registro, arquivo)
            caminho = arquivo.name

        call_command('ingest_legislativo', caminho)
        self.assertEqual(EdicaoMeritoHistorico.objects.count(), 0)  # criação inicial não gera histórico

        registro[0]['Posicionamento da FNP'] = 'Posição revisada'
        with open(caminho, 'w', encoding='utf-8') as arquivo:
            json.dump(registro, arquivo)

        call_command('ingest_legislativo', caminho)

        historico = EdicaoMeritoHistorico.objects.get()
        self.assertEqual(historico.campo, 'posicionamento_fnp')
        self.assertEqual(historico.valor_anterior, 'Posição inicial')
        self.assertEqual(historico.valor_novo, 'Posição revisada')
        self.assertIsNone(historico.autor)

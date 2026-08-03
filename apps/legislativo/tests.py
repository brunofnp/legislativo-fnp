import io
import json
import tempfile

from django.contrib.auth.models import Group
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.comentarios.models import Comentario, PalavraProibida
from apps.comentarios.moderacao import classificar_comentario, contem_palavra_proibida
from apps.proposicoes.models import EdicaoMeritoHistorico, Macrotema, Proposicao, Tema
from apps.usuarios.middleware import CadastroPendenteMiddleware
from apps.usuarios.models import Perfil, Usuario

from .throttling import rate_limited
from .views import (
    PROPOSICOES_POR_PAGINA,
    HomeView,
    PerfilView,
    denunciar_comentario,
    exportar_meus_dados,
    get_home_sections,
    solicitar_exclusao,
)


def _request_with_session(path):
    request = RequestFactory().get(path)
    SessionMiddleware(lambda req: None).process_request(request)
    request.session.save()
    return request


def _post_request_with_session(path, data=None):
    request = RequestFactory().post(path, data=data or {})
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


class ModeracaoAutomaticaTest(TestCase):
    def test_comentario_normal_e_aprovado(self):
        self.assertEqual(classificar_comentario('Ótima iniciativa, parabéns!'), 'aprovado')

    def test_comentario_com_palavra_proibida_e_reprovado(self):
        PalavraProibida.objects.create(palavra='droga')
        self.assertEqual(classificar_comentario('Isso é uma droga de proposta'), 'rejeitado')

    def test_checagem_ignora_acento_e_caixa(self):
        PalavraProibida.objects.create(palavra='droga')
        self.assertTrue(contem_palavra_proibida('Isso é uma DRÓGA de proposta'))

    def test_nao_bloqueia_substring_dentro_de_outra_palavra(self):
        PalavraProibida.objects.create(palavra='droga')
        self.assertFalse(contem_palavra_proibida('Precisamos de uma drogaria no bairro'))

    def test_palavra_inativa_nao_bloqueia(self):
        PalavraProibida.objects.create(palavra='droga', ativa=False)
        self.assertEqual(classificar_comentario('isso é uma droga'), 'aprovado')


class CadastroPendenteMiddlewareTest(TestCase):
    def _passa_pela_middleware(self, usuario, path='/qualquer-pagina/'):
        request = RequestFactory().get(path)
        request.user = usuario
        middleware = CadastroPendenteMiddleware(lambda req: HttpResponse('ok'))
        return middleware(request)

    def test_usuario_pendente_e_redirecionado(self):
        usuario = Usuario.objects.create(username='pendente1', email='pendente1@fnp.org.br')
        response = self._passa_pela_middleware(usuario)
        self.assertEqual(response.status_code, 302)
        self.assertIn('cadastro-pendente', response.url)

    def test_usuario_aprovado_passa_direto(self):
        usuario = Usuario.objects.create(username='aprovado1', email='aprovado1@fnp.org.br')
        usuario.perfil.status_aprovacao = Perfil.APROVADO
        usuario.perfil.save()
        response = self._passa_pela_middleware(usuario)
        self.assertEqual(response.status_code, 200)

    def test_staff_passa_direto_mesmo_com_cadastro_pendente(self):
        usuario = Usuario.objects.create(username='staffx', email='staffx@fnp.org.br', is_staff=True)
        usuario.perfil.status_aprovacao = Perfil.PENDENTE
        usuario.perfil.save()
        response = self._passa_pela_middleware(usuario)
        self.assertEqual(response.status_code, 200)


class DenunciaComentarioTest(TestCase):
    def setUp(self):
        self.proposicao = Proposicao.objects.create(titulo='PL teste denúncia', casa='camara')
        self.autor = Usuario.objects.create(username='autor_d', email='autor_d@fnp.org.br')
        self.comentario = Comentario.objects.create(
            proposicao=self.proposicao, texto='comentário', autor=self.autor, status_moderacao='aprovado',
        )

    def _denunciar(self, usuario):
        request = _post_request_with_session(f'/comentario/{self.comentario.pk}/denunciar/')
        request.user = usuario
        return denunciar_comentario(request, pk=self.comentario.pk)

    def test_denuncia_unica_nao_oculta_comentario(self):
        denunciante = Usuario.objects.create(username='d1', email='d1@fnp.org.br')
        self._denunciar(denunciante)
        self.comentario.refresh_from_db()
        self.assertEqual(self.comentario.status_moderacao, 'aprovado')
        self.assertEqual(self.comentario.denuncias.count(), 1)

    def test_atingir_limite_de_denuncias_oculta_comentario(self):
        for i in range(Comentario.DENUNCIAS_PARA_OCULTAR):
            denunciante = Usuario.objects.create(username=f'd{i}', email=f'd{i}@fnp.org.br')
            self._denunciar(denunciante)
        self.comentario.refresh_from_db()
        self.assertEqual(self.comentario.status_moderacao, 'pendente')

    def test_mesmo_usuario_nao_denuncia_duas_vezes(self):
        denunciante = Usuario.objects.create(username='drepetido', email='drepetido@fnp.org.br')
        self._denunciar(denunciante)
        self._denunciar(denunciante)
        self.comentario.refresh_from_db()
        self.assertEqual(self.comentario.denuncias.count(), 1)


class LGPDTest(TestCase):
    def test_exportar_meus_dados_retorna_json_com_campos_esperados(self):
        usuario = Usuario.objects.create(username='lgpd1', email='lgpd1@fnp.org.br', first_name='Ana')
        request = _request_with_session(reverse('legislativo:exportar_meus_dados'))
        request.user = usuario
        response = exportar_meus_dados(request)

        self.assertEqual(response.status_code, 200)
        dados = json.loads(response.content)
        self.assertEqual(dados['usuario']['email'], 'lgpd1@fnp.org.br')
        self.assertIn('attachment', response['Content-Disposition'])

    def test_solicitar_exclusao_marca_data_no_perfil(self):
        usuario = Usuario.objects.create(username='lgpd2', email='lgpd2@fnp.org.br')
        self.assertIsNone(usuario.perfil.exclusao_solicitada_em)

        request = _post_request_with_session(reverse('legislativo:solicitar_exclusao'))
        request.user = usuario
        response = solicitar_exclusao(request)

        self.assertEqual(response.status_code, 200)
        usuario.perfil.refresh_from_db()
        self.assertIsNotNone(usuario.perfil.exclusao_solicitada_em)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class AvatarUrlTest(TestCase):
    def test_sem_foto_retorna_none(self):
        usuario = Usuario.objects.create(username='av1', email='av1@fnp.org.br')
        self.assertIsNone(usuario.get_avatar_url())

    def test_foto_google_e_usada_como_fallback(self):
        usuario = Usuario.objects.create(username='av2', email='av2@fnp.org.br')
        usuario.perfil.foto_google_url = 'https://exemplo.com/foto.jpg'
        usuario.perfil.save()
        self.assertEqual(usuario.get_avatar_url(), 'https://exemplo.com/foto.jpg')

    def test_foto_manual_tem_prioridade_sobre_a_do_google(self):
        usuario = Usuario.objects.create(username='av3', email='av3@fnp.org.br')
        usuario.perfil.foto_google_url = 'https://exemplo.com/foto.jpg'
        buffer = io.BytesIO()
        Image.new('RGB', (2, 2)).save(buffer, format='PNG')
        usuario.perfil.foto.save('avatar.png', SimpleUploadedFile('avatar.png', buffer.getvalue()), save=True)

        self.assertIn('avatar', usuario.get_avatar_url())
        self.assertNotEqual(usuario.get_avatar_url(), 'https://exemplo.com/foto.jpg')


class RateLimitTest(TestCase):
    def setUp(self):
        cache.clear()

    def test_bloqueia_apos_atingir_o_limite(self):
        request = _post_request_with_session('/qualquer/')
        for _ in range(3):
            self.assertFalse(rate_limited('teste', request, limit=3, window_seconds=60))
        self.assertTrue(rate_limited('teste', request, limit=3, window_seconds=60))

    def test_prefixos_diferentes_nao_compartilham_limite(self):
        request = _post_request_with_session('/qualquer/')
        for _ in range(3):
            self.assertFalse(rate_limited('comentario', request, limit=3, window_seconds=60))
        self.assertFalse(rate_limited('participacao', request, limit=3, window_seconds=60))


class PaginacaoHomeTest(TestCase):
    def test_home_pagina_quando_mais_de_uma_pagina_de_resultado(self):
        for i in range(PROPOSICOES_POR_PAGINA + 5):
            Proposicao.objects.create(titulo=f'PL paginação {i}', casa='camara')

        sections = get_home_sections('', '', page_number=1)

        self.assertEqual(sections['page_obj'].paginator.num_pages, 2)
        self.assertEqual(len(sections['proposicoes']), PROPOSICOES_POR_PAGINA)

import io
import json
import tempfile

from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.comentarios.models import Comentario, ComentarioLike, PalavraProibida
from apps.comentarios.moderacao import classificar_comentario, contem_palavra_proibida
from apps.proposicoes.models import EdicaoMeritoHistorico, Macrotema, Proposicao, Tema
from apps.usuarios.middleware import CadastroPendenteMiddleware, MFAObrigatorioStaffMiddleware
from apps.usuarios.models import Perfil, Usuario

from .forms import ComentarioForm
from .throttling import _client_ip, rate_limited
from .views import (
    PROPOSICOES_POR_PAGINA,
    HomeView,
    ParticipacaoListView,
    PerfilView,
    ProposicaoDetailView,
    curtir_comentario,
    denunciar_comentario,
    get_filtered_proposicoes,
    get_home_sections,
    solicitar_exclusao,
    usuario_publico,
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


class MFAObrigatorioStaffMiddlewareTest(TestCase):
    def _passa_pela_middleware(self, usuario, path='/qualquer-pagina/'):
        request = RequestFactory().get(path)
        request.user = usuario
        middleware = MFAObrigatorioStaffMiddleware(lambda req: HttpResponse('ok'))
        return middleware(request)

    def test_staff_sem_2fa_e_redirecionado_pra_ativacao(self):
        usuario = Usuario.objects.create(username='staffsem2fa', email='staffsem2fa@fnp.org.br', is_staff=True)
        response = self._passa_pela_middleware(usuario)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/2fa/', response.url)

    def test_staff_com_2fa_passa_direto(self):
        from allauth.mfa.models import Authenticator

        usuario = Usuario.objects.create(username='staffcom2fa', email='staffcom2fa@fnp.org.br', is_staff=True)
        Authenticator.objects.create(user=usuario, type=Authenticator.Type.TOTP, data={})
        response = self._passa_pela_middleware(usuario)
        self.assertEqual(response.status_code, 200)

    def test_usuario_comum_sem_2fa_nao_e_afetado(self):
        usuario = Usuario.objects.create(username='comumsem2fa', email='comumsem2fa@fnp.org.br', is_staff=False)
        response = self._passa_pela_middleware(usuario)
        self.assertEqual(response.status_code, 200)

    def test_pagina_de_ativacao_do_2fa_fica_liberada_pro_staff_sem_2fa(self):
        usuario = Usuario.objects.create(username='staffativando', email='staffativando@fnp.org.br', is_staff=True)
        response = self._passa_pela_middleware(usuario, path=reverse('mfa_activate_totp'))
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
    def test_solicitar_exclusao_marca_data_no_perfil(self):
        usuario = Usuario.objects.create(username='lgpd2', email='lgpd2@fnp.org.br')
        self.assertIsNone(usuario.perfil.exclusao_solicitada_em)

        request = _post_request_with_session(reverse('legislativo:solicitar_exclusao'))
        request.user = usuario
        response = solicitar_exclusao(request)

        self.assertEqual(response.status_code, 200)
        usuario.perfil.refresh_from_db()
        self.assertIsNotNone(usuario.perfil.exclusao_solicitada_em)


class ExportarDadosEngajamentoTest(TestCase):
    """Exportação em massa/por usuário pro Root -- diferente da exportação
    de LGPD (LGPDTest acima), que cada usuário faz só dos próprios dados."""

    def setUp(self):
        self.root = Usuario.objects.create(
            username='rootexp', email='rootexp@fnp.org.br', is_staff=True, is_superuser=True,
        )
        self.staff_comum = Usuario.objects.create(
            username='staffexp', email='staffexp@fnp.org.br', is_staff=True,
        )
        self.usuario = Usuario.objects.create(username='alvoexp', email='alvoexp@fnp.org.br', first_name='Alvo')

    def test_nao_superuser_recebe_permission_denied(self):
        from django.core.exceptions import PermissionDenied

        from apps.usuarios.admin_views import exportar_dados_view

        request = _request_with_session('/admin/exportar-dados/')
        request.user = self.staff_comum
        with self.assertRaises(PermissionDenied):
            exportar_dados_view(request)

    def test_superuser_exportacao_em_massa_inclui_todos_os_usuarios(self):
        from apps.usuarios.admin_views import exportar_dados_view

        request = _post_request_with_session('/admin/exportar-dados/', {'modo': 'massa'})
        request.user = self.root
        response = exportar_dados_view(request)

        self.assertEqual(response.status_code, 200)
        dados = json.loads(response.content)
        self.assertEqual(dados['total_usuarios'], Usuario.objects.count())
        self.assertIn('attachment', response['Content-Disposition'])

    def test_superuser_exportacao_de_um_usuario_especifico(self):
        from apps.usuarios.admin_views import exportar_dados_view

        request = _post_request_with_session(
            '/admin/exportar-dados/', {'modo': 'usuario', 'usuario_id': self.usuario.pk},
        )
        request.user = self.root
        response = exportar_dados_view(request)

        dados = json.loads(response.content)
        self.assertEqual(dados['total_usuarios'], 1)
        self.assertEqual(dados['usuarios'][0]['cadastro']['email'], 'alvoexp@fnp.org.br')


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

    def test_foto_maior_que_o_limite_e_rejeitada(self):
        from django.core.exceptions import ValidationError

        from apps.usuarios.models import FOTO_PERFIL_TAMANHO_MAXIMO_MB, validar_tamanho_foto_perfil

        usuario = Usuario.objects.create(username='av4', email='av4@fnp.org.br')
        buffer = io.BytesIO()
        Image.new('RGB', (2, 2)).save(buffer, format='PNG')
        arquivo = SimpleUploadedFile('avatar.png', buffer.getvalue())
        arquivo.size = FOTO_PERFIL_TAMANHO_MAXIMO_MB * 1024 * 1024 + 1  # simula arquivo grande sem gerar bytes reais

        with self.assertRaises(ValidationError):
            validar_tamanho_foto_perfil(arquivo)

        usuario.perfil.foto = arquivo
        with self.assertRaises(ValidationError):
            usuario.perfil.full_clean()


class CustomSignupFormCaptchaTest(TestCase):
    def test_sem_chaves_configuradas_formulario_nao_tem_campo_captcha(self):
        from .forms import CustomSignupForm

        self.assertNotIn('captcha', CustomSignupForm().fields)

    @override_settings(RECAPTCHA_HABILITADO=True)
    def test_com_chaves_configuradas_formulario_ganha_campo_captcha(self):
        from .forms import CustomSignupForm

        self.assertIn('captcha', CustomSignupForm().fields)


class GoogleSignupDomainRestrictionTest(TestCase):
    """Cadastro novo via Google só é aberto pra e-mail @fnp.org.br -- login
    de quem já tem conta não passa por is_open_for_signup (ver docstring
    do adapter), então não é coberto/afetado por este teste."""

    class _ContaSocialFalsa:
        def __init__(self, email):
            self.user = type('UsuarioFalso', (), {'email': email})()
            self.account = type('SocialAccountFalso', (), {'extra_data': {'email': email}})()

    def test_email_institucional_pode_se_cadastrar(self):
        from apps.usuarios.adapters import GoogleAccountAdapter

        adapter = GoogleAccountAdapter()
        sociallogin = self._ContaSocialFalsa('funcionario@fnp.org.br')
        self.assertTrue(adapter.is_open_for_signup(None, sociallogin))

    def test_email_nao_institucional_nao_pode_se_cadastrar(self):
        from apps.usuarios.adapters import GoogleAccountAdapter

        adapter = GoogleAccountAdapter()
        sociallogin = self._ContaSocialFalsa('prefeito@algummunicipio.gov.br')
        self.assertFalse(adapter.is_open_for_signup(None, sociallogin))


class UsernamePadraoTest(TestCase):
    """Username de cadastro novo segue "nome.sobrenome" (ex.: Bruno Marra ->
    bruno.marra), mesmo padrão das contas já cadastradas manualmente --
    sem isso o allauth usaria só o primeiro nome."""

    def test_nome_e_sobrenome_viram_nome_ponto_sobrenome(self):
        from apps.usuarios.adapters import CustomAccountAdapter

        usuario = Usuario(first_name='Bruno', last_name='Marra', email='brunoteste@fnp.org.br')
        CustomAccountAdapter().populate_username(None, usuario)
        self.assertEqual(usuario.username, 'bruno.marra')

    def test_acentos_sao_removidos(self):
        from apps.usuarios.adapters import CustomAccountAdapter

        usuario = Usuario(first_name='José', last_name='Andrade', email='joseandrade@fnp.org.br')
        CustomAccountAdapter().populate_username(None, usuario)
        self.assertEqual(usuario.username, 'jose.andrade')

    def test_username_ja_existente_ganha_sufixo_unico(self):
        from apps.usuarios.adapters import CustomAccountAdapter

        Usuario.objects.create(username='bruno.marra', email='brunooriginal@fnp.org.br')
        usuario = Usuario(first_name='Bruno', last_name='Marra', email='brunosegundo@fnp.org.br')
        CustomAccountAdapter().populate_username(None, usuario)
        self.assertNotEqual(usuario.username, 'bruno.marra')
        self.assertTrue(usuario.username.startswith('bruno.marra'))

    def test_sem_sobrenome_cai_no_padrao_do_allauth(self):
        from apps.usuarios.adapters import CustomAccountAdapter

        usuario = Usuario(first_name='Nucleo', last_name='', email='nucleo2@fnp.org.br')
        CustomAccountAdapter().populate_username(None, usuario)
        self.assertEqual(usuario.username, 'nucleo')


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


class AcessoAdminViaGrupoTest(TestCase):
    """Adicionar alguém a Administrador FNP/Root pelo widget de grupos do
    Admin precisa conceder is_staff sozinho -- sem isso a pessoa nem
    conseguia logar em /admin/, e a sidebar do site nunca mostrava o link
    "Painel Admin" (que checava só is_superuser antes desta correção)."""

    def test_adicionar_ao_grupo_administrador_fnp_concede_staff(self):
        call_command('setup_roles')
        usuario = Usuario.objects.create(username='novoadm', email='novoadm@fnp.org.br')
        self.assertFalse(usuario.is_staff)

        grupo = Group.objects.get(name='Administrador FNP')
        usuario.groups.add(grupo)

        usuario.refresh_from_db()
        self.assertTrue(usuario.is_staff)

    def test_usuario_comum_sem_grupo_admin_nao_ganha_staff(self):
        usuario = Usuario.objects.create(username='comumx', email='comumx@fnp.org.br')
        self.assertFalse(usuario.is_staff)


class HomeFiltroEstatisticaTest(TestCase):
    def setUp(self):
        self.pauta = Proposicao.objects.create(titulo='PL na pauta', casa='camara', pauta=True)
        Proposicao.objects.create(titulo='PL fora da pauta', casa='camara', pauta=False)

    def test_filtro_pauta_retorna_so_proposicoes_na_pauta(self):
        proposicoes = get_filtered_proposicoes('', '', filtro='pauta')
        self.assertEqual(list(proposicoes), [self.pauta])

    def test_home_view_marca_filtro_ativo_no_contexto(self):
        request = _request_with_session(reverse('legislativo:home') + '?filtro=pauta')
        response = HomeView.as_view()(request)
        content = response.content.decode('utf-8')
        self.assertIn('Na pauta (1)', content)
        self.assertIn('Limpar filtro', content)
        # Com filtro ativo, as seções fixas (Urgentes/Em alta) somem da página.
        self.assertNotIn('id="cards-urgentes"', content)


class HomeFiltroPorMacrotemaTest(TestCase):
    def test_tema_slug_casa_com_macrotema_tambem(self):
        macrotema = Macrotema.objects.create(nome='Meio Ambiente', slug='meio-ambiente', cor='#15803d')
        proposicao = Proposicao.objects.create(titulo='PL ambiental', casa='camara', macrotema=macrotema)
        Proposicao.objects.create(titulo='PL qualquer', casa='camara')

        proposicoes = get_filtered_proposicoes('', 'meio-ambiente')
        self.assertEqual(list(proposicoes), [proposicao])


class RespostaAninhadaTest(TestCase):
    """O model já suportava profundidade ilimitada via parent -- o que
    faltava era o template renderizar recursivamente e permitir responder
    a uma resposta (não só a comentários de primeiro nível)."""

    def test_resposta_de_resposta_aparece_na_pagina(self):
        proposicao = Proposicao.objects.create(titulo='PL teste aninhamento', casa='camara')
        autor = Usuario.objects.create(username='autoresq', email='autoresq@fnp.org.br')
        raiz = Comentario.objects.create(
            proposicao=proposicao, texto='comentário raiz', autor=autor, status_moderacao='aprovado',
        )
        resposta1 = Comentario.objects.create(
            proposicao=proposicao, texto='primeira resposta', autor=autor, parent=raiz, status_moderacao='aprovado',
        )
        Comentario.objects.create(
            proposicao=proposicao, texto='resposta da resposta', autor=autor, parent=resposta1,
            status_moderacao='aprovado',
        )

        request = _request_with_session(f'/proposicao/{proposicao.pk}/')
        request.user = autor
        response = ProposicaoDetailView.as_view()(request, pk=proposicao.pk)
        content = response.content.decode('utf-8')

        self.assertIn('primeira resposta', content)
        self.assertIn('resposta da resposta', content)
        # "Responder" precisa existir também dentro do bloco aninhado, não só
        # no comentário raiz -- checa que aparece mais de uma vez.
        self.assertGreater(content.count('data-parent-id="'), 1)


class EnviarParticipacaoRemovidaTest(TestCase):
    def test_pagina_da_proposicao_nao_tem_mais_o_formulario_avulso(self):
        proposicao = Proposicao.objects.create(titulo='PL sem participação avulsa', casa='camara')
        request = _request_with_session(f'/proposicao/{proposicao.pk}/')
        request.user = Usuario.objects.create(username='semparticip', email='semparticip@fnp.org.br')
        response = ProposicaoDetailView.as_view()(request, pk=proposicao.pk)
        content = response.content.decode('utf-8')
        self.assertNotIn('Enviar participação', content)


class ParticipacoesComoEngajamentoTest(TestCase):
    """"Participações" mostra só as proposições em que o próprio usuário
    logado comentou -- não é mais uma lista pública de Participacao."""

    def test_requer_login(self):
        request = _request_with_session(reverse('legislativo:participacao_list'))
        from django.contrib.auth.models import AnonymousUser

        request.user = AnonymousUser()
        response = ParticipacaoListView.as_view()(request)
        self.assertEqual(response.status_code, 302)

    def test_mostra_so_proposicoes_do_proprio_usuario(self):
        proposicao_minha = Proposicao.objects.create(titulo='PL que comentei', casa='camara')
        proposicao_outro = Proposicao.objects.create(titulo='PL de outra pessoa', casa='camara')
        eu = Usuario.objects.create(username='euparticipo', email='euparticipo@fnp.org.br')
        outro = Usuario.objects.create(username='outroparticipa', email='outroparticipa@fnp.org.br')
        Comentario.objects.create(proposicao=proposicao_minha, texto='comentei', autor=eu, status_moderacao='aprovado')
        Comentario.objects.create(proposicao=proposicao_outro, texto='comentou', autor=outro, status_moderacao='aprovado')

        request = _request_with_session(reverse('legislativo:participacao_list'))
        request.user = eu
        response = ParticipacaoListView.as_view()(request)
        content = response.content.decode('utf-8')

        self.assertIn('PL que comentei', content)
        self.assertNotIn('PL de outra pessoa', content)


class PerfilEmailEditavelTest(TestCase):
    def test_alterar_email_atualiza_usuario_e_email_address_do_allauth(self):
        from allauth.account.models import EmailAddress

        usuario = Usuario.objects.create(username='trocaemail', email='antigo@fnp.org.br', first_name='Troca')
        request = _post_request_with_session(
            reverse('legislativo:perfil'),
            {'first_name': 'Troca', 'last_name': '', 'email': 'novo@fnp.org.br'},
        )
        request.user = usuario
        response = PerfilView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        usuario.refresh_from_db()
        self.assertEqual(usuario.email, 'novo@fnp.org.br')
        self.assertTrue(EmailAddress.objects.filter(user=usuario, email='novo@fnp.org.br', verified=False).exists())

    def test_nao_permite_email_ja_usado_por_outro_usuario(self):
        Usuario.objects.create(username='dono', email='ocupado@fnp.org.br')
        usuario = Usuario.objects.create(username='querendo', email='livre@fnp.org.br', first_name='Q')
        request = _post_request_with_session(
            reverse('legislativo:perfil'),
            {'first_name': 'Q', 'last_name': '', 'email': 'ocupado@fnp.org.br'},
        )
        request.user = usuario
        PerfilView.as_view()(request)

        usuario.refresh_from_db()
        self.assertEqual(usuario.email, 'livre@fnp.org.br')  # não mudou


class ComentarioLikeTest(TestCase):
    def test_curtir_e_descurtir_alterna(self):
        proposicao = Proposicao.objects.create(titulo='PL curtido', casa='camara')
        autor = Usuario.objects.create(username='autorcurtido', email='autorcurtido@fnp.org.br')
        curtidor = Usuario.objects.create(username='curtidor', email='curtidor@fnp.org.br')
        comentario = Comentario.objects.create(
            proposicao=proposicao, texto='comentário curtido', autor=autor, status_moderacao='aprovado',
        )

        request = _post_request_with_session(f'/comentario/{comentario.pk}/curtir/')
        request.user = curtidor
        curtir_comentario(request, pk=comentario.pk)
        self.assertEqual(comentario.likes.count(), 1)

        request2 = _post_request_with_session(f'/comentario/{comentario.pk}/curtir/')
        request2.user = curtidor
        curtir_comentario(request2, pk=comentario.pk)
        self.assertEqual(comentario.likes.count(), 0)

    def test_likes_entram_no_ranking_em_alta(self):
        proposicao = Proposicao.objects.create(titulo='PL bombou de like', casa='camara')
        autor = Usuario.objects.create(username='autorbombou', email='autorbombou@fnp.org.br')
        comentario = Comentario.objects.create(
            proposicao=proposicao, texto='comentário', autor=autor, status_moderacao='aprovado',
        )
        for i in range(3):
            curtidor = Usuario.objects.create(username=f'curtidor{i}', email=f'curtidor{i}@fnp.org.br')
            ComentarioLike.objects.create(comentario=comentario, usuario=curtidor)

        sections = get_home_sections('', '')
        self.assertIn(proposicao, list(sections['em_alta']))


class DefinirSenhaSocialTest(TestCase):
    """Conta sem senha local (login só via Google) não pode criar uma senha
    direto a partir da sessão -- precisa confirmar pelo e-mail cadastrado,
    reaproveitando o fluxo de "Esqueci minha senha" do allauth."""

    def test_usuario_sem_senha_ve_tela_de_confirmacao_por_email(self):
        from apps.usuarios.views import definir_senha_social

        usuario = Usuario.objects.create(username='soogoogle', email='soogoogle@fnp.org.br')
        usuario.set_unusable_password()
        usuario.save()
        self.assertFalse(usuario.has_usable_password())

        request = _request_with_session('/contas/password/set/')
        request.user = usuario
        response = definir_senha_social(request)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('ainda não tem uma senha', content)

    def test_post_envia_email_de_confirmacao(self):
        from django.core import mail

        from apps.usuarios.views import definir_senha_social

        usuario = Usuario.objects.create(username='soogoogle2', email='soogoogle2@fnp.org.br')
        usuario.set_unusable_password()
        usuario.save()
        request = _post_request_with_session('/contas/password/set/')
        request.user = usuario
        response = definir_senha_social(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn('Confira seu e-mail', response.content.decode('utf-8'))
        self.assertEqual(len(mail.outbox), 1)

    def test_usuario_com_senha_e_redirecionado_pra_alterar_senha(self):
        from apps.usuarios.views import definir_senha_social

        usuario = Usuario.objects.create(username='comsenha', email='comsenha@fnp.org.br')
        usuario.set_password('umasenhaqualquer123')
        usuario.save()

        request = _request_with_session('/contas/password/set/')
        request.user = usuario
        response = definir_senha_social(request)

        self.assertEqual(response.status_code, 302)
        self.assertIn('password/change', response.url)


class UsuarioPublicoTest(TestCase):
    def test_pagina_publica_mostra_proposicoes_comentadas(self):
        proposicao = Proposicao.objects.create(titulo='PL do fulano', casa='camara')
        fulano = Usuario.objects.create(username='fulano', email='fulano@fnp.org.br', first_name='Fulano')
        Comentario.objects.create(proposicao=proposicao, texto='oi', autor=fulano, status_moderacao='aprovado')

        request = _request_with_session(f'/usuario/{fulano.pk}/')
        from django.contrib.auth.models import AnonymousUser

        request.user = AnonymousUser()
        response = usuario_publico(request, pk=fulano.pk)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('Fulano', content)
        self.assertIn('PL do fulano', content)


class ComentarioParentEscopadoTest(TestCase):
    """Auditoria de segurança 2026-08-11: 'parent' (campo escondido do form
    de comentário) não podia apontar pra um comentário de outra proposição --
    sem isso, um POST manual conseguia encaixar uma resposta na árvore de
    comentários de uma proposição diferente da que o formulário pertence."""

    def setUp(self):
        self.autor = Usuario.objects.create(username='autorparent', email='autorparent@fnp.org.br')
        self.proposicao_a = Proposicao.objects.create(titulo='PL A', casa='camara')
        self.proposicao_b = Proposicao.objects.create(titulo='PL B', casa='camara')
        self.comentario_raiz_b = Comentario.objects.create(
            proposicao=self.proposicao_b, texto='raiz em B', autor=self.autor, status_moderacao='aprovado',
        )

    def test_parent_de_outra_proposicao_e_rejeitado(self):
        form = ComentarioForm(
            data={'texto': 'tentando responder em B a partir de A', 'parent': self.comentario_raiz_b.pk},
            proposicao=self.proposicao_a,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('parent', form.errors)

    def test_parent_da_mesma_proposicao_e_aceito(self):
        comentario_raiz_a = Comentario.objects.create(
            proposicao=self.proposicao_a, texto='raiz em A', autor=self.autor, status_moderacao='aprovado',
        )
        form = ComentarioForm(
            data={'texto': 'resposta legítima em A', 'parent': comentario_raiz_a.pk},
            proposicao=self.proposicao_a,
        )
        self.assertTrue(form.is_valid())

    def test_post_view_com_parent_de_outra_proposicao_nao_salva_comentario(self):
        request = _post_request_with_session(
            f'/proposicao/{self.proposicao_a.pk}/',
            {'texto': 'ataque via view', 'parent': self.comentario_raiz_b.pk},
        )
        request.user = self.autor
        ProposicaoDetailView.as_view()(request, pk=self.proposicao_a.pk)

        self.assertFalse(Comentario.objects.filter(texto='ataque via view').exists())


class EmailConfirmadoNoAdminTest(TestCase):
    """A coluna 'E-mail confirmado' do UsuarioAdmin dá ao Root o sinal que
    faltava pra recusar um cadastro suspeito antes de aprovar, já que o
    cadastro por e-mail/senha não exige confirmação pra navegar."""

    def test_email_nao_confirmado_aparece_como_false(self):
        from allauth.account.models import EmailAddress

        from apps.usuarios.admin import UsuarioAdmin

        usuario = Usuario.objects.create(username='naoconfirmado', email='naoconfirmado@fnp.org.br')
        EmailAddress.objects.create(user=usuario, email=usuario.email, verified=False, primary=True)

        admin_instance = UsuarioAdmin(Usuario, admin.site)
        request = _request_with_session('/admin/usuarios/usuario/')
        obj = admin_instance.get_queryset(request).get(pk=usuario.pk)

        self.assertFalse(admin_instance.email_confirmado(obj))

    def test_email_confirmado_aparece_como_true(self):
        from allauth.account.models import EmailAddress

        from apps.usuarios.admin import UsuarioAdmin

        usuario = Usuario.objects.create(username='confirmado', email='confirmado@fnp.org.br')
        EmailAddress.objects.create(user=usuario, email=usuario.email, verified=True, primary=True)

        admin_instance = UsuarioAdmin(Usuario, admin.site)
        request = _request_with_session('/admin/usuarios/usuario/')
        obj = admin_instance.get_queryset(request).get(pk=usuario.pk)

        self.assertTrue(admin_instance.email_confirmado(obj))


class AuditoriaAprovacaoCadastroTest(TestCase):
    """Ações em massa de aprovar/rejeitar cadastro usavam .update() direto,
    que nunca passa pelo LogEntry automático do Django Admin -- não ficava
    registrado quem aprovou/rejeitou. Corrigido registrando explicitamente."""

    def test_aprovar_cadastros_registra_log_entry(self):
        from django.contrib.admin.models import LogEntry

        from apps.usuarios.admin import UsuarioAdmin

        root = Usuario.objects.create(username='rootauditoria', email='rootauditoria@fnp.org.br', is_superuser=True)
        alvo = Usuario.objects.create(username='alvoauditoria', email='alvoauditoria@fnp.org.br')

        from django.contrib.messages.storage.fallback import FallbackStorage

        request = _post_request_with_session('/admin/usuarios/usuario/')
        request.user = root
        request._messages = FallbackStorage(request)
        admin_instance = UsuarioAdmin(Usuario, admin.site)
        admin_instance.aprovar_cadastros(request, Usuario.objects.filter(pk=alvo.pk))

        entrada = LogEntry.objects.get(object_id=str(alvo.pk))
        self.assertEqual(entrada.user_id, root.pk)
        self.assertIn('aprovado', entrada.change_message.lower())


class SenhaMinimaTest(TestCase):
    def test_senha_curta_e_rejeitada(self):
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            validate_password('curta123')  # 8 caracteres, abaixo do novo mínimo de 10

    def test_senha_com_dez_caracteres_e_aceita(self):
        from django.contrib.auth.password_validation import validate_password

        validate_password('umasenhagrande123')


class SessionCookieAgeTest(TestCase):
    def test_sessao_nao_e_eterna(self):
        from django.conf import settings

        self.assertEqual(settings.SESSION_COOKIE_AGE, 60 * 60 * 24 * 7)


@override_settings(ALLOWED_HOSTS=['testserver'])
class DenunciaRateLimitTest(TestCase):
    def setUp(self):
        cache.clear()
        self.proposicao = Proposicao.objects.create(titulo='PL denunciado muito', casa='camara')
        self.autor = Usuario.objects.create(username='autordenunciado', email='autordenunciado@fnp.org.br')
        self.denunciante = Usuario.objects.create(username='denuncianteativo', email='denuncianteativo@fnp.org.br')
        self.denunciante.perfil.status_aprovacao = Perfil.APROVADO
        self.denunciante.perfil.save()

    def test_bloqueia_apos_dez_denuncias_na_janela(self):
        # Client mantém o cookie de sessão entre chamadas (como um navegador
        # de verdade) -- com RequestFactory cru, cada chamada gerava uma
        # sessão nova, e o rate limit (sessão+IP) nunca acumulava contagem.
        self.client.force_login(self.denunciante)
        comentarios = [
            Comentario.objects.create(
                proposicao=self.proposicao, texto=f'comentário {i}', autor=self.autor, status_moderacao='aprovado',
            )
            for i in range(11)
        ]
        for comentario in comentarios:
            self.client.post(f'/comentario/{comentario.pk}/denunciar/')

        total_denuncias = sum(c.denuncias.count() for c in comentarios)
        self.assertEqual(total_denuncias, 10)  # a 11ª foi bloqueada pelo rate limit


class ClientIpTest(TestCase):
    """Atrás do Nginx, REMOTE_ADDR é sempre o IP do próprio Nginx -- o rate
    limit precisa ler X-Forwarded-For (o último valor da lista, que é o que
    o Nginx efetivamente viu, não um valor que o próprio cliente possa ter
    forjado antes dele)."""

    def test_usa_ultimo_valor_de_x_forwarded_for(self):
        request = RequestFactory().get('/', HTTP_X_FORWARDED_FOR='1.2.3.4, 10.0.0.5')
        self.assertEqual(_client_ip(request), '10.0.0.5')

    def test_sem_header_usa_remote_addr(self):
        request = RequestFactory().get('/', REMOTE_ADDR='203.0.113.9')
        self.assertEqual(_client_ip(request), '203.0.113.9')

import re
from io import BytesIO

from django.contrib.auth.models import AbstractUser, Group, Permission
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models
from PIL import Image

FOTO_PERFIL_TAMANHO_MAXIMO_MB = 5
# Exibido nos ~40-70px do avatar (topbar/comentários) mesmo em telas retina
# -- 512px de lado já sobra bastante margem, evita servir uma foto de
# celular moderno (podem vir com 4000px+) do jeito que foi enviada, sem
# nenhum redimensionamento (achado da auditoria mobile, 2026-08-13).
FOTO_PERFIL_LADO_MAXIMO_PX = 512


def validar_tamanho_foto_perfil(arquivo):
    limite = FOTO_PERFIL_TAMANHO_MAXIMO_MB * 1024 * 1024
    if arquivo.size > limite:
        raise ValidationError(f'Imagem muito grande (máx. {FOTO_PERFIL_TAMANHO_MAXIMO_MB}MB).')


class Municipio(models.Model):
    nome = models.CharField(max_length=255)
    uf = models.CharField(max_length=2)
    slug = models.SlugField(unique=True)
    prefeito = models.CharField(max_length=255, blank=True)
    populacao = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = 'Município'
        verbose_name_plural = 'Municípios'
        db_table = 'legislativo_municipio'

    def __str__(self):
        return f'{self.nome}/{self.uf}'


class Usuario(AbstractUser):
    # Redeclarados apenas para fixar o nome da tabela M2M implícita (era
    # legislativo_usuario_* antes do model migrar de app; sem isso o Django
    # tentaria usar usuarios_usuario_* e quebraria contra a tabela existente).
    groups = models.ManyToManyField(
        Group,
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        related_name='user_set',
        related_query_name='user',
        db_table='legislativo_usuario_groups',
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='user_set',
        related_query_name='user',
        db_table='legislativo_usuario_user_permissions',
    )

    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        db_table = 'legislativo_usuario'

    def get_display_name(self):
        """Nome amigável para exibição na UI — nunca o e-mail cru."""
        nome_completo = self.get_full_name().strip()
        if nome_completo:
            return nome_completo
        local = (self.email or self.username).split('@')[0]
        partes = [parte.capitalize() for parte in re.split(r'[._-]+', local) if parte]
        return ' '.join(partes) or self.email or self.username

    def get_avatar_url(self):
        """Foto enviada manualmente tem prioridade; senão usa a foto importada do Google, se houver."""
        perfil = getattr(self, 'perfil', None)
        if not perfil:
            return None
        if perfil.foto:
            return perfil.foto.url
        return perfil.foto_google_url or None


class Perfil(models.Model):
    """Dados complementares de Usuario (1-para-1), separados do model de autenticação nativo."""

    PENDENTE = 'pendente'
    APROVADO = 'aprovado'
    REJEITADO = 'rejeitado'
    STATUS_APROVACAO_CHOICES = [
        (PENDENTE, 'Pendente'),
        (APROVADO, 'Aprovado'),
        (REJEITADO, 'Rejeitado'),
    ]

    EQUIPE_FNP = 'equipe_fnp'
    PREFEITO = 'prefeito'
    INDICADO_PREFEITURA = 'indicado_prefeitura'
    PARLAMENTAR = 'parlamentar'
    CLASSE_USUARIO_CHOICES = [
        (EQUIPE_FNP, 'Equipe FNP'),
        (PREFEITO, 'Prefeito'),
        (INDICADO_PREFEITURA, 'Indicado da prefeitura'),
        (PARLAMENTAR, 'Parlamentar'),
    ]

    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        related_name='perfil',
    )
    classe_usuario = models.CharField(max_length=32, choices=CLASSE_USUARIO_CHOICES, blank=True)
    municipio = models.ForeignKey(
        Municipio,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='perfis',
    )
    telefone = models.CharField(max_length=32, blank=True)
    cargo = models.CharField(max_length=255, blank=True)
    setor_responsavel = models.CharField(max_length=255, blank=True)
    status_aprovacao = models.CharField(
        max_length=16,
        choices=STATUS_APROVACAO_CHOICES,
        default=PENDENTE,
    )
    foto = models.ImageField(
        upload_to='avatars/', blank=True, null=True, validators=[validar_tamanho_foto_perfil],
    )
    foto_google_url = models.URLField(blank=True)
    exclusao_solicitada_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Perfil'
        verbose_name_plural = 'Perfis'
        db_table = 'legislativo_perfil'

    def __str__(self):
        return f'Perfil de {self.usuario}'

    def save(self, *args, **kwargs):
        if self.foto:
            self._redimensionar_foto_se_necessario()
        super().save(*args, **kwargs)

    def _redimensionar_foto_se_necessario(self):
        self.foto.seek(0)
        try:
            imagem = Image.open(self.foto)
            if imagem.width <= FOTO_PERFIL_LADO_MAXIMO_PX and imagem.height <= FOTO_PERFIL_LADO_MAXIMO_PX:
                return
            imagem.load()
        except Exception:
            # Arquivo corrompido/formato exótico -- deixa o ImageField
            # nativo do Django recusar na validação, não é papel do resize.
            return

        if imagem.mode not in ('RGB', 'RGBA'):
            imagem = imagem.convert('RGB')
        imagem.thumbnail((FOTO_PERFIL_LADO_MAXIMO_PX, FOTO_PERFIL_LADO_MAXIMO_PX), Image.LANCZOS)

        buffer = BytesIO()
        formato = 'PNG' if imagem.mode == 'RGBA' else 'JPEG'
        imagem.save(buffer, format=formato, quality=85, optimize=True)
        self.foto = ContentFile(buffer.getvalue(), name=self.foto.name)


class TentativaLogin(models.Model):
    """Log de auditoria de login (sucesso/falha) -- antes só existia o
    rate-limit interno do allauth (ACCOUNT_RATE_LIMITS), que conta tentativas
    mas não é consultável. Ver signals.py (registrar_login_sucesso/falha)."""

    usuario = models.ForeignKey(
        Usuario,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='tentativas_login',
    )
    email = models.CharField(max_length=255, blank=True)
    sucesso = models.BooleanField()
    ip = models.GenericIPAddressField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Tentativa de login'
        verbose_name_plural = 'Tentativas de login'
        db_table = 'legislativo_tentativa_login'
        ordering = ['-criado_em']

    def __str__(self):
        status = 'sucesso' if self.sucesso else 'falha'
        quando = self.criado_em.strftime('%d/%m/%Y %H:%M')
        return f'{self.email or self.usuario_id} — {status} em {quando}'

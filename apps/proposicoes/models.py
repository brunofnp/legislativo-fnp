import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models

ANEXO_TAMANHO_MAXIMO_MB = 10
ANEXO_EXTENSOES_PERMITIDAS = ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'jpeg', 'png']


def validar_tamanho_anexo(arquivo):
    limite = ANEXO_TAMANHO_MAXIMO_MB * 1024 * 1024
    if arquivo.size > limite:
        raise ValidationError(f'Arquivo muito grande (máx. {ANEXO_TAMANHO_MAXIMO_MB}MB).')


class Macrotema(models.Model):
    nome = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    cor = models.CharField(max_length=7, default='#000000')

    class Meta:
        verbose_name = 'Macrotema'
        verbose_name_plural = 'Macrotemas'
        db_table = 'legislativo_macrotema'

    def __str__(self):
        return self.nome


class Tema(models.Model):
    nome = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    macrotema = models.ForeignKey(
        Macrotema,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='temas',
    )

    class Meta:
        verbose_name = 'Tema'
        verbose_name_plural = 'Temas'
        db_table = 'legislativo_tema'

    def __str__(self):
        return self.nome


class Proposicao(models.Model):
    CASA_CHOICES = [
        ('camara', 'Câmara'),
        ('senado', 'Senado'),
    ]
    PRIORIDADE_CHOICES = [
        ('alta', 'Alta'),
        ('media', 'Média'),
        ('baixa', 'Baixa'),
        ('normal', 'Normal'),
    ]
    # Campos de mérito: toda edição gera uma linha em EdicaoMeritoHistorico, nunca sobrescreve silenciosamente.
    CAMPOS_MERITO = ('posicionamento_fnp', 'acoes_incidencia', 'riscos_oportunidades')

    titulo = models.CharField(max_length=1024)
    casa = models.CharField(max_length=32, choices=CASA_CHOICES)
    status_tramitacao = models.CharField(max_length=128, blank=True)
    local = models.CharField(max_length=128, blank=True)
    pauta = models.BooleanField(default=False)
    urgente = models.BooleanField(default=False)
    aprovada = models.BooleanField(default=False)
    parada = models.BooleanField(default=False)
    prioridade_fnp = models.CharField(max_length=16, choices=PRIORIDADE_CHOICES, default='normal')
    temas = models.ManyToManyField(
        Tema,
        blank=True,
        related_name='proposicoes',
        db_table='legislativo_proposicao_temas',
    )
    macrotema = models.ForeignKey(
        Macrotema,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='proposicoes',
    )
    ementa_resumida = models.TextField(blank=True)
    proximos_eventos = models.TextField(blank=True)
    interlocutores = models.TextField(blank=True)
    ultima_movimentacao = models.TextField(blank=True)
    link = models.URLField(blank=True)
    posicionamento_fnp = models.TextField(blank=True)
    acoes_incidencia = models.TextField(blank=True)
    riscos_oportunidades = models.TextField(blank=True)
    visualizacoes = models.PositiveIntegerField(default=0)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Proposição'
        verbose_name_plural = 'Proposições'
        ordering = ['-criado_em']
        db_table = 'legislativo_proposicao'

    def __str__(self):
        return self.titulo

    def urls_impressao(self):
        """Links diretos das versões de impressão da fonte oficial (Câmara/
        Senado) -- ver apps.proposicoes.print_urls."""
        from .print_urls import urls_impressao_oficial

        return urls_impressao_oficial(self.link)


class EdicaoMeritoHistorico(models.Model):
    proposicao = models.ForeignKey(
        Proposicao,
        on_delete=models.CASCADE,
        related_name='historico_edicoes',
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='edicoes_merito',
    )
    campo = models.CharField(max_length=64)
    valor_anterior = models.TextField(blank=True)
    valor_novo = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Histórico de edição de mérito'
        verbose_name_plural = 'Históricos de edição de mérito'
        ordering = ['-criado_em']
        db_table = 'legislativo_edicaomeritohistorico'

    def __str__(self):
        return f'{self.campo} — {self.proposicao}'


class Noticia(models.Model):
    proposicao = models.ForeignKey(
        Proposicao,
        on_delete=models.CASCADE,
        related_name='noticias',
    )
    titulo = models.CharField(max_length=512)
    resumo = models.TextField(blank=True)
    url = models.URLField(max_length=1000, blank=True)
    publicado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Notícia'
        verbose_name_plural = 'Notícias'
        ordering = ['-publicado_em']
        db_table = 'legislativo_noticia'

    def __str__(self):
        return self.titulo


class AnexoProposicao(models.Model):
    """Documentos/ementas anexados por prefeitos, indicados de prefeitura ou
    parlamentares (ver Perfil.classe_usuario) -- complementa o mérito e
    subsídios da FNP com material trazido pela própria base de usuários."""

    proposicao = models.ForeignKey(
        Proposicao,
        on_delete=models.CASCADE,
        related_name='anexos',
    )
    arquivo = models.FileField(
        upload_to='anexos_proposicoes/%Y/%m/',
        validators=[validar_tamanho_anexo, FileExtensionValidator(ANEXO_EXTENSOES_PERMITIDAS)],
    )
    titulo = models.CharField(max_length=255, blank=True)
    enviado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='anexos_enviados',
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Anexo da proposição'
        verbose_name_plural = 'Anexos da proposição'
        ordering = ['-criado_em']

    def __str__(self):
        return self.nome_exibicao

    @property
    def nome_exibicao(self):
        return self.titulo or os.path.basename(self.arquivo.name)

    @property
    def extensao(self):
        return os.path.splitext(self.arquivo.name)[1].lstrip('.').lower()

from django.contrib.auth.models import AbstractUser
from django.db import models


class Municipio(models.Model):
    nome = models.CharField(max_length=255)
    uf = models.CharField(max_length=2)
    slug = models.SlugField(unique=True)
    prefeito = models.CharField(max_length=255, blank=True)
    populacao = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = 'Município'
        verbose_name_plural = 'Municípios'

    def __str__(self):
        return f'{self.nome}/{self.uf}'


class Usuario(AbstractUser):
    municipio = models.OneToOneField(
        Municipio,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='usuario',
    )
    telefone = models.CharField(max_length=32, blank=True)
    cargo = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'


class Macrotema(models.Model):
    nome = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    cor = models.CharField(max_length=7, default='#000000')

    class Meta:
        verbose_name = 'Macrotema'
        verbose_name_plural = 'Macrotemas'

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

    def __str__(self):
        return self.titulo


class Comentario(models.Model):
    MODERACAO_CHOICES = [
        ('pendente', 'Pendente'),
        ('aprovado', 'Aprovado'),
        ('rejeitado', 'Rejeitado'),
    ]

    autor = models.ForeignKey(
        Usuario,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='comentarios',
    )
    proposicao = models.ForeignKey(
        Proposicao,
        on_delete=models.CASCADE,
        related_name='comentarios',
    )
    texto = models.TextField()
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='respostas',
    )
    status_moderacao = models.CharField(
        max_length=16,
        choices=MODERACAO_CHOICES,
        default='pendente',
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Comentário'
        verbose_name_plural = 'Comentários'
        ordering = ['criado_em']

    def __str__(self):
        return f'Comentário de {self.autor or "Anônimo"} em {self.proposicao}'


class EdicaoMeritoHistorico(models.Model):
    proposicao = models.ForeignKey(
        Proposicao,
        on_delete=models.CASCADE,
        related_name='historico_edicoes',
    )
    autor = models.ForeignKey(
        Usuario,
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
    url = models.URLField(blank=True)
    publicado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Notícia'
        verbose_name_plural = 'Notícias'
        ordering = ['-publicado_em']

    def __str__(self):
        return self.titulo


class Participacao(models.Model):
    class Tipo(models.TextChoices):
        CADASTRO = 'cadastro', 'Cadastro'
        SUGESTAO = 'sugestao', 'Sugestão'
        INDICACAO = 'indicacao', 'Indicação'
        DUVIDA = 'duvida', 'Dúvida'

    tipo = models.CharField(max_length=16, choices=Tipo.choices)
    municipio = models.CharField(max_length=255)
    uf = models.CharField(max_length=2, blank=True)
    proposicao = models.CharField(max_length=512, blank=True)
    responsavel = models.CharField(max_length=255)
    cargo = models.CharField(max_length=255, blank=True)
    email = models.EmailField()
    whatsapp = models.CharField(max_length=64, blank=True)
    mensagem = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Participação'
        verbose_name_plural = 'Participações'
        ordering = ['-criado_em']

    def __str__(self):
        return f'{self.get_tipo_display()} — {self.municipio} ({self.responsavel})'

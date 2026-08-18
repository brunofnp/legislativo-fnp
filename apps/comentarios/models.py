import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models

from apps.proposicoes.models import Proposicao

COMENTARIO_IMAGEM_TAMANHO_MAXIMO_MB = 8
COMENTARIO_VIDEO_TAMANHO_MAXIMO_MB = 25
COMENTARIO_MIDIA_EXTENSOES_IMAGEM = ['jpg', 'jpeg', 'png', 'gif']
COMENTARIO_MIDIA_EXTENSOES_VIDEO = ['mp4', 'webm', 'mov']
COMENTARIO_MIDIA_EXTENSOES_PERMITIDAS = COMENTARIO_MIDIA_EXTENSOES_IMAGEM + COMENTARIO_MIDIA_EXTENSOES_VIDEO


def validar_tamanho_midia_comentario(arquivo):
    extensao = os.path.splitext(arquivo.name)[1].lstrip('.').lower()
    limite_mb = (
        COMENTARIO_VIDEO_TAMANHO_MAXIMO_MB if extensao in COMENTARIO_MIDIA_EXTENSOES_VIDEO
        else COMENTARIO_IMAGEM_TAMANHO_MAXIMO_MB
    )
    if arquivo.size > limite_mb * 1024 * 1024:
        raise ValidationError(f'Arquivo muito grande (máx. {limite_mb}MB).')


class Comentario(models.Model):
    MODERACAO_CHOICES = [
        ('pendente', 'Pendente'),
        ('aprovado', 'Aprovado'),
        ('rejeitado', 'Rejeitado'),
    ]

    # Denúncias distintas de usuários para o comentário voltar sozinho a
    # 'pendente' (some da listagem pública até revisão manual).
    DENUNCIAS_PARA_OCULTAR = 3

    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
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
    midia = models.FileField(
        upload_to='comentarios_midia/%Y/%m/',
        blank=True,
        null=True,
        validators=[validar_tamanho_midia_comentario, FileExtensionValidator(COMENTARIO_MIDIA_EXTENSOES_PERMITIDAS)],
    )
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
        db_table = 'legislativo_comentario'

    def __str__(self):
        return f'Comentário de {self.autor or "Anônimo"} em {self.proposicao}'

    @property
    def tipo_midia(self):
        if not self.midia:
            return None
        extensao = os.path.splitext(self.midia.name)[1].lstrip('.').lower()
        if extensao in COMENTARIO_MIDIA_EXTENSOES_VIDEO:
            return 'video'
        if extensao in COMENTARIO_MIDIA_EXTENSOES_IMAGEM:
            return 'imagem'
        return None


class ComentarioLike(models.Model):
    """Curtida de um usuário num comentário do fórum -- soma na contagem
    exibida e entra como peso no ranking "Em alta" da home (ver
    apps.legislativo.views.get_home_sections)."""

    comentario = models.ForeignKey(
        Comentario,
        on_delete=models.CASCADE,
        related_name='likes',
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comentario_likes',
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Curtida de comentário'
        verbose_name_plural = 'Curtidas de comentário'
        ordering = ['-criado_em']
        constraints = [
            models.UniqueConstraint(fields=['comentario', 'usuario'], name='like_unico_por_usuario'),
        ]

    def __str__(self):
        return f'{self.usuario} curtiu o comentário #{self.comentario_id}'


class PalavraProibida(models.Model):
    """Lista editável via Admin (Root/Administrador FNP) — nunca hardcoded no
    código. Comentário que contiver alguma palavra ativa aqui é reprovado
    automaticamente no envio, sem precisar de moderação manual prévia."""

    palavra = models.CharField(max_length=100, unique=True)
    ativa = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Palavra proibida'
        verbose_name_plural = 'Palavras proibidas'
        ordering = ['palavra']

    def __str__(self):
        return self.palavra


class DenunciaComentario(models.Model):
    """Complemento à lista de palavras proibidas: cobre assédio/sarcasmo sem
    palavrão, que nenhuma lista de termos pega. Ao atingir
    `Comentario.DENUNCIAS_PARA_OCULTAR` denúncias distintas, o comentário
    volta sozinho para 'pendente' (some da listagem pública) até um Root/
    Administrador FNP revisar — ver denunciar_comentario() em views.py."""

    comentario = models.ForeignKey(
        Comentario,
        on_delete=models.CASCADE,
        related_name='denuncias',
    )
    denunciante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='denuncias_feitas',
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Denúncia de comentário'
        verbose_name_plural = 'Denúncias de comentário'
        ordering = ['-criado_em']
        constraints = [
            models.UniqueConstraint(fields=['comentario', 'denunciante'], name='denuncia_unica_por_usuario'),
        ]

    def __str__(self):
        return f'Denúncia de {self.denunciante} — comentário #{self.comentario_id}'


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
    setor_responsavel = models.CharField(max_length=255)
    cargo = models.CharField(max_length=255, blank=True)
    email = models.EmailField()
    telefone = models.CharField(max_length=64, blank=True)
    mensagem = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Participação'
        verbose_name_plural = 'Participações'
        ordering = ['-criado_em']
        db_table = 'legislativo_participacao'

    def __str__(self):
        return f'{self.get_tipo_display()} — {self.municipio} ({self.setor_responsavel})'


class Notificacao(models.Model):
    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notificacoes',
    )
    proposicao = models.ForeignKey(
        Proposicao,
        on_delete=models.CASCADE,
        related_name='notificacoes',
    )
    comentario = models.ForeignKey(
        Comentario,
        on_delete=models.CASCADE,
        related_name='notificacoes',
        null=True,
        blank=True,
    )
    mensagem = models.CharField(max_length=255)
    lida = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Notificação'
        verbose_name_plural = 'Notificações'
        ordering = ['-criado_em']
        db_table = 'legislativo_notificacao'

    def __str__(self):
        return f'Notificação para {self.destinatario} — {self.mensagem}'

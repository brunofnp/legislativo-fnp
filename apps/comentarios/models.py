from django.conf import settings
from django.db import models

from apps.proposicoes.models import Proposicao


class Comentario(models.Model):
    MODERACAO_CHOICES = [
        ('pendente', 'Pendente'),
        ('aprovado', 'Aprovado'),
        ('rejeitado', 'Rejeitado'),
    ]

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
        db_table = 'legislativo_participacao'

    def __str__(self):
        return f'{self.get_tipo_display()} — {self.municipio} ({self.responsavel})'


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

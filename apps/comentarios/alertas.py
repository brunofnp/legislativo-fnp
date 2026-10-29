"""Alerta individual: quando uma proposição seguida se move, cada seguidor
recebe uma Notificacao (sempre) e um e-mail (se tiver optado).

A detecção é por signal no save() da Proposicao (pega ingest e Admin). O
envio de e-mail é best-effort: nunca propaga exceção para o save().
"""
from __future__ import annotations

import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.proposicoes.models import Proposicao

logger = logging.getLogger(__name__)

# Mudança em qualquer um destes campos conta como "movimentação".
CAMPOS_ALERTA = ('status_tramitacao', 'ultima_movimentacao', 'pauta', 'urgente', 'aprovada', 'prioridade_fnp')


@receiver(pre_save, sender=Proposicao)
def _guardar_mudanca(sender, instance, **kwargs):
    if not instance.pk:
        instance._alerta_mudou = False
        return
    anterior = sender.objects.filter(pk=instance.pk).values(*CAMPOS_ALERTA).first()
    instance._alerta_mudou = bool(
        anterior and any(anterior[campo] != getattr(instance, campo) for campo in CAMPOS_ALERTA)
    )


@receiver(post_save, sender=Proposicao)
def _notificar(sender, instance, created, **kwargs):
    if created or not getattr(instance, '_alerta_mudou', False):
        return
    notificar_seguidores(instance)


def notificar_seguidores(proposicao):
    from .emails import enviar_email_alerta
    from .models import Notificacao

    detalhe = proposicao.status_tramitacao or proposicao.ultima_movimentacao or 'atualização'
    mensagem = f'"{proposicao.titulo}" teve movimentação: {detalhe}'[:255]

    for seguida in proposicao.seguidores.select_related('usuario__perfil'):
        usuario = seguida.usuario
        notificacao = Notificacao.objects.create(
            destinatario=usuario,
            proposicao=proposicao,
            tipo=Notificacao.TIPO_MOVIMENTACAO,
            mensagem=mensagem,
        )
        perfil = getattr(usuario, 'perfil', None)
        if perfil and perfil.receber_email_atualizacoes and usuario.email:
            try:
                enviar_email_alerta(usuario, proposicao)
                Notificacao.objects.filter(pk=notificacao.pk).update(enviado_email=True)
            except Exception:
                logger.exception('Falha ao enviar e-mail de alerta para %s', usuario.pk)

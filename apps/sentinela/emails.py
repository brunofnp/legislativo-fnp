"""E-mail do alerta do sentinela temático (nova proposição CBS/IBS).

Usa o backend de e-mail configurado (Gmail API em produção). Best-effort: quem
chama (o comando) captura exceções para uma falha de e-mail não interromper a
varredura nem o processamento dos demais itens.
"""
from __future__ import annotations

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse


def enviar_email_sentinela(usuarios, proposicao, termo=''):
    """Envia um e-mail para cada membro do time (lista de usuários)."""
    site_url = getattr(settings, 'SITE_URL', '')
    contexto = {
        'proposicao': proposicao,
        'termo': termo,
        'detalhe_url': f'{site_url}{reverse("legislativo:proposicao_detail", args=[proposicao.pk])}',
        'ficha_url': proposicao.link,
    }
    assunto = f'[FNP] Nova proposição no radar tributário: {proposicao.titulo}'
    corpo_txt = render_to_string('emails/alerta_sentinela.txt', contexto)
    corpo_html = render_to_string('emails/alerta_sentinela.html', contexto)
    destinatarios = [u.email for u in usuarios if u.email]
    if not destinatarios:
        return
    msg = EmailMultiAlternatives(assunto, corpo_txt, settings.DEFAULT_FROM_EMAIL, destinatarios)
    msg.attach_alternative(corpo_html, 'text/html')
    msg.send()

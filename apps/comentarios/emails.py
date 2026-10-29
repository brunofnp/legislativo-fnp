"""E-mail de alerta de movimentação (proposição seguida).

Usa o backend de e-mail configurado (Gmail API em produção). O envio é
best-effort: quem chama (ver alertas.py) captura exceções para nunca quebrar
o save()/ingest.
"""
from __future__ import annotations

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse


def enviar_email_alerta(usuario, proposicao):
    site_url = getattr(settings, 'SITE_URL', '')
    contexto = {
        'usuario': usuario,
        'proposicao': proposicao,
        'detalhe_url': f'{site_url}{reverse("legislativo:proposicao_detail", args=[proposicao.pk])}',
        'perfil_url': f'{site_url}{reverse("legislativo:perfil")}',
    }
    assunto = f'[FNP] Movimentação: {proposicao.titulo}'
    corpo_txt = render_to_string('emails/alerta_movimentacao.txt', contexto)
    corpo_html = render_to_string('emails/alerta_movimentacao.html', contexto)
    msg = EmailMultiAlternatives(assunto, corpo_txt, settings.DEFAULT_FROM_EMAIL, [usuario.email])
    msg.attach_alternative(corpo_html, 'text/html')
    msg.send()

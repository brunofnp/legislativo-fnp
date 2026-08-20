"""Backend de e-mail que envia via Gmail API (HTTPS) em vez de SMTP direto.

A DigitalOcean bloqueia por padrão as portas de SMTP de saída (587/465) em
toda conta nova -- confirmado testando diretamente no droplet (`ufw` e o
Cloud Firewall liberam tudo, mas mesmo assim as duas portas dão timeout,
enquanto HTTPS/443 funciona normalmente). Em vez de esperar suporte da DO
liberar, a Gmail API contorna o problema por completo, já que fala HTTPS.

Depende de um Service Account no Google Cloud com Domain-wide Delegation
autorizada no Admin Console do Workspace (Segurança > Controle de acesso e
dados > Delegação em todo o domínio), escopo `gmail.send`, impersonando
GMAIL_SENDER_EMAIL -- sem isso o Google recusa a autenticação."""

import base64
import json

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.send']


class GmailApiEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        try:
            service = self._build_service()
        except Exception:
            if not self.fail_silently:
                raise
            return 0

        enviados = 0
        for message in email_messages:
            try:
                raw = base64.urlsafe_b64encode(message.message().as_bytes()).decode()
                service.users().messages().send(userId='me', body={'raw': raw}).execute()
                enviados += 1
            except Exception:
                if not self.fail_silently:
                    raise
        return enviados

    def _build_service(self):
        credentials_info = json.loads(base64.b64decode(settings.GMAIL_SERVICE_ACCOUNT_JSON_B64))
        credentials = service_account.Credentials.from_service_account_info(
            credentials_info, scopes=SCOPES,
        ).with_subject(settings.GMAIL_SENDER_EMAIL)
        # cache_discovery=False -- evita o googleapiclient tentar escrever
        # um arquivo de cache no disco (falha silenciosa em container com
        # filesystem restrito, gera só um warning confuso no log).
        return build('gmail', 'v1', credentials=credentials, cache_discovery=False)

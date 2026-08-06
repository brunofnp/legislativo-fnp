from __future__ import annotations

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

# Falha segura: sem a env var, roda como produção fechada (DEBUG=False) —
# antes o padrão era 'True', então um .env ausente/corrompido em produção
# vazaria stack trace, SQL de erro e configuração pra qualquer visitante.
DEBUG = os.getenv('DEBUG', 'False').lower() in ('1', 'true', 'yes')

# Sem fallback pra uma chave conhecida (era 'django-insecure-change-me',
# a mesma string usada em todo tutorial Django — se a env var sumisse em
# produção, rodaria com uma chave pública, comprometendo sessão/CSRF).
# Em dev local sem SECRET_KEY no .env, gera uma efêmera (muda a cada
# reinício, invalida sessão, mas nunca é previsível); em produção
# (DEBUG=False) sem a env var, falha no boot em vez de rodar insegura.
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        from django.core.management.utils import get_random_secret_key
        SECRET_KEY = get_random_secret_key()
    else:
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured(
            'SECRET_KEY não configurada. Defina a variável de ambiente SECRET_KEY '
            '(nunca reaproveitar entre ambientes) antes de subir em produção.'
        )

ALLOWED_HOSTS = [host.strip() for host in os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',') if host.strip()]

# Derivado do próprio ALLOWED_HOSTS em vez de uma env var nova -- fica
# sempre em sincronia. Pula hosts de dev local (sem HTTPS, não precisam).
CSRF_TRUSTED_ORIGINS = [
    f'https://{host}' for host in ALLOWED_HOSTS if host not in ('127.0.0.1', 'localhost')
]

# Referrer-Policy explícito (mesmo valor que já é o default do Django desde
# a 3.0 -- documentado aqui pra não depender implicitamente do default de
# uma versão futura mudar sem a gente perceber).
SECURE_REFERRER_POLICY = 'same-origin'

# CAPTCHA no cadastro (django-recaptcha) — só ativa se as duas chaves
# estiverem configuradas (criar em https://www.google.com/recaptcha/admin,
# tipo "reCAPTCHA v2 checkbox"). Sem chave, o campo nem aparece no
# CustomSignupForm (ver forms.py) e o CSP abaixo não abre exceção
# nenhuma pro Google -- comportamento hoje é idêntico a antes de ter
# django-recaptcha instalado.
RECAPTCHA_PUBLIC_KEY = os.getenv('RECAPTCHA_PUBLIC_KEY', '')
RECAPTCHA_PRIVATE_KEY = os.getenv('RECAPTCHA_PRIVATE_KEY', '')
RECAPTCHA_HABILITADO = bool(RECAPTCHA_PUBLIC_KEY and RECAPTCHA_PRIVATE_KEY)

# Content-Security-Policy (django-csp). style-src precisa de 'unsafe-inline'
# porque vários templates ainda usam atributo style="..." inline (achado
# no levantamento, não corrigido agora -- é um cleanup maior, ver
# Pendências) -- então a proteção de XSS via CSS/estilo fica mais fraca
# por enquanto. script-src fica estrito (só 'self' + nonce automático):
# o único <script> inline do projeto (detecção de tema/fonte antes da
# primeira renderização, em base.html) usa {{ CSP_NONCE }}; o onclick
# que existia em admin/usuarios/usuario/submit_line.html foi movido pra
# um JS externo (mesmo padrão do admin_quick_actions.js) especificamente
# pra não precisar de 'unsafe-inline' em script.
from csp.constants import NONCE, SELF, UNSAFE_INLINE  # noqa: E402

_csp_script_src = [SELF, NONCE]
_csp_frame_src = ["'none'"]
if RECAPTCHA_HABILITADO:
    # Widget do reCAPTCHA carrega um <script src> do Google + um iframe
    # (o script inline dele próprio já ganha nonce via override em
    # templates/django_recaptcha/includes/js_v2_checkbox.html).
    _csp_script_src += ['https://www.google.com/recaptcha/', 'https://www.gstatic.com/recaptcha/']
    _csp_frame_src = ['https://www.google.com/recaptcha/']

CONTENT_SECURITY_POLICY = {
    'DIRECTIVES': {
        'default-src': [SELF],
        'script-src': _csp_script_src,
        'style-src': [SELF, UNSAFE_INLINE, 'https://fonts.googleapis.com'],
        'font-src': [SELF, 'https://fonts.gstatic.com'],
        'img-src': [SELF, 'data:', 'https:'],  # https: cobre foto de perfil do Google (googleusercontent.com, vários subdomínios)
        'connect-src': [SELF],
        'frame-src': _csp_frame_src,
        'form-action': [SELF],
        'frame-ancestors': ["'none'"],
        'base-uri': [SELF],
        'object-src': ["'none'"],
    },
}

# Monitoramento de erro (Sentry) — só ativa se SENTRY_DSN estiver setado
# (fica desligado em dev local por padrão, sem precisar de conta/projeto).
SENTRY_DSN = os.getenv('SENTRY_DSN', '')
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.0,  # só captura erro, sem tracing de performance
        send_default_pii=False,  # nunca envia dado pessoal de usuário por padrão
        environment='production' if not DEBUG else 'development',
    )

INSTALLED_APPS = [
    'apps.legislativo.admin_site.FNPAdminConfig',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.mfa',
    'csp',
    'django_recaptcha',
    'apps.usuarios',
    'apps.proposicoes',
    'apps.comentarios',
    'apps.legislativo',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'csp.middleware.CSPMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'apps.usuarios.middleware.CadastroPendenteMiddleware',
    'apps.usuarios.middleware.MFAObrigatorioStaffMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'setup.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'base_templates', BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.legislativo.context_processors.notificacoes',
                'csp.context_processors.nonce',
            ],
        },
    },
]

WSGI_APPLICATION = 'setup.wsgi.application'

DATABASES = {
    'default': dj_database_url.parse(os.getenv('DATABASE_URL', f'sqlite:///{BASE_DIR / "db.sqlite3"}'))
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'usuarios.Usuario'

SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# ACCOUNT_LOGIN_METHODS/ACCOUNT_SIGNUP_FIELDS substituem
# ACCOUNT_AUTHENTICATION_METHOD/ACCOUNT_EMAIL_REQUIRED/ACCOUNT_USERNAME_REQUIRED
# (renomeados no upgrade allauth 0.60->65.x) -- mesmo comportamento de antes:
# login só por e-mail, sem campo de username no cadastro.
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
# 'optional' em vez de 'none': manda e-mail de confirmação mas não bloqueia
# login sem clicar -- cadastro pendente (CadastroPendenteMiddleware) já
# exige aprovação manual da equipe antes de liberar navegação de qualquer
# forma, então 'mandatory' (bloquear login sem confirmar) não é obrigatório
# agora. Nota: sem EMAIL_BACKEND configurado, o e-mail de confirmação usa o
# backend console do Django (não entrega de verdade) -- ver Pendências.
ACCOUNT_EMAIL_VERIFICATION = 'optional'
ACCOUNT_LOGOUT_ON_GET = True
LOGIN_URL = '/contas/login/'
LOGIN_REDIRECT_URL = '/'
ACCOUNT_LOGOUT_REDIRECT_URL = '/'
ACCOUNT_SIGNUP_FORM_CLASS = 'apps.legislativo.forms.CustomSignupForm'

# Explícito em vez de depender do default embutido do allauth (mesmo valor
# de fábrica, só documentado): limita tentativa de login falha por IP e por
# conta atacada, cadastro em massa e reset de senha. Nota: o cache padrão
# do Django (LocMemCache) é por processo -- com múltiplos workers do
# Gunicorn, cada processo conta separado, então o limite efetivo pode ser
# até N vezes mais permissivo (N = nº de workers). Revisar se vale trocar
# pra um cache compartilhado (Redis) — não decidido ainda, ver Pendências.
ACCOUNT_RATE_LIMITS = {
    'login_failed': '10/m/ip,5/5m/key',
    'signup': '20/m/ip',
    'reset_password': '20/m/ip,5/m/key',
}

# 2FA (allauth.mfa) — TOTP (app autenticador) + códigos de recuperação.
# Sem WebAuthn/passkey por enquanto (exige mais infraestrutura de
# navegador/HTTPS, não decidido). Disponível pra qualquer usuário em
# /contas/2fa/; reforçado como obrigatório pra staff via
# apps.usuarios.middleware.MFAObrigatorioStaffMiddleware.
MFA_SUPPORTED_TYPES = ['totp', 'recovery_codes']

SOCIALACCOUNT_ADAPTER = 'apps.usuarios.adapters.GoogleAccountAdapter'

# Unifica conta: se alguém já se cadastrou com e-mail/senha e depois tenta
# entrar com o Google usando o mesmo e-mail, loga na MESMA conta em vez de
# barrar com "e-mail já em uso" — seguro porque o Google confirma a posse do
# e-mail via OAuth (allauth só permite por padrão para provedores confiáveis).
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': os.getenv('GOOGLE_CLIENT_ID', ''),
            'secret': os.getenv('GOOGLE_CLIENT_SECRET', ''),
            'key': '',
        },
        'SCOPE': ['profile', 'email'],
    }
}

# Cabeçalhos de segurança — só em produção (DEBUG=False), para não quebrar o
# runserver local (HTTP puro, sem TLS). Assume que o Nginx do droplet `fnp-web`
# repassa X-Forwarded-Proto (padrão em configs de proxy reverso); se não
# repassar, SECURE_SSL_REDIRECT causa loop de redirecionamento — confirmar
# antes de habilitar em produção pela primeira vez.
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

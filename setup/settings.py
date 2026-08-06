from __future__ import annotations

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-change-me')
DEBUG = os.getenv('DEBUG', 'True').lower() in ('1', 'true', 'yes')
ALLOWED_HOSTS = [host.strip() for host in os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',') if host.strip()]

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
    'apps.usuarios',
    'apps.proposicoes',
    'apps.comentarios',
    'apps.legislativo',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'apps.usuarios.middleware.CadastroPendenteMiddleware',
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
USE_L10N = True
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

ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_LOGOUT_ON_GET = True
LOGIN_URL = '/contas/login/'
LOGIN_REDIRECT_URL = '/'
ACCOUNT_LOGOUT_REDIRECT_URL = '/'
ACCOUNT_SIGNUP_FORM_CLASS = 'apps.legislativo.forms.CustomSignupForm'

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

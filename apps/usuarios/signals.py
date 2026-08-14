from allauth.socialaccount.signals import pre_social_login
from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.core.mail import send_mail
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver
from django.urls import reverse

from .models import Perfil, TentativaLogin, Usuario

USUARIO_GROUP_NAME = 'Usuário'

# Grupos que dão acesso ao Django Admin -- ver sincronizar_staff_por_grupo
# abaixo. Sem isso, adicionar alguém a "Administrador FNP" pelo widget de
# grupos do UsuarioAdmin não bastava: a pessoa continuava sem is_staff (não
# conseguia nem logar em /admin/) e a sidebar do site nunca mostrava o link
# "Painel Admin" (que só checava is_superuser).
GRUPOS_COM_ACESSO_ADMIN = {'Root', 'Administrador FNP'}


@receiver(post_save, sender=Usuario)
def adicionar_ao_grupo_usuario(sender, instance, created, **kwargs):
    if created and not instance.is_superuser:
        group, _ = Group.objects.get_or_create(name=USUARIO_GROUP_NAME)
        instance.groups.add(group)


@receiver(m2m_changed, sender=Usuario.groups.through)
def sincronizar_staff_por_grupo(sender, instance, action, pk_set, **kwargs):
    if action != 'post_add' or not pk_set:
        return
    nomes = set(Group.objects.filter(pk__in=pk_set).values_list('name', flat=True))
    if nomes & GRUPOS_COM_ACESSO_ADMIN and not instance.is_staff:
        instance.is_staff = True
        instance.save(update_fields=['is_staff'])


@receiver(post_save, sender=Usuario)
def criar_perfil(sender, instance, created, **kwargs):
    if created:
        status_inicial = Perfil.APROVADO if (instance.is_staff or instance.is_superuser) else Perfil.PENDENTE
        Perfil.objects.get_or_create(usuario=instance, defaults={'status_aprovacao': status_inicial})
        if status_inicial == Perfil.PENDENTE:
            notificar_cadastro_pendente(instance)


def notificar_cadastro_pendente(usuario):
    """E-mail pra CADASTRO_PENDENTE_NOTIFICACAO_EMAILS sempre que um
    cadastro novo nasce pendente -- pedido explícito do usuário,
    2026-08-14. `fail_silently=True` de propósito: SMTP fora do ar (ou
    ainda sem EMAIL_BACKEND real configurado em produção, ver Pendências
    no CLAUDE.md) nunca pode derrubar o cadastro em si -- mesmo raciocínio
    do bug já corrigido antes com o e-mail de confirmação do allauth."""
    destinatarios = settings.CADASTRO_PENDENTE_NOTIFICACAO_EMAILS
    if not destinatarios:
        return
    link = settings.SITE_URL + reverse('admin:usuarios_usuario_change', args=[usuario.pk])
    send_mail(
        subject='Novo cadastro aguardando aprovação — Painel Legislativo FNP',
        message=(
            f'{usuario.get_display_name()} ({usuario.email}) acabou de se cadastrar '
            'no Painel Legislativo FNP e está aguardando aprovação.\n\n'
            f'Revisar e aprovar ou rejeitar: {link}'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=destinatarios,
        fail_silently=True,
    )


def _client_ip(request):
    """Mesma lógica de apps.legislativo.throttling._client_ip, duplicada de
    propósito aqui em vez de importada -- apps.legislativo depende de
    apps.usuarios, nunca o contrário (ver Diretrizes de Engenharia em
    CLAUDE.md), então importar de lá criaria dependência circular. Nginx é o
    único ponto de entrada confiável em produção; o último valor de
    X-Forwarded-For é o que ele de fato anexou."""
    if request is None:
        return ''
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded_for:
        return forwarded_for.split(',')[-1].strip()
    return request.META.get('REMOTE_ADDR', '')


@receiver(user_logged_in)
def registrar_login_sucesso(sender, request, user, **kwargs):
    TentativaLogin.objects.create(
        usuario=user,
        email=user.email,
        sucesso=True,
        ip=_client_ip(request) or None,
    )


@receiver(user_login_failed)
def registrar_login_falha(sender, credentials, request=None, **kwargs):
    email = credentials.get('email') or credentials.get('username', '')
    TentativaLogin.objects.create(
        usuario=None,
        email=email,
        sucesso=False,
        ip=_client_ip(request) or None,
    )


@receiver(pre_social_login)
def atualizar_foto_google(sender, request, sociallogin, **kwargs):
    """Login social novo é coberto por GoogleAccountAdapter.save_user; aqui
    cobrimos o usuário que já existia e está apenas voltando a logar, para
    manter a foto do Google em dia caso ele a tenha trocado."""
    if not sociallogin.is_existing:
        return
    foto_url = sociallogin.account.extra_data.get('picture', '')
    if foto_url:
        Perfil.objects.filter(usuario=sociallogin.user).update(foto_google_url=foto_url)

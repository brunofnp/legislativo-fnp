from allauth.socialaccount.signals import pre_social_login
from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Perfil, Usuario

USUARIO_GROUP_NAME = 'Usuário'


@receiver(post_save, sender=Usuario)
def adicionar_ao_grupo_usuario(sender, instance, created, **kwargs):
    if created and not instance.is_superuser:
        group, _ = Group.objects.get_or_create(name=USUARIO_GROUP_NAME)
        instance.groups.add(group)


@receiver(post_save, sender=Usuario)
def criar_perfil(sender, instance, created, **kwargs):
    if created:
        status_inicial = Perfil.APROVADO if (instance.is_staff or instance.is_superuser) else Perfil.PENDENTE
        Perfil.objects.get_or_create(usuario=instance, defaults={'status_aprovacao': status_inicial})


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

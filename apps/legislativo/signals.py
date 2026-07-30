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
        Perfil.objects.get_or_create(usuario=instance)

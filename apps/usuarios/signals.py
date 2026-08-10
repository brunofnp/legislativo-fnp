from allauth.socialaccount.signals import pre_social_login
from django.contrib.auth.models import Group
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from .models import Perfil, Usuario

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

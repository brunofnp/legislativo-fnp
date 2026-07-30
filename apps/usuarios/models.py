import re

from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models


class Municipio(models.Model):
    nome = models.CharField(max_length=255)
    uf = models.CharField(max_length=2)
    slug = models.SlugField(unique=True)
    prefeito = models.CharField(max_length=255, blank=True)
    populacao = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = 'Município'
        verbose_name_plural = 'Municípios'
        db_table = 'legislativo_municipio'

    def __str__(self):
        return f'{self.nome}/{self.uf}'


class Usuario(AbstractUser):
    # Redeclarados apenas para fixar o nome da tabela M2M implícita (era
    # legislativo_usuario_* antes do model migrar de app; sem isso o Django
    # tentaria usar usuarios_usuario_* e quebraria contra a tabela existente).
    groups = models.ManyToManyField(
        Group,
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        related_name='user_set',
        related_query_name='user',
        db_table='legislativo_usuario_groups',
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='user_set',
        related_query_name='user',
        db_table='legislativo_usuario_user_permissions',
    )

    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        db_table = 'legislativo_usuario'

    def get_display_name(self):
        """Nome amigável para exibição na UI — nunca o e-mail cru."""
        nome_completo = self.get_full_name().strip()
        if nome_completo:
            return nome_completo
        local = (self.email or self.username).split('@')[0]
        partes = [parte.capitalize() for parte in re.split(r'[._-]+', local) if parte]
        return ' '.join(partes) or self.email or self.username


class Perfil(models.Model):
    """Dados complementares de Usuario (1-para-1), separados do model de autenticação nativo."""

    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        related_name='perfil',
    )
    municipio = models.OneToOneField(
        Municipio,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='perfil',
    )
    telefone = models.CharField(max_length=32, blank=True)
    cargo = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'Perfil'
        verbose_name_plural = 'Perfis'
        db_table = 'legislativo_perfil'

    def __str__(self):
        return f'Perfil de {self.usuario}'

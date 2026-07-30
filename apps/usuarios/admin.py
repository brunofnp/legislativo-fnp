from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Municipio, Perfil, Usuario


class PerfilInline(admin.StackedInline):
    model = Perfil
    can_delete = False
    extra = 0


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """Hierarquia de perfis (Root / Administrador FNP / Usuário) é gerenciada aqui via
    grupos e permissões nativas do Django — ver `python manage.py setup_roles`."""

    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser', 'is_active')
    list_filter = UserAdmin.list_filter + ('groups',)
    inlines = [PerfilInline]


@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = ('nome', 'uf', 'prefeito')
    search_fields = ('nome', 'uf', 'prefeito')

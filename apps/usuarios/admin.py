from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Municipio, Perfil, Usuario


class PerfilInline(admin.StackedInline):
    model = Perfil
    can_delete = False
    extra = 0
    autocomplete_fields = ['municipio']


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """Hierarquia de perfis (Root / Administrador FNP / Usuário) é gerenciada aqui via
    grupos e permissões nativas do Django — ver `python manage.py setup_roles`."""

    list_display = (
        'username', 'email', 'first_name', 'last_name',
        'status_cadastro', 'exclusao_pendente', 'is_staff', 'is_superuser', 'is_active',
    )
    list_filter = UserAdmin.list_filter + ('groups', 'perfil__status_aprovacao', 'perfil__exclusao_solicitada_em')
    inlines = [PerfilInline]
    actions = ['aprovar_cadastros', 'rejeitar_cadastros']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('perfil')

    @admin.display(description='Cadastro', ordering='perfil__status_aprovacao')
    def status_cadastro(self, obj):
        perfil = getattr(obj, 'perfil', None)
        return perfil.get_status_aprovacao_display() if perfil else '—'

    @admin.display(description='Exclusão solicitada', boolean=True, ordering='perfil__exclusao_solicitada_em')
    def exclusao_pendente(self, obj):
        perfil = getattr(obj, 'perfil', None)
        return bool(perfil and perfil.exclusao_solicitada_em)

    @admin.action(description='Aprovar cadastros selecionados')
    def aprovar_cadastros(self, request, queryset):
        atualizados = Perfil.objects.filter(usuario__in=queryset).update(status_aprovacao=Perfil.APROVADO)
        self.message_user(request, f'{atualizados} cadastro(s) aprovado(s).')

    @admin.action(description='Rejeitar cadastros selecionados')
    def rejeitar_cadastros(self, request, queryset):
        atualizados = Perfil.objects.filter(usuario__in=queryset).update(status_aprovacao=Perfil.REJEITADO)
        self.message_user(request, f'{atualizados} cadastro(s) rejeitado(s).')


@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = ('nome', 'uf', 'prefeito')
    list_filter = ('uf',)
    search_fields = ('nome', 'uf', 'prefeito')

from django.contrib import admin, messages
from django.contrib.admin.actions import delete_selected as django_delete_selected
from django.contrib.auth.admin import UserAdmin
from django.http import HttpResponseRedirect
from django.urls import reverse

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
    actions = ['aprovar_cadastros', 'rejeitar_cadastros', 'aprovar_exclusoes', 'rejeitar_exclusoes']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('perfil')

    def response_change(self, request, obj):
        """Botões extras na página do próprio usuário (ver
        templates/admin/usuarios/usuario/submit_line.html) para aprovar/
        rejeitar cadastro e exclusão sem precisar voltar pra listagem e usar
        a ação em massa."""
        if '_aprovar_cadastro' in request.POST:
            Perfil.objects.filter(usuario=obj).update(status_aprovacao=Perfil.APROVADO)
            self.message_user(request, 'Cadastro aprovado.')
            return HttpResponseRedirect(request.path)
        if '_rejeitar_cadastro' in request.POST:
            Perfil.objects.filter(usuario=obj).update(status_aprovacao=Perfil.REJEITADO)
            self.message_user(request, 'Cadastro rejeitado.')
            return HttpResponseRedirect(request.path)
        if '_rejeitar_exclusao' in request.POST:
            Perfil.objects.filter(usuario=obj).update(exclusao_solicitada_em=None)
            self.message_user(request, 'Solicitação de exclusão rejeitada.')
            return HttpResponseRedirect(request.path)
        if '_aprovar_exclusao' in request.POST:
            perfil = getattr(obj, 'perfil', None)
            if not perfil or not perfil.exclusao_solicitada_em:
                self.message_user(request, 'Este usuário não tem exclusão solicitada.', level=messages.WARNING)
                return HttpResponseRedirect(request.path)
            nome = str(obj)
            obj.delete()
            self.message_user(request, f'Conta de {nome} excluída.')
            return HttpResponseRedirect(reverse('admin:usuarios_usuario_changelist'))
        return super().response_change(request, obj)

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

    @admin.action(description='Aprovar exclusão solicitada (exclui a conta)')
    def aprovar_exclusoes(self, request, queryset):
        alvo = queryset.filter(perfil__exclusao_solicitada_em__isnull=False)
        ignorados = queryset.count() - alvo.count()
        if ignorados:
            self.message_user(
                request,
                f'{ignorados} usuário(s) ignorado(s) por não ter exclusão solicitada.',
                level=messages.WARNING,
            )
        if not alvo:
            return None
        # Reaproveita a ação nativa "Excluir selecionados" (mesma tela de
        # confirmação com o resumo de objetos relacionados que serão apagados
        # em cascata) em vez de excluir direto sem confirmação.
        return django_delete_selected(self, request, alvo)

    @admin.action(description='Rejeitar solicitação de exclusão (mantém a conta)')
    def rejeitar_exclusoes(self, request, queryset):
        atualizados = Perfil.objects.filter(
            usuario__in=queryset, exclusao_solicitada_em__isnull=False,
        ).update(exclusao_solicitada_em=None)
        self.message_user(request, f'{atualizados} solicitação(ões) de exclusão rejeitada(s).')


@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = ('nome', 'uf', 'prefeito')
    list_filter = ('uf',)
    search_fields = ('nome', 'uf', 'prefeito')

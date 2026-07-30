from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    Comentario,
    EdicaoMeritoHistorico,
    Macrotema,
    Municipio,
    Noticia,
    Notificacao,
    Participacao,
    Proposicao,
    Tema,
    Usuario,
)


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """Hierarquia de perfis (Root / Administrador FNP / Usuário) é gerenciada aqui via
    grupos e permissões nativas do Django — ver `python manage.py setup_roles`."""

    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser', 'is_active')
    list_filter = UserAdmin.list_filter + ('groups',)
    fieldsets = UserAdmin.fieldsets + (
        ('Dados FNP', {'fields': ('municipio', 'telefone', 'cargo')}),
    )


@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = ('nome', 'uf', 'prefeito')
    search_fields = ('nome', 'uf', 'prefeito')


@admin.register(Macrotema)
class MacrotemaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'slug', 'cor')
    search_fields = ('nome',)
    prepopulated_fields = {'slug': ('nome',)}


@admin.register(Tema)
class TemaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'slug', 'macrotema')
    search_fields = ('nome',)
    prepopulated_fields = {'slug': ('nome',)}


class EdicaoMeritoHistoricoInline(admin.TabularInline):
    model = EdicaoMeritoHistorico
    extra = 0
    readonly_fields = ('autor', 'campo', 'valor_anterior', 'valor_novo', 'criado_em')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Proposicao)
class ProposicaoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'casa', 'status_tramitacao', 'prioridade_fnp', 'macrotema', 'urgente', 'aprovada')
    list_filter = ('casa', 'prioridade_fnp', 'macrotema', 'urgente', 'aprovada')
    search_fields = ('titulo', 'ementa_resumida')
    inlines = [EdicaoMeritoHistoricoInline]

    def save_model(self, request, obj, form, change):
        """Campo de mérito nunca é sobrescrito silenciosamente: toda mudança gera uma linha de histórico."""
        if change:
            valores_anteriores = Proposicao.objects.filter(pk=obj.pk).values(*Proposicao.CAMPOS_MERITO).first() or {}
            EdicaoMeritoHistorico.objects.bulk_create([
                EdicaoMeritoHistorico(
                    proposicao=obj,
                    autor=request.user,
                    campo=campo,
                    valor_anterior=valores_anteriores.get(campo, ''),
                    valor_novo=getattr(obj, campo),
                )
                for campo in Proposicao.CAMPOS_MERITO
                if valores_anteriores.get(campo, '') != getattr(obj, campo)
            ])
        super().save_model(request, obj, form, change)


@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    list_display = ('autor', 'proposicao', 'status_moderacao', 'criado_em')
    list_filter = ('status_moderacao',)
    search_fields = ('texto',)


@admin.register(EdicaoMeritoHistorico)
class EdicaoMeritoHistoricoAdmin(admin.ModelAdmin):
    list_display = ('proposicao', 'autor', 'campo', 'criado_em')
    search_fields = ('campo', 'valor_anterior', 'valor_novo')


@admin.register(Noticia)
class NoticiaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'proposicao', 'publicado_em')
    search_fields = ('titulo',)


@admin.register(Participacao)
class ParticipacaoAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'municipio', 'proposicao', 'responsavel', 'email', 'criado_em')
    list_filter = ('tipo', 'uf')
    search_fields = ('municipio', 'proposicao', 'responsavel', 'email')


@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    list_display = ('destinatario', 'proposicao', 'mensagem', 'lida', 'criado_em')
    list_filter = ('lida',)
    search_fields = ('mensagem',)

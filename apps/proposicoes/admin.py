from django.contrib import admin

from .models import EdicaoMeritoHistorico, Macrotema, Noticia, Proposicao, Tema


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


@admin.register(EdicaoMeritoHistorico)
class EdicaoMeritoHistoricoAdmin(admin.ModelAdmin):
    list_display = ('proposicao', 'autor', 'campo', 'criado_em')
    search_fields = ('campo', 'valor_anterior', 'valor_novo')


@admin.register(Noticia)
class NoticiaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'proposicao', 'publicado_em')
    search_fields = ('titulo',)

from django.contrib import admin

from .models import AnexoProposicao, EdicaoMeritoHistorico, Macrotema, Noticia, Proposicao, Tema


@admin.register(Macrotema)
class MacrotemaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'slug', 'cor')
    search_fields = ('nome',)
    prepopulated_fields = {'slug': ('nome',)}


@admin.register(Tema)
class TemaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'slug', 'macrotema')
    list_filter = ('macrotema',)
    search_fields = ('nome',)
    prepopulated_fields = {'slug': ('nome',)}
    autocomplete_fields = ['macrotema']


class EdicaoMeritoHistoricoInline(admin.TabularInline):
    model = EdicaoMeritoHistorico
    extra = 0
    readonly_fields = ('autor', 'campo', 'valor_anterior', 'valor_novo', 'criado_em')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class NoticiaInline(admin.TabularInline):
    model = Noticia
    extra = 0
    fields = ('titulo', 'url', 'publicado_em')


class AnexoProposicaoInline(admin.TabularInline):
    model = AnexoProposicao
    extra = 0
    fields = ('titulo', 'arquivo', 'enviado_por', 'criado_em')
    readonly_fields = ('enviado_por', 'criado_em')


@admin.register(Proposicao)
class ProposicaoAdmin(admin.ModelAdmin):
    list_display = (
        'titulo', 'casa', 'status_tramitacao', 'macrotema',
        'prioridade_fnp', 'pauta', 'urgente', 'aprovada', 'parada',
    )
    # Edição direta na listagem (sem abrir cada proposição) — "titulo" fica de
    # fora por ser a coluna usada como link para a página de edição completa.
    list_editable = ('macrotema', 'prioridade_fnp', 'pauta', 'urgente', 'aprovada', 'parada')
    list_filter = ('macrotema', 'prioridade_fnp', 'urgente', 'pauta', 'casa')
    search_fields = ('titulo', 'ementa_resumida')
    date_hierarchy = 'atualizado_em'
    autocomplete_fields = ['macrotema', 'temas']
    inlines = [EdicaoMeritoHistoricoInline, NoticiaInline, AnexoProposicaoInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('macrotema')

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
    """Somente leitura: histórico é gerado automaticamente por ProposicaoAdmin.save_model
    e por ingest_legislativo, nunca criado à mão — senão perde o valor de auditoria."""

    list_display = ('proposicao', 'campo', 'autor', 'criado_em')
    list_filter = ('campo',)
    search_fields = ('campo', 'valor_anterior', 'valor_novo')
    date_hierarchy = 'criado_em'
    ordering = ('-criado_em',)
    autocomplete_fields = ['proposicao']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('proposicao', 'autor')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Noticia)
class NoticiaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'proposicao', 'publicado_em')
    search_fields = ('titulo',)
    autocomplete_fields = ['proposicao']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('proposicao')


@admin.register(AnexoProposicao)
class AnexoProposicaoAdmin(admin.ModelAdmin):
    list_display = ('nome_exibicao', 'proposicao', 'enviado_por', 'criado_em')
    search_fields = ('titulo', 'proposicao__titulo')
    autocomplete_fields = ['proposicao']
    readonly_fields = ('enviado_por', 'criado_em')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('proposicao', 'enviado_por')

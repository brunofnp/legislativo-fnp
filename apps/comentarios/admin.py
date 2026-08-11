from django.contrib import admin
from django.utils.html import format_html
from django.utils.text import Truncator

from django.db.models import Count

from .models import Comentario, DenunciaComentario, Notificacao, PalavraProibida, Participacao


@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    # Ordenado por proposição (não por data) de propósito -- agrupa os
    # comentários da mesma proposição em sequência na listagem, facilita
    # moderar/excluir todos os de uma proposição de uma vez em vez de
    # caçá-los espalhados numa lista só por data.
    list_display = ('trecho', 'autor', 'proposicao', 'status_moderacao', 'total_denuncias', 'criado_em')
    list_editable = ('status_moderacao',)
    list_filter = ('status_moderacao', ('proposicao', admin.RelatedOnlyFieldListFilter))
    ordering = ('proposicao__titulo', '-criado_em')
    search_fields = ('texto',)
    autocomplete_fields = ['proposicao', 'parent']
    actions = ['aprovar_selecionados', 'rejeitar_selecionados']
    list_per_page = 50

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .select_related('proposicao', 'autor', 'parent')
            .annotate(_total_denuncias=Count('denuncias', distinct=True))
        )

    @admin.display(description='Comentário')
    def trecho(self, obj):
        texto_truncado = Truncator(obj.texto).chars(80)
        if obj.parent_id:
            return format_html('↳ {}', texto_truncado)
        return texto_truncado

    @admin.display(description='Denúncias', ordering='_total_denuncias')
    def total_denuncias(self, obj):
        return obj._total_denuncias

    @admin.action(description='Aprovar selecionados')
    def aprovar_selecionados(self, request, queryset):
        atualizados = queryset.update(status_moderacao='aprovado')
        self.message_user(request, f'{atualizados} comentário(s) aprovado(s).')

    @admin.action(description='Rejeitar selecionados')
    def rejeitar_selecionados(self, request, queryset):
        atualizados = queryset.update(status_moderacao='rejeitado')
        self.message_user(request, f'{atualizados} comentário(s) rejeitado(s).')


@admin.register(Participacao)
class ParticipacaoAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'municipio', 'proposicao', 'setor_responsavel', 'email', 'criado_em')
    list_filter = ('tipo', 'uf')
    search_fields = ('municipio', 'proposicao', 'setor_responsavel', 'email')


@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    list_display = ('destinatario', 'proposicao', 'mensagem', 'lida', 'criado_em')
    list_filter = ('lida',)
    search_fields = ('mensagem',)


@admin.register(PalavraProibida)
class PalavraProibidaAdmin(admin.ModelAdmin):
    list_display = ('palavra', 'ativa', 'criado_em')
    list_filter = ('ativa',)
    search_fields = ('palavra',)


@admin.register(DenunciaComentario)
class DenunciaComentarioAdmin(admin.ModelAdmin):
    """Só leitura para criação — denúncia nasce do botão "Denunciar" no
    fórum, nunca deveria ser cadastrada à mão. Root pode excluir uma denúncia
    indevida (ex.: brigada coordenada contra um comentário legítimo)."""

    list_display = ('comentario', 'denunciante', 'criado_em')
    list_filter = (('comentario__proposicao', admin.RelatedOnlyFieldListFilter),)
    search_fields = ('comentario__texto',)
    autocomplete_fields = ['comentario', 'denunciante']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('comentario', 'denunciante')

    def has_add_permission(self, request):
        return False

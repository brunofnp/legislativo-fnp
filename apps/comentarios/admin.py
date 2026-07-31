from django.contrib import admin
from django.utils.html import format_html
from django.utils.text import Truncator

from .models import Comentario, Notificacao, PalavraProibida, Participacao


@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    list_display = ('trecho', 'autor', 'proposicao', 'status_moderacao', 'criado_em')
    list_editable = ('status_moderacao',)
    list_filter = ('status_moderacao', ('proposicao', admin.RelatedOnlyFieldListFilter))
    search_fields = ('texto',)
    autocomplete_fields = ['proposicao', 'parent']
    actions = ['aprovar_selecionados', 'rejeitar_selecionados']
    list_per_page = 50

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('proposicao', 'autor', 'parent')

    @admin.display(description='Comentário')
    def trecho(self, obj):
        texto_truncado = Truncator(obj.texto).chars(80)
        if obj.parent_id:
            return format_html('↳ {}', texto_truncado)
        return texto_truncado

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

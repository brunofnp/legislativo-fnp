from django.contrib import admin

from .models import Comentario, Notificacao, Participacao


@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    list_display = ('autor', 'proposicao', 'status_moderacao', 'criado_em')
    list_filter = ('status_moderacao',)
    search_fields = ('texto',)


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

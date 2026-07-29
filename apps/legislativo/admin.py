from django.contrib import admin

from .models import (
    Comentario,
    EdicaoMeritoHistorico,
    Macrotema,
    Municipio,
    Noticia,
    Participacao,
    Proposicao,
    Tema,
    Usuario,
)


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_staff', 'is_active')
    search_fields = ('username', 'email')


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


@admin.register(Proposicao)
class ProposicaoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'casa', 'status_tramitacao', 'prioridade_fnp', 'macrotema', 'urgente', 'aprovada')
    list_filter = ('casa', 'prioridade_fnp', 'macrotema', 'urgente', 'aprovada')
    search_fields = ('titulo', 'ementa_resumida')


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

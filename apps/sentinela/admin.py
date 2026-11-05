from django.contrib import admin

from .models import ItemSentinelaVisto, TermoSentinela


@admin.register(TermoSentinela)
class TermoSentinelaAdmin(admin.ModelAdmin):
    list_display = ('termo', 'ativo', 'criado_em')
    list_editable = ('ativo',)
    search_fields = ('termo',)


@admin.register(ItemSentinelaVisto)
class ItemSentinelaVistoAdmin(admin.ModelAdmin):
    list_display = ('fonte', 'id_externo', 'titulo', 'alertado', 'visto_em')
    list_filter = ('fonte', 'alertado')
    search_fields = ('id_externo', 'titulo')

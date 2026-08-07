# Popula PalavraProibida com uma lista inicial de termos comuns banidos em
# redes sociais (xingamentos, calão sexual, e ofensas de cunho racial,
# homofóbico, misógino e capacitista) -- a pedido explícito do usuário, pra
# moderação automática já funcionar de imediato em vez de nascer vazia.
#
# Nota de arquitetura: apps/comentarios/moderacao.py documenta que a lista
# nunca deveria ficar hardcoded no código-fonte pra evitar "lista
# desatualizada, incompleta ou embaraçosa versionada no git" -- esta
# migração roda só uma vez (RunPython de seed), não é a lista em si: a
# partir daqui os termos vivem no banco e são 100% editáveis via Admin
# (PalavraProibida.ativa, adicionar/remover) -- este arquivo é só o ponto
# de partida, não precisa ficar em sincronia com o banco depois.
from django.db import migrations

PALAVRAS_INICIAIS = [
    # Xingamentos/calão geral
    'merda', 'porra', 'caralho', 'cacete', 'bosta', 'foda-se', 'fodase',
    'arrombado', 'arrombada', 'desgraçado', 'desgraçada', 'cuzão', 'cuzona',
    'corno', 'filho da puta', 'filha da puta', 'fdp', 'puta', 'putinha',
    # Calão sexual
    'buceta', 'piroca', 'xoxota',
    # Misoginia
    'piranha', 'vagabunda', 'vadia',
    # Homofobia
    'viado', 'bicha', 'boiola', 'sapatão', 'traveco',
    # Capacitismo
    'retardado', 'retardada', 'mongoloide',
    # Racismo
    'macaco', 'crioulo',
]


def popular_palavras(apps, schema_editor):
    PalavraProibida = apps.get_model('comentarios', 'PalavraProibida')
    for palavra in PALAVRAS_INICIAIS:
        PalavraProibida.objects.get_or_create(palavra=palavra, defaults={'ativa': True})


def remover_palavras(apps, schema_editor):
    PalavraProibida = apps.get_model('comentarios', 'PalavraProibida')
    PalavraProibida.objects.filter(palavra__in=PALAVRAS_INICIAIS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('comentarios', '0005_denunciacomentario_and_more'),
    ]

    operations = [
        migrations.RunPython(popular_palavras, remover_palavras),
    ]

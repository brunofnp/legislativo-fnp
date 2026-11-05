from django.db import migrations

TERMOS = [
    'CBS',
    'IBS',
    'Contribuição sobre Bens e Serviços',
    'Imposto sobre Bens e Serviços',
    'reforma tributária',
    'IVA',
    'Imposto Seletivo',
    'LC 214',
    'comitê gestor do IBS',
    'split payment',
]


def seed(apps, schema_editor):
    TermoSentinela = apps.get_model('sentinela', 'TermoSentinela')
    for termo in TERMOS:
        TermoSentinela.objects.get_or_create(termo=termo, defaults={'ativo': True})


def unseed(apps, schema_editor):
    TermoSentinela = apps.get_model('sentinela', 'TermoSentinela')
    TermoSentinela.objects.filter(termo__in=TERMOS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('sentinela', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]

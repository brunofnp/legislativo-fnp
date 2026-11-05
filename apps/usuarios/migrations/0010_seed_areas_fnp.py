from django.db import migrations
from django.utils.text import slugify

# Áreas de nível coordenação/gerência do organograma da Secretaria-Executiva
# (ORGANOGRAMA-FLUXOS-FNP, vigente em 28/07/2026). A coordenação pode
# adicionar/editar outras depois no Django Admin.
AREAS = [
    'Secretaria-Executiva',
    'Coordenação de Administração',
    'Coordenação de Comunicação e Eventos',
    'Coordenação de Finanças Públicas e Assuntos Legislativos',
    'Coordenação de Meio Ambiente e Mobilidade Urbana',
    'Coordenação de Relações Internacionais e Gestão de Associados',
    'Superintendência e Área Técnica',
    'Gerência de Dados e Inovação',
    'Gerência de Estruturação de Projetos',
]


def seed_areas(apps, schema_editor):
    AreaFNP = apps.get_model('usuarios', 'AreaFNP')
    for ordem, nome in enumerate(AREAS, start=1):
        AreaFNP.objects.get_or_create(
            nome=nome,
            defaults={'slug': slugify(nome), 'ordem': ordem},
        )


def remove_areas(apps, schema_editor):
    AreaFNP = apps.get_model('usuarios', 'AreaFNP')
    AreaFNP.objects.filter(nome__in=AREAS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0009_areafnp_perfil_papel_area_perfil_area'),
    ]

    operations = [
        migrations.RunPython(seed_areas, remove_areas),
    ]

from __future__ import annotations

from pathlib import Path

from django.apps import apps
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Gera um dicionário de dados em Markdown a partir dos modelos Django.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            default='docs/dicionario_de_dados.md',
            help='Caminho do arquivo Markdown de saída.',
        )

    def handle(self, *args, **options):
        output_path = Path(options['output'])
        lines: list[str] = [
            '# Dicionário de dados\n',
            '\n',
            'Este documento foi gerado automaticamente pelo comando `python manage.py generate_data_dictionary`.\n',
            '\n',
        ]
        app_config = apps.get_app_config('legislativo')
        for model in app_config.get_models():
            lines.append(f'## {model._meta.verbose_name_plural.title()}\n')
            lines.append(f'**Nome do modelo:** `{model._meta.label}`\n')
            lines.append('\n')
            lines.append('| Campo | Tipo | Obrigatório | Relacionamento | Descrição |\n')
            lines.append('|------|------|-------------|----------------|-----------|\n')
            for field in model._meta.get_fields():
                if field.many_to_many or field.one_to_many:
                    continue
                name = field.name
                field_type = field.get_internal_type()
                required = 'Sim' if getattr(field, 'blank', False) is False and getattr(field, 'null', False) is False else 'Não'
                relation = ''
                if field.is_relation and field.related_model is not None:
                    relation = f'FK -> `{field.related_model._meta.label}`'
                lines.append(f'| `{name}` | {field_type} | {required} | {relation} |  |\n')
            lines.append('\n')
        output_path.write_text(''.join(lines), encoding='utf-8')
        self.stdout.write(self.style.SUCCESS(f'Dicionário de dados gerado em {output_path}'))

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import requests
from django.core.management import call_command
from django.core.management.base import BaseCommand

FIRESTORE_BASE = 'https://firestore.googleapis.com/v1/projects/legislativo-fnp/databases/(default)/documents'


def decode_value(value):
    if value is None or 'nullValue' in value:
        return None
    if 'stringValue' in value:
        return value['stringValue']
    if 'integerValue' in value:
        return int(value['integerValue'])
    if 'doubleValue' in value:
        return value['doubleValue']
    if 'booleanValue' in value:
        return value['booleanValue']
    if 'timestampValue' in value:
        return value['timestampValue']
    if 'arrayValue' in value:
        return [decode_value(v) for v in value['arrayValue'].get('values', [])]
    if 'mapValue' in value:
        return {k: decode_value(v) for k, v in value['mapValue'].get('fields', {}).items()}
    return None


def decode_document(doc):
    return {k: decode_value(v) for k, v in doc.get('fields', {}).items()}


class Command(BaseCommand):
    help = (
        'Importa as proposições do banco Firestore do antigo app '
        '(legislativo-fnp.web.app) para o banco atual, reaproveitando o '
        'comando ingest_legislativo.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--collection',
            type=str,
            default='proposicoes',
            help='Nome da coleção do Firestore a importar (default: proposicoes).',
        )
        parser.add_argument('--dry-run', action='store_true', help='Não grava no banco, apenas valida o payload')
        parser.add_argument(
            '--keep-json',
            type=str,
            default='',
            help='Se informado, salva uma cópia do JSON baixado nesse caminho.',
        )

    def handle(self, *args, **options):
        collection = options['collection']
        registros = self._fetch_all(collection)
        self.stdout.write(f'{len(registros)} documento(s) encontrados em "{collection}" no Firestore legado.')

        if options['keep_json']:
            Path(options['keep_json']).write_text(
                json.dumps(registros, ensure_ascii=False, indent=2), encoding='utf-8'
            )

        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as tmp:
            json.dump(registros, tmp, ensure_ascii=False)
            tmp_path = tmp.name

        try:
            call_command('ingest_legislativo', tmp_path, dry_run=options['dry_run'])
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def _fetch_all(self, collection):
        registros = []
        page_token = None
        url = f'{FIRESTORE_BASE}/{collection}'

        while True:
            params = {'pageSize': 100}
            if page_token:
                params['pageToken'] = page_token
            response = requests.get(url, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()
            documentos = data.get('documents', [])
            registros.extend(decode_document(doc) for doc in documentos)
            page_token = data.get('nextPageToken')
            if not page_token or not documentos:
                break

        return registros

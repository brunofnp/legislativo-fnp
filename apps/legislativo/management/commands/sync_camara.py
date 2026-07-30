from __future__ import annotations

import time
from datetime import datetime

import requests
from django.core.management.base import BaseCommand

from ...data_utils import slug_for_name
from apps.proposicoes.models import Macrotema, Proposicao

CAMARA_API = 'https://dadosabertos.camara.leg.br/api/v2'

DEFAULT_KEYWORDS = [
    'municípios',
    'municipal',
    'prefeituras',
    'FPM',
]

MACROTEMA_KEYWORDS = {
    'Infraestrutura': ['transporte', 'saneamento', 'mobilidade', 'infraestrutura', 'obras', 'habitação'],
    'Saúde': ['saúde', 'sus ', 'hospital', 'vigilância sanitária'],
    'Educação': ['educação', 'escola', 'creche', 'ensino'],
    'Finanças Públicas': ['fpm', 'repasse', 'financiamento', 'tributár', 'orçament', 'fundo de participação'],
    'Meio Ambiente': ['ambiental', 'clima', 'resíduos', 'saneamento básico'],
    'Gestão Pública': ['gestão pública', 'administração pública', 'servidor público', 'licitação'],
}

URGENTE_KEYWORDS = ['urgência', 'urgente']
APROVADA_KEYWORDS = ['transformad', 'sancionad', 'promulgad', 'aprovad']
PAUTA_KEYWORDS = ['pronta para pauta', 'incluíd', 'ordem do dia']


def classify_macrotema(texto: str) -> str | None:
    texto = texto.lower()
    for nome, keywords in MACROTEMA_KEYWORDS.items():
        if any(keyword in texto for keyword in keywords):
            return nome
    return None


def get_or_create_macrotema(nome: str | None):
    if not nome:
        return None
    macrotema, _ = Macrotema.objects.get_or_create(
        nome=nome,
        defaults={'slug': slug_for_name(nome), 'cor': '#1A4B8F'},
    )
    return macrotema


class Command(BaseCommand):
    help = 'Sincroniza proposições de interesse municipal a partir da API de Dados Abertos da Câmara dos Deputados.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--keywords',
            type=str,
            default=','.join(DEFAULT_KEYWORDS),
            help='Lista de palavras-chave separadas por vírgula usadas para buscar proposições relevantes.',
        )
        parser.add_argument('--paginas', type=int, default=2, help='Número de páginas por palavra-chave (100 itens cada).')
        parser.add_argument(
            '--watch',
            type=int,
            default=0,
            help='Se maior que zero, roda em loop contínuo a cada N segundos (para manter os dados atualizados).',
        )

    def handle(self, *args, **options):
        keywords = [k.strip() for k in options['keywords'].split(',') if k.strip()]
        paginas = options['paginas']
        watch = options['watch']

        if watch > 0:
            self.stdout.write(f'Modo watch ativado: sincronizando a cada {watch}s. Ctrl+C para interromper.')
            while True:
                self._sync_once(keywords, paginas)
                time.sleep(watch)
        else:
            self._sync_once(keywords, paginas)

    def _sync_once(self, keywords, paginas):
        vistos = set()
        criadas = 0
        atualizadas = 0

        for keyword in keywords:
            for pagina in range(1, paginas + 1):
                resultados = self._buscar_proposicoes(keyword, pagina)
                if not resultados:
                    break
                for item in resultados:
                    prop_id = item['id']
                    if prop_id in vistos:
                        continue
                    vistos.add(prop_id)
                    created = self._upsert_proposicao(item)
                    if created:
                        criadas += 1
                    else:
                        atualizadas += 1
                    time.sleep(0.15)

        self.stdout.write(f'Sincronização concluída: {criadas} criada(s), {atualizadas} atualizada(s).')

    def _buscar_proposicoes(self, keyword, pagina):
        try:
            response = requests.get(
                f'{CAMARA_API}/proposicoes',
                params={
                    'keywords': keyword,
                    'itens': 100,
                    'pagina': pagina,
                    'ordem': 'DESC',
                    'ordenarPor': 'id',
                },
                timeout=15,
            )
            response.raise_for_status()
            return response.json().get('dados', [])
        except requests.RequestException as exc:
            self.stderr.write(f'Erro ao buscar proposições para "{keyword}": {exc}')
            return []

    def _buscar_detalhe(self, prop_id):
        try:
            response = requests.get(f'{CAMARA_API}/proposicoes/{prop_id}', timeout=15)
            response.raise_for_status()
            return response.json().get('dados', {})
        except requests.RequestException as exc:
            self.stderr.write(f'Erro ao buscar detalhe da proposição {prop_id}: {exc}')
            return {}

    def _upsert_proposicao(self, item):
        prop_id = item['id']
        detalhe = self._buscar_detalhe(prop_id)
        status = detalhe.get('statusProposicao') or {}

        ementa = item.get('ementa') or ''
        descricao_situacao = status.get('descricaoSituacao') or ''
        descricao_tramitacao = status.get('descricaoTramitacao') or ''
        sigla_orgao = status.get('siglaOrgao') or ''
        regime = status.get('regime') or ''
        data_hora = status.get('dataHora', '')

        texto_classificacao = f'{ementa} {item.get("keywords") or ""}'
        texto_status = f'{descricao_situacao} {descricao_tramitacao} {regime}'.lower()

        titulo = f'{item["siglaTipo"]} {item["numero"]}/{item["ano"]}'
        ultima_movimentacao = descricao_tramitacao
        if data_hora:
            try:
                dt = datetime.fromisoformat(data_hora)
                ultima_movimentacao = f'{descricao_tramitacao} em {dt.strftime("%d/%m/%Y")}'
            except ValueError:
                pass

        props = {
            'casa': 'camara',
            'status_tramitacao': descricao_situacao or 'Status indisponível',
            'local': sigla_orgao,
            'urgente': any(k in texto_status for k in URGENTE_KEYWORDS),
            'aprovada': any(k in texto_status for k in APROVADA_KEYWORDS),
            'pauta': any(k in texto_status for k in PAUTA_KEYWORDS),
            'macrotema': get_or_create_macrotema(classify_macrotema(texto_classificacao)),
            'ementa_resumida': ementa,
            'ultima_movimentacao': ultima_movimentacao,
            'link': f'https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={prop_id}',
        }

        _, created = Proposicao.objects.update_or_create(titulo=titulo, defaults=props)
        return created

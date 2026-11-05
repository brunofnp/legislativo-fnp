"""Busca de proposições por palavra-chave nas fontes oficiais, para o sentinela.

Câmara: usa o índice de palavras-chave do Dados Abertos (curado pela Câmara),
que é mais confiável que casar a ementa no texto cru. Senado: a busca por
palavra do Dados Abertos foi descontinuada (migraram para /processo, que só
busca por sigla/número/ano), então fica como gancho best-effort que hoje
devolve lista vazia -- entra quando houver endpoint novo. Nenhuma exceção de
rede escapa: falha de API vira lista vazia.
"""
from __future__ import annotations

import datetime

import requests

CAMARA_API = 'https://dadosabertos.camara.leg.br/api/v2'
TIMEOUT = 20


def _desde(dias: int) -> str:
    return (datetime.date.today() - datetime.timedelta(days=max(1, dias))).isoformat()


def buscar_camara(termos: list[str], dias: int = 15) -> list[dict]:
    """Proposições da Câmara que casam com algum termo (palavra-chave indexada),
    apresentadas nos últimos ``dias``. Dedupe por id. Nunca levanta exceção."""
    desde = _desde(dias)
    vistos: dict[str, dict] = {}
    for termo in termos:
        try:
            resp = requests.get(
                f'{CAMARA_API}/proposicoes',
                params={
                    'keywords': termo,
                    'dataApresentacaoInicio': desde,
                    'ordenarPor': 'id',
                    'ordem': 'DESC',
                    'itens': 100,
                },
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            dados = resp.json().get('dados', [])
        except (requests.RequestException, ValueError):
            continue
        for item in dados:
            prop_id = str(item.get('id') or '')
            if not prop_id or prop_id in vistos:
                continue
            sigla = item.get('siglaTipo') or ''
            numero = item.get('numero') or ''
            ano = item.get('ano') or ''
            vistos[prop_id] = {
                'fonte': 'camara',
                'id_externo': prop_id,
                'titulo': f'{sigla} {numero}/{ano}'.strip(),
                'casa': 'camara',
                'ementa': item.get('ementa') or '',
                'link': f'https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={prop_id}',
                'termo': termo,
            }
    return list(vistos.values())


def buscar_senado(termos: list[str], dias: int = 15) -> list[dict]:
    """Gancho best-effort: a busca por palavra-chave do Dados Abertos do Senado
    foi descontinuada. Devolve [] até haver endpoint novo; nunca quebra."""
    return []


def buscar(termos: list[str], dias: int = 15) -> list[dict]:
    """Candidatos de todas as fontes."""
    termos = [t.strip() for t in termos if t and t.strip()]
    if not termos:
        return []
    return buscar_camara(termos, dias) + buscar_senado(termos, dias)

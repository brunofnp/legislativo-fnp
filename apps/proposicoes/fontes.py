"""Busca de proposições nas fontes oficiais (Câmara e Senado).

Reutilizado pelo cadastro no painel e, no futuro, pelo `sync_camara`. Cada
função devolve um dicionário normalizado (mesmas chaves do `ingest_legislativo`)
ou ``None`` quando não encontra. Nenhuma exceção de rede escapa: falha de API
vira ``None`` (quem chama trata como "não encontrada / tente de novo").
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import requests

CAMARA_API = 'https://dadosabertos.camara.leg.br/api/v2'
SENADO_API = 'https://legis.senado.leg.br/dadosabertos'
TIMEOUT = 15

# Tipos aceitos no formulário; a sigla é a mesma nas duas casas.
TIPOS = ['PL', 'PEC', 'PLP', 'PLN', 'PLV', 'MPV', 'PDL', 'PRC', 'PLC', 'PLS']


def _normalizar(titulo, casa, *, status='', local='', ultima='', ementa='', link=''):
    return {
        'titulo': titulo,
        'casa': casa,
        'status_tramitacao': status or '',
        'local': local or '',
        'ultima_movimentacao': ultima or '',
        'ementa_resumida': ementa or '',
        'link': link or '',
    }


def buscar_camara(tipo: str, numero: int, ano: int):
    """Busca na API de Dados Abertos da Câmara. ``None`` se não achar."""
    try:
        resp = requests.get(
            f'{CAMARA_API}/proposicoes',
            params={'siglaTipo': tipo, 'numero': numero, 'ano': ano},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        dados = resp.json().get('dados', [])
    except requests.RequestException:
        return None
    if not dados:
        return None

    item = dados[0]
    prop_id = item['id']
    ementa = item.get('ementa') or ''
    status_situacao = ''
    sigla_orgao = ''
    ultima = ''
    try:
        det = requests.get(f'{CAMARA_API}/proposicoes/{prop_id}', timeout=TIMEOUT)
        det.raise_for_status()
        status = det.json().get('dados', {}).get('statusProposicao') or {}
        status_situacao = status.get('descricaoSituacao') or ''
        sigla_orgao = status.get('siglaOrgao') or ''
        descricao_tram = status.get('descricaoTramitacao') or ''
        data_hora = status.get('dataHora') or ''
        ultima = descricao_tram
        if data_hora:
            try:
                dt = datetime.fromisoformat(data_hora)
                ultima = f'{descricao_tram} em {dt.strftime("%d/%m/%Y")}'.strip()
            except ValueError:
                pass
    except requests.RequestException:
        pass

    return _normalizar(
        f'{tipo} {numero}/{ano}',
        'camara',
        status=status_situacao or 'Em tramitação',
        local=sigla_orgao,
        ultima=ultima,
        ementa=ementa,
        link=f'https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={prop_id}',
    )


def buscar_senado(tipo: str, numero: int, ano: int):
    """Busca na API de Dados Abertos do Senado. ``None`` se não achar."""
    try:
        resp = requests.get(
            f'{SENADO_API}/processo',
            params={'sigla': tipo, 'numero': numero, 'ano': ano},
            headers={'Accept': 'application/json'},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        dados = resp.json()
    except requests.RequestException:
        return None
    if isinstance(dados, dict):
        dados = dados.get('ListaProcesso', {}).get('Processos', {}).get('Processo', [])
    if not isinstance(dados, list) or not dados:
        return None

    item = dados[0] if isinstance(dados[0], dict) else {}
    codigo = item.get('codigoMateria') or item.get('CodigoMateria')
    if not codigo:
        return None
    ementa = item.get('ementa') or item.get('Ementa') or ''
    situacao = (
        item.get('situacaoAtual')
        or item.get('descricaoSituacao')
        or item.get('situacao')
        or item.get('descricaoObjetivoProcesso')
        or ''
    )
    data_situacao = item.get('dataSituacaoAtual') or ''
    ultima = ''
    if data_situacao:
        try:
            ultima = datetime.fromisoformat(data_situacao).strftime('%d/%m/%Y')
        except ValueError:
            ultima = str(data_situacao)

    return _normalizar(
        f'{tipo} {numero}/{ano}',
        'senado',
        status=situacao or 'Em tramitação',
        ultima=ultima,
        ementa=ementa,
        link=f'https://www25.senado.leg.br/web/atividade/materias/-/materia/{codigo}',
    )


def buscar_status_camara(prop_id):
    """Situação atual de uma proposição da Câmara pelo ``idProposicao``.

    Usado pelo atualizador dirigido (``atualizar_tramitacao``) para refrescar a
    última movimentação das proposições já no painel. Devolve um dicionário com
    a movimentação já formatada em ``ultima`` (``None`` se a API falhar ou não
    trouxer dados — nenhuma exceção de rede escapa)."""
    try:
        det = requests.get(f'{CAMARA_API}/proposicoes/{prop_id}', timeout=TIMEOUT)
        det.raise_for_status()
        status = det.json().get('dados', {}).get('statusProposicao') or {}
    except requests.RequestException:
        return None
    if not status:
        return None

    situacao = status.get('descricaoSituacao') or ''
    tramitacao = status.get('descricaoTramitacao') or ''
    despacho = (status.get('despacho') or '').strip()
    orgao = status.get('siglaOrgao') or ''
    data_hora = status.get('dataHora') or ''
    data_fmt = ''
    if data_hora:
        try:
            data_fmt = datetime.fromisoformat(data_hora).strftime('%d/%m/%Y')
        except ValueError:
            data_fmt = ''

    corpo = despacho or tramitacao or situacao
    if not corpo:
        return None
    ultima = f'{data_fmt}: {corpo}' if data_fmt else corpo
    return {
        'situacao': situacao,
        'orgao': orgao,
        'tramitacao': tramitacao,
        'despacho': despacho,
        'data': data_fmt,
        'ultima': ultima.strip(),
    }


def buscar_status_senado(cod):
    """Situação atual de uma matéria do Senado pelo ``codigoMateria``.

    Usado pelo atualizador de pauta para saber se a matéria está na Ordem do
    Dia. Devolve um dicionário com ``na_pauta`` (True quando a situação indica
    ordem do dia) ou ``None`` em falha de rede/parse — nenhuma exceção escapa."""
    try:
        r = requests.get(
            f'{SENADO_API}/materia/situacaoatual/{cod}',
            headers={'Accept': 'application/json'},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        d = r.json()
    except (requests.RequestException, ValueError):
        return None
    try:
        m = d['SituacaoAtualMateria']['Materias']['Materia']
        m = m[0] if isinstance(m, list) else m
        a = m['SituacaoAtual']['Autuacoes']['Autuacao']
        a = a[0] if isinstance(a, list) else a
        si = a['Situacoes']['Situacao']
        si = si[0] if isinstance(si, list) else si
        situacao = si.get('DescricaoSituacao') or ''
        data = si.get('DataSituacao') or ''
    except (KeyError, IndexError, TypeError):
        return None
    return {
        'situacao': situacao,
        'data': data,
        'na_pauta': 'ordem do dia' in situacao.lower(),
    }


def pauta_camara(dias: int = 7):
    """Conjunto de ``idProposicao`` (str) que estão na pauta das sessões
    DELIBERATIVAS da Câmara (Plenário e comissões) de hoje até ``dias`` à
    frente, lido da agenda oficial (``/eventos`` + ``/eventos/{id}/pauta``).

    Devolve ``None`` se não conseguir ler a lista de eventos — sinal para quem
    chama NÃO alterar nada (uma falha de rede não pode "esvaziar" a pauta).
    Um ``set`` (mesmo vazio) significa leitura bem-sucedida."""
    hoje = date.today()
    fim = hoje + timedelta(days=max(1, dias))
    url = f'{CAMARA_API}/eventos'
    params = {'dataInicio': hoje.isoformat(), 'dataFim': fim.isoformat(), 'itens': 100}

    eventos: list[dict] = []
    try:
        while url:
            resp = requests.get(url, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
            body = resp.json()
            eventos.extend(body.get('dados', []))
            url = None
            params = None
            for link in body.get('links', []):
                if link.get('rel') == 'next':
                    url = link.get('href')
                    break
            if len(eventos) > 2000:
                break
    except (requests.RequestException, ValueError):
        return None

    ids: set[str] = set()
    for ev in eventos:
        if 'eliberativ' not in (ev.get('descricaoTipo') or '').lower():
            continue
        ev_id = ev.get('id')
        if not ev_id:
            continue
        try:
            r = requests.get(f'{CAMARA_API}/eventos/{ev_id}/pauta', timeout=TIMEOUT)
            r.raise_for_status()
            itens = r.json().get('dados', [])
        except (requests.RequestException, ValueError):
            continue
        for it in itens:
            prop = it.get('proposicao_') or {}
            pid = prop.get('id')
            if pid:
                ids.add(str(pid))
    return ids


def buscar_proposicao(tipo: str, numero: int, ano: int):
    """Tenta a Câmara; se não achar, o Senado. Devolve o dicionário
    normalizado ou ``None``."""
    tipo = (tipo or '').strip().upper()
    return buscar_camara(tipo, numero, ano) or buscar_senado(tipo, numero, ano)

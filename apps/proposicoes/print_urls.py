import re
from urllib.parse import parse_qs, urlparse

CAMARA_BASE = 'https://www.camara.leg.br/proposicoesWeb'


def urls_impressao_oficial(link):
    """A partir do link da fonte oficial (Câmara ou Senado, já gravado em
    Proposicao.link), monta os links diretos de impressão de cada casa --
    nunca uma página de tramitação normal.

    Câmara tem 3 formatos (reduzida/completa/personalizada), todos
    dependem só do idProposicao -- o mesmo número aparece tanto em
    .../propostas-legislativas/<id> (formato usado no legado importado)
    quanto em .../fichadetramitacao?idProposicao=<id> (formato usado pelo
    sync_camara.py), confirmado comparando as duas formas nos dados reais
    importados. O jsessionid que o site da Câmara anexa nas URLs de
    impressão é dispensável -- é só o fallback de rastreio de sessão do
    Java pra navegador sem cookie, a URL funciona sem ele.

    Senado só tem 1 formato (PDF único, sem variação de recorte): a mesma
    URL da matéria com "/pdf" no final.

    Se o link existir mas a fonte não for reconhecida, cai num fallback de
    1 item (link direto pra própria fonte) -- nunca fica sem nenhuma opção
    enquanto houver link cadastrado."""
    if not link:
        return {}

    partes = urlparse(link)
    host = partes.netloc.lower()

    if host.endswith('camara.leg.br'):
        id_proposicao = None
        query = parse_qs(partes.query)
        if 'idProposicao' in query:
            id_proposicao = query['idProposicao'][0]
        else:
            match = re.search(r'/propostas-legislativas/(\d+)', partes.path)
            if match:
                id_proposicao = match.group(1)
        if id_proposicao:
            return {
                'Impressão reduzida': f'{CAMARA_BASE}/prop_imp?idProposicao={id_proposicao}&ord=1&tp=reduzida',
                'Impressão completa': f'{CAMARA_BASE}/prop_imp?idProposicao={id_proposicao}&ord=1&tp=completa',
                'Impressão personalizada': f'{CAMARA_BASE}/prop_visual_impress?idProposicao={id_proposicao}&ord=1',
            }

    if host.endswith('senado.leg.br'):
        return {'Imprimir (PDF)': f'{link.rstrip("/")}/pdf'}

    return {'Abrir na fonte oficial': link}

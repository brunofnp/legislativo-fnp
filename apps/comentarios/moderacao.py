"""Moderação automática de comentários.

Política adotada (padrão comum em fóruns — Discourse "watched words", automod
do Reddit, filtros do phpBB/vBulletin): pré-moderação total não escala para
uma equipe pequena e atrasa a discussão; a alternativa consolidada é publicar
por padrão e bloquear automaticamente por lista de termos, mantida pelos
próprios moderadores (nunca hardcoded no código-fonte — evita lista
desatualizada, incompleta ou embaraçosa versionada no git). A checagem usa
fronteira de palavra (\\b) para não pegar substrings soltas (ex.: bloquear
"cu" não deveria reprovar "cultura" — o clássico "Scunthorpe problem" de
filtros de palavrão) e ignora acentuação/maiúsculas.

Ainda assim, nenhuma lista de termos pega tudo (sarcasmo, assédio sem
palavrão, contexto). Considerar no futuro um mecanismo de denúncia pelos
próprios usuários como complemento — não implementado aqui por não ter sido
pedido."""

import re
import unicodedata

from .models import PalavraProibida


def _normalizar(texto):
    texto = texto.lower()
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')


def contem_palavra_proibida(texto):
    texto_normalizado = _normalizar(texto)
    for palavra in PalavraProibida.objects.filter(ativa=True).values_list('palavra', flat=True):
        termo = _normalizar(palavra).strip()
        if termo and re.search(rf'\b{re.escape(termo)}\b', texto_normalizado):
            return True
    return False


def classificar_comentario(texto):
    """'rejeitado' se contiver palavra proibida ativa, senão 'aprovado' —
    comentário nasce publicado, sem precisar de aprovação manual."""
    return 'rejeitado' if contem_palavra_proibida(texto) else 'aprovado'

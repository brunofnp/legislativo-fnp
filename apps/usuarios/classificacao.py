"""Classificação automática do perfil de acesso (Perfil.classe_usuario) a
partir do cargo informado no cadastro -- nunca escolhida manualmente pelo
usuário. "Equipe FNP" nunca é atribuída por aqui: só via promoção manual
pelo Root/Administrador FNP no Admin (mesmo raciocínio de não confiar em
autodeclaração pra um campo que carrega identidade/confiança, já usado em
apps.comentarios.moderacao pra palavra proibida)."""

import re
import unicodedata


def _normalizar(texto):
    texto = (texto or '').lower()
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')


_PADRAO_PREFEITO = re.compile(r'\bprefeit\w*\b')
_PADRAO_PARLAMENTAR = re.compile(r'\b(deputad\w*|senador\w*|vereador\w*|parlamentar\w*)\b')


def classificar_por_cargo(cargo):
    """'prefeito' se o cargo citar prefeito/prefeita, 'parlamentar' se citar
    deputado/senador/vereador, senão 'indicado_prefeitura' -- padrão pra
    qualquer outro cargo municipal (secretário, assessor, diretor etc.)."""
    from apps.usuarios.models import Perfil

    texto = _normalizar(cargo)
    if _PADRAO_PREFEITO.search(texto):
        return Perfil.PREFEITO
    if _PADRAO_PARLAMENTAR.search(texto):
        return Perfil.PARLAMENTAR
    return Perfil.INDICADO_PREFEITURA

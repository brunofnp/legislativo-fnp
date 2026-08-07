"""Conteúdo do modal "Ajuda desta página" (botão "?" na topbar/Admin) --
texto varia por página, indexado pelo url_name de cada view. Mantido como
dado Python simples (não modelo de banco) porque é conteúdo editorial fixo
da própria plataforma, não algo que a equipe FNP precise curar via Admin
(diferente de PalavraProibida, por exemplo)."""

AJUDA_PADRAO = {
    'titulo': 'Painel Legislativo FNP',
    'descricao': 'Acompanhe proposições de interesse municipal em tramitação no Congresso Nacional.',
    'dicas': [],
}

AJUDA_PAGINAS = {
    'home': {
        'titulo': 'Painel Geral',
        'descricao': (
            'O que o Congresso Nacional está discutindo e o impacto nos municípios -- '
            'proposições urgentes, em alta e a lista completa, sempre atualizadas.'
        ),
        'dicas': [
            'Use a busca (ou Ctrl K) e o filtro de tema pra encontrar uma proposição específica.',
            'A estrela em cada card favorita a proposição -- acompanhe depois em "Favoritos" na barra lateral.',
            'Clique em qualquer card pra abrir a discussão completa e comentar.',
        ],
    },
    'proposicao_detail': {
        'titulo': 'Proposição em detalhe',
        'descricao': (
            'Resumo, status de tramitação e o fórum de discussão da proposição -- '
            'o título é um link direto pra fonte oficial (Câmara ou Senado).'
        ),
        'dicas': [
            'Comente pra participar da discussão -- fica visível pra todo mundo, moderado automaticamente.',
            'Use "Enviar participação" pra registrar uma sugestão, dúvida ou indicação sobre essa proposição.',
        ],
    },
    'perfil': {
        'titulo': 'Meu perfil',
        'descricao': 'Seus dados de cadastro, foto e os links de privacidade (LGPD) da sua conta.',
        'dicas': [
            'O nome cadastrado aqui aparece nos seus comentários e na barra superior.',
            'Alterar senha, exportação de dados e exclusão de conta ficam na barra lateral, em "Privacidade".',
        ],
    },
    'favoritos_list': {
        'titulo': 'Favoritos',
        'descricao': 'As proposições que você marcou com a estrela, num só lugar pra acompanhar de perto.',
        'dicas': [],
    },
    'participacao_list': {
        'titulo': 'Participações',
        'descricao': 'Sugestões, dúvidas e indicações que você enviou sobre proposições específicas.',
        'dicas': [],
    },
    'cadastro_pendente': {
        'titulo': 'Cadastro em análise',
        'descricao': (
            'Seu cadastro ainda não foi aprovado por um administrador da FNP -- '
            'a navegação libera assim que a aprovação acontecer.'
        ),
        'dicas': [],
    },
    # Django Admin -- url_name aqui não tem o prefixo "legislativo:".
    'index': {
        'titulo': 'Administração e hierarquia de acesso',
        'descricao': (
            'Painel do Root: métricas de pendências (moderação, cadastros, exclusões) e atalhos '
            'pros changelists mais usados.'
        ),
        'dicas': [
            'Os números nos cards do topo já são links direto pra fila filtrada correspondente.',
            'A barra lateral agrupa cada área por função -- clique pra expandir os grupos com mais de um item.',
        ],
    },
    'exportar_dados': {
        'titulo': 'Exportar dados',
        'descricao': (
            'Exporta cadastro e interação (comentários, participações, denúncias) de um usuário específico '
            'ou em massa, em JSON -- pra alimentar o banco externo de pontuação de engajamento.'
        ),
        'dicas': [
            'Exclusivo do Root: dado de interação de outras pessoas é informação sensível.',
            'Selecionar "em massa" exporta todo mundo; selecionar um usuário exporta só a pessoa escolhida.',
        ],
    },
}


def ajuda_para_pagina(url_name):
    return AJUDA_PAGINAS.get(url_name, AJUDA_PADRAO)

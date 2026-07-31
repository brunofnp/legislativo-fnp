# CLAUDE.md — Contexto do Projeto Legislativo FNP

> Arquivo de contexto para sessões com Claude Code. Atualizado automaticamente a cada 3h enquanto há sessão ativa (mantém este arquivo fiel ao código para evitar redescoberta/gasto de tokens em sessões futuras).
> Última atualização: 2026-07-31 (Django Admin reconstruído com dashboard/sidebar em camadas e ícones, aprovação de cadastro, fotos de perfil com import do Google, LGPD, cadastro com município/setor/telefone, moderação automática de comentários por palavra proibida)

---

## Visão Geral

**Legislativo FNP** é uma plataforma Django para acompanhamento legislativo voltada ao monitoramento de proposições em tramitação no Congresso Nacional e ao impacto para municípios. A proposta é reunir um painel institucional, visual profissional e fluxo de participação colaborativa para a Frente Nacional de Prefeitas e Prefeitos.

URL de produção: GitHub Pages/hosting definido pela organização (branch `main` do remoto `production`)
Branch de desenvolvimento ativo: `next`

---

## Stack Tecnológica

| Camada | Tecnologia |
|---|---|
| Backend | Django 4.2.x · Python 3.12 local (via `.venv/`) / 3.11 no CI |
| Auth | django-allauth (login por e-mail + Google OAuth, cadastro manual ou Google) |
| Banco (dev) | SQLite |
| Banco (prod) | PostgreSQL (planejado, via `DATABASE_URL`) |
| Templates | Django Templates + CSS/JS vanilla |
| Estáticos | WhiteNoise |
| Dados | Modelos Django + management commands (`ingest_legislativo`, `sync_legado_firestore`, `sync_camara --watch`) |
| Mídia | Pillow (`ImageField` de `Perfil.foto`), `MEDIA_URL`/`MEDIA_ROOT` (`media/`, gitignored; servido via `runserver` em DEBUG) |
| UI | HTML semântico, CSS customizado (dark mode via `[data-theme]`), JavaScript vanilla |
| Testes | Django TestCase (via `RequestFactory`, não `self.client` — ver Observações) + pytest |

**Observação sobre Python 3.14:** Django 4.2 só suporta oficialmente até Python 3.12 — no 3.14 há um bug real do próprio Django (`copy.copy()` sobre `RequestContext`, `django/template/context.py`) que quebra `self.client.get(...)` nos testes E **todas as telas de listagem/adicionar do Django Admin** em runtime normal (não só em teste). Não é bug deste projeto, não afeta CI (3.11) nem produção. Fix local: sempre rodar via `.venv/` (Python 3.12, já criado e no `.gitignore`) — ver `docs/runbook.md`. Os testes usam `RequestFactory` + `SessionMiddleware` manual (funciona em qualquer versão, mantido por robustez).

---

## Estrutura de Arquivos

```
apps/
  usuarios/                 # Usuario (auth nativo), Perfil (FK p/ Municipio), Municipio
    models.py                # Perfil: status_aprovacao, foto, foto_google_url, setor_responsavel, exclusao_solicitada_em
    admin.py                # UsuarioAdmin (UserAdmin nativo) + PerfilInline + status de cadastro/exclusão
    signals.py               # cria Perfil (status pendente p/ novo usuário, aprovado p/ staff); atualiza foto do Google em login social
    middleware.py            # CadastroPendenteMiddleware — bloqueia navegação até perfil ser aprovado
    adapters.py              # GoogleAccountAdapter — importa foto de perfil do Google no signup social
  proposicoes/               # Proposicao, Macrotema, Tema, Noticia, EdicaoMeritoHistorico
    models.py
    admin.py                 # ProposicaoAdmin.save_model grava EdicaoMeritoHistorico; badge de macrotema; inlines
  comentarios/                # Comentario, Participacao, Notificacao, PalavraProibida
    models.py
    admin.py                 # ações em massa de moderação de comentário; PalavraProibida registrada aqui
    moderacao.py              # classificar_comentario() — aprova/rejeita automaticamente por palavra proibida
  legislativo/                # camada de views/urls/forms que orquestra os 3 apps acima
    admin.py                  # vazio (registros vivem nos apps de domínio)
    admin_site.py              # FNPAdminSite/FNPAdminConfig — AdminSite customizado (dashboard, index_template)
    models.py                 # vazio (models vivem nos apps de domínio)
    views.py
    urls.py
    forms.py                # CustomSignupForm (município/UF/setor/cargo/telefone), PerfilForm, PerfilDadosForm, ComentarioForm, ParticipacaoForm
    context_processors.py   # notificacoes + usuario_display_name + usuario_avatar_url
    data_utils.py            # split_temas() — separa temas compostos "A, B/C"
    templatetags/
      admin_icons.py           # ícones SVG por app/model do Django Admin (barra lateral)
    tests.py
    management/
      commands/
        ingest_legislativo.py
        sync_legado_firestore.py  # importa as 104 proposições reais do Firestore legado (legislativo-fnp.web.app)
        sync_camara.py             # sync ao vivo via API Dados Abertos da Câmara, com --watch
        setup_roles.py              # cria grupos Root/Administrador FNP/Usuário, promove um e-mail a Root
static/
  css/
    style.css               # app-shell, dark mode, acessibilidade, cards, auth
    admin-custom.css         # reskin completo do Django Admin (tema sempre claro, sidebar sempre escura)
  js/
    main.js
  img/
    logo-FNP.png
  favicon.svg
templates/
  base.html                  # rodapé (_footer.html) só renderiza na home (url_name == 'home')
  _sidebar.html             # menu lateral, só renderiza na página de perfil (mostrar_sidebar=True)
  _topbar.html              # barra superior (breadcrumb "Voltar | Título", busca, tema, notificações, avatar)
  _footer.html               # rodapé com links de LGPD (Política de Privacidade/Exportar/Excluir) + DPO
  _search_modal.html        # busca via Ctrl+K
  socialaccount/login.html  # confirmação de login Google, traduzida
  allauth/layouts/base.html # override raiz de TODAS as páginas do allauth (login/signup/logout/etc.)
  admin/
    base_site.html            # dark mode do Django Admin desativado; header/breadcrumb sempre claros
    fnp_index.html             # dashboard com métricas acionáveis (pendências de moderação/aprovação/exclusão)
    nav_sidebar.html           # sidebar do Admin reescrita (sem tabela padrão do Django, com ícones e grupos recolhíveis)
  legislativo/
    home.html
    perfil.html                # + upload de foto, município/UF/setor/telefone, links de conta/privacidade
    proposicao_detail.html
    participacao_list.html
    favoritos_list.html
    cadastro_pendente.html      # tela de bloqueio para cadastro ainda não aprovado
    politica_privacidade.html
    solicitar_exclusao.html
    _proposicao_card.html
setup/
  settings.py                 # LOGIN_URL, MEDIA_URL/ROOT, SOCIALACCOUNT_ADAPTER
  urls.py
  wsgi.py
  asgi.py
docs/
  README.md
  runbook.md
  adr/
    0001-initial-architecture.md
```

---

## Arquitetura do Projeto

### Domínio principal

Os models são divididos por domínio em `apps.usuarios`, `apps.proposicoes` e `apps.comentarios` (ver Estrutura de Arquivos). O app `legislativo` continua sendo a camada de views/urls/forms/templates que orquestra os três — todo `{% url 'legislativo:...' %}` nos templates continua válido, só os models/admins mudaram de app. Responsabilidades:
- modelar proposições (104 reais, migradas do Firestore legado), macrotemas, temas (M2M), comentários, participação, notificações e usuários
- renderizar a homepage com cards de briefing compactos (Urgentes, Áreas de interesse, Em alta, Últimos acessados, Todas)
- exibir detalhes de proposições e suportar fórum de comentários com notificação aos participantes
- autenticação opcional (navegação pública não exige login) via e-mail/senha ou Google OAuth

### Padrão atual de UI

- **Pública (não logado):** header simples só com logo (link externo para fnp.org.br) + botão "Entrar". Sem sidebar.
- **Autenticada:** topbar estilo breadcrumb (`← Voltar | Título`, oculto na própria home) + busca Ctrl+K, tamanho de fonte, dark mode, notificações, avatar (foto real se houver, senão inicial) com nome "Nome Sobrenome" + sidebar lateral colapsável, mas a sidebar **só é exibida na página de perfil** (`/perfil/`), não em todo o site. Logo da FNP (link externo) aparece no topbar nas páginas sem sidebar.
- Cards compactos (redesenhados segundo justinmind.com/ui-design/cards): badges de prioridade/urgência, chip de tema, meta-linha com ícones (Casa/Status/Municípios), estrela de favorito sem círculo.
- "Áreas de interesse" e filtro de tema em dropdown pesquisável (mesmo componente, `.tema-dropdown`).
- Rodapé (`_footer.html`) só renderiza na home — demais páginas não o incluem (`base.html` checa `request.resolver_match.url_name == 'home'`); tem links de LGPD (Política de Privacidade, Exportar meus dados, Solicitar exclusão) + contato do DPO.
- Acessibilidade: skip links (Alt+1/Alt+2), `:focus-visible` global, `prefers-reduced-motion`, `role="search"`, `aria-hidden` em ícones decorativos — ver `docs/adr` / commit `8efad51`.
- Dark mode via `[data-theme="dark"]` + `localStorage['fnp-theme']`; tamanho de fonte via `localStorage['fnp-font-size']`; sidebar colapsada via `localStorage['fnp-sidebar-collapsed']`.

### Django Admin — identidade visual e navegação própria

O Admin não usa mais o tema padrão do Django nem o modo escuro nativo (removido em `templates/admin/base_site.html` — `dark-mode-vars` vazio, sem toggle): cabeçalho, breadcrumb e conteúdo são **sempre claros**; só a barra lateral é escura (mesma paleta do site público). `AdminSite` customizado (`apps/legislativo/admin_site.py`, ligado via `FNPAdminConfig` no lugar de `django.contrib.admin` em `INSTALLED_APPS`) adiciona um dashboard na página inicial (`templates/admin/fnp_index.html`) com métricas clicáveis: comentários pendentes, cadastros pendentes, solicitações de exclusão, proposições urgentes/na pauta.

A barra lateral (`templates/admin/nav_sidebar.html`) **não reaproveita** `admin/app_list.html` (a versão do Django sempre renderiza o link "Adicionar" de cada model, show_changelinks só controla "Modificar") — é um loop próprio: apps com 1 model viram link direto, apps com mais de um viram grupo recolhível (`<details>/<summary>` nativos, sem JS próprio), cada um com ícone (`apps/legislativo/templatetags/admin_icons.py`, mapeamento por `app_label`/`object_name` com fallback). Cuidado ao mexer aqui: Django define `a:link, a:visited { color: var(--link-fg) }` globalmente com especificidade maior que uma classe simples — qualquer novo link na sidebar precisa repetir os pseudo-seletores (`#nav-sidebar .algo:link, #nav-sidebar .algo:visited`) ou fica ilegível nos links já visitados.

### Funcionalidades já implementadas

- Home com listagem, busca, filtro por tema (M2M), estatísticas (total, pauta, urgentes, alta prioridade, com relator)
- Favoritos e "últimos acessados" (funcionam mesmo sem login, via sessão)
- "Em alta" (ranking por visualizações + comentários) e "Áreas de interesse" (derivado dos temas mais acessados)
- Cadastro e login (e-mail/senha próprio ou Google OAuth via django-allauth); Google **sem credenciais reais ainda** — `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` vazios em `.env`, documentado em `docs/runbook.md`
- Cadastro coleta município/UF (vira `Municipio` via `get_or_create`, `Perfil.municipio` é `ForeignKey` — vários usuários podem apontar pro mesmo município), setor responsável, cargo e telefone; mesmos campos editáveis depois em `/perfil/`
- **Aprovação de cadastro:** todo cadastro novo nasce `Perfil.status_aprovacao='pendente'` (staff nasce `'aprovado'`); `CadastroPendenteMiddleware` redireciona usuário pendente para `cadastro_pendente.html` até um Root/Administrador FNP aprovar (ação em massa no `UsuarioAdmin`)
- **Fotos de perfil:** upload manual (`Perfil.foto`) ou importação automática da foto do Google no login social (`GoogleAccountAdapter.save_user` + signal `pre_social_login` para manter atualizada); exibida no topbar e nos comentários do fórum, com fallback pra inicial do nome
- **LGPD:** página de Política de Privacidade, exportação dos dados do usuário em JSON (`exportar_meus_dados`) e solicitação de exclusão de conta (`solicitar_exclusao` — só marca `Perfil.exclusao_solicitada_em`, exclusão real é manual pelo Root via Admin, sem autoexclusão instantânea)
- Página de perfil (`PerfilView`) com edição de nome/foto/telefone/cargo/município/UF/setor responsável, link para trocar senha (allauth) e para as ações de LGPD
- Fórum de comentários por proposição com notificação aos demais participantes da discussão (só dispara se o comentário for aprovado)
- **Moderação automática de comentários** (`apps/comentarios/moderacao.py`): comentário nasce aprovado por padrão (sem fila manual); é reprovado automaticamente só se contiver alguma `PalavraProibida` ativa (lista editável via Admin, nunca hardcoded). Checagem por fronteira de palavra (`\b`), sem acento/caixa — evita falso positivo tipo "droga" bloquear "drogaria" (Scunthorpe problem). Autor vê mensagem explicando a reprovação. Comentários "pendente" anteriores a essa mudança continuam precisando de revisão manual (ação em massa no Admin) — o auto-approve só vale pra novos envios.
- Endpoint SSE/polling para atualização de dados em tempo real
- Acessibilidade WCAG 2.1-aligned (skip links, foco visível, redução de movimento)

---

## Modelos principais

### Proposicao

Campos principais: `titulo`, `casa`, `status_tramitacao`, `local`, `pauta`, `urgente`, `aprovada`, `parada`, `prioridade_fnp`, `macrotema`, `ementa_resumida`, `proximos_eventos`, `interlocutores`, `ultima_movimentacao`, `link`, `posicionamento_fnp`, `acoes_incidencia`, `riscos_oportunidades`, `visualizacoes` (contador para "Em alta").

**`temas`** é `ManyToManyField` para `Tema` (migrado de FK única — ver migração `0002_replace_tema_with_m2m.py`, que separa nomes compostos "A, B/C" via `split_temas()`).

### Usuario / Perfil

`Usuario` é `AUTH_USER_MODEL`, estende `AbstractUser` (só dados de autenticação). `Perfil` guarda `municipio` (**ForeignKey**, não mais 1-para-1 — vários usuários podem ser do mesmo município), `telefone`, `cargo`, `setor_responsavel`, `foto` (upload), `foto_google_url` (importada no login social), `status_aprovacao` (pendente/aprovado/rejeitado) e `exclusao_solicitada_em`; criado automaticamente por signal (`signals.py`) a todo cadastro novo — inline no Admin de Usuario. Nome de exibição é `Usuario.get_display_name()` (nome completo ou derivado do e-mail) — nunca o e-mail cru na UI. Avatar é `Usuario.get_avatar_url()` (foto manual tem prioridade sobre a do Google). Hierarquia de acesso via grupos nativos do Django: **Root** (superusuário), **Administrador FNP**, **Usuário** (padrão); ver `python manage.py setup_roles`.

### Macrotema / Tema

- `Macrotema` organiza a classificação editorial das proposições
- `Tema` representa subcategorias mais específicas (M2M com Proposicao)

### Participacao / Comentario / Notificacao / PalavraProibida

- `Participacao` permite registrar contribuições, sugestões, dúvidas ou indicações — campos `municipio`, `uf`, `setor_responsavel`, `cargo`, `email`, `telefone`, `mensagem` (mesmo vocabulário do cadastro de usuário; `setor_responsavel`/`telefone` foram renomeados de `responsavel`/`whatsapp`)
- `Comentario` é a base do fórum por proposição; `status_moderacao` é calculado automaticamente no envio via `apps.comentarios.moderacao.classificar_comentario()` — não fica mais pendente por padrão
- `PalavraProibida` (`palavra`, `ativa`) é a lista, editável só via Admin, que aciona a reprovação automática
- `Notificacao` é criada para todo comentarista anterior quando alguém novo comenta na mesma discussão (`notificar_participantes_da_discussao`), só quando o comentário é aprovado

---

## Fluxo de dados e importação

As proposições podem ser importadas via management command:

```powershell
python manage.py ingest_legislativo <caminho-do-json>
```

O comando aceita payloads no formato de lista de registros com campos como:
- `Proposição`
- `Casa`
- `Status da Tramitação`
- `Tema`
- `Macrotema`
- `Ementa Resumida`
- `Próximos Eventos/Ações Esperadas`
- `Interlocutores Estratégicos...`
- `Última Movimentação`
- `Posicionamento da FNP`
- `Ações de Incidência da FNP...`
- `Riscos e Oportunidades`

O comando cria ou atualiza proposições, temas, macrotemas e notícias associadas.

---

## UI e UX — Convenções adotadas

### Estrutura visual

- Hero com mensagem institucional
- Estatísticas em cards
- Busca e filtros em painel dedicado
- Cards de briefing com leitura rápida
- Modal de detalhe para aprofundamento

### Responsividade

Toda alteração deve respeitar compatibilidade com dispositivos móveis:
- layouts responsivos
- legibilidade em telas pequenas
- espaço confortável para toque
- navegação estável em telas estreitas
- evitar dependência excessiva de hover como mecanismo principal

### Diretrizes de design

- visual institucional, sério e profissional
- leitura rápida, editorial e executiva
- prioridade ao entendimento imediato da proposição
- linguagem clara para usuários técnicos e gestores

### Acessibilidade (WCAG 2.1)

- skip links no topo (`#conteudo-principal`, `#menu-principal`, `#rodape`), atalhos Alt+1/Alt+2
- `:focus-visible` visível em todos os elementos interativos (light e dark mode)
- `@media (prefers-reduced-motion: reduce)` respeitado
- `role="search"` + `<label>` nos campos de busca; `aria-hidden="true"` em ícones decorativos
- zoom nativo do navegador (sem controle de zoom customizado)

---

## Git — Remotos e fluxo

O projeto usa dois remotos com papeis distintos:

| Remoto | URL | Uso |
|---|---|---|
| `origin` | `https://github.com/brunofnp/legislativo-fnp.git` | Repositório pessoal — desenvolvimento |
| `production` | `https://github.com/dadosfnp/legislativo-fnp.git` | Repositório da organização — produção |

### Branches

- `next` → branch principal de desenvolvimento
- `main` → branch de produção

### Fluxo diário

```powershell
git checkout next
git pull origin next
git push origin next
```

Para produção:

```powershell
git checkout main
git pull production main
git push production main
```

---

## CI e validação

### Validações locais recomendadas

- `python manage.py check`
- `python manage.py test apps.legislativo`
- `python manage.py collectstatic --noinput`

### Regras de qualidade

- manter o projeto funcional em Django e com templates renderizando corretamente
- preservar responsividade e estabilidade visual
- testar mudanças de UI e fluxo antes de publicar

---

## Diretrizes de Engenharia (padrão fixo — não revisitar sem pedido explícito)

Estas são decisões arquiteturais fechadas para o projeto. Se uma sugestão minha reabrir alguma delas (banco, SSE, Admin, auth, etc.), eu devo sinalizar isso explicitamente antes de agir, não decidir sozinho.

**Estrutura:** modelo Radar Brasil — `apps/` (um app por domínio), `base_templates/` (layout compartilhado), `templates/` por app, `static/`, `setup/` (settings/urls raiz), `locale/`, `docs/`. Um app = uma responsabilidade; nada de app genérico "core" virando depósito. `requirements.txt` (prod) e `requirements-dev.txt` (dev/lint/teste) separados; `.env.example` versionado, `.env` nunca. Models já divididos: `apps.usuarios`/`apps.proposicoes`/`apps.comentarios`; `apps.legislativo` é a camada de views/urls/forms que orquestra os três (não um app "core" de despejo — só não tem models próprios).

**Models/banco:** status/urgência/categoria é sempre coluna real calculada na ingestão, nunca string-matching em template/JS (`urgente`, `aprovada`, `parada`, `prioridade_fnp` já são assim). Edição de campo de mérito nunca sobrescreve — grava linha de histórico (autor, campo, valor anterior, novo, data); `EdicaoMeritoHistorico` é gravado automaticamente pelo `ProposicaoAdmin.save_model` e por `ingest_legislativo` sempre que `posicionamento_fnp`/`acoes_incidencia`/`riscos_oportunidades` mudam (campos listados em `Proposicao.CAMPOS_MERITO`). FK de thread sempre com `related_name` explícito (`Comentario.parent` → `related_name='respostas'`, já correto). Migrations sempre revisadas antes de aplicar, nunca schema editado direto em produção. Ingestão idempotente via `update_or_create` (já é o padrão em `ingest_legislativo.py`).

**Views/templates:** server-side rendering por padrão; JS só para interatividade puramente client-side sobre dado já carregado (filtro/busca). Nunca SPA client-side recalculando dado que já deveria vir pronto do servidor. Django Admin para telas administrativas (edição de mérito, gestão de macrotema, moderação de comentários, hierarquia de usuários via grupos/permissões nativas) em vez de CRUD customizado, a menos que a necessidade seja genuinamente pública-facing. Customização visual do Admin é feita sobrescrevendo templates/CSS do próprio Django (`AdminSite` customizado, `nav_sidebar.html` próprio) — nunca reescrever o Admin do zero como CRUD à parte.

**Autenticação:** auth nativo do Django, nunca senha única/`if pass == X`. Permissão via `django.contrib.auth` (permissions/groups) — grupos **Root** (superusuário, bypassa checagem de permissão), **Administrador FNP** (moderação/edição de conteúdo) e **Usuário** (padrão, atribuído automaticamente por signal a todo cadastro novo); ver `python manage.py setup_roles`. `Usuario` (auth) e `Perfil` (município/telefone/cargo/setor/foto, via signal) já são separados como o padrão User+Profile pede; `Perfil.municipio` é `ForeignKey` (não 1-para-1 — vários usuários podem ser do mesmo município). Cadastro novo exige aprovação (`Perfil.status_aprovacao`) antes de liberar navegação (`CadastroPendenteMiddleware`); staff já nasce aprovado.

**Moderação de comentários:** publicação é automática por padrão (não pré-moderação total) — só é bloqueada por lista de palavras proibidas gerenciada via Admin (`PalavraProibida`), nunca hardcoded no código. Checagem por fronteira de palavra, sem acento/caixa. Ver `apps/comentarios/moderacao.py`. Não introduzir fila de aprovação manual por padrão de novo sem decisão revista — o ponto desta mudança foi justamente tirar a equipe pequena desse gargalo.

**Tempo real:** SSE é a solução fechada para notificação (já implementado). Não introduzir WebSocket/Channels/Redis sem decisão revista explicitamente.

**Ingestão:** management command via cron. Não sugerir Celery/fila sem pedido, dado 1 dev só operando.

**Testes/lint:** seguir `pytest.ini`/`.flake8`/`pyproject.toml` já existentes (padrão Radar Brasil), sem ferramenta concorrente. Testar regra de negócio (cálculo de urgência, idempotência de carga, thread de comentário), não perseguir cobertura em código trivial.

**Infraestrutura:** Docker + Nginx no Droplet `fnp-web`, 1 database + 1 role dedicados no Postgres Managed, segredos em `.env` do servidor + Bitwarden, nunca no git. Mudança em Nginx compartilhado (ex.: SSE/upgrade de conexão) é mudança de infra compartilhada — sinalizar como tal e testar por túnel SSH antes de publicar.

**Processo:** entregas sequenciais e demonstráveis (1 dev só) — cada etapa roda sozinha antes da próxima começar, sem empilhar trabalho não testável.

---

## Regras de colaboração

1. **Nunca** adicionar `Co-Authored-By: Claude` em commits
2. **Nunca** inserir "Generated with Claude Code" em PRs ou commits
3. O autor dos commits deve ser `brunofnp`
4. Manter documentação atualizada quando houver mudanças significativas
5. Priorizar compatibilidade mobile em todas as alterações
6. Usar `next` para desenvolvimento e `main` para produção

---

## Estado Atual do Projeto (2026-07-31)

### Branch atual: `next` (main/production em ff-only com next; sem divergência — último merge levou tudo desta sessão pra `main`/`production` também)

### Conquistas implementadas

- Dados reais: 104 proposições migradas do Firestore legado + sync ao vivo com a Câmara
- Autenticação completa: cadastro próprio ou Google OAuth (allauth), todas as páginas allauth estilizadas via override de `allauth/layouts/base.html`
- Painel autenticado: topbar estilo breadcrumb + sidebar (restrita à página de perfil), dark mode, tamanho de fonte, busca Ctrl+K, notificações de menção/resposta, avatar com foto real (upload ou Google)
- Favoritos, "em alta", "áreas de interesse" (dropdown pesquisável), "últimos acessados" — funcionam com ou sem login (sessão)
- Cards redesenhados (compactos, hierarquia visual limpa)
- Acessibilidade: skip links, foco visível, `prefers-reduced-motion`, aria labels
- BOM UTF-8 removido de todo o repositório (causava gap visual no header e quebrava o CI via `pyproject.toml`)
- Hierarquia de acesso: grupos Root/Administrador FNP/Usuário via `setup_roles`, `bruno.marra@fnp.org.br` promovido a Root; link "Painel Admin" na sidebar do site só aparece pro Root (`is_superuser`, não só `is_staff`)
- Histórico de mérito conectado: `EdicaoMeritoHistorico` agora é gravado de fato (Admin e reingestão), não só um model dormente no schema
- Fórum redesenhado: métricas (comentários/participantes/visualizações), avatar, nome de exibição e resposta encadeada funcional; comentário nasce aprovado, só é reprovado automaticamente por palavra proibida (`apps/comentarios/moderacao.py`)
- `Usuario` (auth) separado de `Perfil` (município/telefone/cargo/setor/foto/status de aprovação) — `Perfil.municipio` é `ForeignKey` (corrigido de 1-para-1, que travaria dois usuários do mesmo município)
- Models divididos por domínio: `apps.usuarios`/`apps.proposicoes`/`apps.comentarios` (era tudo em `apps.legislativo`); tabelas e dados preservados via `SeparateDatabaseAndState` (zero DDL real, só realocação de estado) — **atenção:** qualquer migration nova que faça DDL real numa tabela `legislativo_*` precisa declarar dependência explícita na migration `legislativo` que criou a tabela de verdade, senão o banco de testes (criado do zero) pode tentar alterar uma tabela que ainda não existe
- Aprovação de cadastro: `Perfil.status_aprovacao` + `CadastroPendenteMiddleware` + tela `cadastro_pendente.html`
- Fotos de perfil: upload manual + importação automática do Google (adapter + signal), com fallback pra inicial do nome
- LGPD: Política de Privacidade, exportação de dados (JSON) e solicitação de exclusão de conta (fila de revisão do Root, não é instantâneo)
- Cadastro/perfil ganharam município (FK), UF, setor responsável, cargo, telefone — mesmo vocabulário usado em "Enviar participação" (`Participacao.setor_responsavel`/`telefone`, renomeados de `responsavel`/`whatsapp`)
- Django Admin **reconstruído**, não só reskinado: `AdminSite` customizado com dashboard de métricas acionáveis, dark mode nativo do Django desativado (Admin sempre claro, só a sidebar é escura), barra lateral própria com ícones por função e grupos recolhíveis (sem o link "Adicionar" que o `app_list.html` padrão sempre renderiza)
- Navegabilidade: topbar ganhou "← Voltar" estilo breadcrumb (oculto na própria home), rodapé só aparece na home
- Ambiente local migrado para Python 3.12 (`.venv/`) — Python 3.14 tem um bug real do Django 4.2 (`copy.copy()` em `RequestContext`) que quebra todas as telas de listagem/adicionar do Admin em runtime normal, não só em teste; ver `docs/runbook.md`

### Itens validados (nesta última rodada)

- `python manage.py check` → sem issues
- `python manage.py test` → 10/10 OK, inclusive recriando o banco de testes do zero (pegou o bug de dependência de migration entre apps)
- Testado via `Client` (não só `RequestFactory`): signup com novos campos, dois usuários no mesmo município, upload de foto, exportação de dados, solicitação de exclusão, moderação automática (aprovado/rejeitado/falso-positivo de substring), dashboard do Admin refletindo pendências
- `LOGIN_URL` não estava configurado (bug pré-existente, não introduzido nesta sessão) — `@login_required` mandava usuário anônimo pra `/accounts/login/` (404) em vez de `/contas/login/`; corrigido
- Commit único enviado para `next` (origin) e mergeado/enviado para `main` em `origin` e `production`

### Pendências e próximos passos

- Obter credenciais reais do Google OAuth (`GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`) — bloqueado no usuário, documentado em `docs/runbook.md`
- Popular `PalavraProibida` de verdade via Admin (a lista nasce vazia de propósito — curadoria é decisão da equipe FNP, não do código)
- Comentários "pendente" que já existiam antes da moderação automática continuam precisando de revisão manual (ação em massa no Admin) — o auto-approve só vale pra envios novos
- Considerar mecanismo de denúncia de comentário pelos próprios usuários como complemento à lista de palavras proibidas (nenhuma lista pega sarcasmo/assédio sem palavrão) — não implementado, não foi pedido ainda
- Rodar `sync_legado_firestore`/`sync_camara` contra o banco de produção (só rodado localmente até agora)
- Migrar produção de SQLite para PostgreSQL
- Integração com o Senado (hoje só Câmara via `sync_camara`)
- Redesign visual vem sendo feito incrementalmente a partir de referências de outra plataforma FNP que o usuário está enviando aos poucos (sidebar/topbar do site público e do Admin já alinhados; mais capturas de tela podem vir e pedir mais ajuste)

---

## Documentação Técnica

| Arquivo | Conteúdo |
|---|---|
| `README.md` | Visão geral do projeto e fluxo de repositórios |
| `docs/runbook.md` | Operação e procedimentos de execução |
| `docs/adr/0001-initial-architecture.md` | Arquitetura inicial do projeto |
| `CONTRIBUTING.md` | Padrões de contribuição |

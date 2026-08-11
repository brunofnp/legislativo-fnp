# CLAUDE.md — Contexto do Projeto Legislativo FNP

> Arquivo de contexto para sessões com Claude Code. Atualizado automaticamente a cada 3h enquanto há sessão ativa (mantém este arquivo fiel ao código para evitar redescoberta/gasto de tokens em sessões futuras).
> Última atualização: 2026-08-11 — **Auditoria de segurança completa (pentest de 48 itens) rodada a pedido do usuário**, 1 achado crítico e 8 riscos corrigidos, 73 testes limpos. **Mesmo dia**: senha do `doadmin` rotacionada e validada (pendência fechada, produção usa a role `legislativo`, não afetada); **promoção completa `next` → `main` → produção autorizada explicitamente pelo usuário** (CI verde, deploy confirmado via SSH, migration `comentarios.0007_comentariolike` aplicada); checklist de segurança pós-deploy rodado (SSH/fail2ban e firewall sem achado; acesso cross-sistema no Postgres confirmado como arquitetura intencional, não vulnerabilidade; atualizações de SO/Docker pendentes, precisam de janela de manutenção); `doadmin` rotacionado uma 2ª vez (exposto em texto puro no chat) e Client Secret do Google OAuth também rotacionado de fato — login Google testado e confirmado funcionando em produção. Ajuste de UX nos botões de ação rápida do Admin (lado a lado em vez de empilhados) promovido junto. Detalhes nas seções datadas 2026-08-11 do Estado Atual: "Auditoria de segurança (pentest de 48 itens)" e "Rotação do `doadmin`, promoção `next` → `main` → produção e início da verificação de infra por SSH".

---

## Visão Geral

**Legislativo FNP** é uma plataforma Django para acompanhamento legislativo voltada ao monitoramento de proposições em tramitação no Congresso Nacional e ao impacto para municípios. A proposta é reunir um painel institucional, visual profissional e fluxo de participação colaborativa para a Frente Nacional de Prefeitas e Prefeitos.

URL de produção: `legislativo.fnp.org.br` (droplet `fnp-web` na DigitalOcean, via branch `main` do remoto `production`) — **no ar desde 2026-08-05**, HTTPS via Let's Encrypt/certbot, confirmado com `curl` retornando 200 e HTML real da home
Branch de desenvolvimento ativo: `next`

---

## Stack Tecnológica

| Camada | Tecnologia |
|---|---|
| Backend | Django 5.2 LTS (suporte até abril/2028) · Python 3.12 local (via `.venv/`) / 3.11 no CI |
| Auth | django-allauth 65.x (login por e-mail + Google OAuth, cadastro manual ou Google) |
| Banco (dev) | SQLite |
| Banco (prod) | PostgreSQL 18 (DigitalOcean Managed Database, `fnp-database`), via `DATABASE_URL` |
| Templates | Django Templates + CSS/JS vanilla |
| Estáticos | WhiteNoise |
| Dados | Modelos Django + management commands (`ingest_legislativo`, `sync_legado_firestore`, `sync_camara --watch`) |
| Mídia | Pillow (`ImageField` de `Perfil.foto`), `MEDIA_URL`/`MEDIA_ROOT` (`media/`, gitignored; servido via `runserver` em DEBUG) |
| UI | HTML semântico, CSS customizado (dark mode via `[data-theme]`), JavaScript vanilla |
| Testes | Django TestCase (via `RequestFactory`, não `self.client` — ver Observações) + pytest |

**Observação sobre Python 3.14:** documentado quando o projeto ainda estava no Django 4.2 — havia um bug real do próprio Django (`copy.copy()` sobre `RequestContext`, `django/template/context.py`) que quebrava `self.client.get(...)` nos testes E as telas de listagem/adicionar do Admin em runtime normal no 3.14. Com o upgrade pra Django 5.2 (2026-08-06), esse bug pode já ter sido corrigido nas versões mais novas — **não testado/reverificado ainda** (o `.venv/` local continua em Python 3.12 por segurança). Os testes continuam usando `RequestFactory` + `SessionMiddleware` manual (funciona em qualquer versão, mantido por robustez), independente disso.

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
  comentarios/                # Comentario, Participacao, Notificacao, PalavraProibida, DenunciaComentario
    models.py                  # Comentario.DENUNCIAS_PARA_OCULTAR = 3
    admin.py                 # ações em massa de moderação de comentário; PalavraProibida e DenunciaComentario registradas aqui
    moderacao.py              # classificar_comentario() — aprova/rejeita automaticamente por palavra proibida
  legislativo/                # camada de views/urls/forms que orquestra os 3 apps acima
    admin.py                  # vazio (registros vivem nos apps de domínio)
    admin_site.py              # FNPAdminSite/FNPAdminConfig — AdminSite customizado (dashboard, index_template)
    models.py                 # vazio (models vivem nos apps de domínio)
    views.py                 # get_home_sections() pagina "Todas as proposições" (24/página); denunciar_comentario()
    urls.py
    forms.py                # CustomSignupForm (município/UF/setor/cargo/telefone), PerfilForm, PerfilDadosForm, ComentarioForm, ParticipacaoForm
    context_processors.py   # notificacoes + usuario_display_name + usuario_avatar_url
    data_utils.py            # split_temas() — separa temas compostos "A, B/C"
    throttling.py             # rate_limited() — throttle simples via cache (sessão+IP), sem dependência externa
    templatetags/
      admin_icons.py           # ícones SVG por app/model do Django Admin (barra lateral)
    tests.py                  # 29 testes — RequestFactory/middleware direto, não self.client (ver Observação Python 3.14)
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
  settings.py                 # LOGIN_URL, MEDIA_URL/ROOT, SOCIALACCOUNT_ADAPTER, cabeçalhos de segurança (if not DEBUG)
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
- Cadastro e login (e-mail/senha próprio ou Google OAuth via django-allauth); credenciais reais do Google já criadas (2026-08-04) e preenchidas no `.env` local — tela de consentimento OAuth ainda em modo "teste" (só e-mails listados como usuário de teste no Google Cloud Console conseguem logar), ver pendências
- Cadastro coleta município/UF (vira `Municipio` via `get_or_create`, `Perfil.municipio` é `ForeignKey` — vários usuários podem apontar pro mesmo município), setor responsável, cargo e telefone; mesmos campos editáveis depois em `/perfil/`
- **Aprovação de cadastro:** todo cadastro novo nasce `Perfil.status_aprovacao='pendente'` (staff nasce `'aprovado'`); `CadastroPendenteMiddleware` redireciona usuário pendente para `cadastro_pendente.html` até um Root/Administrador FNP aprovar ou rejeitar (ações em massa simétricas `aprovar_cadastros`/`rejeitar_cadastros` no `UsuarioAdmin`) — tela de aviso já distingue mensagem para pendente vs. rejeitado
- **Fotos de perfil:** upload manual (`Perfil.foto`) ou importação automática da foto do Google no login social (`GoogleAccountAdapter.save_user` + signal `pre_social_login` para manter atualizada); exibida no topbar e nos comentários do fórum, com fallback pra inicial do nome
- **LGPD:** página de Política de Privacidade e solicitação de exclusão de conta (`solicitar_exclusao` — só marca `Perfil.exclusao_solicitada_em`, exclusão real é manual pelo Root via Admin, sem autoexclusão instantânea). `UsuarioAdmin` tem ações simétricas `aprovar_exclusoes` (reaproveita a tela de confirmação nativa do `delete_selected` — exclui de fato) e `rejeitar_exclusoes` (limpa `exclusao_solicitada_em`, mantém a conta), no mesmo padrão de `aprovar_cadastros`/`rejeitar_cadastros`. Exportação de dados **não é mais self-service** (removido em 2026-08-07, a pedido do usuário) — só o Root exporta, via `/admin/exportar-dados/` (ver "Exportar dados de engajamento" no Estado Atual); pedido de portabilidade de dados de um usuário específico é atendido por lá, selecionando a pessoa.
- Página de perfil (`PerfilView`) com edição de nome/foto/telefone/cargo/município/UF/setor responsável, link para trocar senha (allauth) e para as ações de LGPD
- Fórum de comentários por proposição com notificação aos demais participantes da discussão (só dispara se o comentário for aprovado)
- **Moderação automática de comentários** (`apps/comentarios/moderacao.py`): comentário nasce aprovado por padrão (sem fila manual); é reprovado automaticamente só se contiver alguma `PalavraProibida` ativa (lista editável via Admin, nunca hardcoded). Checagem por fronteira de palavra (`\b`), sem acento/caixa — evita falso positivo tipo "droga" bloquear "drogaria" (Scunthorpe problem). Autor vê mensagem explicando a reprovação. Comentários "pendente" anteriores a essa mudança continuam precisando de revisão manual (ação em massa no Admin) — o auto-approve só vale pra novos envios.
- **Denúncia de comentário** (`DenunciaComentario`, botão "Denunciar" no fórum, `denunciar_comentario` em views.py): complemento à lista de palavras proibidas para pegar assédio/sarcasmo sem palavrão. Usuário logado denuncia (não pode denunciar 2x o mesmo comentário — `UniqueConstraint`); ao atingir `Comentario.DENUNCIAS_PARA_OCULTAR` (3) denúncias distintas, o comentário volta sozinho para `'pendente'` até revisão manual. Visível no Admin (`total_denuncias` na listagem de Comentario).
- **Rate limiting** nos formulários públicos (`apps/legislativo/throttling.py`): máx. 5 comentários/5min e 3 participações/10min por sessão+IP, via cache padrão do Django (sem dependência nova — trocar para Redis se o app crescer para múltiplos workers).
- **Paginação** na home: "Todas as proposições" pagina de 24 em 24 (`PROPOSICOES_POR_PAGINA` em views.py) via `Paginator`; "Urgentes"/"Em alta" continuam como destaques fixos (6/4 itens), não paginam.
- **Cabeçalhos de segurança de produção**: `SECURE_SSL_REDIRECT`, HSTS, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` — só ativam com `DEBUG=False`, assumindo que o Nginx do droplet repassa `X-Forwarded-Proto` (confirmar antes de habilitar em produção pela primeira vez, ver comentário em `settings.py`).
- Endpoint SSE/polling para atualização de dados em tempo real; cards de Urgentes/Em alta/Todas se atualizam sozinhos (sem F5) via `api_proposicoes_cards`, que renderiza o HTML pronto (mesmos templates) em vez de duplicar lógica em JS
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

### Participacao / Comentario / Notificacao / PalavraProibida / DenunciaComentario

- `Participacao` permite registrar contribuições, sugestões, dúvidas ou indicações — campos `municipio`, `uf`, `setor_responsavel`, `cargo`, `email`, `telefone`, `mensagem` (mesmo vocabulário do cadastro de usuário; `setor_responsavel`/`telefone` foram renomeados de `responsavel`/`whatsapp`)
- `Comentario` é a base do fórum por proposição; `status_moderacao` é calculado automaticamente no envio via `apps.comentarios.moderacao.classificar_comentario()` — não fica mais pendente por padrão. `DENUNCIAS_PARA_OCULTAR = 3` (classe constante)
- `PalavraProibida` (`palavra`, `ativa`) é a lista, editável só via Admin, que aciona a reprovação automática
- `DenunciaComentario` (`comentario` FK, `denunciante` FK, `UniqueConstraint` por par) registra denúncias de usuários; ao atingir o limite, oculta o comentário automaticamente (`denunciar_comentario` em views.py)
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

**Moderação de comentários:** publicação é automática por padrão (não pré-moderação total) — só é bloqueada por lista de palavras proibidas gerenciada via Admin (`PalavraProibida`), nunca hardcoded no código. Checagem por fronteira de palavra, sem acento/caixa. Ver `apps/comentarios/moderacao.py`. Complementado por denúncia de usuários (`DenunciaComentario` — 3 denúncias distintas ocultam o comentário sozinho). Não introduzir fila de aprovação manual por padrão de novo sem decisão revista — o ponto desta mudança foi justamente tirar a equipe pequena desse gargalo.

**Rate limiting/segurança:** throttle de formulário público via cache do Django (`apps/legislativo/throttling.py`), não via pacote externo — trocar por Redis só se o app crescer para múltiplos workers/servidores (não fazer isso preventivamente). Cabeçalhos de segurança de produção (HSTS/SSL redirect/cookies seguros) só ativam com `DEBUG=False` — nunca testar/depurar com eles ligados em ambiente local sem TLS.

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
- Navegabilidade: topbar ganhou "← Voltar" estilo breadcrumb (oculto na própria home) e, na própria home, um link "Início" (ícone de casa) que só aparece quando há paginação/filtro ativo (`?page=`/`?q=`/`?tema=`) na URL — home "limpa" (`/`) não mostra nenhum dos dois; rodapé só aparece na home
- Busca da home com sugestões ao digitar: debounce de 250ms, mínimo de 2 caracteres, fragmento HTML renderizado no servidor (`api_busca_sugestoes` + `_busca_sugestoes.html`), guarda contra race condition comparando o termo buscado com o valor atual do campo antes de exibir
- Índice do Admin sem duplicidade de menu: `fnp_index.html` não chama mais `{{ block.super }}` (que herdava o `admin/app_list.html` padrão, duplicando a navegação da sidebar); no lugar, dois painéis novos — "Top proposições por engajamento" (mesma fórmula de relevância da home: visualizações + comentários×5) e "Usuários e comentários" (cadastros/aprovações/comentários aprovados-rejeitados-denunciados) — mais uma fileira de atalhos rápidos (pills) pros changelists mais usados; dados computados em `FNPAdminSite.index()`
- Ambiente local migrado para Python 3.12 (`.venv/`) — Python 3.14 tem um bug real do Django 4.2 (`copy.copy()` em `RequestContext`) que quebra todas as telas de listagem/adicionar do Admin em runtime normal, não só em teste; ver `docs/runbook.md`

### Itens validados (nesta última rodada)

- `python manage.py check` → sem issues
- `python manage.py test` → 29/29 OK (era 10/10; 19 testes novos nesta sessão), inclusive recriando o banco de testes do zero (pegou o bug de dependência de migration entre apps)
- Testado via `Client` (não só `RequestFactory`): signup com novos campos, dois usuários no mesmo município, upload de foto, exportação de dados, solicitação de exclusão, moderação automática (aprovado/rejeitado/falso-positivo de substring), dashboard do Admin refletindo pendências
- `LOGIN_URL` não estava configurado (bug pré-existente, não introduzido nesta sessão) — `@login_required` mandava usuário anônimo pra `/accounts/login/` (404) em vez de `/contas/login/`; corrigido
- Commit único enviado para `next` (origin) e mergeado/enviado para `main` em `origin` e `production`

### Auditoria de duplicidade/código morto (2026-07-31)

Rodada de limpeza a pedido do usuário — `ruff --select F401,F811,F841` no repo
inteiro voltou limpo depois de: `.site-header` e `.auth-card h1` que estavam
definidos duas vezes em `style.css` (a segunda versão sempre vencia, a
primeira era código morto) mescladas numa só regra; `console.log` de debug
removido de `main.js`; imports não usados (`pathlib.Path`) removidos de
`ingest_legislativo.py` e `setup/asgi.py`. Templates, JS e migrations
conferidos sem órfãos.

### Melhorias de produto/segurança (2026-07-31, mesma sessão)

A pedido do usuário, implementadas todas as sugestões que couberam sem
depender de acesso externo (Google Cloud Console) ou decisão de infra maior
(migração pra Postgres): paginação da home (24/página), rate limiting nos
formulários públicos, denúncia de comentário, cabeçalhos de segurança de
produção, e 19 testes novos (de 10 para 29) cobrindo moderação automática,
aprovação de cadastro (middleware testado diretamente), LGPD, avatar/Google e
os itens novos desta rodada. `ruff`, `check --deploy` (com `DEBUG=False`
simulado) e `makemigrations --check` todos limpos.

### Navegação, busca e Admin (2026-07-31, mesma sessão)

A pedido do usuário, a partir de duas capturas de tela (índice do Admin com
menu duplicado abaixo do dashboard; página "Painel Geral" de outra plataforma
FNP usada só como referência de estilo/fonte, não de conteúdo): link
"Início" na topbar da home paginada/filtrada, sugestões de busca ao digitar
na home, e reconstrução do conteúdo do índice do Admin (painéis de
engajamento/usuários + atalhos, sem repetir a sidebar). `check`, `test`
(29/29) e `collectstatic` limpos; renderização do índice do Admin verificada
via `Client` autenticado como superusuário (sem tabela de app_list duplicada,
sem links "+ Adicionar" soltos, painéis novos presentes no HTML).

### Deploy — containerização Docker (2026-08-03)

A pedido do usuário, a partir de um guia de deploy (Docker + Nginx no droplet
`fnp-web`, banco `fnp-database` gerenciado na DigitalOcean, ambos já
provisionados e confirmados no dashboard real): criados `Dockerfile`,
`docker-compose.yml`, `entrypoint.sh`, `.dockerignore` e `.gitattributes`
(força LF em `*.sh`, evita o container quebrar se o arquivo for editado no
Windows). Nenhuma mudança de código Django foi necessária — `DATABASE_URL`
(`dj-database-url`), `psycopg2-binary`, `gunicorn` e `whitenoise` já
existiam em `requirements.txt`/`settings.py` desde antes. Passos detalhados
(reconhecimento via SSH, Trusted Sources, role/database dedicados, deploy
key, validação por túnel SSH antes do Nginx, bloco Nginx isolado, TLS) estão
em `docs/runbook.md` — tudo isso depende de acesso SSH ao droplet, que o
Claude Code não tem; só o código/arquivos de containerização foram
preparados aqui. `manage.py check` limpo; build Docker local não pôde ser
testado (Docker Desktop não estava com o daemon rodando nesta máquina).

### Deploy real e correções pós-deploy (2026-08-05)

Deploy efetivamente rodando no droplet `fnp-web` pela primeira vez nesta
sessão (via SSH conduzido pelo usuário, comandos passados pelo Claude Code —
sem acesso direto). Site caiu em produção logo depois de subir, com vários
problemas em cadeia, todos corrigidos:

- **CSS/JS voltando 404** — `docker-compose.yml` não montava `staticfiles/`
  como volume; o `collectstatic` do `entrypoint.sh` gravava só dentro do
  container, e o Nginx (`deploy/nginx-legislativo.conf`) serve `/static/`
  direto de um caminho no host. Fix: `./staticfiles:/app/staticfiles`
  adicionado ao `docker-compose.yml`.
- **Container em restart loop (502 Bad Gateway)** — depois do fix acima, o
  volume novo foi criado pelo Docker como `root:root` (rodado via `sudo`),
  mas o processo do container roda como `appuser` (UID 1000, `Dockerfile`
  não usa root) — sem permissão de escrita. Fix: `chown -R 1000:1000` no
  host. **Atenção:** o volume de `media/` tem o mesmo risco em tese (nunca
  testado upload de foto em produção) — vale conferir/chown antes que
  alguém tente subir uma foto de perfil e caia no mesmo loop.
- **Certificado SSL perdido** — copiar `deploy/nginx-legislativo.conf` por
  cima de `/etc/nginx/sites-enabled/legislativo.conf` (pra sincronizar um
  ajuste de comentário sobre DNS) apagou os blocos que o certbot tinha
  adicionado (`listen 443 ssl`, `ssl_certificate`, redirect 80→443). Fix:
  `sudo certbot --nginx -d legislativo.fnp.org.br` de novo, opção "1:
  Attempt to reinstall". **Lembrete permanente:** todo `cp` desse arquivo
  pro `/etc/nginx/sites-enabled/` precisa ser seguido de certbot de novo,
  senão o Nginx volta a servir o certificado de outro sistema do droplet.
- **Banco de produção com dado errado** — o serviço `sync-camara`
  (`docker-compose.yml`, busca contínua por palavra-chave na API da
  Câmara) subiu sozinho antes de qualquer importação do legado e populou
  71 proposições **sem nenhuma curadoria da FNP** (`interlocutores` vazio
  em todas). Comparação por título mostrou só 3 em comum com as 104 reais
  do Firestore legado. Fix: zerado (`Proposicao.objects.all().delete()`,
  confirmado sem comentários/participações reais antes) e reimportado via
  `sync_legado_firestore` → 104/104 batendo. **Risco que continua**: o
  `sync-camara --watch 1800` roda a cada 30min com as mesmas keywords
  (`municípios,municipal,prefeituras,FPM`) e pode voltar a criar
  proposições não-curadas com o tempo — decisão de produto ainda em
  aberto (ver Pendências).
- **Import do legado quebrando no meio** — `Noticia.url` é `URLField`
  padrão (200 chars), mas links de notícia do Google News no Firestore
  legado chegam a 714 chars (783 dos registros afetados) — um
  `StringDataRightTruncation` no Postgres derrubava o comando inteiro sem
  isolar por registro. Fix: migration `0003_alter_noticia_url`
  (`max_length=1000`).
- **Root preso na própria tela de aprovação de cadastro** — banco de
  produção novo, ninguém ainda com `is_staff=True`; `CadastroPendenteMiddleware`
  bloqueia todo mundo que não seja staff, inclusive quem seria o Root. Fix:
  `python manage.py setup_roles` (promove `bruno.marra@fnp.org.br`,
  idempotente) — **necessário rodar manualmente em todo banco de produção
  novo do zero**, não acontece sozinho.

### Auditoria de segurança e upgrade Django/allauth (2026-08-06)

A pedido do usuário, levantamento de segurança do sistema (plataforma é fórum
de discussão política, alvo plausível de ataque) — achados verificados no
código, não lista genérica. Dois itens **Crítico** corrigidos nesta sessão:

- **Django 4.2 sem patch de segurança desde 2026-04-07** (confirmado na
  fonte oficial, `djangoproject.com/download`) — upgrade feito em 3 etapas
  (5.0→5.1→5.2 LTS, suporte até abril/2028), cada uma com `check` + 29
  testes limpos e o changelog oficial cruzado contra o código real (nada
  do 5.0/5.1/5.2 afetava o projeto, fora `USE_L10N` removida). Pré-requisito
  descoberto no caminho: o `django-allauth` instalado (0.60.1) só suportava
  até Django 4.2 — upgrade pra 65.19 exigiu trocar
  `ACCOUNT_EMAIL_REQUIRED`/`ACCOUNT_USERNAME_REQUIRED`/
  `ACCOUNT_AUTHENTICATION_METHOD` por `ACCOUNT_LOGIN_METHODS`/
  `ACCOUNT_SIGNUP_FIELDS` (renomeados) e adicionar o extra `[socialaccount]`
  ao pacote (senão o login Google quebra). Verificado end-to-end com
  `Client` contra banco descartável: cadastro, login por e-mail, logout
  (inclusive via GET, que o Django 5.0 removeu do `LogoutView` nativo mas
  não do allauth) e índice do Admin — tudo funcionando. **Login Google real
  via OAuth não dá pra automatizar, precisa de teste manual.**
- **`DEBUG`/`SECRET_KEY` com fallback inseguro** — `DEBUG` tinha default
  `'True'` (deveria falhar fechado); `SECRET_KEY` caía pra
  `'django-insecure-change-me'`, string conhecida de todo tutorial Django,
  se a env var sumisse. Agora `DEBUG` default é `False`, e produção sem
  `SECRET_KEY` derruba o boot (`ImproperlyConfigured`) em vez de rodar
  insegura; dev local sem a env var gera uma chave efêmera.

Também integrado: monitoramento de erro (Sentry, `SENTRY_DSN` opcional via
env, desligado por padrão) — hoje uma queda só é percebida se alguém tentar
acessar e avisar manualmente, como aconteceu várias vezes antes desta
sessão. Backup do `fnp-database` confirmado ativo (7 dias de retenção,
point-in-time recovery, painel DO → Actions → Restore from backup).

**Itens Alto/Médio, todos fechados na sequência (mesma sessão):**

- Rate limit de login por IP explícito (`ACCOUNT_RATE_LIMITS`) — o allauth
  65.x já vem com isso por padrão, só documentado.
- **2FA obrigatório pra staff** (`allauth.mfa`, TOTP + códigos de
  recuperação) via `MFAObrigatorioStaffMiddleware` novo — **todo staff
  existente sem 2FA fica bloqueado no primeiro acesso depois do deploy**,
  avisar a equipe antes. **Desativado a pedido do usuário em 2026-08-06**
  (linha comentada em `MIDDLEWARE`, ver `setup/settings.py`) — 2FA deixou de
  ser obrigatório pra staff; a funcionalidade continua disponível e
  opcional em `/contas/2fa/` pra quem quiser ativar por conta própria, e a
  classe do middleware segue em `apps/usuarios/middleware.py`, é só
  reativar a linha se a decisão for revista.
- `SECURE_REFERRER_POLICY`, `CSRF_TRUSTED_ORIGINS` (derivado do
  `ALLOWED_HOSTS`) explícitos.
- Limite de upload de foto de perfil (5MB): validador em `Perfil.foto` +
  `client_max_body_size 6M` no `deploy/nginx-legislativo.conf` (precisa de
  `cp` manual + reload no droplet pra valer, como todo ajuste desse
  arquivo).
- `ACCOUNT_EMAIL_VERIFICATION` `'none'` → `'optional'`.
- **Content-Security-Policy** (`django-csp`) — `script-src` estrito (nonce
  automático), `style-src` com `'unsafe-inline'` (vários templates ainda
  usam `style="..."` inline, cleanup maior não feito agora).
- **Lockfile com hash** (`requirements.lock`, pip-tools) — Dockerfile
  instala dele agora, com verificação de hash. `pip-audit` rodando no CI a
  cada push/PR.
- **CAPTCHA no cadastro** (`django-recaptcha`) — só ativa com
  `RECAPTCHA_PUBLIC_KEY`/`RECAPTCHA_PRIVATE_KEY` preenchidas.
- **Achado extra do `pip-audit`** (não estava na lista original): Pillow
  10.4.0 tinha 24 vulnerabilidades conhecidas, corrigidas só na série
  12.x — atualizado (`>=10.0,<11.0` → `>=12.0,<13.0`).

### Rodada de UX/UI + restrição de cadastro Google + exportação de engajamento (2026-08-07)

A pedido do usuário, a partir de capturas de tela anotadas (home, card de
proposição, fórum, tela de confirmação de login Google): (1) filtro da
home ao rolar a página — passou por 3 iterações no mesmo dia (painel
inteiro sticky → encolhia ao ficar "grudado" → **estado final**: só o
filtro de Tema fica sticky, como uma pill alinhada à direita
(`.tema-filter-floating`, `top: var(--header-height)`, offset medido em
JS via `initStickyHeaderOffset` em `main.js` porque a altura do
cabeçalho varia por breakpoint/tamanho de fonte); a barra de busca
grande voltou a ser 100% estática, no lugar original — o painel sticky
cheio tampava boa parte da primeira fileira de cards ao rolar listas
longas (Urgentes/Em alta/Todas), e mesmo a versão "encolhida" ainda
incomodava; (2) badge
"SEM PAUTA" tinha a mesma cor de alerta (vermelho) de "PAUTA", como se
qualquer proposição sem pauta fosse urgente — `badge-pauta-on`/
`badge-pauta-off` agora diferenciam; meta-itens do card ganharam `title`
explicando que "status" é o nome oficial da fase de tramitação (evita
confusão com a função "Notificações" do próprio site — o texto que
aparecia ali, ex. "Notificações", é dado real vindo da fonte oficial, não
bug); (3) fonte dos rótulos dos cards de estatística da home aumentada
(0.75rem → 0.85rem); (4) comentários do fórum: só os 5 primeiros
aparecem, resto fica atrás de um botão "Ver mais comentários (N)"
(`comment-extra`/`.hidden`, expandido via JS sem reload); (5) rodapé
subindo pro meio da página em telas allauth com pouco conteúdo (ex. tela
de confirmação "Entrar com Google") — `body` global virou flex column
(fix de padrão "rodapé no fim", `templates/allauth/layouts/base.html` não
tinha o wrapper `.app-main`/`.app-shell` que o `base.html` normal tem);
(6) título da proposição na página de detalhe agora é hyperlink pra fonte
oficial (`Proposicao.link`, populado em 102/104 registros) quando
existir; (7) **cadastro novo via Google restrito a e-mail institucional
@fnp.org.br** — `GoogleAccountAdapter.is_open_for_signup()` em
`apps/usuarios/adapters.py` bloqueia cadastro (não login — quem já tem
conta continua entrando normal, independente do domínio) se o e-mail do
Google não terminar em `@fnp.org.br`; aviso formal nas telas de
login/cadastro (`.google-hint`) explicando que prefeitura/entidade
pública deve usar o botão "Cadastre-se", e `account/signup_closed.html`
sobrescrito com mensagem específica em vez do texto genérico em inglês do
allauth; (8) **exportação de dados de engajamento pro Root**, telas
novas — só visível/acessível a `is_superuser` (`/admin/exportar-dados/`,
registrado via `FNPAdminSite.get_urls()`), exporta cadastro (Usuario +
Perfil) e interação (comentários, participações — casadas por e-mail, já
que `Participacao` não tem FK pra Usuario —, denúncias feitas,
notificações) de um usuário específico ou em massa, em JSON pra alimentar
um banco externo de pontuação de engajamento; nesta primeira versão,
implementada como uma tela **separada** da exportação de LGPD que já
existia (`exportar_meus_dados`, self-service) — **corrigido depois no
mesmo dia**, ver "Exportar dados de engajamento — correção" abaixo.
`check`, `makemigrations --check` e 41 testes (era 38) limpos; páginas
renderizadas via `Client` pra conferir ausência de erro de template (não
visualmente — sem acesso a navegador neste ambiente).

### Exportar dados de engajamento — correção (2026-08-07, mesmo dia)

Usuário apontou que a implementação original não seguiu o pedido original
à risca: "somente na área do root devemos ter o botão de exportar
informações" foi lido por mim, na hora, como "criar uma área nova pro
Root" — mas deixei a exportação de LGPD antiga (`exportar_meus_dados`,
self-service, qualquer usuário logado) **intacta e visível pra todo
mundo**, e a nova exportação só apareceu como um botão solto no
dashboard do Admin, não um item de menu de verdade como os outros do
Root. Correção, consolidando num único ponto de exportação:

- **Removida por completo** a exportação de LGPD self-service
  (`exportar_meus_dados`): view, URL (`/conta/exportar-meus-dados/`),
  teste e os 2 links que existiam (`_sidebar.html` na seção
  "Privacidade" — visível pra qualquer usuário — e `_footer.html`). Root
  agora cobre pedido de portabilidade de dados exportando a pessoa
  específica na tela nova.
- **Renomeado** de "Exportar dados de engajamento" pra só **"Exportar
  dados"** (título da página, breadcrumb, pill do dashboard) — nome mais
  curto, como pedido.
- **Item de menu de verdade** adicionado em `templates/admin/
  nav_sidebar.html` (não só a pill do dashboard) — link direto "Exportar
  dados" com ícone próprio (`download`, novo em `admin_icons.py`),
  visível só pra `request.user.is_superuser`, no mesmo padrão visual dos
  outros itens da barra lateral do Admin.
- 44 testes (era 45, -1 pelo teste do `exportar_meus_dados` removido);
  smoke test via `Client` confirmando: usuário comum não vê mais o link
  em lugar nenhum, staff sem `is_superuser` não vê o item novo no Admin,
  só Root vê.

**Bug real encontrado e corrigido: login Google local não funcionava**
(usuário reportou: clica em "Continuar" na tela de confirmação e nada
acontece, sem navegar). A URL de OAuth construída pelo Django estava
correta (`client_id` real, `redirect_uri` batendo com o cadastrado no
Google Cloud Console) e o servidor respondia `302 Found` certinho — o
Console do navegador (checado pelo usuário a pedido) mostrou a causa
real: `Sending form data to '<URL>' violates ... "form-action 'self'".
The request has been blocked.` A CSP adicionada na auditoria de
segurança (`CONTENT_SECURITY_POLICY`, 2026-08-06) tinha `form-action:
[SELF]` — o Chrome valida `form-action` não só contra o destino imediato
do POST (que é same-origin, `/contas/google/login/`), mas também contra
o destino final de um eventual redirect 302 dessa resposta; como o
destino final é `accounts.google.com` (origem diferente), o navegador
bloqueava a navegação silenciosamente (sem erro visível fora do
Console). Fix em `setup/settings.py`: `form-action` passou a incluir
`https://accounts.google.com` explicitamente. `check` e 41 testes
continuam limpos; confirmado via `Client` que o header
`Content-Security-Policy` da resposta agora inclui o domínio do Google
em `form-action` — **confirmado pelo usuário no Microsoft Edge: login
completo até o fim, inclusive a verificação de 2FA do Root** (a conta já
tinha TOTP configurado de antes; o allauth pede o código no login
independente do `MFAObrigatorioStaffMiddleware` desativado, que só força
configuração de quem ainda não tem 2FA — comportamento esperado, não
bug). No Chrome (perfil "Trabalho") o mesmo teste não foi refeito depois
do fix — se persistir bloqueado lá, é outra causa (extensão/política do
perfil), não mais a CSP.

**Username padrão de cadastro novo virou "nome.sobrenome"** (ex.: Bruno
Marra → `bruno.marra`), a pedido do usuário, pra bater com o padrão já
usado nas contas cadastradas manualmente (visível na listagem do Admin).
O allauth por padrão usaria só o primeiro nome (`populate_username`
pega o primeiro campo não-vazio de uma lista, não combina nome+sobrenome)
— `CustomAccountAdapter.populate_username` em `apps/usuarios/adapters.py`
(novo `ACCOUNT_ADAPTER`) prioriza `"{nome}.{sobrenome}"` reaproveitando a
sanitização/checagem de unicidade nativa do allauth (acento é removido,
duplicata ganha sufixo). Vale tanto pro cadastro por e-mail/senha quanto
pelo Google (`DefaultSocialAccountAdapter` delega pro `ACCOUNT_ADAPTER`).
4 testes novos (nome+sobrenome, acento, duplicata, só primeiro nome sem
sobrenome). No caminho, achado um bug real de configuração: sem
`EMAIL_BACKEND`, o default do próprio Django é SMTP (não console, como
um comentário antigo aqui dizia) — cadastro local derrubava com
`ConnectionRefusedError` ao mandar o e-mail de confirmação, sem SMTP
local rodando. Corrigido: `DEBUG=True` sem `EMAIL_BACKEND` no ambiente
agora usa `console.EmailBackend` automaticamente. `check` e 45 testes
(era 41) limpos; cadastro completo testado via `Client` HTTP real
(não só a função do adapter isolada) confirmando o username gerado.

### Promoção completa `next` → `main` → produção (2026-08-07)

A pedido explícito do usuário ("subir tudo pra next e produção"), depois
de validar `check` + 45 testes + `makemigrations --check` limpos: `main`
local recebeu um `git merge --ff-only origin/next` (sem divergência, fast-
forward direto) e foi enviado tanto pro `origin` quanto pro `production`
(GitHub `dadosfnp/legislativo-fnp`), levando **tudo** que estava represado
desde a última sincronização de produção (bem antes desta sessão) —
upgrade Django 4.2→5.2 LTS, django-allauth 0.60→65.19, toda a auditoria de
segurança (MFA depois desativado, CSP com o fix de `form-action`, rate
limit, CAPTCHA, lockfile+pip-audit), mais tudo desta sessão (restrição de
cadastro Google, exportação de engajamento, username `nome.sobrenome`,
fix do `EMAIL_BACKEND` em dev, ajustes de UI, redução de `--paginas` do
`sync-camara`). **O push no git não reinicia os containers sozinho** — o
deploy de fato (rebuild + restart) é feito pelo usuário via SSH
(`docker compose build && docker compose up -d` em `/opt/legislativo-fnp`,
o `entrypoint.sh` já roda `migrate`/`collectstatic` automaticamente,
inclusive a migration nova `0005_alter_perfil_foto`). Ver item no topo das
pendências pra confirmar que subiu sem erro.

**CI quebrou logo depois do push pra `main`** (usuário recebeu e-mail do
GitHub Actions) — causa: o job de CI não define `DEBUG`/`SECRET_KEY`, e
a correção de segurança de 2026-08-06 fez `DEBUG` virar `False` por
padrão (fail-closed), então o `settings.py` passou a exigir
`SECRET_KEY` e derrubar o boot antes de qualquer teste rodar. Isso
estava quebrado desde aquela correção, mas só apareceu agora porque o
CI só roda em push pra `main` (`.github/workflows/ci.yml`,
`on: push: branches: [main]`) — essa foi a primeira vez que `main`
recebia push desde então. Fix: `DEBUG: 'True'` no `env:` do job (CI se
comporta como dev local, chave efêmera, não como produção real).
Confirmado verde via `gh run watch` nos dois repositórios (`origin` e
`production`) depois do fix.

### Deploy de produção confirmado (2026-08-07)

Rebuild via SSH concluído com sucesso em `/opt/legislativo-fnp`, depois de
corrigir no caminho: (1) `git pull production main` falhou porque o clone
do droplet só tem o remoto `origin` (aponta direto pro
`dadosfnp/legislativo-fnp` — o nome "production" só existe na máquina
local, com dois remotos); comando certo era `git pull origin main`. (2) Na
primeira tentativa, o `docker compose build` seguiu mesmo com o `git pull`
tendo falhado, reconstruindo com código **antigo** (cache pesado,
`requirements.txt` em vez de `requirements.lock`, "No migrations to
apply") — silencioso, só percebido comparando o log linha a linha.
Depois do pull correto (`e69e5d9` → `f2ae093`), rebuild real: migrations
novas aplicadas limpo (`account.0006`-`0009`, `mfa.0001`-`0003`,
`usuarios.0005_alter_perfil_foto`), 136 estáticos coletados, Gunicorn sem
traceback. Verificado depois via SSH: `curl -sI
https://legislativo.fnp.org.br/` → `200 OK` por fora (não só dentro do
container), e `docker compose top sync-camara` confirmando o comando
rodando com `--paginas 1` de fato. **Login Google em produção ainda não
testado no navegador de verdade** (só o lado servidor foi confirmado) —
próximo passo do usuário.

### CSP `style-src` sem `'unsafe-inline'` (2026-08-07)

Item que estava nas pendências desde a auditoria de segurança de
2026-08-06, fechado ainda no mesmo dia a pedido do usuário ("das
pendências o que podemos implementar?"). Levantamento mostrou só 6
ocorrências de `style="..."` em todo o projeto, em 2 padrões: (1) 4
`style="margin: 0;"` redundantes (`.auth-card` não tem margin pra
sobrescrever — só deletados) mais 1 com largura customizada de verdade
(`politica_privacidade.html`, virou classe `.auth-card-wide`); (2) 2
chips de cor de macrotema (`style="color: X; border-color: X;"`,
`_proposicao_card.html` e `proposicao_detail.html`) — cor é cadastrada
por registro no Admin, não dá pra virar classe CSS fixa. Resolvido com
`data-cor-macrotema="{{ cor }}"` + `initMacrotemaColors()` em `main.js`
setando via `element.style.setProperty(...)` (CSP não restringe mudança
de estilo via CSSOM/JavaScript, só o atributo `style=""` em HTML) —
hookado tanto no load inicial quanto depois do live-update de cards via
SSE/polling (`applyCards()`). `UNSAFE_INLINE` removido do import e do
`style-src` em `settings.py`. **Gap residual, não corrigido**: duas
páginas nativas do allauth não sobrescritas por templates deste projeto
(`account/email_change.html`, `account/phone_change.html`) têm
`style="display: none"` próprio — mas nenhuma das duas é linkada em
lugar nenhum da UI (sem gestão de múltiplos e-mails nem 2FA por telefone
expostos), risco insignificante. `check` e 44 testes limpos; confirmado
via `Client` que o header `Content-Security-Policy` da resposta não tem
mais `'unsafe-inline'` em `style-src`, e que o chip de macrotema
renderiza `data-cor-macrotema` com o valor certo.

### `PalavraProibida` populada com lista inicial (2026-08-07)

A pedido explícito do usuário, migration de seed
(`apps/comentarios/migrations/0006_seed_palavras_proibidas.py`, `RunPython`
idempotente via `get_or_create`) populou 35 termos comuns banidos em redes
sociais — xingamentos/calão geral, calão sexual, misoginia, homofobia,
capacitismo, racismo. **Nota de arquitetura**: `moderacao.py` documenta
que a lista nunca deveria ficar hardcoded no código pra evitar "lista
desatualizada, incompleta ou embaraçosa versionada no git" — esta
migração roda só uma vez pra popular o banco; a partir daqui a lista é
100% editável via Admin (`PalavraProibida.ativa`, adicionar/remover),
igual antes. Testado: comentário legítimo segue `aprovado`, comentário
com termo da lista vira `rejeitado`, e o teste de Scunthorpe (`cultura`
não deveria bloquear por conter `cu`) continua passando. `check`, 44
testes e `makemigrations --check` limpos.

### Header com ícones sempre visíveis, "Ajuda desta página" e tour de onboarding (2026-08-07)

A pedido do usuário, a partir de capturas de tela de outro sistema da FNP
("Sistema FNP", usado só como referência visual/UX, não código):

- **Topbar do site público reformulada**: tamanho da fonte e tema
  claro/escuro saíram do menu "..." (`.topbar-more-panel`, removido por
  completo — CSS/JS mortos limpos) e viraram ícones sempre visíveis, no
  mesmo padrão da referência (busca → avatar+nome → sino → Aa → lua → "?"
  → Sair). Em mobile, `.app-topbar-actions` ganhou `flex-wrap: wrap` pra
  não transbordar horizontalmente com mais ícones na fileira — não
  visualmente testado num aparelho de verdade, vale conferir.
- **Header do Django Admin**: ganhou o ícone de "Ajuda desta página"
  também (ver abaixo). **Sem toggle de tema escuro no Admin** —
  reabriria a diretriz fechada "Admin sempre claro" (ver Diretrizes de
  Engenharia), sinalizado e propositalmente deixado de fora. Sino de
  notificações também deixado de fora do Admin por ora (exigiria portar
  todo o CSS/JS do dropdown pro admin-custom.css/admin_quick_actions.js
  — Root já vê pendências via os cards do dashboard).
- **"Ajuda desta página"** (novo): modal acionado pelo ícone "?",
  conteúdo varia por página. `apps/legislativo/ajuda_conteudo.py` tem um
  dicionário `AJUDA_PAGINAS` indexado por `url_name` (título, descrição
  e lista "como usar"), com fallback genérico; injetado globalmente via
  novo context processor `apps.legislativo.context_processors.ajuda_pagina`
  (registrado no `TEMPLATES`, por isso funciona também no Admin sem
  código extra por view). Cobre home, detalhe de proposição, perfil,
  favoritos, participações, cadastro pendente, índice do Admin e a tela
  de exportar dados. Modal (`templates/_help_modal.html`) duplicado em
  CSS entre `style.css` (site público, usa as CSS vars de tema) e
  `admin-custom.css` (Admin, sempre claro, cores fixas) — mesma
  separação que já existia entre os dois reskins.
- **Tour de onboarding** (novo, só site público — Admin não tem):
  `templates/_tour_modal.html`, 6 passos com conteúdo adaptado ao que a
  plataforma realmente tem (Painel Geral, Ctrl+K, favoritos, fórum,
  notificações, "Ajuda desta página" — não é cópia do sistema de
  referência, que tem módulos que não existem aqui). Aparece sozinho no
  Painel Geral (`window.location.pathname === '/'`) pra quem nunca viu
  ou desmarcou "Não mostrar novamente" da última vez — persistência via
  `localStorage` (`fnp-tour-visto`), mesmo padrão já usado pra
  tema/tamanho de fonte/sidebar recolhida, sem migration nem campo novo
  no `Perfil`. Pode ser revisto a qualquer momento pelo botão "Rever o
  tour" dentro do modal de Ajuda (`window.iniciarTourFNP`, exposto
  globalmente por `initTour()` em `main.js`).
- **Item dos submenus em cascata (pedido separado do usuário) foi
  propositalmente pulado** — perguntei onde faltava aplicar esse padrão
  (Admin já tem via `nav_sidebar.html`) e o usuário respondeu "deixe como
  está", então nada mudou na sidebar do site público (`_sidebar.html`
  continua uma lista plana, sem colapsar).
- `check`, 44 testes e `makemigrations --check` limpos; validado via
  `Client` que os modais renderizam com o conteúdo certo por página
  (inclusive no Admin) e que os elementos removidos (`.topbar-more-*`)
  sumiram — **não testado visualmente num navegador de verdade**, sem
  acesso a esse ambiente aqui; vale uma conferida cuidadosa antes de
  considerar pronto (é a maior mudança de UI de uma vez só nesta sessão).

### Acabamento do header/Ajuda/tour + correções pós-uso (2026-08-07, mesmo dia)

Usuário testou o que subiu na rodada anterior e voltou com 5 ajustes
finos, todos fechados e já promovidos pra produção (`main`/`production`
em `4298291`, deploy no droplet confirmado saudável, sem migration —
só CSS/JS/templates):

- **Header do Admin**: casinha ("Ver o site") saiu do canto direito e
  foi pro lado do título "Painel Root — Legislativo FNP" (`#branding`
  virou flex row, `gap: 0.75rem`); esse título encolheu pro mesmo
  tamanho de "Painel Geral" (`1.1rem`, era bem maior por padrão do
  Django). Botão de Ajuda (um `<button>`) tinha acabamento diferente dos
  ícones vizinhos (todos `<a>`) porque `.fnp-icon-btn` não resetava
  `border`/`background`/`padding` nativos do navegador — corrigido.
- **Tour mais compacto + botão de voltar ao topo**: painel do tour
  reduzido (era 480px com bastante espaço sobrando pro pouco texto),
  mais o `.back-to-top-btn` novo (canto inferior direito, aparece com
  `scrollY > 500px`, scroll suave, respeita `prefers-reduced-motion`).
- **Contorno de foco distorcia o avatar do perfil**: a regra global
  `a:focus-visible` forçava `border-radius: 2px` em qualquer elemento
  focado — inofensivo pra botão/input normal, mas `.user-menu-trigger`
  (pill de `999px`, avatar+nome no topbar) virava quase um retângulo reto
  quando focado, criando um "anel" torto em cima do avatar redondo.
  Removido o valor fixo — contorno agora acompanha o raio natural de
  cada elemento (Chrome/Firefox/Safari já fazem isso sozinhos sem
  precisar forçar).
- **Modais de Ajuda/tour "esbeltos" demais**: a compactação do item
  anterior deixou os dois estreitos demais pro texto (quebrava em 3
  linhas, silhueta de coluna alta) — usuário pediu mais horizontal.
  Ajuda voltou pra `540px` (era 480px), tour foi pra `460px` (era 380px,
  reduzido demais na rodada anterior).
- **Fonte da sidebar do site público pequena demais**: estava em
  `0.78rem` de propósito, porque "Exportar meus dados" não cabia numa
  fonte maior — esse item saiu da sidebar quando a exportação virou
  exclusiva do Root (ver "Exportar dados de engajamento — correção"
  acima), então não há mais rótulo comprido o bastante pra justificar
  fonte menor. Foi pra `0.9rem`, igual `.fnp-nav-link` do Admin; ícones
  e rótulo de seção ajustados proporcionalmente.

`check` e 44 testes limpos a cada mudança; CI verde (`gh run watch`) nos
dois repositórios antes de cada promoção pra produção. Ainda **não
confirmado visualmente num navegador** se essas 5 correções resolveram
por completo — usuário reportou os problemas a partir de captura de
tela, mas não confirmou o resultado final depois do último deploy.

**Novo hábito combinado com o usuário**: a frase "Por hoje é só" é
gatilho explícito pra atualizar este arquivo e subir pra `next` (nunca
`main`/produção junto — essa promoção continua exigindo autorização à
parte a cada vez).

### Rodada de 23 pedidos (home/filtros, fórum, navegação, conta) — 2026-08-10

A pedido do usuário ("vamos começar mais uma semana", 11 capturas de tela
anotadas, 23 itens numerados), tudo commitado só em `next` — **não
promovido pra `main`/produção** (autorização à parte, como sempre).
Trabalho organizado em bugs primeiro, depois features, per item:

- **Acesso ao Admin via grupo não funcionava (bug real)** — adicionar
  alguém ao grupo "Administrador FNP" pelo widget de grupos do
  `UsuarioAdmin` nunca setava `is_staff`, então a pessoa continuava sem
  conseguir logar em `/admin/`; e a sidebar do site só mostrava o link
  "Painel Admin" pra `is_superuser`, nunca pra staff comum. Fix:
  `sincronizar_staff_por_grupo` (novo `m2m_changed` em
  `apps/usuarios/signals.py`) seta `is_staff=True` automaticamente ao
  entrar em "Root"/"Administrador FNP"; `_sidebar.html` trocou
  `user.is_superuser` por `user.is_staff` (Root continua ganhando
  `is_staff` via `setup_roles`, então nada mudou pra ele).
- **Notificação duplicada ao comentar** — auditoria no código não achou
  bug de duplicação no lado servidor (`notificar_participantes_da_discussao`
  já dedupava por `autor_id`, chamada uma única vez por request). Causa
  mais provável: duplo-clique no botão antes do redirect da primeira
  resposta chegar, mandando dois POSTs. Fix defensivo: botão de comentário
  desabilita no `submit` (`initPreventDoubleSubmit` em `main.js`).
- **Painel de Resumo deformando com o fórum** — `.detail-grid` esticava os
  dois lados pra mesma altura (comportamento padrão de grid); `Resumo`
  crescia junto conforme a lista de comentários crescia à direita. Fix de
  uma linha: `align-items: start` no `.detail-grid` — resolve os 3 pedidos
  relacionados (painel não deformar, "Ver mais" não quebrar o layout,
  Resumo não esticar) de uma vez.
- **Respostas aninhadas no fórum** — `Comentario.parent` já suportava
  profundidade ilimitada no model, mas o template só renderizava 1 nível
  e só o comentário raiz tinha botão "Responder". Novo partial recursivo
  `templates/legislativo/_comentario.html` (se inclui pra cada resposta),
  junto com `Prefetch` explícito de 4 níveis em `_forum_context` (mais
  fundo que isso ainda funciona, só sem prefetch/com N+1 — perfil de uso
  não deve chegar lá).
- **"Enviar Participação" removida do fórum** — formulário avulso
  (`ParticipacaoForm`) tirado da página da proposição a pedido do
  usuário; `Participacao` (model) e sua tela no Admin continuam existindo
  pra dado histórico/exportação de engajamento do Root, só não tem mais
  entrada nova pela UI pública.
- **"Participações" virou engajamento de verdade** — antes listava
  `Participacao.objects.all()` (público, sem filtro). Agora
  `ParticipacaoListView` exige login e mostra as proposições em que o
  próprio usuário comentou (`Comentario.objects.filter(autor=...)`),
  como cards clicáveis (reaproveita `_proposicao_card.html`, igual
  Favoritos) — resolve "só minhas participações" + "cards clicáveis pra
  proposição" de uma vez. Sidebar do perfil passou a aparecer também em
  Favoritos e Participações (`mostrar_sidebar: True` nas duas views; o
  item ativo/selecionado já funcionava sozinho, `_sidebar.html` já
  comparava `request.resolver_match.url_name`).
- **Página de perfil público de usuário** (nova) — `/usuario/<pk>/`
  (`usuario_publico`), acessível clicando no nome/avatar de quem comentou
  no fórum (`_comentario.html`); mostra nome, cargo/município (dados já
  públicos no fórum) e as proposições em que a pessoa comentou. Sem
  login exigido, mesmo princípio de "fórum é público" do resto do site —
  não expõe e-mail/telefone.
- **Filtro da home consolidado** — cards de estatística (Total/Na
  pauta/Urgentes/Alta prioridade/Com relator) viraram links clicáveis
  (`?filtro=pauta` etc., novo `get_filtered_proposicoes(..., filtro=)` +
  `FILTROS_ESTATISTICA`/`FILTRO_LABELS` em views.py) e o número voltou a
  usar a mesma cor escura do `.section-heading` (eram coloridos por
  categoria, lido como decoração). Qualquer filtro ativo (tema, busca ou
  card de estatística) agora colapsa Urgentes/Áreas de
  interesse/Em alta/Últimos acessados e mostra só uma lista consolidada
  em "Todas as proposições", retitulada (ex.: "Na pauta (7)") com um
  "Limpar filtro ×" — resolve de uma vez "mover pro topo como grupo",
  "não perder o filtro ao trocar de área de interesse" e a percepção de
  "filtro quebrado" (Urgentes/Em alta antes nunca respeitavam tema/busca,
  só a grade "Todas" filtrava). `tema=` na URL agora casa tanto com
  `Tema.slug` quanto `Macrotema.slug` (chip do card/detalhe mostra o
  macrotema quando existe, então o link do chip precisava bater com um
  slug de Macrotema, não só de Tema). Busca ganhou preview em tempo real
  (debounce de 250ms chamando `/api/proposicoes-cards/?q=...`, sem
  tema/filtro — digitar sempre substitui o filtro anterior, nunca soma).
- **Navegação "Voltar" reescrita** — trocada a heurística antiga
  (`document.referrer` + `history.length`, que caía no fallback estático
  pra home sempre que o referrer não era same-site ou a página tinha sido
  recarregada via POST/redirect) por uma pilha própria em
  `sessionStorage` (`initBackNavigation` em `main.js`): cada carregamento
  de página empilha a URL atual (sem duplicar se for a mesma de novo, o
  que cobre o redirect pós-comentário); "Voltar" desempilha a página
  atual e navega pra anterior de verdade. Determinístico, não é afetado
  por "Ver mais comentários" (interação só local, não mexe na pilha).
  Painel Admin ganhou botão "Voltar" próprio (ícone ao lado do título,
  `templates/admin/base_site.html`) que sempre volta pro `/perfil/` do
  usuário, como pedido.
- **E-mail editável no perfil** — `PerfilForm` ganhou o campo `email`
  (antes só texto cinza fixo), com validação de unicidade e sincronização
  do `EmailAddress` do allauth (`verified=False` depois de trocar, já que
  é um e-mail nunca confirmado) — sem isso o allauth ficaria com um
  registro de e-mail desatualizado em paralelo ao `Usuario.email` real.
- **Like em comentários** (novo) — `ComentarioLike` (model, 1 curtida por
  usuário por comentário via `UniqueConstraint`), botão de curtir em
  `_comentario.html` (toggle via POST, `curtir_comentario` em views.py),
  contagem soma no ranking "Em alta" da home (`relevancia` ganhou
  `+ likes_count * 2`, mesmo princípio de peso que comentários já tinham).
- **Solicitar exclusão de conta redesenhada** — bug real encontrado no
  caminho: a view nunca passava `mostrar_sidebar: True`, então a página
  caía no layout sem `.app-content` (sem `align-items: center`) e ficava
  "grudada" no canto esquerdo em vez de centralizada — mesma causa raiz
  em qualquer página nova que esqueça essa flag. Fix + reforço visual:
  ícone de alerta, lista clara de consequências, botão "Cancelar" ao lado
  do de confirmar (antes só existia o botão de exclusão).
- **Troca de senha (senha atual + nova + confirmar)** — checado e já
  funciona por padrão pra quem já tem senha local:
  `allauth.account.forms.ChangePasswordForm` (usado por
  `/contas/senha/alterar/`, já linkado na sidebar) sempre pede
  `oldpassword` + `password1` + `password2`. **Correção no mesmo dia**:
  o usuário testou com uma conta que só loga via Google (sem senha local)
  e viu a tela "Definir senha" (só nova+confirmar, sem "senha atual") —
  comportamento nativo do allauth pra esse caso (não tem senha atual pra
  confirmar), mas o usuário pediu uma camada extra: exigir confirmação
  por e-mail antes de deixar a sessão criar a primeira senha local sozinha
  (evita que uma sessão sequestrada vire uma porta dos fundos permanente
  de login por senha). `account_set_password` (`/contas/password/set/`)
  foi sobrescrita (`apps/usuarios/views.py::definir_senha_social`,
  registrada em `setup/urls.py` antes do `include('allauth.urls')`, mesmo
  nome de URL) — em vez de mostrar o formulário de senha direto, manda um
  e-mail via `ResetPasswordForm` do próprio allauth (reaproveita o fluxo
  já testado de "Esqueci minha senha", token com expiração) e só define a
  senha quando a pessoa clica no link recebido. Conta que já tem senha
  local continua indo direto pra "Alterar senha", sem esse passo extra.

`check`, `makemigrations --check`, `ruff --select F401,F811,F841` e 61
testes (era 44, +17 novos cobrindo cada bug/feature acima) limpos.
Smoke test via `Client` (não só `RequestFactory`) confirmando 200 em
home com/sem filtro, fórum com resposta aninhada de verdade, Favoritos,
Participações, Solicitar Exclusão, `/admin/` pro Root e o fluxo completo
de `/contas/password/set/` (e-mail de fato enviado via `console.EmailBackend`
em dev). **Sem acesso a
navegador neste ambiente** — nada disso foi conferido visualmente
(cards clicáveis, colapso das seções ao filtrar, preview em tempo real
da busca, layout do fórum); vale uma rodada de conferência visual antes
de considerar pronto pra promover.

### Auditoria de segurança (pentest de 48 itens) — 2026-08-11

A pedido do usuário ("aja como pentester sênior... varredura de segurança
completa"), rodada em 3 fases: relatório primeiro (48 itens, categorias
A-L), aprovação do usuário, depois correção. Achados por leitura de código
(sem acesso a SSH/painel da Digital Ocean — itens de infraestrutura pura
ficaram marcados "não verificável daqui").

**Achado crítico corrigido (rebaixado de severidade após investigar o
mecanismo de verdade)**: `SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT`
(fusão de login Google com conta local existente do mesmo e-mail) parecia,
à primeira vista, permitir que alguém se cadastrasse com o e-mail de outra
pessoa (sem confirmar posse) e "roubasse" a conta quando a vítima real
entrasse via Google depois. Investigando o código-fonte do allauth
(`socialaccount/internal/flows/email_authentication.py::wipe_password`),
descobri que o próprio allauth já mitiga esse cenário exato: se o e-mail
da conta local não estava verificado, a senha do atacante é apagada
automaticamente no momento da fusão. O risco residual real (não o que o
relatório da Fase 1 descreveu) é só a janela entre o cadastro fraudulento
ser aprovado pela equipe e a vítima de fato logar via Google — que pode
nunca acontecer, se a pessoa só usa e-mail/senha. Fix: coluna nova
"E-mail confirmado" em `UsuarioAdmin` (`EmailAddress.verified`, via
`Exists`/`OuterRef` no `get_queryset`), visível na mesma listagem onde
Root já aprova/rejeita cadastro — dá o sinal que faltava pra recusar um
cadastro suspeito sem exigir SMTP configurado (`ACCOUNT_EMAIL_VERIFICATION
='mandatory'` seria o fix "de livro-texto", mas travaria todo cadastro
por e-mail/senha em produção até o `EMAIL_BACKEND` real estar configurado
lá — não fiz essa troca agora, ver Pendências).

**Riscos corrigidos:**

- **Comentário podia ser encaixado como resposta em outra proposição** —
  `ComentarioForm` expunha `parent` sem restringir o queryset à proposição
  atual; um POST manual conseguia colar uma "resposta" na árvore de
  comentários de uma proposição diferente da que o formulário pertencia
  (achado só por leitura de código, não reportado por ninguém). Fix:
  `ComentarioForm.__init__` agora recebe `proposicao=` e restringe
  `self.fields['parent'].queryset` a comentários dela só.
- **Nenhum registro de quem aprovou/rejeitou um cadastro ou exclusão** —
  `aprovar_cadastros`/`rejeitar_cadastros`/`rejeitar_exclusoes` usam
  `.update()` em massa, que nunca passa pelo `LogEntry` automático do
  Django Admin (só `save_model` de edição individual passa). Fix: helper
  `UsuarioAdmin._registrar_log()` grava um `LogEntry` explícito (autor,
  objeto, mensagem) em toda ação de aprovação/rejeição, em massa ou
  individual (`response_change`).
- **Senha mínima só o default do Django (8 caracteres, sem outra
  exigência)** — `MinimumLengthValidator` ganhou `min_length=10`
  explícito. Não adicionei regra de "precisa ter maiúscula/símbolo": é a
  orientação atual do NIST/OWASP (comprimento > regras de complexidade,
  que na prática só geram senha previsível tipo "Senha123!").
- **Sessão sem expiração explícita** — caía no default do Django (2
  semanas). `SESSION_COOKIE_AGE = 60 * 60 * 24 * 7` (7 dias) agora
  explícito em `settings.py`.
- **Denúncia de comentário sem rate limit** — só `@login_required` +
  `UniqueConstraint` (não dá pra denunciar o mesmo comentário 2x)
  limitavam abuso; agora também `rate_limited('denuncia', ..., limit=10,
  window_seconds=600)`, mesmo padrão de `comentario`/`participacao`.
- **Rate limit dos formulários públicos praticamente sem componente de
  IP** — `throttling.py` usava `REMOTE_ADDR`, mas o Gunicorn só é
  alcançado via Nginx (porta do container presa em `127.0.0.1`, ver
  `docker-compose.yml`) sem nada traduzindo `X-Forwarded-For` — na
  prática `REMOTE_ADDR` era sempre o IP do próprio Nginx pra qualquer
  visitante, e o rate limit sobrava só na sessão (reset trivial limpando
  cookies). Fix: `_client_ip()` novo lê `X-Forwarded-For` (o **último**
  valor da lista — o que o Nginx de fato viu e anexou via
  `$proxy_add_x_forwarded_for`, não um valor que o próprio cliente possa
  ter forjado antes dele), com fallback pra `REMOTE_ADDR` em dev local
  (sem Nginx na frente).

`check`, `check --deploy` (simulando produção), `makemigrations --check`,
`ruff --select F401,F811,F841` e 73 testes (era 58, +15 novos cobrindo
cada fix) limpos. Smoke test via `Client` confirmando a coluna nova no
Admin e o fórum renderizando normal com o `ComentarioForm` escopado.

**Itens do relatório de 48 que já estavam ✅ e não precisaram de mudança**
(cobertos em detalhe na resposta da Fase 1, não repetidos aqui): sem SQL
bruto/`\|safe`/`mark_safe` em conteúdo de usuário em todo o projeto,
`.env` nunca commitado (checado o histórico inteiro do git), CSP/HSTS/
cookies seguros/clickjacking já configurados desde a auditoria de
2026-08-06, container roda non-root com porta presa em `127.0.0.1`,
upload de foto usa `ImageField` (valida estrutura real via Pillow, não só
extensão) com limite de 5MB, `sync_camara` não é endpoint HTTP.

### Rotação do `doadmin`, promoção `next` → `main` → produção e início da verificação de infra por SSH (2026-08-11, mesmo dia)

Continuação da mesma sessão da auditoria de pentest acima, agora com o
usuário conduzindo comandos por SSH no droplet `fnp-web` (sem acesso
direto do Claude Code, como sempre — só os comandos passados aqui).

- **Senha do `doadmin` do `fnp-database` rotacionada e validada.** Duas
  tentativas iniciais de `psql` falharam autenticação (senha ainda não
  propagada ou erro de copy/paste do painel da DigitalOcean), a terceira
  conectou com sucesso. Fecha a pendência que vinha desde uma sessão
  anterior (senha exposta numa captura de tela). Verificado no caminho
  que o `DATABASE_URL` de produção usa a role dedicada `legislativo`
  (banco `legislativo_fnp`), não `doadmin` — a rotação não exigiu
  nenhuma mudança no `.env` do servidor nem restart de container. A
  tentativa de testar a role `legislativo` contra um banco `homolog`
  falhou autenticação, mas a pendência era só sobre o `doadmin`; a
  investigação de `legislativo`/`homolog` foi deixada de lado a pedido
  do usuário.
- **Promoção completa `next` → `main`, autorizada explicitamente pelo
  usuário** ("vamos subir para a next e para a produção"). Antes do
  push: `check`, `makemigrations --check` e os 73 testes revalidados
  localmente (limpos). `main` estava 3 commits atrás de `next` e era
  fast-forward puro (sem divergência) — levou de uma vez a rodada de 23
  pedidos (2026-08-10), a exigência de confirmação por e-mail antes de
  senha em conta só-Google, e a auditoria de segurança do pentest de 48
  itens (2026-08-11). Push pra `origin` e `production`; CI verde nos
  dois repositórios (`gh run watch`).
- **Deploy real confirmado no droplet via SSH** — `git pull origin main`
  (o clone do droplet só tem o remoto `origin`, apontando pro
  `dadosfnp/legislativo-fnp`), `docker compose build && docker compose
  up -d`. Build não veio do cache na camada `COPY . .` (diferente do
  incidente de 2026-08-07, onde um build rodou silenciosamente com
  código antigo) — sinal de que o `git pull` de fato trouxe código novo
  antes do build. `docker compose logs legislativo` (nome do serviço
  neste `docker-compose.yml`, não `web`) confirmou
  `Applying comentarios.0007_comentariolike... OK`, coleta de estáticos
  e Gunicorn subindo sem traceback; `curl -sI
  https://legislativo.fnp.org.br/` → `200 OK` com os headers de
  segurança esperados (CSP, HSTS, `X-Frame-Options: DENY`, cookie
  `Secure`).
- **Checklist de segurança pós-deploy** (a pedido do usuário, aproveitando
  o SSH já aberto) — itens que a auditoria de pentest tinha marcado "não
  verificável daqui" por falta de acesso à infraestrutura:
  - `PasswordAuthentication no` confirmado via `sshd -T` (login só por
    chave) — reduz bastante a gravidade de `PermitRootLogin yes` (ainda
    não é best practice, zero rastreabilidade por usuário, mas força
    bruta de senha não funciona; fail2ban ativo, 349 banimentos
    históricos). Existe 1 usuário não-root no droplet (`phillippi`,
    comentário `/etc/passwd` diz "deploy IFEM" — de outro sistema, não
    do legislativo-fnp). Baixa prioridade, não mexido.
  - `ufw status verbose` → só 22/80/443 liberados, nada do Postgres
    (25060) ou Gunicorn (8004) exposto publicamente — sem achado.
  - `apt list --upgradable` → vários pacotes desatualizados, **inclusive
    o próprio Docker** (`docker-ce`, `containerd.io`,
    `docker-compose-plugin`) e **reboot pendente** (`/var/run/reboot-required`
    existe). Não aplicado ainda — upgrade do Docker e reboot da máquina
    derrubam produção brevemente, precisa de janela de manutenção
    combinada, não uma correção no meio de uma sessão de checklist.
  - **O cluster Postgres `fnp-database` é compartilhado de propósito
    entre todos os sistemas da FNP** (roles `fnp_financeiro`,
    `admin_sistema`, `ifem_app`, `nucleo_carga`, `nucleo_ro`, vistos no
    painel da DigitalOcean) — **confirmado pelo usuário que é
    arquitetura intencional, não achado de segurança**: os sistemas da
    FNP devem conversar entre si. Checado via
    `has_database_privilege('legislativo', datname, 'CONNECT')` que a
    role `legislativo` conecta em `defaultdb`/`homolog`/`fnp_sistema`
    além do próprio `legislativo_fnp` — isso é esperado, não corrigido
    (tentativa de `REVOKE CONNECT FROM legislativo` rodada antes dessa
    confirmação não teve efeito de qualquer forma, por causa do
    `CONNECT` que o Postgres concede a `PUBLIC` por padrão em toda
    database nova). **Não é mais pendência.**
  - **Senha do `doadmin` apareceu em texto puro no terminal colado no
    chat desta sessão** (a mesma que tinha acabado de ser rotacionada por
    causa de uma exposição anterior por captura de tela) — **rotacionada
    de novo e validada** (`SELECT current_user;` retornando `doadmin`)
    ainda na mesma sessão, sem colar a senha nova no chat desta vez.
    Lição registrada: cluster compartilhado com outros sistemas da FNP,
    então qualquer credencial exposta em sessão de terminal/chat (de
    qualquer role, não só `doadmin`) merece rotação — cuidado ao colar
    comandos com senha visível daqui pra frente.
  - **Client Secret do Google OAuth também rotacionado de fato** (o
    usuário voltou atrás da decisão inicial de aceitar o risco) — novo
    secret gerado via "+ Add secret" no Google Cloud Console (o cliente
    OAuth `legislativo-fnp` usa o modelo novo do Google com múltiplos
    secrets simultâneos, dá pra trocar sem downtime), `GOOGLE_CLIENT_SECRET`
    atualizado no `.env` de produção, container recriado
    (`docker compose up -d --force-recreate legislativo`, sem rebuild —
    só variável de ambiente) sem erro no log. **Login Google testado e
    confirmado funcionando em produção de verdade** (conta
    `@fnp.org.br`, via painel `/admin/usuarios/usuario/`) — fecha
    também o item separado "testar login Google em produção" que
    estava pendente. **Falta só**: voltar no Google Cloud Console e
    desativar/excluir o secret antigo (criado 2026-08-04) pra fechar a
    exposição por completo — enquanto ele continuar "Ativadas", ainda é
    uma credencial válida em paralelo à nova.
- **Ajuste de UX no Admin, mesma sessão**: botões de ação rápida por
  linha (`UsuarioAdmin.acoes_rapidas` — "Aprovar exclusão"/"Manter
  conta" etc.) apareciam empilhados verticalmente em vez de lado a lado
  — eram `<button>` soltos separados só por um espaço de texto, que
  quebra linha como texto normal quando o espaço aperta. Fix: os botões
  agora renderizam dentro de um `<div class="fnp-quick-actions">` com
  `display: flex; gap: 0.35rem` (`apps/usuarios/admin.py` +
  `admin-custom.css`), lado a lado sempre.

### Pendências e próximos passos

**Mais urgente agora:**

- **Configurar `EMAIL_BACKEND` real em produção (SMTP/SES/etc.)** —
  passou de pendência menor pra pré-requisito de segurança: sem isso, não
  dá pra avançar pra `ACCOUNT_EMAIL_VERIFICATION='mandatory'` (o fix mais
  robusto pro achado da fusão de conta, ver auditoria acima) sem quebrar
  cadastro por e-mail/senha em produção.
- **Desativar/excluir o Client Secret antigo do Google OAuth** no Google
  Cloud Console (o criado em 2026-08-04) — o novo já está em produção e
  validado, mas o antigo continua uma credencial ativa em paralelo até
  ser desligado por lá.
- **Confirmar restante dos itens de infraestrutura** (fora do que já foi
  checado em 2026-08-11: SSH key-only ✅, `ufw` ✅, `PermitRootLogin yes`
  ainda ligado mas baixa prioridade, atualizações de SO + Docker
  pendentes com reboot — precisa de janela de manutenção): `fnp-database`
  só aceita conexão do `fnp-web` via Trusted Sources (painel DO, não dá
  pra verificar por SSH).
- **Conferir visualmente no navegador a rodada de 23 itens acima** — só
  o lado servidor foi validado (testes + smoke test via `Client`); nada
  foi visto renderizado de verdade. Prioridade: cards de estatística
  clicáveis, colapso/consolidação do filtro da home, layout do fórum com
  respostas aninhadas + like, botão "Voltar" em fluxos reais de
  navegação.
- **Confirmar visualmente no navegador se os 5 ajustes finos da rodada
  anterior ficaram bons** (header do Admin, tour, contorno de foco,
  largura dos modais, fonte da sidebar) — já em produção, mas sem
  confirmação visual final do usuário ainda.
- **Decidir o que fazer com as 70 proposições não-curadas já em
  produção** (`interlocutores` vazio) — o `--paginas 1` já está no ar,
  então agora dá pra limpar sem risco de recriação imediata no próximo
  ciclo do `sync-camara`. Reais, sem duplicata, só sem revisão editorial
  da FNP.

**Seguem em aberto (sem mudança nesta sessão):**

- Contas externas que faltam ser criadas pra ativar o que já está
  implementado (tudo desligado até lá, zero risco): `SENTRY_DSN`
  (sentry.io), `RECAPTCHA_PUBLIC_KEY`/`RECAPTCHA_PRIVATE_KEY`
  (google.com/recaptcha/admin).
- `EMAIL_BACKEND` de produção ainda não configurado com um backend real
  (SMTP/SES/etc.) via env var — `ACCOUNT_EMAIL_VERIFICATION=optional`
  manda e-mail de confirmação mas não entrega de verdade lá. (O bug de
  dev, cadastro local derrubando sem `EMAIL_BACKEND`, já foi corrigido —
  isso aqui é só sobre produção ter um backend real configurado.)
- Cache do Django é `LocMemCache` (por processo) — com Gunicorn
  `--workers 3`, rate limit de login e `throttling.py` de
  comentário/participação têm limite efetivo até 3x mais permissivo do
  que o configurado. Trocar por Redis é reabrir a diretriz "só trocar se
  crescer pra múltiplos workers" — decisão ainda não tomada.
- `deploy/nginx-legislativo.conf` atualizado (limite de upload 6MB) ainda
  não copiado pro droplet — `cp` manual + certbot de novo (reinstalar
  sobrescreve o bloco SSL, já aconteceu antes).
- Droplet `fnp-web` sem backup próprio (só o `fnp-database` tem).
- Reverificar se o bug do Python 3.14 (`copy.copy()` em `RequestContext`)
  ainda ocorre agora que o projeto está no Django 5.2 — não testado,
  `.venv/` local continua em 3.12 por segurança.
- Conferir/chown o volume de `media/` no droplet antes do primeiro upload
  de foto de perfil em produção (mesmo risco de permissão que o
  `staticfiles/` teve, nunca testado).
- ~~Client Secret do Google OAuth exposto numa captura de tela em sessão
  anterior~~ — **decisão do usuário em 2026-08-11: não rotacionar**
  (risco aceito, baixo — app ainda em modo "teste" no Google Cloud
  Console). Não é mais pendência de segurança.
- Falta preencher `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` no `.env` do
  servidor de produção (não é o mesmo `.env` local) e adicionar e-mails
  de teste na tela de consentimento OAuth até o app sair do modo
  "teste" — item funcional separado do risco de exposição acima. Nota:
  o login Google em produção já foi testado e confirmado funcionando
  em 2026-08-11 (ver seção datada acima), então o `.env` do servidor já
  tem `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` preenchidos de fato —
  falta só adicionar e-mails de teste na tela de consentimento se
  alguém novo (fora quem já testou) precisar logar via Google antes do
  app sair do modo "teste".
- Comentários "pendente" de antes da moderação automática continuam
  precisando de revisão manual (ação em massa no Admin).
- Integração com o Senado (hoje só Câmara via `sync_camara`).
- Redesign visual incremental a partir de referências que o usuário vai
  mandando aos poucos (sidebar/topbar do site público e do Admin já
  alinhados; mais capturas de tela podem vir e pedir mais ajuste).

---

## Documentação Técnica

| Arquivo | Conteúdo |
|---|---|
| `README.md` | Visão geral do projeto e fluxo de repositórios |
| `docs/runbook.md` | Operação e procedimentos de execução |
| `docs/adr/0001-initial-architecture.md` | Arquitetura inicial do projeto |
| `CONTRIBUTING.md` | Padrões de contribuição |

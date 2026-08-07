# CLAUDE.md — Contexto do Projeto Legislativo FNP

> Arquivo de contexto para sessões com Claude Code. Atualizado automaticamente a cada 3h enquanto há sessão ativa (mantém este arquivo fiel ao código para evitar redescoberta/gasto de tokens em sessões futuras).
> Última atualização: 2026-08-07 (rodada de UX/UI a partir de capturas de tela anotadas — filtro sticky na home, badge "sem pauta" com cor própria, título da proposição como hyperlink pra fonte oficial, "Ver mais" nos comentários, rodapé fixo no fim da página em telas allauth —, cadastro novo via Google restrito a e-mail @fnp.org.br, e exportação de dados de engajamento exclusiva do Root; ver "Rodada de UX/UI + restrição de cadastro Google + exportação de engajamento" no Estado Atual. Bug real encontrado e corrigido no login Google local: CSP `form-action: 'self'` (da auditoria de segurança) bloqueava o redirect final pro Google — `form-action` agora inclui `https://accounts.google.com`; confirmado funcionando de ponta a ponta no Microsoft Edge (Chrome ainda não retestado). Sessão anterior, 2026-08-06: itens Alto/Médio da auditoria de segurança fechados — rate limit de login, 2FA obrigatório pra staff (depois desativado a pedido do usuário), CSP, lockfile+pip-audit, CAPTCHA, limite de upload; upgrade Django 4.2→5.2 LTS e django-allauth 0.60→65.19 — ver "Auditoria de segurança e upgrade Django/allauth" no Estado Atual)

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
- **LGPD:** página de Política de Privacidade, exportação dos dados do usuário em JSON (`exportar_meus_dados`) e solicitação de exclusão de conta (`solicitar_exclusao` — só marca `Perfil.exclusao_solicitada_em`, exclusão real é manual pelo Root via Admin, sem autoexclusão instantânea). `UsuarioAdmin` tem ações simétricas `aprovar_exclusoes` (reaproveita a tela de confirmação nativa do `delete_selected` — exclui de fato) e `rejeitar_exclusoes` (limpa `exclusao_solicitada_em`, mantém a conta), no mesmo padrão de `aprovar_cadastros`/`rejeitar_cadastros`
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
proposição, fórum, tela de confirmação de login Google): (1) painel de
busca/filtro da home agora acompanha o cabeçalho ao rolar a página
(`position: sticky`, offset calculado em JS via `initStickyHeaderOffset`
em `main.js` porque a altura do cabeçalho varia por breakpoint e pelo
tamanho de fonte configurável — nunca hardcoded em px); (2) badge
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
um banco externo de pontuação de engajamento; **completamente separada**
da exportação de LGPD já existente (`exportar_meus_dados`, cada usuário
só dos próprios dados, continua intacta). `check`, `makemigrations
--check` e 41 testes (era 38) limpos; páginas renderizadas via `Client`
pra conferir ausência de erro de template (não visualmente — sem acesso a
navegador neste ambiente).

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

### Pendências e próximos passos

- **Login Google local no Chrome (perfil "Trabalho") não foi reconfirmado**
  depois do fix de CSP -- funcionou no Microsoft Edge, mas o teste original
  que expôs o bug foi feito nesse perfil do Chrome; vale um retest rápido
  lá pra garantir que não é uma segunda causa (extensão/política) somada à
  da CSP.
- **Testar login com Google de verdade em produção** depois do upgrade do
  allauth (0.60→65.19) — só o login por e-mail foi verificado
  automaticamente; o fluxo OAuth real precisa de navegador/conta Google.
- **Contas externas que faltam ser criadas** pra ativar o que já está
  implementado (tudo desligado até então, zero risco): `SENTRY_DSN`
  (sentry.io), `RECAPTCHA_PUBLIC_KEY`/`RECAPTCHA_PRIVATE_KEY`
  (google.com/recaptcha/admin).
- **`EMAIL_BACKEND` não configurado** — `ACCOUNT_EMAIL_VERIFICATION=optional`
  manda e-mail de confirmação, mas sem backend real (SMTP/SES/etc.) ele
  usa o backend console do Django e não entrega de verdade.
- **Cache do Django é `LocMemCache`** (por processo) — com o Gunicorn
  rodando `--workers 3`, tanto o rate limit de login quanto o
  `throttling.py` de comentário/participação têm limite efetivo até 3x
  mais permissivo do que o configurado (cada processo conta separado).
  Decisão de trocar por cache compartilhado (Redis) ainda em aberto — é
  reabrir a diretriz "só trocar por Redis se crescer pra múltiplos
  workers", que já aconteceu.
- **`style-src` do CSP com `'unsafe-inline'`** — vários templates usam
  atributo `style="..."` inline; remover exigiria um cleanup maior
  (mover pra classes CSS) não feito agora.
- **Rodar `deploy/nginx-legislativo.conf` atualizado no droplet**
  (`client_max_body_size`) — `cp` manual + certbot de novo (reinstalar
  sobrescreve o bloco SSL, já aconteceu antes nesta sessão).
- **Droplet `fnp-web` sem backup próprio** (só o `fnp-database` tem — o
  droplet em si, com Nginx/Docker/certificados, não tem snapshot nenhum).
- Reverificar se o bug do Python 3.14 (`copy.copy()` em `RequestContext`)
  documentado acima ainda ocorre agora que o projeto está no Django 5.2 —
  não testado ainda, `.venv/` local continua em 3.12 por segurança.
- **Política do `sync-camara` ainda não decidida**: hoje ele descobre e cria
  proposições novas sozinho via busca por palavra-chave, sem qualquer
  curadoria — o mesmo problema que causou a limpeza acima pode se repetir
  a cada 30min. Decidir (revisão explícita, é mudança na diretriz de
  Ingestão): manter como descoberta livre + fila de revisão manual no
  Admin, restringir a só atualizar proposições já existentes (sem criar
  novas), ou afinar as keywords.
- Conferir/chown o volume de `media/` no droplet antes do primeiro upload de
  foto de perfil em produção (mesmo risco de permissão do `staticfiles/`,
  nunca testado)
- Rotacionar a senha do `doadmin` do `fnp-database` — foi exposta numa captura de tela compartilhada em sessão anterior (não foi usada/reproduzida, mas ficou registrada na conversa)
- Credenciais reais do Google OAuth criadas em 2026-08-04 (Client ID/Secret preenchidos no `.env` local, não versionado); Client Secret foi exposto numa captura de tela compartilhada em sessão anterior (risco baixo — app ainda em modo "teste" no Google Cloud Console, só e-mails cadastrados como usuário de teste completam o login; mesmo assim, considerar gerar um novo secret se o app for publicado). Redirect URIs já cadastrados e salvos no cliente OAuth (`http://127.0.0.1:8000/contas/google/login/callback/` dev + `https://legislativo.fnp.org.br/contas/google/login/callback/` produção). Falta: (1) testar o login local de fato; (2) preencher `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` no `.env` do servidor de produção (não é o mesmo `.env` local); (3) adicionar e-mails de teste na tela de consentimento OAuth até o app sair do modo "teste"
- Popular `PalavraProibida` de verdade via Admin (a lista nasce vazia de propósito — curadoria é decisão da equipe FNP, não do código)
- Comentários "pendente" que já existiam antes da moderação automática continuam precisando de revisão manual (ação em massa no Admin) — o auto-approve só vale pra envios novos
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

# CLAUDE.md — Contexto do Projeto Legislativo FNP

> Arquivo de contexto para sessões com Claude Code. Atualizado automaticamente a cada 3h enquanto há sessão ativa (mantém este arquivo fiel ao código para evitar redescoberta/gasto de tokens em sessões futuras).
> Última atualização: 2026-08-19 — **6 funcionalidades novas na proposição/comentário/cadastro + 3 rodadas de refino no mesmo dia, mais uma sessão nova no mesmo dia com fix de bug real, SMTP configurado e classe de usuário virando automática.** (1) anexos de documentos na proposição — **exige aprovação de Root/Administrador FNP antes de aparecer pro público** (nasce sempre "pendente", sem checagem automática de conteúdo de arquivo, diferente do comentário), com upload redesenhado (ícone de clipe + nome do arquivo escolhido, no lugar do "Escolher arquivo" nativo), (2) foto/vídeo nos comentários do fórum — refeito como toolbar estilo rede social (botão "+" de anexar da galeria + botão de câmera com captura de foto OU gravação de vídeo ao vivo via MediaRecorder, substituindo o `<input type="file">` cru que "ficou muito esquisito"), (3) seção "Notícias relacionadas", (4) botão de impressão — 2 rodadas de ajuste a partir de feedback real, virou um menu com hover que aponta direto pras versões de impressão de verdade da Câmara/Senado (não mais uma página de impressão nossa), (5) botão de compartilhar (Web Share API + fallback WhatsApp/X/Facebook/copiar link), (6) classe de usuário (Equipe FNP/Prefeito/Indicado da prefeitura/Parlamentar). No caminho da 1ª promoção, o CI pegou 4 CVEs novas em `sqlparse` (dependência transitiva do Django, não usada direto no projeto) — corrigido antes de re-promover; também resolvida a pendência de `client_max_body_size` do Nginx (6M → 30M, vídeo de comentário até 25MB). `next` → `main` → produção → droplet confirmado saudável (`curl` 200 OK, headers de segurança corretos) nas 2 primeiras promoções do dia; a 3ª (redesenho do upload de anexo) já está em `main`/CI verde, **deploy no droplet passado pro usuário mas ainda sem confirmação de retorno nesta sessão** — conferir/atualizar antes de considerar o dia todo fechado. **Na sessão seguinte, mesmo dia**: usuário reportou 500 real em produção ao tentar definir senha numa conta só-Google (`/contas/password/set/`) — causa raiz era `EMAIL_BACKEND` de produção ainda sem SMTP real (pendência antiga), `form.save()` subindo `ConnectionRefusedError` cru; corrigido com tratamento de erro (nunca mais 500, mostra aviso e deixa tentar de novo). No mesmo fôlego, `EMAIL_HOST`/`PORT`/`USE_TLS`/`USER`/`PASSWORD` configurados em `settings.py` pro Gmail/Workspace (`naoresponda@fnp.org.br`) — **conta ainda não criada**, e-mail de solicitação enviado pro Keven, falta ele criar + gerar senha de app antes de preencher o `.env` do droplet. Também: "Você é" (select cru, autodeclarado, editável até depois do cadastro em `/perfil/` — brecha real, dava pra virar "Equipe FNP" sozinho) virou **"Perfil de acesso"**, classificado automaticamente a partir do cargo informado no cadastro (`apps/usuarios/classificacao.py`, nunca mais autodeclarado), exibido como valor estático (não editável) em `/perfil/`; Root/Administrador FNP continuam editando via Django Admin. Tudo isso só em `next` (`db3f932`, `f7c7868`, `b792e00`) — **não promovido pra produção ainda**. Ver seções datadas mais abaixo pro detalhe de cada item. Sessão anterior (2026-08-13/14) foi a auditoria de UX mobile + fixes de produção — ver seções datadas mais abaixo.

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

## Postura de segurança (referência rápida)

> Histórico completo, com o raciocínio por trás de cada item (o que foi
> corrigido, o que foi decisão consciente, o que ainda está pendente):
> `docs/adr/0003-seguranca-auditoria-hardening.md`. Esta seção é só o
> resumo do estado atual — atualizar aqui quando algo mudar, mas deixar a
> narrativa completa no ADR.

O projeto é tratado como alvo plausível de ataque (fórum de discussão
política pública, cadastro aberto) — não como sistema interno de baixo
risco. Duas rodadas de auditoria já feitas: hardening geral em 2026-08-06
(junto do upgrade Django 4.2→5.2) e pentest completo de 48 itens em
2026-08-11 (relatório → correção → revarredura, no mesmo dia).

| Área | Estado |
|---|---|
| Framework | Django 5.2 LTS (suporte até abril/2028), `django-allauth` 65.x |
| `DEBUG`/`SECRET_KEY` | Fail-closed — produção sem `SECRET_KEY` não sobe |
| HTTPS/HSTS | `SECURE_SSL_REDIRECT`, HSTS 1 ano + subdomínios + preload, cookies `Secure` (só com `DEBUG=False`) |
| CSP | Ativo, `script-src` com nonce, sem `'unsafe-inline'` em nenhuma diretiva |
| Rate limit | Comentário/participação/denúncia + login (allauth nativo), IP real via `X-Forwarded-For` (não `REMOTE_ADDR` cru) |
| Senha | Mínimo 10 caracteres (`MinimumLengthValidator`), sem regra extra de complexidade (orientação NIST/OWASP atual) |
| Sessão | Expira em 7 dias (`SESSION_COOKIE_AGE`) |
| 2FA | Disponível em `/contas/2fa/`, **opcional** — não obrigatório pra staff (decisão consciente, ver Diretrizes) |
| Dependências | `requirements.lock` com hash; `pip-audit` no CI a cada push/PR |
| Monitoramento | Sentry ativo em produção (`SENTRY_DSN`) |
| Log de auditoria | `TentativaLogin` (sucesso/falha de login) + `LogEntry` explícito em aprovação/rejeição de cadastro/exclusão em massa |
| Infraestrutura | Cloud Firewall DO + `ufw` (só 22/80/443), SSH key-only, `fail2ban` ativo, Trusted Sources do banco restrito ao droplet + 1 IP |

**Pendências de segurança em aberto** (lista completa e atualizada em
"Pendências e próximos passos" mais abaixo): rotacionar `SECRET_KEY` +
senha da role `legislativo` + `GOOGLE_CLIENT_SECRET` (expostos num print
do `.env`); desativar o Client Secret antigo do Google no Console;
decidir se `acoes_incidencia`/`riscos_oportunidades` deveriam exigir
login; configurar `EMAIL_BACKEND` real em produção; atualizações de
SO/Docker com reboot pendente (adiado, droplet compartilhado).

**Regra permanente**: qualquer credencial exposta em captura de tela ou
terminal colado no chat (mesmo já rotacionada antes) merece rotação —
já aconteceu duas vezes com a mesma credencial (`doadmin`) nesta sessão
de auditoria. Nunca colar comando com senha visível sem necessidade.

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

### Revarredura de segurança (48 itens de novo) + log de auditoria de login (2026-08-11, mesma sessão)

A pedido do usuário ("vamos voltar a nossa varredura de segurança
completa"), reconferido item a item dos 48 originais contra o estado atual
do código (não só memória da sessão — grep/leitura direta de cada item).
**41 ✅, 1 decisão consciente já tomada** (role `legislativo` cross-sistema,
ver seção anterior), **6 com nuance**:

- Item 12/16 (verificação de e-mail mandatória): mesma pendência antiga,
  bloqueada por `EMAIL_BACKEND` real em produção — nada novo.
- Item 39 (Admin em `/admin/` sem allowlist de IP): informacional, aceito
  dado o resto das defesas (2FA opcional, aprovação de cadastro, rate
  limit) — não mudado.
- **Item 40, achado novo**: `posicionamento_fnp`/`acoes_incidencia`/
  `riscos_oportunidades` aparecem em `proposicao_detail.html` **sem
  exigir login** (`ProposicaoDetailView` não tem `@login_required`) —
  qualquer visitante anônimo vê a estratégia de incidência interna da
  FNP. Não corrigido ainda — **precisa de decisão do usuário** (é
  intencional/transparência institucional, ou só `posicionamento_fnp`
  deveria ser público?). Ver Pendências.
- Item 45 (Cloud Firewall da DigitalOcean, camada separada do `ufw`
  local): ainda não conferido no painel.
- **Item 47, corrigido nesta sessão**: não havia log de tentativa de
  login consultável (só o rate-limit interno do allauth, que conta mas
  não expõe). Novo model `TentativaLogin` (`apps/usuarios/models.py`,
  migration `0006_tentativalogin`) grava sucesso/falha via signals
  `user_logged_in`/`user_login_failed` (`apps/usuarios/signals.py`) —
  `usuario` (nulo em falha), `email` tentado, `ip` (mesma lógica de
  `X-Forwarded-For` do `throttling.py`, duplicada de propósito pra não
  inverter a dependência de camada `legislativo`→`usuarios`), `criado_em`.
  Registrado no Admin como só-leitura (`has_add_permission`/
  `has_change_permission` retornam `False`) — é log de auditoria, nunca
  editado à mão. 2 testes novos via `Client` real contra
  `reverse('account_login')` (senha certa gera sucesso com `usuario`
  preenchido; senha errada gera falha com `usuario=None`).
- Item 48 (Sentry desligado): mesma pendência antiga, falta só criar a
  conta em sentry.io e preencher `SENTRY_DSN`.

`check`, `makemigrations --check`, `ruff --select F401,F811,F841` e 75
testes (era 73, +2) limpos.

### Cloud Firewall confirmado, Sentry ativado e achado real via Sentry (2026-08-11, mesma sessão)

Continuação dos itens "azuis" do checklist pós-revarredura (dependiam de
painel/conta externa, não código):

- **Cloud Firewall da DigitalOcean confirmado** (`FirewallSistemaFNP`,
  aplicado ao `fnp-web`) — inbound só libera 22/80/443 pra `All
  IPv4`/`All IPv6`, mesma política do `ufw` local. Sem achado.
- **Sentry ativado de verdade** — conta criada, projeto Django, DSN
  colado no `.env` de produção, container recriado. Validado com
  `sentry_sdk.capture_message()` via `manage.py shell` (sem precisar
  quebrar nada de propósito) — evento apareceu no painel em segundos.
  **No processo, o Sentry já pegou um erro real rodando em produção**:
  `DisallowedHost: Invalid HTTP_HOST header: 'localhost:8004'`, 3
  eventos — era o próprio healthcheck do Docker (`curl
  http://localhost:8004/`, sem header `Host` correto) sendo rejeitado
  pelo Django, e a causa raiz do "container unhealthy" registrado horas
  antes na mesma sessão (ver correção acima). `EMAIL_BACKEND` real (o
  terceiro item azul) ficou pra depois, a pedido do usuário.
- **Novo incidente de exposição de segredo**: um print do `.env` de
  produção no `nano` mostrou `SECRET_KEY`, a senha da role `legislativo`
  no `DATABASE_URL` e o `GOOGLE_CLIENT_SECRET` em texto puro nesta
  sessão de chat. Usuário optou por terminar o Sentry primeiro e tratar
  a rotação depois — **ainda não rotacionados**, ver Pendências.
- **`sync-camara` voltou a poluir a base em menos de um dia**: banco
  tinha sido limpo pra 104/104 mais cedo na mesma sessão, voltou a 165
  (usuário percebeu no próprio Painel Geral, `TOTAL: 165`). Confirma que
  `--paginas 1` sozinho não é suficiente — o serviço continuava criando
  proposição sem curadoria a cada ciclo de 30min. Ação: `sync-camara`
  parado na hora (`docker compose stop sync-camara`, efeito imediato,
  antes mesmo do deploy em lote) e desativado por padrão no
  `docker-compose.yml` via `profiles: ["sync-camara"]` (não sobe mais
  com `docker compose up -d` puro; reativar com `docker compose
  --profile sync-camara up -d sync-camara`, decisão futura sobre um
  fluxo de atualização em tempo real com curadoria). Banco limpo de
  novo pra 104/104 (mesmo processo de mais cedo: `sync_legado_firestore`
  restaura os 104, depois apaga quem não está nesse conjunto).

### Excluir comentário (autor e Admin) + comentários agrupados por proposição no Admin (2026-08-11, mesma sessão)

A pedido do usuário, três pedidos relacionados a moderação de comentário:

- **Autor exclui o próprio comentário** — botão "Excluir" novo em
  `_comentario.html` (mesmo estilo do "Denunciar"), só aparece se
  `comentario.autor_id == request.user.id`. `excluir_comentario`
  (`apps/legislativo/views.py`) só apaga de fato **se o comentário não
  tiver resposta ainda** — `Comentario.parent` é `on_delete=CASCADE`,
  então excluir um comentário com resposta apagaria resposta de
  **outra pessoa** junto; se tiver resposta, o botão nem aparece no
  template, e o POST direto (bypass manual) simplesmente não apaga nada
  (sem mensagem de erro — `django.contrib.messages` não está plugado no
  site público, não introduzido só por causa disso).
- **Root/Administrador FNP excluem comentário de qualquer um pelo
  Admin** — Root (superusuário) já podia via o botão nativo do Django
  Admin (bypassa checagem de permissão, comportamento padrão que já
  existia, nada mudou aí). "Administrador FNP" **não tinha** permissão
  de `delete` em `Comentario` (só `view`/`change`) — adicionada em
  `setup_roles.py` (`ADMINISTRADOR_PERMISSOES`). **Atenção**: como
  `setup_roles` não roda automático no deploy, precisa rodar manual em
  produção depois desse deploy pra quem já é "Administrador FNP" ganhar
  o botão de excluir.
- **Comentários agrupados por proposição no Admin** — `ComentarioAdmin`
  ganhou `ordering = ('proposicao__titulo', '-criado_em')`; comentários
  da mesma proposição ficam em sequência na listagem (mais recente
  primeiro dentro de cada grupo) em vez de espalhados por data. Filtro
  por proposição na barra lateral (já existia) continua funcionando
  pra isolar uma proposição específica.

`check`, `makemigrations --check` (sem migration nova — só views/admin/
template/permissão), `ruff --select F401,F811,F841` e 78 testes (era 75,
+3) limpos.

### Deploy em lote confirmado: `next` → `main` → produção → droplet (2026-08-11, fim da sessão)

A pedido do usuário ("já vamos fazer o deploy de tudo"), tudo acumulado no
dia promovido de uma vez: fix do link `?` vazio, `TentativaLogin`
(migration `usuarios.0006_tentativalogin`), exclusão de comentário,
agrupamento por proposição no Admin, healthcheck do Docker corrigido, e
`sync-camara` desativado por `profiles`. `check`/`makemigrations --check`/
78 testes revalidados antes do push; `main` era fast-forward puro (sem
divergência); CI verde nos dois repositórios. Deploy real no droplet via
SSH confirmado passo a passo: `git pull` trouxe o código novo, migration
`usuarios.0006_tentativalogin` aplicada, `docker compose ps` mostrou só o
serviço `legislativo` rodando (`sync-camara` não subiu, confirma que
`profiles` funcionou) e, pela primeira vez, **`(healthy)` de verdade**
(não mais preso em `unhealthy`) depois de ~30s. `setup_roles` rodado
manualmente pra aplicar a permissão nova de excluir comentário ao grupo
"Administrador FNP" (16 permissões, era 15). `curl` confirmando `200 OK`.

### Edição de foto de perfil vira lápis no hover (2026-08-13)

A pedido do usuário, a partir de uma captura de tela da tela "Meu perfil":
o campo de foto era o `<input type="file">` cru do Django
(`ClearableFileInput`), com o botão nativo "Escolher arquivo" grande do
lado do avatar. Substituído por um lápis pequeno que só aparece no hover/
foco sobre o avatar (`.perfil-avatar-edit-btn`, posicionado no canto do
círculo) — ao clicar, abre um menu (`<details>`, mesmo padrão sem-JS-
próprio do `tema-dropdown`) com "Abrir câmera", "Importar arquivo" e
"Remover foto" (esse último só aparece se já existe `Perfil.foto`).

O widget nativo do Django continua existindo no DOM (`display: none`,
`.perfil-avatar-widget-hidden`) — é ele quem de fato recebe o arquivo e
processa o "Limpar" no submit; o menu novo só aciona esse input via JS
(`initPerfilAvatarEdit` em `main.js`). "Remover foto" marca o checkbox
`foto-clear_id` que o `ClearableFileInput` já gera. Preview atualiza na
hora (`URL.createObjectURL`, sem esperar o submit) — se ainda não havia
foto (mostrando só a inicial), o `<span>` fallback é substituído por um
`<img>` novo no DOM.

**Correção no mesmo dia, depois do usuário testar de verdade** — 2
bugs reais: (1) o menu (`<details>`) só fechava clicando de novo no
lápis, nunca clicando fora — fix: `document.addEventListener('click', ...)`
fechando se o clique for fora do menu, mesmo padrão já usado no
`tema-dropdown`. (2) "Abrir câmera" não abria câmera nenhuma no desktop
— a primeira versão setava `capture="user"` no `<input type="file">`
antes do `.click()`, mas esse atributo só é respeitado por navegador
mobile; desktop ignora e cai no seletor de arquivo comum (foi
exatamente o que o usuário viu ao testar no Chrome/Windows). Fix de
verdade: modal novo (`#avatar-camera-modal`) com `<video>` ao vivo via
`getUserMedia({video: {facingMode: 'user'}})`, botão "Capturar foto"
desenha o frame atual num `<canvas>` (desespelhado — o `<video>` só é
espelhado visualmente via CSS `transform: scaleX(-1)`, efeito "selfie"),
converte pra `Blob`/`File` via `canvas.toBlob()` e injeta no
`fileInput.files` via `DataTransfer`, reaproveitando a mesma função de
preview. Erro de permissão/sem câmera mostra mensagem no próprio modal
em vez de falhar silencioso. Funciona igual em desktop e mobile agora
(não depende mais de comportamento específico de plataforma).

`check` e 78 testes limpos (nenhum teste novo — tudo client-side, sem
lógica de servidor nova). **Ainda não confirmado pelo usuário** — os
dois bugs foram vistos no Chrome/Windows antes da correção; falta
testar de novo depois do fix (câmera de verdade abrindo, menu fechando
ao clicar fora) antes de promover pra produção.

### Auditoria de UX mobile completa (2026-08-13)

A pedido do usuário ("a versão mobile precisa ficar impecável, é o modo
principal do produto"), auditoria em 3 fases seguindo um roteiro rígido
do usuário: nada de "presumir que ficou bom" — só testado de verdade,
com emulação de dispositivo real (Playwright + Chromium headless
instalado no `.venv` pra isso) em 4 larguras (360/390/414/768px),
screenshot + medição programática (scroll, tap target, font-size) como
evidência, publicado como Artifact.

**Fase 1 (diagnóstico)**: 20 itens checados (A-G do roteiro do usuário).
5 ✅, 7 ⚠️, **3 ❌ QUEBRADO reais**: (1) scroll horizontal na topbar
autenticada + no dropdown de "Tema" estourando a borda da tela; (2) a
sidebar do site **não colapsa em hambúrguer** — renderiza como painel
largo cobrindo/empurrando o conteúdo em todos os 4 breakpoints, sem
jeito de fechar (bug real, não só falta de responsividade — havia uma
tentativa incompleta de virar gaveta, mas o estado padrão sem
`localStorage` nascia "aberto", cobrindo o próprio botão hambúrguer que
deveria fechá-la); (3) **o lápis de editar foto de perfil construído
horas antes nesta mesma sessão** tem `opacity: 0` por padrão, só visível
no `:hover` — inexistente em touchscreen, achado por medição direta
(`getComputedStyle().opacity === "0"` sem hover).

**Fase 2 (correção, depois de aprovação do usuário)**: todos os 15 itens
não-✅ corrigidos.
- Sidebar: dois estados agora separados — `sidebar-collapsed` (desktop,
  preferência salva) e `sidebar-mobile-open` (mobile, sempre começa
  fechado) — antes compartilhavam a mesma flag. Fundo escurecido
  clicável + botão de fechar novos.
- Topbar: `.app-topbar-title` ganhou `min-width: 0` + truncamento
  (`text-overflow: ellipsis`) — sem isso, um item flex com `flex: 1`
  nunca encolhe abaixo do próprio conteúdo, empurrando a topbar inteira
  pra fora do viewport em breadcrumb comprido.
- Dropdown de "Tema": ancorado por `right: 0` em vez de `left: 0` no
  variante flutuante (o único alinhado à direita) — achado só
  interagindo de verdade, não aparecia na medição estática.
- Lápis do avatar: `@media (hover: hover)` escopa o "esconde até
  hover" só pra quem tem mouse de verdade; toque sempre mostra. Área de
  toque foi de 20×20px pra 44×44px reais (círculo visível continua
  pequeno, via `::before`).
- Tap targets (`.sidebar-link`, `.tema-option`, `.favorito-btn`,
  ícones/botão de logout do Admin) — 44px mínimo, só na faixa mobile.
- **Achado no meio da correção**: a primeira tentativa de consertar o
  font-size dos inputs (`.auth-form input[type=...]`, 15.2px→16px) não
  teve efeito nenhum na medição — existia uma segunda regra mais
  específica (`.auth-card form input:not(...)`) vencendo a cascata de
  verdade em cadastro/login/perfil. Só apareceu reconferindo com
  `document.styleSheets` depois que o "fix" inicial não mudou nada —
  exatamente o tipo de coisa que só se pega testando, não só editando.
  `telefone` também virou `type="tel"` (cadastro e perfil).
- Campo de busca sobe pro topo da tela ao focar em mobile
  (`scrollIntoView`), pra sugestões não nascerem abaixo da dobra.
- `Perfil.save()` agora redimensiona a foto (Pillow, máx. 512px de
  lado) antes de gravar — não tinha nenhum resize server-side antes,
  só validação de tamanho de arquivo.
- `.field-label` subiu de 12px pra 13.1px (badges/meta-texto de card
  deixados de propósito, risco de quebrar o desenho visual sem terem
  sido pedidos).

**Fase 3 (checklist final)**: reconferido nos mesmos 4 breakpoints —
17 de 20 ✅. Seguem "não testável aqui", precisam de dispositivo físico
antes do lançamento: teclado virtual cobrindo campo (emulador não
simula o resize de viewport do teclado real do iOS/Android), rodapé
(não rolado até o fim, home tem 30.000+px de altura), contraste de cor
dos badges (não medido com ferramenta própria), SSE se recuperando de
troca de rede, tempo de carga em 4G real (a medição da Fase 1 não tinha
throttling nenhum, metodologia inválida, não refeita). Recomendado
testar em Safari iOS real e Chrome Android real antes do lançamento
(comportamento de teclado/viewport do WebKit é notoriamente diferente).

`check`, `makemigrations --check`, `ruff --select F401,F811,F841` e 78
testes limpos a cada rodada. Relatórios completos (com screenshot de
cada achado, antes/depois) publicados como Artifact — ver histórico da
conversa pros links. **Só em `next`, não promovido** — servidor de dev
local usado pros testes já foi parado, dados de teste (`mobiletest`)
limpos.

### Dois bugs de produção real (topbar sumindo, overflow no fórum) — 2026-08-13, mesmo dia

Usuário reportou por captura de tela do celular, **de produção real**
(não `next`), dois problemas que sobraram depois da auditoria acima —
tratados como prioridade máxima ("90% do uso é mobile"), mesma regra de
sempre: nada de presumir corrigido, teste em breakpoint real (360-414px)
com Playwright + screenshot antes/depois.

- **Causa raiz do "os ícones somem em outras páginas"**: `templates/
  allauth/layouts/base.html` (login, cadastro, alterar senha, 2FA,
  confirmação de login social) tinha uma **cópia hardcoded** do
  cabeçalho público, sem nenhum `{% if user.is_authenticated %}` —
  qualquer pessoa logada que caísse numa tela allauth via "Entrar" em
  vez da topbar de verdade (busca/avatar/sino/Aa/tema/ajuda/sair), daí a
  percepção de "alguns botões somem". Fix: `templates/_header.html`
  novo, único ponto de renderização do cabeçalho (decide entre
  `_topbar.html` autenticado ou o header público), incluído tanto por
  `base.html` quanto por `allauth/layouts/base.html` — nunca mais duas
  cópias divergentes. **Bug no caminho, achado só depois de screenshotar
  a página de novo**: o comentário multi-linha `{# ... #}` desse arquivo
  novo aparecia **literal na tela**, como texto visível — Django só
  remove `{# #}` se for de uma linha só; comentário de várias linhas
  precisa de `{% comment %}...{% endcomment %}`. Trocado, confirmado via
  `curl` que o HTML não contém mais o texto do comentário.
- **Reorganização da topbar mobile** (parte visual do mesmo problema,
  reportada como "dois grupos soltos de ícone"): com 6-7 controles
  sempre visíveis (busca, avatar, sino, Aa, tema, ajuda, sair) sobrando
  só uma coluna estreita ao lado do título, a topbar quebrava em ~1-2
  ícones por linha. `.app-topbar` ganhou `flex-wrap`, com título e
  `.app-topbar-actions` cada um em `flex-basis: 100%` — 3 linhas
  próprias (marca+Voltar, título, ações) em vez de tudo competindo pela
  mesma linha; a linha de ações cheia agora cabe 5-6 ícones por fileira
  em 360-414px, não mais 1-2.
- **Overflow horizontal real na página de detalhe** (a causa mais
  provável do "card Resumo parecendo sobrepor" reportado, embora não
  reproduzido visualmente — ver abaixo): `.detail-panel-main`,
  `.detail-sidebar` e `.panel-block` são `display: grid` sem
  `min-width: 0` — item de grid nunca encolhe abaixo do próprio
  conteúdo por padrão, empurrando ~66px de página pra fora do viewport
  em mobile sem cortar nada visivelmente, só forçando scroll horizontal
  (mesmo padrão de bug já corrigido na topbar na auditoria anterior).
  **Segundo achado, mais fundo**: mesmo depois desse fix, sobrava
  overflow variável por largura (38px em 360px, 8px em 390px) — rastreado
  até `.comments-nested` (lista de respostas aninhadas do fórum,
  também `display: grid`) sem `min-width:0` no `<li class="comment-card">`
  dentro dela; cada nível de resposta empurrava o comentário pra fora.
  Truque de depuração: script Playwright percorrendo todo `body *`
  medindo `getBoundingClientRect().right > viewport`, ordenado pelo mais
  saliente — achou o elemento exato em vez de adivinhar por inspeção
  visual. Também corrigido no caminho: `.comment-author` (nome+data) e
  `.comment-actions-row` (curtir/responder/denunciar/excluir) sem
  `flex-wrap`, quebrando a página quando nome de autor comprido +
  timestamp não cabiam na mesma linha.
- **"Card Resumo sobrepondo" não reproduzido em Chromium** mesmo depois
  dos fixes acima — screenshot de página inteira em 390px mostra os
  cards (Resumo, Casa/Status, Próximos eventos, Interlocutores, Última
  movimentação, Mérito, Fórum) empilhados limpos, sem sobreposição, sem
  corte de texto. Hipótese mais provável (não confirmada): o overflow
  horizontal real corrigido acima causava esse efeito visual em Safari
  iOS/Chrome Android de verdade durante rolagem elástica, mas não em
  Chromium headless — vale o usuário reconferir no celular real depois
  desse deploy antes de fechar como resolvido.
- **Achados extras da regressão** (checklist "scroll horizontal + tap
  target 44px" da auditoria anterior, revalidado): botão de fechar a
  gaveta da sidebar (`.app-sidebar-close`, 40×40) e os botões "Abrir
  câmera"/"Importar arquivo" do menu de foto de perfil (31px de altura)
  abaixo do mínimo de 44px — só na faixa mobile, corrigidos junto.

Regressão completa revalidada via Playwright: **13 páginas × 3
breakpoints (360/390/414) = 39 checagens de scroll horizontal, todas
limpas**; página de detalhe e perfil também checadas em 768px. `check`,
`makemigrations --check`, `ruff --select F401,F811,F841` e 78 testes
limpos. Confirmado por grep que só 2 templates no projeto todo têm tag
`<html>` própria (`base.html` e `allauth/layouts/base.html`) e ambos
passam por `_header.html` agora — não sobrou nenhuma página com cabeçalho
duplicado. Commitado e enviado só pra `next` (`d09e20a`) — **não
promovido pra produção**, autorização à parte como sempre.

### Comentários do fórum reorganizados no mobile, estilo Facebook (2026-08-13, mesmo dia)

Usuário reportou por captura de tela real (celular, comentário de
resposta "Carlos Pereira") a data cortando na borda da tela e o texto
quebrando palavra por palavra numa coluna estreitíssima — pediu pra usar
a estrutura de comentário do Facebook (balão com nome+texto, barra de
metadados/ações embaixo) como referência.

- **`templates/legislativo/_comentario.html` reestruturado**: nome+texto
  agora ficam dentro de um `.comment-bubble` (balão cinza-claro
  arredondado); `.comment-time` saiu de dentro do cabeçalho do nome e
  foi pra dentro de `.comment-actions-row`, junto com curtir/Responder/
  Denunciar/Excluir — bate com o padrão do Facebook ("Nome + texto" num
  bloco, "2 sem · Curtir · Responder" embaixo). Resposta aninhada
  (`{% include ... with extra_class='comment-reply' %}`) ganhou classe
  própria pra estilo diferenciado.
- **Achado real via medição, não só inspeção visual**: um script
  Playwright percorrendo a cadeia de elementos-pai do balão mediu que a
  resposta aninhada tinha só **105px de largura útil** pra texto num
  celular de 375px — soma de paddings empilhados (página → `.detail-
  panel` 2rem cada lado → `.panel-block` 1.5rem → cartão do comentário
  pai → indentação de `.comments-nested` → cartão do próprio comentário
  aninhado, cada um com seu padding/avatar/gap). O maior consumidor
  isolado era `.detail-panel` (32px cada lado, sozinho mais que todo o
  resto somado) — não tinha nenhum ajuste de mobile antes.
- **Fix em 3 partes**: (1) resposta aninhada (`.comment-card.comment-
  reply`) perdeu o próprio cartão (padding/fundo/borda) — só o balão
  carrega o visual agora, igual ao Facebook, que nunca aninha caixa
  dentro de caixa; avatar da resposta também menor (1.7rem vs 2.1rem).
  (2) `.detail-panel` ganhou `padding: 1.25rem` no mobile (era 2rem
  sempre). (3) `.panel-block` ganhou `padding: 1rem` no mobile (era
  1.5rem sempre) e `.comments-nested`/`.comment-card` ganharam
  indentação/padding mais enxutos só na faixa mobile. Resultado: de
  105px pra 171px de largura útil no balão da resposta (375px) — texto
  volta a quebrar por palavra completa, não por caractere.
- Testado visualmente (screenshot, não só medição) em 360/375/390/414px
  anônimo e autenticado (com curtir/Denunciar/Excluir visíveis), mais
  768px — barra de ações quebra em 2 linhas de forma limpa quando
  necessário, sem overflow em nenhum caso.

`check`, `makemigrations --check`, `ruff --select F401,F811,F841` e 78
testes limpos; as mesmas 39 checagens de scroll horizontal (13 páginas ×
3 breakpoints) revalidadas sem regressão. Commitado e enviado só pra
`next` (`66bf0e0`) — não promovido.

### Cabeçalho público (anônimo) sem Voltar/Início no mobile (2026-08-13, mesmo dia)

Usuário testou localmente (não produção) e circulou, numa captura de
tela, o espaço vazio ao lado da logo perguntando "aonde foram parar os
botões de voltar e home" — achado real, não regressão de hoje: o
cabeçalho público (usuário anônimo, sem login) **nunca teve** esse
padrão. A logo sempre abriu o site institucional externo
(`fnp.org.br`, não o painel), e o único link interno que sobrava
("Painel Legislativo da FNP", `.brand-text`) some por `display:none`
em telas ≤560px — sem sobrar nenhum jeito de navegar de volta ao
início a partir de uma página interna sem estar logado.

Fix: `templates/_header.html` (ramo anônimo) ganhou o mesmo padrão
Voltar/Início que `_topbar.html` (autenticado) já usa — "Voltar" fora
da home, "Início" na home só quando há filtro ativo na URL (mesmas
duas condições, mesmas classes CSS `.topbar-back-link` reaproveitadas,
sem duplicar estilo). Agrupado com a logo dentro de um `.header-left`
novo (antes `.header-inner` só tinha 2 filhos em `space-between` —
logo e "Entrar" — inserir um terceiro no meio quebraria esse layout).

Testado em 360/390px, home limpa (sem filtro, corretamente sem
Voltar/Início — não faz sentido voltar pra onde já se está),
home com filtro (mostra "Início") e página de detalhe (mostra
"Voltar") — screenshot confirmando visualmente ao lado da logo, exato
ponto que o usuário circulou. `check`, `makemigrations --check`,
`ruff --select F401,F811,F841` e 78 testes limpos; as mesmas 39
checagens de scroll horizontal revalidadas sem regressão. Commitado e
enviado só pra `next` (`d0114e3`) — não promovido.

### Promoção completa `next` → `main` → produção → droplet (2026-08-13, fim da sessão)

A pedido explícito do usuário ("vamos subir todas as alterações até o
momento tanto na next quanto na main (produção) e no droplet também"),
promovido tudo que foi feito nesta sessão de uma vez: `check`,
`makemigrations --check`, 78 testes e `ruff` revalidados antes do push;
`main` local (`3dc6812`) estava 13 commits atrás de `next` (`dd3390a`)
e era fast-forward puro, sem divergência — levou a topbar sumindo em
páginas allauth (`_header.html` unificado), o overflow horizontal no
fórum/página de detalhe, os comentários reorganizados estilo Facebook,
o Voltar/Início adicionado ao cabeçalho público, mais o redesenho do
cabeçalho público e toda a auditoria de UX mobile de 3 fases anterior
no mesmo dia. Push pra `origin` e `production`; CI verde nos dois
repositórios (`gh run watch`).

Deploy real no droplet via SSH conduzido pelo usuário: `git pull origin
main` trouxe o fast-forward (`3dc6812..dd3390a`), `docker compose build`
reconstruiu a camada `COPY . .` com código novo de verdade (não veio do
cache, diferente do incidente de 2026-08-07), `docker compose up -d`
subiu sem erro. Log confirmou "No migrations to apply" (bate com o
`makemigrations --check` limpo local — nenhuma migration nesta leva),
138 estáticos coletados (3 novos, resto sem mudança), Gunicorn sem
traceback. `docker compose ps` mostrou só o serviço `legislativo`
rodando (`sync-camara` continua desativado por `profiles`, como
esperado). `curl -sI https://legislativo.fnp.org.br/` → `200 OK` com
todos os cabeçalhos de segurança esperados (CSP com `form-action`
incluindo o Google, HSTS, `X-Frame-Options: DENY`, cookie `Secure`) —
essa checagem via Nginx real já confirma o site funcionando de ponta a
ponta, independente do rótulo interno `(health: starting)` do Docker
ainda não ter virado `(healthy)` no momento da checagem (só uma questão
de tempo, não bloqueia nada).

### Cabeçalho mobile redesenhado (1 linha) + busca sempre visível + 2 bugs de sidebar recolhida (2026-08-13, já em produção)

A pedido do usuário, já testando em produção real (`legislativo.fnp.org.br`,
DevTools em modo device), a partir de um mockup anotado à mão: o
cabeçalho autenticado no mobile virou **uma linha só** (logo + título +
Aa + tema + ajuda + notificações + perfil + Sair, nessa ordem exata,
conferida item a item depois de uma correção — a primeira tentativa
tinha colocado avatar/sino logo depois do título, usuário corrigiu:
"o ícone do perfil tem que vir logo à esquerda [do Sair], à esquerda
do perfil vêm as notificações"), e o botão "Buscar..." que abria o
modal Ctrl+K virou um **campo de busca de verdade, sempre visível**,
numa segunda linha ocupando a largura toda — mesmo raciocínio de
"duplicidade de função" que já tinha tirado a busca solta do meio da
home em mobile (`.search-panel`, escondida por completo no mobile
agora, meses depois de criada).

**Trade-off assumido de propósito**: pra caber logo + título + 6
controles numa linha de 360-414px, os ícones ficaram menores que o
padrão de 44px (WCAG) estabelecido na auditoria de mobile mais cedo no
mesmo dia — em torno de 32px agora, só nessa linha específica do
cabeçalho. Sinalizado ao usuário no chat, não é um retrocesso
silencioso.

**Implementação técnica**: sem alterar nenhuma marcação existente,
`.app-topbar-actions` vira `display:contents` no mobile (seus filhos
passam a participar do `flex-wrap` do `.app-topbar` direto, em vez de
ficarem presos numa segunda linha própria) e cada ícone recebe `order`
explícito; um `::after` com `flex-basis:100%` força a quebra de linha
antes do campo de busca novo, sem precisar de um `<div>` extra só pra
isso. Zero mudança fora do media query mobile — desktop conferido
pixel a pixel sem diferença.

**Dois bugs reais achados no caminho** (usuário reportou por captura
de tela comparando "antes"/"depois" da gaveta do menu mobile):

- **Rótulos de texto sumiam na gaveta mobile** sempre que
  `fnp-sidebar-collapsed=1` tinha ficado salvo no `localStorage` de uma
  sessão anterior em tela larga no mesmo aparelho (ex.: navegador
  redimensionado) — a auditoria de mobile de mais cedo no mesmo dia já
  tinha corrigido a LARGURA da gaveta pra esse caso específico
  (`.sidebar-collapsed.sidebar-mobile-open .app-sidebar`), mas não a
  regra que esconde `.sidebar-link span`/`.sidebar-section-label`
  (`.sidebar-collapsed .sidebar-link span { display:none }`), que
  continuava valendo por cima. Fix: mesma técnica de especificidade (3
  classes) pra vencer a regra de 2 classes do modo "recolhido" do
  desktop, dessa vez sobre os rótulos.
- **Logo cortado no meio ao recolher a sidebar no desktop** —
  `logo-FNP.png` é um lockup só (marca "FNP" + "Frente Nacional..." por
  extenso embutidos na mesma imagem, 187×69px, sem versão separada só
  do ícone); com `height:2rem; width:auto`, a imagem inteira não cabe
  na largura da sidebar recolhida (4.75rem), cortando o texto no meio
  sem terminar em lugar nenhum limpo. Fix: `object-fit:cover` +
  `object-position:left` recorta só os primeiros ~78px da imagem
  original (a marca "FNP" + as 3 bolinhas de cor), medido testando
  larguras de corte via Pillow até achar o ponto exato onde a marca
  termina sem invadir o texto. **Mesmo bug vazava pra gaveta mobile**
  quando o `fnp-sidebar-collapsed=1` também estava presente (a gaveta é
  sempre largura cheia, não devia herdar o recorte do modo desktop) —
  corrigido com a mesma técnica de especificidade das duas correções
  acima.

`check`, `makemigrations --check`, `ruff --select F401,F811,F841` e 78
testes limpos; as mesmas 39 checagens de scroll horizontal revalidadas
sem regressão; testado também o envio de fato do campo de busca novo
(`?q=` chegando certo na home). Commitado e enviado pra `next`
(`442003d`).

### Segunda promoção `next` → `main` → produção → droplet, fim da sessão (2026-08-13)

A pedido explícito do usuário ("Aplique na next, produção e droplet e
em seguida por hoje é só"), `check`/`makemigrations --check`/78
testes/`ruff` revalidados, `main` local (`dd3390a`) era fast-forward
puro com `next` (`2153484`, 2 commits) — levou o redesenho do
cabeçalho mobile em 1 linha, a busca sempre visível, e os 2 fixes de
sidebar recolhida (rótulos sumindo na gaveta, logo cortado no
desktop). Push pra `origin` e `production`; CI verde nos dois.

Deploy no droplet via SSH: `git pull origin main` trouxe o
fast-forward (`dd3390a..2153484`), build sem cache stale, container
subiu. **Primeira checagem de `curl` bateu `502 Bad Gateway`** — não
era erro de verdade, só o container tinha 4 segundos de vida
(`docker compose ps` mostrava "Up 4 seconds", log ainda nem tinha
chegado na linha "Starting gunicorn") quando o `curl` rodou logo em
seguida no mesmo comando colado. Pedido pro usuário esperar ~15-20s e
rodar de novo: `docker compose ps` → `(healthy)`, log completo com
Gunicorn de pé e os 3 workers, `curl` → `200 OK` com todos os
cabeçalhos de segurança. **Lição registrada**: depois de um
`docker compose up -d`, dar uma pausa curta antes do `curl` de
confirmação, ou não estranhar um 502 no primeiro segundo — é o
healthcheck ainda "starting", não uma falha real.

Com isso, **tudo que estava pendente de promoção nesta sessão já está
em produção** — não sobrou nenhum item "só em `next`" da lista de
fixes de hoje.

### Verificação visual pendente de duas rodadas antigas (2026-08-14)

A pedido do usuário ("vamos voltar para as pendências do projeto"),
fechada uma pendência que vinha se arrastando desde 2026-08-07/08-10:
tanto a "rodada de 23 pedidos" quanto os "5 ajustes finos" do Admin
tinham sido validados só por teste de servidor (`Client`/`RequestFactory`),
nunca conferidos de fato renderizados num navegador. Usando Playwright
contra o servidor de dev local, checado item a item:

**Rodada de 23 pedidos (2026-08-10)** — todos confirmados funcionando:
`.detail-grid` com `align-items: start` (Resumo não deforma mais),
resposta aninhada do fórum renderiza de verdade, formulário de
"Enviar Participação" não aparece mais no fórum (o "achado" inicial do
script de teste foi falso positivo — bateu no formulário de comentário,
que reaproveita a classe CSS `.participation-form` por herança visual,
não o formulário de participação de fato), botão/contagem de curtir
presente, card de estatística é um `<a>` clicável de verdade, filtro
ativo mostra "Limpar filtro ×" e consolida a seção (`Urgentes (17)` no
teste), API de preview de busca responde 200, pilha de navegação
"Voltar" no `sessionStorage` funciona (testado navegando A→B→C e
confirmando que "Voltar" sai da página C de verdade), campo de e-mail
editável no perfil, `/participacoes/` carrega mostrando só as próprias
(estado vazio correto pro usuário de teste sem comentários), página de
perfil público de usuário carrega a partir do link do fórum,
`/conta/solicitar-exclusao/` mostra sidebar + ícone de alerta + lista
de consequências + botão Cancelar ao lado do de confirmar, troca de
senha pede senha atual pra conta com senha local. Testado também à
parte, direto via `shell` (mais confiável que clicar no widget
JS do Admin): entrar no grupo "Administrador FNP" seta `is_staff=True`
automaticamente (`sincronizar_staff_por_grupo`); sair do grupo
mantém `is_staff=True` (comportamento intencional — o sinal só reage a
`post_add`, nunca rebaixa sozinho, confirmado lendo `signals.py`, não é
bug). `initPreventDoubleSubmit` (proteção contra notificação
duplicada) confirmado presente e correto em `main.js`.

**5 ajustes finos do Admin (2026-08-07)** — todos confirmados: `#branding`
é `flex` (casinha ao lado do título), título do Admin e "Painel Geral"
do site têm exatamente o mesmo `font-size` (17.6px = 1.1rem), botão de
Ajuda do Admin sem borda/fundo nativo do navegador, avatar mantém
`border-radius: 999px` mesmo com foco de teclado (não vira retângulo),
botão "voltar ao topo" aparece ao rolar além de 500px, fonte da sidebar
do site público em 14.4px (0.9rem). **Achado no caminho**: minha
primeira tentativa de medir a largura dos modais de tour/ajuda deu
"1400px" (falso alarme) — o seletor tinha pego o *backdrop* (que cobre
a tela toda), não o painel interno (`.tour-modal-panel`/
`.help-modal-panel`); corrigindo o seletor, os dois batem exatamente
com o que foi documentado (`460px`/`540px`).

Nenhuma mudança de código nesta sessão — só verificação. Servidor de
dev local parado e usuários de teste (`mobiletest`, `verifytest`)
removidos ao final.

### Promoção `next` → `main` → produção → droplet (2026-08-14)

A pedido do usuário ("vamos subir tudo que fizemos até agora pra a
next e para a produção e droplet"), `check`/`makemigrations --check`/78
testes/`ruff` revalidados antes do push; `main` local (`2153484`) era
fast-forward puro com `next` (`bb62fa7`, 1 commit — só o registro da
verificação visual acima, sem mudança de código). Push pra `origin` e
`production`; CI verde nos dois. Deploy no droplet via SSH sem
migration nesta leva; `docker compose ps` → `(healthy)`, `curl -sI
https://legislativo.fnp.org.br/` → `200 OK` com todos os cabeçalhos de
segurança esperados.

### Fixes de UX na home e e-mail de aviso pra cadastro pendente (2026-08-14, mesma sessão)

Dois pedidos do usuário, ambos com achados reais no caminho:

- **Card de estatística selecionado zerava os outros** — clicar em
  "Na pauta" (ou qualquer card) navegava pra `?filtro=pauta`, e os 5
  números do topo eram recalculados em cima do próprio conjunto já
  filtrado — com poucos/nenhum resultado em "na pauta", os outros
  cards (Urgentes/Alta prioridade/Com relator) também apareciam
  zerados, mesmo tendo proposições reais. Contagem dos cards agora
  reflete busca/tema (facetas de contexto), nunca o próprio filtro de
  card selecionado — fix aplicado nos 3 lugares que calculavam isso
  (`HomeView`, `api_proposicoes_cards` e o stream SSE, que sozinho já
  sobrescrevia o primeiro render correto com os números errados assim
  que conectava). **Regressão pega no caminho**: o próprio fix quebrou
  o título da seção ("Na pauta (N)"), que usava a mesma variável —
  trocado por `page_obj.paginator.count`, a contagem real do filtro
  ativo.
- **Limpar a busca não resetava os cards** — corrigido em duas
  rodadas. Primeiro fix (só cobria quem digita ao vivo sem nunca
  submeter): campo vazio dispara um preview via fetch com `q=` vazio,
  que a view já trata como "sem filtro". Usuário testou e reportou que
  ainda não funcionava numa página vinda de busca *submetida* (`?q=`
  de verdade, ex. apertando "Buscar") — nesse estado,
  Urgentes/Áreas de interesse/Em alta/Últimos acessados nem existem no
  DOM (`{% if not filtro_ativo %}` no template) e o título "Busca por
  X (N)" é texto estático; só trocar o conteúdo de `#cards-todas` via
  AJAX não bastava. Fix definitivo: se a página carregou com filtro de
  verdade (existe `.filtro-limpar-link` no DOM), limpar o campo navega
  pro próprio link "Limpar filtro" — reconstrução completa via SSR, sem
  duplicar lógica de montagem de seção em JS (mesmo princípio das
  Diretrizes de Engenharia). Quem só digita sem nunca submeter continua
  com o reset instantâneo via fetch, sem reload.
- **E-mail de aviso de cadastro pendente** (pedido novo, não um bug) —
  sempre que um cadastro nasce `Perfil.status_aprovacao='pendente'`
  (`criar_perfil` em `apps/usuarios/signals.py`), agora manda e-mail
  pra `ronan.castro@fnp.org.br` e `nucleo.dados@fnp.org.br` (lista em
  `CADASTRO_PENDENTE_NOTIFICACAO_EMAILS`, configurável via env sem
  precisar de deploy) com link direto pra tela de aprovação no Admin.
  `fail_silently=True` de propósito — SMTP fora do ar (ou
  `EMAIL_BACKEND` de produção ainda sem configuração real, ver
  Pendências) nunca pode derrubar o cadastro em si, mesmo bug já
  corrigido antes com o e-mail de confirmação do allauth. Também
  adicionado `DEFAULT_FROM_EMAIL` (não existia, caía no
  `webmaster@localhost` padrão do Django) e `SITE_URL` (derivado de
  `ALLOWED_HOSTS`, mesmo raciocínio do `CSRF_TRUSTED_ORIGINS`, pra
  montar o link absoluto no corpo do e-mail).

`check`, `makemigrations --check`, `ruff --select F401,F811,F841` e 80
testes (era 78, +2 novos cobrindo o e-mail de cadastro pendente e a
ausência dele pra cadastro de staff) limpos — 1 teste pré-existente
(`DefinirSenhaSocialTest`) precisou de ajuste, já contava e-mails
enviados e passou a contar também o aviso novo disparado na criação do
usuário de teste. Testado de ponta a ponta via `manage.py shell` com o
console backend de verdade: assunto/remetente/destinatários/corpo/link
todos corretos. **Nota importante pro usuário**: em produção isso só
entrega de verdade quando `EMAIL_BACKEND` estiver configurado com um
provedor real (SMTP/SES/etc.) — mesma pendência já registrada mais
abaixo; até lá, o e-mail é "enviado" mas não chega em lugar nenhum.

### Rodapé: remove "Solicitar exclusão" duplicado, centraliza "Siga-nos" (2026-08-14, mesma sessão)

Dois ajustes de UX a pedido do usuário, a partir de captura de tela
real: "Solicitar exclusão" no rodapé da home era duplicado (já existe
na sidebar do perfil, Privacidade → Excluir conta) — removido do
rodapé, confirmado que continua acessível pela sidebar. "Siga-nos" e a
fileira de ícones de redes sociais só ficavam alinhados à esquerda
entre si (`justify-items: start`), sem centralizar um em relação ao
outro — trocado pra `justify-items: center`. `check`/80 testes/`ruff`
limpos; 39 checagens de scroll horizontal sem regressão.

### Promoção `next` → `main` → produção → droplet (2026-08-14, fim da sessão)

A pedido do usuário, `check`/`makemigrations --check`/80 testes/`ruff`
revalidados antes do push; `main` local (`bb62fa7`) era fast-forward
puro com `next` (`3dc4c6e`, 6 commits — os fixes de UX da home
descritos acima, o e-mail de aviso de cadastro pendente e os ajustes
do rodapé). Push pra `origin` e `production`; CI verde nos dois. Deploy
no droplet via SSH sem migration nesta leva; `docker compose ps` →
`(healthy)`, `curl -sI https://legislativo.fnp.org.br/` → `200 OK` com
todos os cabeçalhos de segurança esperados. As novas settings de
e-mail (`DEFAULT_FROM_EMAIL`, `CADASTRO_PENDENTE_NOTIFICACAO_EMAILS`,
`SITE_URL`) subiram com os valores padrão embutidos no código, sem
precisar mexer no `.env` do servidor.

### Logo recolhido cortando o "P" + segunda promoção (2026-08-14, mesma sessão)

Usuário reportou em produção (depois testado e reproduzido também em
`next` local) que o logo da sidebar recolhida continuava cortado
mesmo depois do fix anterior (`442003d`) — inicialmente suspeitei de
cache do navegador (confirmei que o CSS certo já estava no servidor
via `curl`), mas o usuário confirmou hard refresh sem mudança. Causa
real: a largura usada no fix anterior (2.25rem, recorte de ~78px da
imagem original) estava **matematicamente errada** — só ficava visível
tirando um screenshot em alta resolução focado só no ícone (no
tamanho normal renderizado, ~36px, o defeito é pequeno demais pra
notar a olho nu). O recorte cortava bem no meio da curva/bojo do "P",
sobrando só o traço vertical. Testado com Pillow em várias larguras
(85 a 110px): o "P" só fecha completo a partir de ~90px, e o texto
"FRENTE..." começa a vazar a partir de ~96-100px. Trocado pra 2.67rem
(recorte de 92px, no meio do intervalo seguro). `check`/80 testes/
`ruff` limpos; confirmado sem overflow na sidebar recolhida (logo
termina em 59px de 76px disponíveis).

Promovido `next` (`6f3c493`) → `main` → produção → droplet na
sequência, sem migration; CI verde nos dois repositórios; `docker
compose ps` → `(healthy)`, `curl` → `200 OK`.

### 6 funcionalidades novas: anexos, mídia no fórum, notícias, impressão, compartilhar, classe de usuário (2026-08-18/19)

A pedido do usuário, 6 pedidos numerados de uma vez (a partir de duas
capturas de tela — card de detalhe em produção, e uma tela do app
legado usada só como referência de estilo pra seção de notícias).
Trabalho planejado antes de mexer em código (`EnterPlanMode`, dado o
volume — 3 apps tocados, 3 migrations novas) e implementado em 6
commits sequenciais e testáveis, ordem do mais contido ao mais amplo:

- **Classe de usuário** (`Perfil.classe_usuario`, migration
  `usuarios.0007`) — Equipe FNP/Prefeito/Indicado da prefeitura/
  Parlamentar. Autodeclarado no cadastro público, mas **sem "Equipe
  FNP" nas opções do formulário de signup** (equipe interna é
  promovida via grupo do Admin, não autodeclarada); editável depois em
  `/perfil/` com as 4 opções. `UsuarioAdmin` ganhou filtro e coluna por
  classe (`perfil__classe_usuario`, mesmo padrão já usado por
  `status_aprovacao`) — uso principal é dar atenção diferenciada por
  tipo de usuário no Admin.
- **Notícias relacionadas** (novo `panel-block` em
  `proposicao_detail.html`, entre Última movimentação e Mérito) —
  reaproveita o model `Noticia` (já existia, já tinha inline no Admin,
  nunca teve template). Badge de fonte derivado do domínio da URL via
  filtro novo `apps.legislativo.templatetags.legislativo_extras.dominio`,
  sem campo novo no banco.
- **Anexos de documentos/ementas** (`AnexoProposicao`, novo, migration
  `proposicoes.0004`) — PDF/Word/Excel/imagem até 10MB, validado por
  extensão (`FileExtensionValidator`) e tamanho. Qualquer usuário
  aprovado envia; autor do próprio envio ou staff excluem (mesmo
  modelo de `excluir_comentario`). Inline no Admin da proposição +
  registro próprio; `Administrador FNP` ganhou permissão via
  `setup_roles.py`.
- **Foto/vídeo nos comentários do fórum** (`Comentario.midia`, novo,
  migration `comentarios.0008`) — imagem até 8MB ou vídeo até 25MB,
  1 arquivo opcional por comentário, sem moderação de conteúdo além da
  que já existe pro texto. **Pendência de infra**: o Nginx do droplet
  tem `client_max_body_size 6M` hoje — vídeo só funciona em produção
  depois de aumentar esse limite lá (mesmo procedimento já usado
  quando o upload de foto de perfil foi liberado), ver Pendências.
- **Botão de impressão** — o item que mais mudou de forma na sessão,
  2 rodadas a partir de feedback real do usuário:
  1. Primeira versão: página de impressão própria
     (`proposicao_print.html`), renderizando os campos do nosso banco,
     com 3 modos (reduzida/completa/personalizada) escolhidos num menu
     `<details>`.
  2. Usuário testou e apontou que queria a impressão de fato — "não a
     página", e "estritamente do link direto da câmara ou da fonte
     real" —, mostrando como referência o menu "Versões para
     impressão" que a própria ficha da Câmara já tem. **Página de
     impressão própria removida por completo** (view, template, CSS,
     modal — tudo sem uso); botão vira um link direto pro
     `Proposicao.link`.
  3. Usuário testou nesse meio-termo e voltou com os 3 links reais que
     o site da Câmara usa (`prop_imp?...&tp=reduzida`,
     `tp=completa`, `prop_visual_impress?...`) e pediu que o menu
     abrisse ao passar o mouse (como no site de referência) e cada
     opção fosse direto pra versão de impressão de verdade — "para
     cada proposição", cada uma com sua fonte. Novo módulo
     `apps/proposicoes/print_urls.py`
     (`urls_impressao_oficial(link)`) deriva os links reais a partir
     só do `Proposicao.link` já cadastrado: Câmara tem 3 formatos,
     todos dependendo só do `idProposicao` — extraído tanto de
     `?idProposicao=<id>` (formato usado por `sync_camara.py`) quanto
     de `/propostas-legislativas/<id>` (formato que sobrou do legado
     importado, confirmado que é o mesmo número comparando as duas
     formas nos dados reais); o `jsessionid` que a Câmara anexa nessas
     URLs é dispensável (só fallback de rastreio de sessão pra
     navegador sem cookie, confirmado testando sem ele). Senado só tem
     1 formato (PDF único, mesma URL da matéria com `/pdf` no final —
     Senado não tem a distinção reduzida/completa/personalizada).
     Fonte não reconhecida cai num fallback de 1 item (link direto pra
     fonte); sem `link` nenhuma, o botão não aparece (nada pra
     imprimir). Menu abre via `:hover`/`:focus-within` em CSS puro,
     sem JS — mesmo princípio de zero-dependência já usado nos outros
     dropdowns do site (`<details>`), mas hover não mapeia bem pra
     `<details>`, daí a divergência de padrão aqui.
- **Botão de compartilhar** — Web Share API quando disponível (abre a
  folha nativa do sistema, principalmente mobile), com fallback num
  menu (WhatsApp/X/Facebook/copiar link via Clipboard API). 100%
  client-side, sem view nova.

**Achado de verificação visual** (Playwright, 4 breakpoints, mesmo
checklist das últimas sessões): os ícones novos de impressão/
compartilhar nasceram em 36px no mobile — abaixo do mínimo de 44px
(WCAG) que o `.favorito-btn` e outros elementos já respeitam desde a
auditoria de mobile de 2026-08-13. Corrigido no mesmo commit da
verificação, antes de qualquer promoção.

`check`, `makemigrations --check`, `ruff --select F401,F811,F841` e
106 testes (era 84 no início da sessão) limpos a cada commit dos 7 no
total (6 funcionalidades + 1 fix de tap target). Verificação visual via
Playwright em cada etapa visualmente relevante (não só no fim) —
screenshot real do dropdown de impressão em hover, do modal antigo (já
removido), da renderização de imagem/vídeo no comentário, do card com
os 3 ícones de ação lado a lado — nos dois casos reais do banco local
(uma proposição da Câmara, uma do Senado), confirmando que as URLs
derivadas batem exatamente com os links que o usuário validou
manualmente no site da Câmara.

### Promoção `next` → `main` → produção → droplet, achado de segurança no caminho (2026-08-19)

A pedido do usuário ("vamos subir tudo pra next e para a produção e
droplet"), `check`/`makemigrations --check`/106 testes/`ruff`
revalidados antes do push; `main` local (`6f3c493`) era fast-forward
puro com `next` (`edb8307`, 9 commits — as 6 funcionalidades acima).
Push pra `origin` e `production` — **CI vermelho pela primeira vez
numa promoção desta sessão**: `pip-audit` (rodava limpo até então)
achou 4 CVEs novas em `sqlparse` 0.5.5 (`PYSEC-2026-3696` a `-3699`,
corrigidas na 0.6.0) — dependência transitiva do Django (formatação de
SQL no Admin), sem uso direto no projeto, achado só porque essa foi a
primeira vez que o CI rodou desde que as vulnerabilidades foram
divulgadas (não relacionado a nenhuma mudança desta sessão). Corrigido
regenerando `requirements.lock` (`pip-compile --generate-hashes
--upgrade-package sqlparse`, só esse pacote mudou no diff), validado
local (`pip-audit -r requirements.lock` limpo, 106 testes OK), commit
separado em `next` primeiro, depois `main` de novo — CI verde nos dois
repositórios na sequência.

Deploy no droplet via SSH: `git pull origin main` trouxe as 27
alterações (3 migrations novas, mais o fix do lockfile), `docker
compose build` (28s de instalação de dependências, sem cache stale —
código novo de verdade), `docker compose up -d` subiu sem erro. Uma
checagem de `curl` rodada muito em seguida do `up -d` bateu `502 Bad
Gateway` de novo (mesmo padrão de sempre — container com poucos
segundos de vida, healthcheck ainda `starting`); ~1 minuto depois,
`docker compose ps` → `(healthy)`, `curl -sI
https://legislativo.fnp.org.br/` → `200 OK` com todos os cabeçalhos de
segurança esperados.

### `client_max_body_size` do Nginx aumentado (6M → 30M), pendência fechada no mesmo dia

A pedido do usuário ("vamos resolver essa pendência agora"), aplicado
direto no droplet via SSH: linha alterada à mão de `6M` pra `30M` em
`/etc/nginx/sites-enabled/legislativo.conf` (`sed` de uma linha só,
nunca `cp` do arquivo inteiro — preserva o bloco SSL do certbot),
`nginx -t` limpo, `reload` sem erro, `curl` confirmando `200 OK`
depois. `deploy/nginx-legislativo.conf` (referência local) atualizado
junto, com o novo valor dimensionado pro maior upload validado no app
(vídeo de comentário, até 25MB, não mais só a foto de perfil de 5MB).

### Toolbar de mídia no comentário refeita como rede social (2026-08-19, mesma sessão)

Usuário testou a mídia de comentário (mesma sessão, item construído
horas antes) e reportou que o `<input type="file">` cru abaixo do
textarea "ficou muito esquisito" — pediu o padrão de qualquer
mensageiro (referência: WhatsApp): um "+" que abre o seletor de
arquivo da galeria, e um ícone de câmera que abre captura ao vivo
(foto ou vídeo, tanto desktop quanto mobile). Reaproveitado o
mecanismo já existente da foto de perfil (`getUserMedia` + `<canvas>`
pra foto), com um modo novo — gravação de vídeo ao vivo via
`MediaRecorder`, com indicador visual de "● Gravando…" e botão que
alterna entre "Gravar vídeo"/"Parar gravação". Preview compacto (com
botão de remover) só aparece quando há de fato um arquivo anexado,
seja por seleção de arquivo ou por captura — resolve o "esquisito" de
ter um campo de upload sempre visível mesmo vazio. Testado via
Playwright com o dispositivo de mídia falso do Chromium
(`--use-fake-device-for-media-stream`): fluxo completo de foto e de
gravação de vídeo, sem regressão de overflow horizontal nos 4
breakpoints móveis de sempre, tap target 44px, dark mode.

### Anexo de proposição passa a exigir aprovação antes de ficar público (2026-08-19, mesma sessão)

Pedido do usuário logo depois da entrega da toolbar de mídia:
documentos anexados numa proposição (item construído mais cedo na
mesma sessão) precisavam de aprovação de Root/Administrador FNP antes
de aparecer na página pública — na primeira versão, o anexo ficava
visível assim que enviado, sem revisão nenhuma. `AnexoProposicao.
status_moderacao` novo (migration `proposicoes.0005`) — ao contrário
do comentário (aprovado por padrão, só bloqueado por palavra
proibida), o anexo **nasce sempre "pendente"**: não existe checagem
automática de conteúdo de arquivo, só revisão humana. Admin ganhou
ações em massa aprovar/rejeitar (mesmo padrão do `ComentarioAdmin`) e
o campo no inline da própria proposição, pra aprovar sem sair da tela
de edição. Página pública só mostra anexo aprovado; o próprio autor do
envio continua vendo o que mandou enquanto pendente (badge "Aguardando
aprovação", pra não parecer que o upload sumiu no vazio), e staff vê
tudo, inclusive rejeitado. Regra de visibilidade calculada no backend
(`ProposicaoDetailView._anexos_context`), não em template — mesmo
princípio de "status calculado no servidor, nunca string-matching em
template/JS" das Diretrizes de Engenharia.

### Segunda promoção do dia: `next` → `main` → produção → droplet (2026-08-19)

A pedido do usuário ("vamos subir tudo para a next, produção e
droplet"), `check`/`makemigrations --check`/112 testes/`ruff`
revalidados antes do push; `main` local (`69d5825`) era fast-forward
puro com `next` (`3931722`, 1 commit — a exigência de aprovação do
anexo). Push pra `origin` e `production`; CI verde nos dois de
primeira (sem repetir o achado do `sqlparse` da promoção anterior no
mesmo dia — já estava corrigido). Deploy no droplet via SSH: `git pull
origin main` trouxe a migration nova (`proposicoes.0005_anexoproposicao_
status_moderacao`), `docker compose build` + `up -d` sem erro; `curl
-sI https://legislativo.fnp.org.br/` já confirmou `200 OK` com todos
os cabeçalhos de segurança certos poucos segundos depois do `up -d`
(mais rápido que o padrão de sempre — o rótulo interno do Docker ainda
dizia `health: starting`, mas o Nginx já estava recebendo resposta boa
do Gunicorn por trás, prova de que o `health: starting` é só questão
de o healthcheck do Docker ainda não ter rodado seu primeiro ciclo, não
um sinal de problema real).

### Upload de anexo redesenhado com ícone de clipe (2026-08-19, mesma sessão)

A partir de uma captura de tela real do formulário de anexo (o mesmo
"Escolher arquivo / Nenhum arquivo escolhido" nativo que a mídia do
comentário também tinha, já corrigida antes na mesma sessão), usuário
pediu o mesmo tratamento aqui: ícone de "clipe" no lugar do botão
nativo. Reaproveita o mesmo princípio já validado na mídia do
comentário (`id_arquivo` escondido + botão estilizado que aciona
`.click()` nele) — clique no clipe abre o seletor de arquivo nativo;
depois de escolhido, o nome do arquivo aparece em destaque com um "×"
pra remover, no lugar do texto "Nenhum arquivo escolhido". O aviso "O
anexo fica visível na página só depois de aprovado pela equipe" (da
exigência de aprovação implementada horas antes) virou um banner
discreto com ícone de informação, em vez de texto solto sem
hierarquia. **Achado no caminho**: o campo de título do anexo
(`input[type="text"]`) nunca tinha ganhado fundo escuro no dark mode
(gap pré-existente, não introduzido nesta sessão) — só ficou óbvio
agora que o formulário estava sendo mexido de qualquer forma; corrigido
junto. Testado via Playwright (login real com usuário de teste
descartável, arquivo escolhido via `set_input_files` no input
escondido, remoção, dark mode, 4 breakpoints móveis sem regressão de
overflow) — `check`, 112 testes e `ruff` limpos.

### Terceira promoção do dia: `next` → `main` (2026-08-19)

A pedido do usuário ("vamos subir para next, produção e droplet"),
`check`/`makemigrations --check`/112 testes/`ruff` revalidados antes
do push; `main` local (`3931722`) era fast-forward puro com `next`
(`34b8c86`, 1 commit — o redesenho do upload de anexo). Push pra
`origin` e `production`; CI verde nos dois, sem migration nesta leva
(só CSS/JS/template). Comandos de deploy passados pro usuário rodar
via SSH no droplet — **confirmação do `docker compose ps`/`curl` pós-
deploy ainda não recebida nesta sessão** (atualizar esta seção com o
resultado assim que confirmado).

### 500 em "Definir senha" (conta só-Google) corrigido + SMTP real configurado (2026-08-19, sessão nova)

Usuário reportou por captura de tela, **em produção**: ao tentar criar a
primeira senha local numa conta que só loga via Google
(`/contas/password/set/`, ver `definir_senha_social` — fluxo que manda
e-mail de confirmação antes de liberar senha, criado em 2026-08-10),
clicar em "Enviar link de confirmação por e-mail" derrubava a página com
`Server Error (500)`.

Causa raiz: `EMAIL_BACKEND` de produção ainda cai no default
`smtp.EmailBackend` sem servidor configurado (pendência já registrada há
tempo, ver "Pendências" — nunca tinha sido priorizada porque nada
sensível dependia disso até agora). `definir_senha_social` chamava
`form.save(request)` (do `ResetPasswordForm` do allauth) direto, sem
tratamento de erro — `ConnectionRefusedError`/`SMTPException` subia cru e
virava 500. Mesmo bug de categoria já visto antes (cadastro derrubando
sem `EMAIL_BACKEND` em dev, e-mail de aviso de cadastro pendente com
`fail_silently=True` por causa disso) — dessa vez pegou um fluxo que
**não tinha** essa proteção. Fix: `try/except (SMTPException, OSError)`
em volta do envio, com `logger.exception` pra não perder o rastro, e uma
mensagem amigável (`erro_envio`) na mesma página em vez de 500 — usuário
pode tentar de novo depois. 1 teste novo (mock do `ResetPasswordForm.save`
levantando `ConnectionRefusedError`, confirma 200 com o aviso em vez de
crash).

**No mesmo fôlego**, usuário decidiu resolver a causa raiz: vai criar
`naoresponda@fnp.org.br` no Google Workspace do domínio (mesmo Workspace
usado pro login Google) como remetente técnico do sistema. E-mail de
solicitação gerado e enviado pro responsável interno (Keven) pedindo a
criação + 2FA ativado + senha de app gerada. `EMAIL_HOST`/`EMAIL_PORT`/
`EMAIL_USE_TLS`/`EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD` já adicionados em
`settings.py` (defaults certos pro Gmail — `smtp.gmail.com:587`,
STARTTLS — só usuário/senha de app faltam vir do `.env` do droplet);
`DEFAULT_FROM_EMAIL` trocado de `painel@fnp.org.br` (endereço que nunca
existiu de verdade) pra `naoresponda@fnp.org.br`. `.env.production.example`
documentado com o passo a passo (senha de app, não a senha normal da
conta). **Ainda falta**: Keven criar a conta e passar a senha de app (nunca
colada em texto puro no chat — é credencial), preencher no `.env` do
droplet, recriar o container (`--force-recreate`, sem rebuild).

`check`, `makemigrations --check`, teste novo + suíte completa e `ruff`
limpos a cada commit. Commitado e enviado pra `next` (`db3f932`,
`f7c7868`) — não promovido.

### "Perfil de acesso" vira classificação automática pelo cargo, não mais autodeclarado (2026-08-19, mesma sessão)

A partir de uma captura de tela de `/perfil/` mostrando o campo "Você é"
como um `<select>` nativo cru ("muito cru", nas palavras do usuário),
pedido de 3 partes: (1) melhorar o design pra bater com o resto do site,
(2) renomear pra "Perfil de acesso", (3) o campo só devia ser editável
por Root/Administrador FNP (pra corrigir o perfil de qualquer usuário),
nunca pelo próprio usuário — que deveria ver um valor estático — e (4) a
categoria deveria ser **identificada automaticamente no cadastro**, a
partir das informações que o usuário já fornece, não escolhida
manualmente.

Investigando o código antes de mexer, achado um problema de verdade
maior que só estética: `classe_usuario` (`Perfil`) já era editável em
`/perfil/` por **qualquer usuário logado**, com as 4 opções incluindo
"Equipe FNP" — o formulário de cadastro público excluía essa opção (ver
sessão de 2026-08-18/19 mais acima), mas nada impedia alguém se cadastrar
como "Prefeito" e depois ir em `/perfil/` e trocar sozinho pra "Equipe
FNP". Ou seja, a única barreira contra autopromoção estava só no
formulário de entrada, não no de edição — brecha real de integridade de
dado usado pelo Root/Admin pra dar atenção diferenciada por tipo de
usuário.

Fix, resolvendo os 4 pedidos numa tacada (a automação elimina a
necessidade de estilizar um `<select>`, porque o campo deixou de ser um
formulário de escolha em qualquer lugar acessível ao usuário comum):

- **`apps/usuarios/classificacao.py`** (novo) — `classificar_por_cargo(cargo)`,
  heurística por palavra-chave (fronteira de palavra, sem acento/caixa,
  mesmo padrão de `apps.comentarios.moderacao`): cargo citando
  "prefeito"/"prefeita" → Prefeito; citando "deputado"/"senador"/
  "vereador"/"parlamentar" → Parlamentar; qualquer outro cargo (padrão,
  cobre secretário/assessor/diretor/chefe de gabinete etc.) → Indicado da
  prefeitura. **Nunca** retorna "Equipe FNP" — essa continua exclusiva de
  promoção manual via grupo do Admin, sem mudança nisso.
- **Cadastro público**: campo `classe_usuario` removido do
  `CustomSignupForm` e do template de signup — `signup()` agora chama
  `classificar_por_cargo(cargo)` em vez de ler escolha manual do POST.
- **`/perfil/`**: `classe_usuario` removido de `PerfilDadosForm.Meta.fields`
  (não é mais editável pelo próprio usuário, nem Root/Admin quando vendo
  o próprio perfil por aqui). Template mostra "Perfil de acesso" como um
  valor estático (`.field-static`, ícone de cadeado, mesma
  forma/padding/borda dos outros campos do formulário — não destoa mais,
  só sinaliza visualmente "travado"), com `title` explicando que é
  automático e que o Root corrige se precisar.
- **Root/Administrador FNP**: continuam corrigindo o valor de qualquer
  usuário via Django Admin (`PerfilInline`, já aceitava o campo sem
  restrição — nenhuma mudança necessária lá; é o "painel de perfis" que o
  pedido do usuário mencionava).
- 7 testes novos (3 casos da heurística de classificação + prefeito/
  parlamentar/indicado no fluxo de signup real + confirma que o campo
  sumiu do formulário público + confirma que POST malicioso pra trocar a
  própria classe não tem efeito + confirma o markup estático no
  template), verificado também via Playwright (screenshot real de
  `/perfil/` em light e dark mode, campo "Perfil de acesso" com ícone de
  cadeado e valor correto, nenhum `<select name="classe_usuario">` em
  lugar nenhum acessível ao usuário comum).

`check`, `makemigrations --check` (sem migration — só comportamento de
formulário/template), 120 testes (era 113) e `ruff` limpos. Commitado e
enviado pra `next` (`b792e00`) — não promovido.

### Documento e áudio no fórum de comentários + comentário só-de-mídia (2026-08-19, mesma sessão)

A pedido do usuário: (1) botão de anexar documento e botão de gravar
áudio na toolbar do comentário do fórum (já tinha foto/vídeo, ver seção
"Toolbar de mídia no comentário refeita como rede social" mais acima),
funcionando em desktop e mobile; (2) comentário deixa de exigir texto
escrito — pode ser só foto, vídeo, áudio ou documento —, mas continua
proibido enviar completamente vazio (nem texto, nem mídia).

- **Ambiguidade real resolvida**: a gravação de áudio ao vivo e a de
  vídeo do fórum usam o mesmo contêiner `.webm` — extensão sozinha não
  distingue as duas. `Comentario.midia_tipo` (novo, migration
  `comentarios.0009`) é calculado em `save()` a partir do `content_type`
  que o navegador manda no upload (autoritativo: `audio/webm` vs
  `video/webm`), com fallback pra extensão só quando content_type não
  vem (`apps/comentarios/models.py::_detectar_categoria_midia`).
  `tipo_midia` (property, usada nos templates) passou a ler esse campo
  em vez de recalcular por extensão toda vez.
- Extensões novas permitidas: áudio (mp3/wav/ogg/m4a, 15MB) e documento
  (pdf/doc/docx/xls/xlsx, 10MB) — mesmo padrão de limite por categoria
  que imagem/vídeo já tinham.
- **Toolbar do comentário** ganhou 2 ícones novos (documento — clipe; áudio
  — microfone), mesmo hidden `<input type="file">` reaproveitado pros 4
  tipos (`accept` trocado via JS conforme o botão clicado, câmera/áudio
  continuam com captura ao vivo). Modal de áudio novo (reaproveita as
  classes `.avatar-camera-modal*` já existentes), com ícone de microfone
  pulsando + cronômetro enquanto grava (`MediaRecorder`, mesma técnica já
  usada pro vídeo, cadeia de `mimeType` com fallback `webm→ogg→mp4`).
  Pré-visualização antes de publicar cobre os 4 tipos agora (imagem/
  vídeo/áudio tocável/documento com nome do arquivo).
- **Renderização no fórum**: documento vira link com ícone (mesmo ícone
  de arquivo já usado nos anexos de proposição) + nome; áudio vira
  `<audio controls>`. **Testado empiricamente via Playwright** (gravação
  de áudio real com `--use-fake-device-for-media-stream`, comentário
  publicado, página recarregada, `<audio>` verificado com
  `readyState=4`/`duration` correto) que o navegador toca o áudio mesmo
  o Nginx/Django servindo `.webm` com `Content-Type: video/webm` (mime
  type padrão da extensão) — não precisou de nenhum ajuste de Nginx.
- **Comentário só-de-mídia**: `Comentario.texto` ganhou `blank=True`
  (migration `comentarios.0010`); `ComentarioForm.clean()` novo exige
  pelo menos um dos dois (texto OU mídia), nunca os dois vazios —
  mensagem amigável ("Escreva um comentário ou anexe uma foto, vídeo,
  áudio ou documento.") via o mesmo mecanismo de toast que já existia
  pra comentário rejeitado por palavra proibida. Template
  (`_comentario.html`) não renderiza mais um `<p></p>` vazio quando o
  comentário é só mídia.
- **Achado de regressão, corrigido no caminho** (não relacionado ao
  pedido, pego pela própria verificação mobile): `.anexo-upload-row`
  (upload de anexo com ícone de clipe, construído mais cedo na mesma
  sessão) causava overflow horizontal real em mobile — item de grid
  dentro de `.anexo-form` (`display: grid`) sem `min-width: 0`, mesmo
  padrão de bug já visto várias vezes antes no projeto (texto sem quebra
  de `.anexo-upload-hint` empurrando a linha inteira pra fora do
  viewport). Fix de uma linha.

`check`, `makemigrations --check`, 128 testes (era 120, +8) e `ruff`
limpos. Verificação visual completa via Playwright: fluxo de documento e
de áudio de ponta a ponta (inclusive o teste empírico de reprodução do
áudio depois de recarregar a página), comentário vazio rejeitado com a
mensagem certa, comentário só-imagem publicado sem erro, 3 breakpoints
móveis (360/390/414px) sem overflow horizontal, dark mode. Commitado e
enviado pra `next` — **promovido pra `main`/produção/droplet na
sequência, a pedido do usuário** (ver seção de promoção logo abaixo).

### SMTP bloqueado pela DigitalOcean — resolvido via Gmail API (2026-08-20)

Depois do fix do 500 em "Definir senha" (sessão anterior, mesmo dia),
usuário testou de verdade em produção e o SMTP continuava sem funcionar.
Investigação em camadas, cada uma eliminando uma hipótese:

1. **Primeiro erro**: `OSError: [Errno 101] Network is unreachable` —
   causa real era o container Docker não ter rota IPv6, e `smtp.gmail.com`
   ter endereço IPv6 (AAAA) cadastrado; o socket tentava conectar por lá
   primeiro e falhava na hora, antes de sequer tentar IPv4 (o Sentry nunca
   bateu nisso porque `sentry.io` só tem IPv4). Fix aplicado em
   `setup/settings.py` (`socket.getaddrinfo` forçado pra `AF_INET` em
   produção) — não afeta Postgres (psycopg2 não usa o socket do Python)
   nem dev.
2. **Segundo erro, depois do fix acima**: `TimeoutError: [Errno 110]
   Connection timed out` — progresso real (agora tentava IPv4 de
   verdade), mas travava até estourar o timeout. Testado em camadas
   direto no droplet (fora do Docker): `ufw` libera saída por padrão
   (`allow (outgoing)`), o Cloud Firewall da DigitalOcean
   (`FirewallSistemaFNP`) libera "All TCP"/"All UDP" pra todos os
   destinos — nenhum dos dois é o bloqueio. Teste de conexão TCP direta
   (`/dev/tcp/smtp.gmail.com/587` e `/465`) deu timeout nas duas, enquanto
   `/dev/tcp/www.google.com/443` conectou na hora — isolou o problema:
   é bloqueio de porta de SMTP especificamente, numa camada acima do
   `ufw`/Cloud Firewall (a própria DigitalOcean bloqueia por padrão portas
   de e-mail de saída em toda conta nova, prática antispam documentada
   por eles). **Chamado de suporte aberto com a DO** pedindo liberação —
   ainda sem resposta, mas não é mais bloqueante (ver item 3).
3. **Solução efetiva, sem esperar a DO**: como HTTPS (443) funciona
   normal, a Gmail API contorna o bloqueio por completo (fala HTTPS, não
   SMTP). Implementado `apps/legislativo/email_backends.py::
   GmailApiEmailBackend` — autentica via Service Account do Google Cloud
   (`legislativo-fnp-email-sender`, projeto `sistema-fnp` — **isolado do
   Service Account que já existia pra outro sistema da FNP**,
   `gmai-sender-sistemafnp`, decisão consciente do usuário de não
   compartilhar credencial entre sistemas mesmo dividindo o projeto do
   Google Cloud) com **Domain-wide Delegation** autorizada no Admin
   Console do Workspace (Segurança → Controle de acesso e dados →
   Delegação em todo o domínio), escopo único
   `https://www.googleapis.com/auth/gmail.send`, impersonando
   `naoresponda@fnp.org.br`. `GMAIL_SERVICE_ACCOUNT_JSON_B64` (conteúdo
   do JSON da chave em base64, uma linha só) + `GMAIL_SENDER_EMAIL` +
   `EMAIL_BACKEND=apps.legislativo.email_backends.GmailApiEmailBackend`
   no `.env` de produção — `EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD` (SMTP)
   continuam no código como alternativa válida pra outro ambiente sem
   esse bloqueio, só não são mais o caminho usado no `fnp-web`.
4. **Testado em 2 camadas antes de promover**: local primeiro (usando o
   `.json` baixado, sem nunca colar o conteúdo no chat — só o caminho do
   arquivo), envio real confirmado (`SUCESSO -- id da mensagem:
   1a020a611ee5fb25`); depois em produção de verdade, via SSH direto no
   droplet (usuário autorizou acesso SSH direto nesta sessão — chave
   `~/.ssh/id_ed25519_fnp_web` já configurada localmente de sessão
   anterior), `send_mail()` real via `manage.py shell` → `enviado sem
   excecao`, e-mail confirmado chegando. `docker compose ps` → healthy,
   `curl` → `200 OK`.
5. **Transferência da chave pro droplet sem nunca passar pelo chat**: com
   autorização do usuário pra conectar via SSH, o conteúdo em base64 foi
   gerado localmente e enviado direto pro `.env` do droplet via
   `ssh ... "cat >> .env" < arquivo_local` — o valor nunca apareceu em
   nenhuma saída de comando nem foi impresso em tela.
6. 4 testes novos (`GmailApiEmailBackendTest`, mock completo da API do
   Google — nunca faz chamada de rede real nem usa credencial de
   verdade): envio com sucesso, lista vazia não monta credenciais, falha
   com/sem `fail_silently`. `check`, `makemigrations --check`, 132 testes
   (era 128) e `ruff` limpos; `pip-audit` no `requirements.lock`
   regenerado (google-api-python-client/google-auth novos) limpo.

Promovido `next` → `main` → produção → droplet no mesmo fôlego (autorização
explícita do usuário — "Pode fazer" — pra eu conduzir o SSH direto).
**Pendência de segurança nova**: senha do `doadmin` apareceu em texto puro
no chat de novo nesta sessão (resultado de query colado sem querer) —
rotacionada mais uma vez já é rotina neste projeto, mas ainda não feito
desta vez, ver Pendências.

### Pendências e próximos passos

**Mais urgente agora:**

- ~~Concluir a configuração de SMTP real~~ — **resolvido de vez em
  2026-08-20, por um caminho diferente do planejado**: a DigitalOcean
  bloqueia por padrão as portas de SMTP de saída (587/465) em toda conta
  nova (achado só testando de verdade — `ufw`/Cloud Firewall liberam
  tudo, o bloqueio é numa camada acima). Chamado de suporte aberto com a
  DO pra liberar (ainda sem resposta, **não é mais bloqueante**), mas a
  solução efetiva foi trocar pra **Gmail API** (fala HTTPS/443, sempre
  liberado) — `apps/legislativo/email_backends.py::GmailApiEmailBackend`,
  testado local e em produção de verdade, e-mail confirmado chegando.
  Ver seção datada "SMTP bloqueado pela DigitalOcean — resolvido via
  Gmail API" acima pro histórico completo.
- ~~Promover a sessão de 2026-08-19 pra `main`/produção/droplet~~ e
  ~~Confirmar o deploy do redesenho do upload de anexo~~ — **ambos
  resolvidos**, várias promoções feitas ao longo de 2026-08-19/20 (ver
  seções datadas "Segunda/Terceira promoção do dia" e as de 2026-08-20
  acima) — tudo que estava represado já está em produção confirmada
  saudável.
- ~~Rotacionar a senha do `doadmin` mais uma vez~~ — **resolvido em
  2026-08-20**, mesmo dia do achado. Apareceu em texto puro no chat
  (query de diagnóstico colada sem querer) e foi rotacionada pelo painel
  DO ainda na sessão — não exigiu mudança em nenhum serviço nosso, só a
  role `legislativo` é usada em produção.
- ~~Aumentar `client_max_body_size` no Nginx do droplet~~ — **resolvido
  em 2026-08-19**: linha alterada à mão de `6M` pra `30M` direto em
  `/etc/nginx/sites-enabled/legislativo.conf` (`sed` de uma linha só,
  nunca `cp` do arquivo inteiro — preserva o bloco SSL do certbot),
  `nginx -t` limpo, `reload` sem erro, `curl` confirmando `200 OK`
  depois. `deploy/nginx-legislativo.conf` (referência local) atualizado
  junto. Vídeo em comentário do fórum (até 25MB) já funciona em
  produção.
- ~~Promover a auditoria de UX mobile (2026-08-13) + os fixes de
  produção do mesmo dia pra `main`/produção~~ — **feito em 2026-08-13**,
  ver seção datada "Promoção completa `next` → `main` → produção →
  droplet" logo abaixo. Ainda pendente: testar em dispositivo físico de
  verdade (Safari iOS + Chrome Android) os 5 itens que emulador não
  cobre da auditoria original (teclado virtual cobrindo campo, rodapé —
  home tem 30.000+px de altura, não rolado até o fim —, contraste de
  cor dos badges, SSE se recuperando de troca de rede, tempo de carga
  em 4G real) **mais** o "card Resumo parecendo sobrepor" reportado no
  celular — não reproduzido em Chromium mesmo depois do fix de
  overflow, vale confirmar se sumiu de verdade agora que está em
  produção.
- **Rotacionar `SECRET_KEY`, senha da role `legislativo` e
  `GOOGLE_CLIENT_SECRET`** — os três apareceram em texto puro num print
  do `.env` de produção nesta sessão de chat (2026-08-11). `SECRET_KEY`
  é o mais barato de trocar (invalida sessões ativas, sem downtime
  real); os outros dois seguem o mesmo roteiro já usado hoje pro
  `doadmin` e pro Google Client Secret anterior.
- **Decidir se o mérito interno da proposição deveria ser público** —
  `posicionamento_fnp` continua fazendo sentido público, mas
  `acoes_incidencia`/`riscos_oportunidades` (estratégia de lobby)
  aparecem pra qualquer visitante anônimo em `proposicao_detail.html`,
  sem exigir login. Achado da revarredura de segurança de 2026-08-11 —
  decisão do usuário antes de eu mexer em código (pode ser intencional).
- ~~Configurar `EMAIL_BACKEND` real em produção~~ — **resolvido em
  2026-08-20** via Gmail API (ver item no topo desta lista). Com isso,
  dá pra reconsiderar `ACCOUNT_EMAIL_VERIFICATION='mandatory'` (o fix
  mais robusto pro achado da fusão de conta, ver auditoria de segurança
  acima) — decisão de produto ainda não tomada, mas o pré-requisito
  técnico não é mais um bloqueio.
- **Desativar/excluir o Client Secret antigo do Google OAuth** no Google
  Cloud Console (o criado em 2026-08-04) — o novo já está em produção e
  validado, mas o antigo continua uma credencial ativa em paralelo até
  ser desligado por lá.
- **Itens de infraestrutura já checados em 2026-08-11**: SSH key-only ✅,
  `ufw` ✅, `PermitRootLogin yes` ainda ligado mas baixa prioridade,
  `media/` chown ✅, limite de upload no Nginx ✅, **Trusted Sources do
  `fnp-database` confirmado restrito** ✅ (painel DO → Network Access: só
  2 origens — `fnp-web` e um IP fixo rotulado "Sistema-FNP", nada de
  "Allow all"). **Só falta**: atualizações de SO + Docker pendentes com
  reboot — **avaliado e adiado de propósito em 2026-08-11**: o droplet
  `fnp-web` hospeda outros sistemas da FNP também (Nginx configurado
  pra `ifem`/`fnp`/`fnp-homolog` além do `legislativo`), então um
  reboot derruba todos juntos, não só o nosso; usuário optou por não
  mexer agora pra não impactar os outros sistemas sem coordenar antes.
  Precisa de uma janela combinada com quem administra os demais.
- ~~Conferir visualmente no navegador a rodada de 23 itens acima~~ —
  **resolvido em 2026-08-14**, ver seção datada "Verificação visual
  pendente de duas rodadas antigas" logo abaixo. Tudo confirmado
  funcionando via Playwright contra o dev local.
- ~~Confirmar visualmente no navegador se os 5 ajustes finos da rodada
  anterior ficaram bons~~ — **resolvido em 2026-08-14**, mesma seção
  acima. Todos os 5 confirmados corretos.
- ~~Decidir o que fazer com as proposições não-curadas já em produção~~ —
  **resolvido em 2026-08-11**: `sync_legado_firestore --keep-json`
  rodado em produção pra restaurar/corrigir os 104 registros curados
  (nenhum "Criada", confirma que a base curada estava intacta), depois
  as 68 proposições fora do legado apagadas via
  `Proposicao.objects.exclude(titulo__in=titulos_104).delete()`
  (uma delas tinha 12 comentários — confirmado pelo usuário que eram só
  de teste, sem perda real). Banco de produção conferido em 104/104
  depois. **Correção same-day**: `--paginas 1` sozinho não foi
  suficiente — voltou a 165 em menos de um dia; `sync-camara` parado e
  desativado por `profiles` (ver seção datada mais abaixo, mesmo dia).

**Seguem em aberto (sem mudança nesta sessão):**

- ~~`SENTRY_DSN` sem conta criada~~ — **resolvido em 2026-08-11**, ver
  seção datada acima.
- Conta externa que falta ser criada pra ativar o que já está
  implementado (tudo desligado até lá, zero risco):
  `RECAPTCHA_PUBLIC_KEY`/`RECAPTCHA_PRIVATE_KEY`
  (google.com/recaptcha/admin).
- `EMAIL_BACKEND` de produção ainda não configurado com um backend real
  (SMTP/SES/etc.) via env var — `ACCOUNT_EMAIL_VERIFICATION=optional`
  manda e-mail de confirmação mas não entrega de verdade lá. (O bug de
  dev, cadastro local derrubando sem `EMAIL_BACKEND`, já foi corrigido —
  isso aqui é só sobre produção ter um backend real configurado.)
  **Ficou mais urgente em 2026-08-14**: o aviso de cadastro pendente pra
  `ronan.castro@fnp.org.br`/`nucleo.dados@fnp.org.br` (ver seção datada
  acima) também depende disso pra chegar de verdade em produção.
- Cache do Django é `LocMemCache` (por processo) — com Gunicorn
  `--workers 3`, rate limit de login e `throttling.py` de
  comentário/participação têm limite efetivo até 3x mais permissivo do
  que o configurado. Trocar por Redis é reabrir a diretriz "só trocar se
  crescer pra múltiplos workers" — decisão ainda não tomada.
- ~~`deploy/nginx-legislativo.conf` com limite de upload 6MB não copiado
  pro droplet~~ — **resolvido em 2026-08-11, sem repetir o incidente de
  2026-08-05**: em vez de `cp` do arquivo inteiro (que apaga o bloco SSL
  do certbot), só a linha `client_max_body_size 6M;` foi inserida à mão
  no arquivo já em produção (`/etc/nginx/sites-enabled/legislativo.conf`),
  validada com `nginx -t` antes do `reload`. No caminho, achado e
  removido um arquivo `legislativo.conf.save` (sobra de uma edição
  anterior do `nano`, não um symlink como os configs de verdade) que
  também declarava `server_name legislativo.fnp.org.br` e causava um
  aviso de "conflicting server name" — não afetava outros sistemas do
  droplet (`fnp`, `ifem`, `fnp-homolog`), só duplicava o nosso.
- Droplet `fnp-web` sem backup próprio (só o `fnp-database` tem).
- Reverificar se o bug do Python 3.14 (`copy.copy()` em `RequestContext`)
  ainda ocorre agora que o projeto está no Django 5.2 — não testado,
  `.venv/` local continua em 3.12 por segurança.
- ~~Conferir/chown o volume de `media/` no droplet~~ — **resolvido em
  2026-08-11**: estava `root:root`, mesmo risco de permissão que o
  `staticfiles/` teve em 2026-08-05. `chown -R 1000:1000` aplicado
  (aparece como dono `phillippi` no host — coincidência de UID 1000 com
  o usuário de deploy do IFEM, não é erro; o container roda como
  `appuser` também UID 1000, e Linux checa por número, não por nome).
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
- ~~Container `legislativo` aparece `(unhealthy)` no `docker compose ps`~~
  — **causa raiz encontrada e corrigida em 2026-08-11, direto pelo
  Sentry** (ver seção datada abaixo): o healthcheck do
  `docker-compose.yml` rodava `curl http://localhost:8004/`, que manda
  `Host: localhost:8004` — o Django rejeitava com `DisallowedHost` (só
  `legislativo.fnp.org.br` está em `ALLOWED_HOSTS`), então o healthcheck
  falhava sempre, mesmo com o site respondendo `200 OK` de verdade via
  Nginx (que usa o Host certo). Fix: `-H "Host: legislativo.fnp.org.br"`
  adicionado ao `curl` do healthcheck, sem tocar em `ALLOWED_HOSTS`.
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
| `docs/adr/0002-deploy-producao-dominio.md` | Como o projeto foi pro ar em `legislativo.fnp.org.br` — infraestrutura, passo a passo e cronologia real do primeiro deploy (2026-08-03/05) |
| `docs/adr/0003-seguranca-auditoria-hardening.md` | Auditorias de segurança, hardening, decisões conscientes e pendências — histórico completo (ver também "Postura de segurança" acima, no corpo deste arquivo) |
| `CONTRIBUTING.md` | Padrões de contribuição |

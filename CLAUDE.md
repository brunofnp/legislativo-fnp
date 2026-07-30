# CLAUDE.md — Contexto do Projeto Legislativo FNP

> Arquivo de contexto para sessões com Claude Code. Atualizado automaticamente a cada 3h enquanto há sessão ativa (mantém este arquivo fiel ao código para evitar redescoberta/gasto de tokens em sessões futuras).
> Última atualização: 2026-07-30 (painel de hierarquia, histórico de mérito conectado, fórum redesenhado, Usuario/Perfil separados)

---

## Visão Geral

**Legislativo FNP** é uma plataforma Django para acompanhamento legislativo voltada ao monitoramento de proposições em tramitação no Congresso Nacional e ao impacto para municípios. A proposta é reunir um painel institucional, visual profissional e fluxo de participação colaborativa para a Frente Nacional de Prefeitas e Prefeitos.

URL de produção: GitHub Pages/hosting definido pela organização (branch `main` do remoto `production`)
Branch de desenvolvimento ativo: `next`

---

## Stack Tecnológica

| Camada | Tecnologia |
|---|---|
| Backend | Django 4.2.x · Python 3.14 local / 3.11 no CI |
| Auth | django-allauth (login por e-mail + Google OAuth, cadastro manual ou Google) |
| Banco (dev) | SQLite |
| Banco (prod) | PostgreSQL (planejado, via `DATABASE_URL`) |
| Templates | Django Templates + CSS/JS vanilla |
| Estáticos | WhiteNoise |
| Dados | Modelos Django + management commands (`ingest_legislativo`, `sync_legado_firestore`, `sync_camara --watch`) |
| UI | HTML semântico, CSS customizado (dark mode via `[data-theme]`), JavaScript vanilla |
| Testes | Django TestCase (via `RequestFactory`, não `self.client` — ver Observações) + pytest |

**Observação sobre testes:** `self.client.get(...)` quebra localmente no Python 3.14 (bug de `copy.copy()` no signal `template_rendered` do Django 4.2, que só suporta oficialmente até 3.11). Os testes usam `RequestFactory` + `SessionMiddleware` manual. O CI roda em 3.11 e não é afetado.

---

## Estrutura de Arquivos

```
apps/
  legislativo/
    admin.py
    models.py              # Usuario, Proposicao, Macrotema, Tema, Comentario, Participacao, Notificacao
    views.py
    urls.py
    forms.py                # CustomSignupForm (allauth), PerfilForm, ComentarioForm, ParticipacaoForm
    context_processors.py   # notificacoes + usuario_display_name (nome "Bonito", nunca o e-mail cru)
    data_utils.py            # split_temas() — separa temas compostos "A, B/C"
    tests.py
    management/
      commands/
        ingest_legislativo.py
        sync_legado_firestore.py  # importa as 104 proposições reais do Firestore legado (legislativo-fnp.web.app)
        sync_camara.py             # sync ao vivo via API Dados Abertos da Câmara, com --watch
static/
  css/
    style.css               # ~1880 linhas: app-shell, dark mode, acessibilidade, cards, auth
  js/
    main.js
  img/
    logo-FNP.png
  favicon.svg
templates/
  base.html
  _sidebar.html             # menu lateral, só renderiza na página de perfil (mostrar_sidebar=True)
  _topbar.html              # barra superior autenticada (busca, tema, notificações, avatar)
  _footer.html
  _search_modal.html        # busca via Ctrl+K
  socialaccount/login.html  # confirmação de login Google, traduzida
  allauth/layouts/base.html # override raiz de TODAS as páginas do allauth (login/signup/logout/etc.)
  legislativo/
    home.html
    perfil.html
    proposicao_detail.html
    participacao_list.html
    favoritos_list.html
    _proposicao_card.html
setup/
  settings.py
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

O núcleo do projeto é o app `legislativo`, responsável por:
- modelar proposições (104 reais, migradas do Firestore legado), macrotemas, temas (M2M), comentários, participação, notificações e usuários
- renderizar a homepage com cards de briefing compactos (Urgentes, Áreas de interesse, Em alta, Últimos acessados, Todas)
- exibir detalhes de proposições e suportar fórum de comentários com notificação aos participantes
- autenticação opcional (navegação pública não exige login) via e-mail/senha ou Google OAuth

### Padrão atual de UI

- **Pública (não logado):** header simples só com logo (link externo para fnp.org.br) + botão "Entrar". Sem sidebar.
- **Autenticada:** topbar (busca Ctrl+K, tamanho de fonte, dark mode, notificações, avatar com nome "Nome Sobrenome") + sidebar lateral colapsável, mas a sidebar **só é exibida na página de perfil** (`/perfil/`), não em todo o site.
- Cards compactos (redesenhados segundo justinmind.com/ui-design/cards): badges de prioridade/urgência, chip de tema, meta-linha com ícones (Casa/Status/Municípios), estrela de favorito sem círculo.
- Dropdown de tema pesquisável no lugar de filtro simples.
- Acessibilidade: skip links (Alt+1/Alt+2), `:focus-visible` global, `prefers-reduced-motion`, `role="search"`, `aria-hidden` em ícones decorativos — ver `docs/adr` / commit `8efad51`.
- Dark mode via `[data-theme="dark"]` + `localStorage['fnp-theme']`; tamanho de fonte via `localStorage['fnp-font-size']`; sidebar colapsada via `localStorage['fnp-sidebar-collapsed']`.

### Funcionalidades já implementadas

- Home com listagem, busca, filtro por tema (M2M), estatísticas (total, pauta, urgentes, alta prioridade, com relator)
- Favoritos e "últimos acessados" (funcionam mesmo sem login, via sessão)
- "Em alta" (ranking por visualizações + comentários) e "Áreas de interesse" (derivado dos temas mais acessados)
- Cadastro e login (e-mail/senha próprio ou Google OAuth via django-allauth); Google **sem credenciais reais ainda** — `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` vazios em `.env`, documentado em `docs/runbook.md`
- Página de perfil (`PerfilView`) com edição de nome/telefone/cargo
- Fórum de comentários por proposição com notificação aos demais participantes da discussão
- Endpoint SSE/polling para atualização de dados em tempo real
- Acessibilidade WCAG 2.1-aligned (skip links, foco visível, redução de movimento)

---

## Modelos principais

### Proposicao

Campos principais: `titulo`, `casa`, `status_tramitacao`, `local`, `pauta`, `urgente`, `aprovada`, `parada`, `prioridade_fnp`, `macrotema`, `ementa_resumida`, `proximos_eventos`, `interlocutores`, `ultima_movimentacao`, `link`, `posicionamento_fnp`, `acoes_incidencia`, `riscos_oportunidades`, `visualizacoes` (contador para "Em alta").

**`temas`** é `ManyToManyField` para `Tema` (migrado de FK única — ver migração `0002_replace_tema_with_m2m.py`, que separa nomes compostos "A, B/C" via `split_temas()`).

### Usuario / Perfil

`Usuario` é `AUTH_USER_MODEL`, estende `AbstractUser` (só dados de autenticação). `Perfil` guarda `municipio`, `telefone`, `cargo` em 1-para-1 com `Usuario`, criado automaticamente por signal (`signals.py`) a todo cadastro novo — inline no Admin de Usuario. Nome de exibição é `Usuario.get_display_name()` (nome completo ou derivado do e-mail) — nunca o e-mail cru na UI. Hierarquia de acesso via grupos nativos do Django: **Root** (superusuário), **Administrador FNP**, **Usuário** (padrão); ver `python manage.py setup_roles`.

### Macrotema / Tema

- `Macrotema` organiza a classificação editorial das proposições
- `Tema` representa subcategorias mais específicas (M2M com Proposicao)

### Participacao / Comentario / Notificacao

- `Participacao` permite registrar contribuições, sugestões, dúvidas ou indicações
- `Comentario` é a base do fórum por proposição
- `Notificacao` é criada para todo comentarista anterior quando alguém novo comenta na mesma discussão (`notificar_participantes_da_discussao`)

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

**Estrutura:** modelo Radar Brasil — `apps/` (um app por domínio), `base_templates/` (layout compartilhado), `templates/` por app, `static/`, `setup/` (settings/urls raiz), `locale/`, `docs/`. Um app = uma responsabilidade; nada de app genérico "core" virando depósito. `requirements.txt` (prod) e `requirements-dev.txt` (dev/lint/teste) separados; `.env.example` versionado, `.env` nunca.
⚠️ **Gap atual:** todo o domínio (proposições, comentários, usuários, notificações) está hoje num único app `apps/legislativo`. Não vou dividir sem pedido explícito — é uma migração de schema/imports não-trivial.

**Models/banco:** status/urgência/categoria é sempre coluna real calculada na ingestão, nunca string-matching em template/JS (`urgente`, `aprovada`, `parada`, `prioridade_fnp` já são assim). Edição de campo de mérito nunca sobrescreve — grava linha de histórico (autor, campo, valor anterior, novo, data); `EdicaoMeritoHistorico` é gravado automaticamente pelo `ProposicaoAdmin.save_model` e por `ingest_legislativo` sempre que `posicionamento_fnp`/`acoes_incidencia`/`riscos_oportunidades` mudam (campos listados em `Proposicao.CAMPOS_MERITO`). FK de thread sempre com `related_name` explícito (`Comentario.parent` → `related_name='respostas'`, já correto). Migrations sempre revisadas antes de aplicar, nunca schema editado direto em produção. Ingestão idempotente via `update_or_create` (já é o padrão em `ingest_legislativo.py`).

**Views/templates:** server-side rendering por padrão; JS só para interatividade puramente client-side sobre dado já carregado (filtro/busca). Nunca SPA client-side recalculando dado que já deveria vir pronto do servidor. Django Admin para telas administrativas (edição de mérito, gestão de macrotema, moderação de comentários, hierarquia de usuários via grupos/permissões nativas) em vez de CRUD customizado, a menos que a necessidade seja genuinamente pública-facing.

**Autenticação:** auth nativo do Django, nunca senha única/`if pass == X`. Permissão via `django.contrib.auth` (permissions/groups) — grupos **Root** (superusuário, bypassa checagem de permissão), **Administrador FNP** (moderação/edição de conteúdo) e **Usuário** (padrão, atribuído automaticamente por signal a todo cadastro novo); ver `python manage.py setup_roles`. `Usuario` (auth) e `Perfil` (município/telefone/cargo, 1-para-1 via signal) já são separados como o padrão User+Profile pede.

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

## Estado Atual do Projeto (2026-07-30)

### Branch atual: `next` (main/production está em ff-only com next; sem divergência)

### Conquistas implementadas

- Dados reais: 104 proposições migradas do Firestore legado + sync ao vivo com a Câmara
- Autenticação completa: cadastro próprio ou Google OAuth (allauth), todas as páginas allauth estilizadas via override de `allauth/layouts/base.html`
- Painel autenticado: topbar + sidebar (restrita à página de perfil), dark mode, tamanho de fonte, busca Ctrl+K, notificações de menção/resposta
- Favoritos, "em alta", "áreas de interesse", "últimos acessados" — funcionam com ou sem login (sessão)
- Cards redesenhados (compactos, hierarquia visual limpa) e filtro de tema em dropdown pesquisável
- Acessibilidade: skip links, foco visível, `prefers-reduced-motion`, aria labels
- BOM UTF-8 removido de todo o repositório (causava gap visual no header e quebrava o CI via `pyproject.toml`)
- Hierarquia de acesso: grupos Root/Administrador FNP/Usuário via `setup_roles`, `bruno.marra@fnp.org.br` promovido a Root
- Histórico de mérito conectado: `EdicaoMeritoHistorico` agora é gravado de fato (Admin e reingestão), não só um model dormente no schema
- Fórum redesenhado: métricas (comentários/participantes/visualizações), avatar, nome de exibição e resposta encadeada funcional
- `Usuario` (auth) separado de `Perfil` (município/telefone/cargo), 1-para-1 via signal — migração `0005_usuario_perfil_split` com backfill

### Itens validados (nesta última rodada)

- `python manage.py check` → sem issues
- `pytest` → 10/10 OK
- Migração `0005` testada localmente (backfill de Perfil confirmado) e via CI (roda do zero)
- Screenshot headless Chrome do fórum redesenhado
- CI verde em `dadosfnp/legislativo-fnp` (run `30573017778`)

### Pendências e próximos passos

- Dividir `apps/legislativo` em apps por domínio (proposições/comentários/usuários) — sinalizado como gap estrutural, não executado ainda por ser migração de app_label de alto risco; aguardando decisão de escopo
- Obter credenciais reais do Google OAuth (`GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`) — bloqueado no usuário, documentado em `docs/runbook.md`
- Rodar `sync_legado_firestore`/`sync_camara` contra o banco de produção (só rodado localmente até agora)
- Migrar produção de SQLite para PostgreSQL
- Integração com o Senado (hoje só Câmara via `sync_camara`)

---

## Documentação Técnica

| Arquivo | Conteúdo |
|---|---|
| `README.md` | Visão geral do projeto e fluxo de repositórios |
| `docs/runbook.md` | Operação e procedimentos de execução |
| `docs/adr/0001-initial-architecture.md` | Arquitetura inicial do projeto |
| `CONTRIBUTING.md` | Padrões de contribuição |

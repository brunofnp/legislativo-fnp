# ADR 0002 — Deploy em produção e domínio `legislativo.fnp.org.br`

- **Status:** Implementado, no ar desde 2026-08-05.
- **Contexto temporal:** infraestrutura preparada em 2026-08-03, deploy real
  em 2026-08-05, hardening/ajustes contínuos desde então (ver seção
  "Linha do tempo" e `CLAUDE.md` para o detalhe sessão a sessão).

Este documento consolida **como** o Painel Legislativo FNP foi colocado no
ar em `legislativo.fnp.org.br`: a decisão de arquitetura, a infraestrutura
real provisionada, o passo a passo técnico e a cronologia real do que
aconteceu (incluindo os incidentes encontrados e corrigidos no caminho).
`docs/runbook.md` continua sendo a referência operacional viva (comandos
prontos pra copiar/colar); este ADR é o registro de **por que** e **como
foi da primeira vez**, não muda a cada sessão.

---

## Contexto

O projeto precisava sair do ambiente local (SQLite, `runserver`) para um
ambiente de produção real, acessível publicamente, com HTTPS e um domínio
institucional da FNP. Duas decisões de infraestrutura já vinham prontas
antes de qualquer código de deploy ser escrito:

- **Droplet compartilhado, não dedicado**: `fnp-web` já existia na
  DigitalOcean hospedando outros sistemas da FNP (`ifem`, `fnp`,
  `fnp-homolog`) — decisão consciente de reaproveitar a máquina em vez de
  provisionar uma nova, aceitando o trade-off de que mudanças de
  infraestrutura compartilhada (Nginx, reboot do SO) afetam todos os
  sistemas juntos, não só o nosso.
- **Postgres gerenciado compartilhado, não dedicado**: cluster
  `fnp-database` (DigitalOcean Managed Database) também já hospedava outros
  sistemas (`ifem_app`, `fnp_financeiro`, `nucleo_dados`/`nucleo_carga`),
  com 1 database + 1 role dedicados por sistema dentro do mesmo cluster —
  mesmo padrão dos demais, não um cluster novo só para o Legislativo.

O Claude Code **nunca teve acesso SSH direto** ao droplet nem ao banco —
todo comando de infraestrutura foi conduzido pelo usuário via SSH/painel da
DigitalOcean, com os comandos exatos passados pelo Claude Code durante a
sessão.

---

## Infraestrutura provisionada

| Recurso | Detalhe |
|---|---|
| Droplet | `fnp-web`, região NYC1, 2 GB RAM, IP `142.93.205.222` |
| Banco | `fnp-database` (DigitalOcean Managed Database), região NYC3, PostgreSQL, 4 GB RAM / 2 vCPU / 60 GiB, "Primary only" (sem standby node) |
| Role/database do app | role `legislativo`, database `legislativo_fnp` (nomes confirmados no painel — diferentes do que a documentação inicial assumia) |
| Domínio | `legislativo.fnp.org.br`, DNS gerenciado no painel da própria DigitalOcean (Networking → Domains — **não** é Cloudflare nem outro provedor) |
| TLS | Let's Encrypt via `certbot --nginx`, renovação automática |
| Container runtime | Docker + Docker Compose |
| Servidor web | Nginx (reverse proxy compartilhado com os outros sistemas do droplet) → Gunicorn (dentro do container, porta 8004, presa em `127.0.0.1`) |
| Estáticos | WhiteNoise dentro do container + Nginx servindo `/static/`/`/media/` direto de um caminho no host (volume montado) |

---

## Decisão de arquitetura de deploy

**Docker + Nginx**, não deploy direto no host (nem PaaS gerenciado tipo
Heroku/Render). Justificativa: reaproveita o mesmo padrão dos outros
sistemas já rodando no droplet compartilhado, isola dependências Python do
resto da máquina, e o `Dockerfile`/`docker-compose.yml` viram parte do
repositório (reprodutível, versionado).

Nenhuma mudança de código Django foi necessária para essa decisão —
`DATABASE_URL` (via `dj-database-url`), `psycopg2-binary`, `gunicorn` e
`whitenoise` já estavam em `requirements.txt`/`settings.py` desde antes de
qualquer trabalho de containerização começar.

Peças criadas especificamente para o deploy:

- `Dockerfile` — imagem Python 3.12-slim, usuário não-root (`appuser`,
  UID 1000), `entrypoint.sh` roda `migrate` + `collectstatic` antes do
  Gunicorn subir.
- `docker-compose.yml` — serviço `legislativo` (app) + serviço
  `sync-camara` (ingestão contínua, hoje desativado por padrão via
  `profiles`, ver Pendências).
- `.dockerignore`.
- `.gitattributes` — força LF em `*.sh`, porque editar `entrypoint.sh` no
  Windows sem isso quebra o container Linux (`\r\n` no shebang).
- `.env.production.example` — template do `.env` real do droplet, com
  `ALLOWED_HOSTS=legislativo.fnp.org.br` e a connection string do
  `fnp-database` já preenchidos (só os segredos ficam de fora).
- `deploy/nginx-legislativo.conf` — bloco Nginx isolado, `server_name
  legislativo.fnp.org.br`, `alias` batendo com `STATIC_ROOT`/`MEDIA_ROOT`.

---

## Processo passo a passo

Ordem seguida (e a seguir em qualquer deploy do zero futuro, ex. um
segundo ambiente):

1. **Reconhecimento do droplet antes de tocar em nada**: `free -h`,
   `docker ps`, `docker stats --no-stream` — confirmar headroom real de
   RAM antes de subir mais um container num droplet compartilhado.
2. **Trusted Sources do banco**: adicionar o droplet `fnp-web` em Trusted
   Sources do `fnp-database` (aba Settings no painel DO) — sem isso a
   conexão cai mesmo com credencial certa.
3. **Role/database dedicados**: confirmar `legislativo`/`legislativo_fnp`
   já provisionados via painel (não criar via `psql` direto — usuário
   criado pelo painel fica com senha recuperável pela interface, criado
   por SQL não fica). Testar conexão via `psql` do próprio droplet antes
   de seguir; se der erro de permissão, `GRANT` via `doadmin` (só para
   esse passo — credencial administrativa do cluster inteiro, nunca vai
   pro `.env` da aplicação).
4. **Clonar o repo no droplet** via Deploy Key SSH read-only; criar o
   `.env` de produção manualmente no servidor a partir de
   `.env.production.example` (não vem do clone — `.env` real nunca é
   commitado).
5. **Build e subida**: `docker compose build && docker compose up -d`.
6. **Validar por túnel SSH antes de tocar no Nginx público**: `ssh -L
   8004:localhost:8004 root@142.93.205.222`, abrir
   `http://localhost:8004` local — confirma que o app funciona por trás
   do Gunicorn antes de expor pra internet.
7. **Só depois, instalar o bloco Nginx** (`deploy/nginx-legislativo.conf`)
   — `nginx -t` sempre antes de `systemctl reload nginx`, já que um erro
   aqui derruba os *outros* sistemas do droplet também.
8. **DNS**: domínio `legislativo.fnp.org.br` apontado no painel
   Networking → Domains da própria DigitalOcean (registro A pro IP do
   droplet) — ação manual pontual, feita direto pelo usuário no painel.
9. **TLS**: `sudo certbot --nginx -d legislativo.fnp.org.br` — gera o
   certificado e já ajusta o bloco Nginx (`listen 443 ssl`, redirect
   80→443) automaticamente.

---

## Linha do tempo real (o que aconteceu de fato)

### 2026-08-03 — Containerização preparada

Todos os arquivos de containerização (`Dockerfile`, `docker-compose.yml`,
`entrypoint.sh` etc.) escritos e commitados nesta sessão, a partir de um
guia de deploy fornecido pelo usuário com a infraestrutura já provisionada
e confirmada no dashboard real (droplet + banco já existiam). `manage.py
check` limpo; **build Docker local não pôde ser testado** (Docker Desktop
sem o daemon rodando na máquina usada para o desenvolvimento) — a primeira
validação de fato só aconteceu no deploy real, dois dias depois.

### 2026-08-05 — Primeiro deploy real, com uma cadeia de incidentes

Deploy efetivamente rodando pela primeira vez, via SSH conduzido pelo
usuário. **O site caiu logo depois de subir**, com problemas em cadeia —
todos corrigidos na mesma sessão:

1. **CSS/JS voltando 404** — `docker-compose.yml` não montava
   `staticfiles/` como volume; `collectstatic` gravava só dentro do
   container, mas o Nginx serve `/static/` direto de um caminho no host.
   Fix: `./staticfiles:/app/staticfiles` adicionado ao compose.
2. **Container em restart loop (502 Bad Gateway)** — o volume novo foi
   criado como `root:root` (criado via `sudo`), mas o processo roda como
   `appuser` (UID 1000, sem privilégio de root no `Dockerfile`) — sem
   permissão de escrita. Fix: `chown -R 1000:1000` no host.
3. **Certificado SSL perdido** — um `cp` de
   `deploy/nginx-legislativo.conf` por cima do arquivo já em produção (só
   pra sincronizar um ajuste de comentário) apagou os blocos que o
   certbot tinha adicionado (`listen 443 ssl`, `ssl_certificate`, redirect
   80→443). Fix: `certbot --nginx` de novo, opção "reinstall". **Lição
   permanente**: todo `cp` desse arquivo por cima do config em produção
   precisa ser seguido de certbot de novo.
4. **Banco de produção com dado errado** — o serviço `sync-camara` (busca
   contínua por palavra-chave na API da Câmara) subiu sozinho *antes* de
   qualquer importação do legado, e populou 71 proposições sem nenhuma
   curadoria da FNP. Fix: banco zerado e reimportado via
   `sync_legado_firestore` → 104/104 batendo com o legado real.
5. **Import do legado quebrando no meio** — links de notícia do Google
   News no Firestore legado chegam a 714 caracteres, mas `Noticia.url`
   era um `URLField` padrão (200 chars) — `StringDataRightTruncation`
   derrubava o comando inteiro sem isolar por registro. Fix: migration
   ampliando o campo pra 1000 chars.
6. **Root preso na própria tela de aprovação de cadastro** — banco de
   produção novo, ninguém ainda com `is_staff=True`, e
   `CadastroPendenteMiddleware` bloqueia todo mundo que não seja staff —
   inclusive quem seria o Root. Fix: `python manage.py setup_roles`
   (idempotente) — **precisa rodar manualmente em todo banco de produção
   novo do zero**, não acontece sozinho.

Depois desses seis fixes, `curl` contra `https://legislativo.fnp.org.br/`
passou a responder `200 OK` com HTML real da home — data efetiva de "no
ar" do projeto.

### Hardening e ajustes de infraestrutura pós-deploy (resumo)

Trabalho contínuo nas sessões seguintes, detalhado sessão a sessão em
`CLAUDE.md` (buscar pelas datas abaixo):

- **2026-08-06** — cabeçalhos de segurança de produção (HSTS, cookies
  seguros, `SECURE_SSL_REDIRECT`), upgrade Django 4.2→5.2 LTS.
- **2026-08-07** — limite de upload de foto de perfil no Nginx
  (`client_max_body_size 6M`, inserido linha a linha no config já em
  produção pra não repetir o incidente do certificado perdido).
- **2026-08-11** — auditoria de infraestrutura completa por SSH: SSH
  key-only confirmado, `ufw` conferido, **Cloud Firewall da DigitalOcean
  confirmado** (camada separada do `ufw` local, só libera 22/80/443),
  **Trusted Sources do banco confirmado restrito** (só o droplet + 1 IP
  fixo, nunca "Allow all"), volume de `media/` corrigido (mesmo risco de
  permissão do incidente original), rotação de credenciais expostas em
  capturas de tela (senha do `doadmin`, Google Client Secret), Sentry
  ativado (e usado pra achar um bug real de healthcheck no mesmo dia —
  ver abaixo), `sync-camara` desativado por `profiles` no
  `docker-compose.yml` depois de voltar a poluir o banco com proposições
  não curadas.
- **Healthcheck do container corrigido** — o `curl` interno do
  healthcheck usava `Host: localhost:8004`, rejeitado pelo Django
  (`DisallowedHost`, só `legislativo.fnp.org.br` está em
  `ALLOWED_HOSTS`) — container aparecia `unhealthy` mesmo servindo `200
  OK` de verdade via Nginx. Fix: `-H "Host: legislativo.fnp.org.br"` no
  `curl` do healthcheck.
- **Arquivo `.conf.save` órfão** — sobra de uma edição anterior via
  `nano` no `/etc/nginx/sites-enabled/`, causando aviso de "conflicting
  server name" (não afetava outros sistemas, só duplicava o nosso) —
  removido.

---

## Estado atual

- **URL**: `legislativo.fnp.org.br`, no ar desde 2026-08-05.
- **Confirmado de ponta a ponta** repetidas vezes ao longo do projeto via
  `docker compose ps` (`healthy`) + `curl -sI` (`200 OK` com todos os
  cabeçalhos de segurança esperados) — checagem padrão depois de todo
  deploy novo.
- **Fluxo de promoção**: `next` (dev) → `main` (produção) via
  fast-forward, replicado em dois remotos (`origin` pessoal +
  `production` da organização) → deploy manual no droplet via SSH
  (`git pull && docker compose build && docker compose up -d`) —
  **nunca automático**, sempre com autorização explícita do usuário a
  cada promoção.

## Pendências relacionadas à infraestrutura

Ver a seção "Pendências e próximos passos" em `CLAUDE.md` para a lista
completa e atualizada. Os itens de infraestrutura em aberto no momento
em que este ADR foi escrito:

- Atualizações de SO + Docker pendentes com reboot — adiado de propósito
  porque o droplet hospeda outros sistemas da FNP; precisa de janela
  combinada com quem administra os demais.
- Droplet `fnp-web` sem backup próprio (só o `fnp-database` tem).
- `EMAIL_BACKEND` de produção ainda sem provedor real configurado
  (SMTP/SES/etc.) — bloqueia a entrega de fato dos e-mails que o app já
  dispara (confirmação de conta, aviso de cadastro pendente).
- `PermitRootLogin yes` ainda ligado no droplet (baixa prioridade dado
  `PasswordAuthentication no` — só chave SSH, sem força bruta de senha
  possível).

# Runbook

## Ambiente local (Windows) — usar Python 3.12, não 3.14

Django 4.2 só suporta oficialmente até Python 3.12. No Python 3.14 (verificado
nesta máquina), um bug interno do próprio Django (`copy.copy()` sobre
`RequestContext` em `django/template/context.py`) quebra **toda tela de
listagem do Admin e a maioria das telas de adicionar/editar**, com
`AttributeError: 'super' object has no attribute 'dicts'`. Não é um bug deste
projeto — não afeta o CI (roda em Python 3.11) nem produção.

Solução: rodar o servidor local sempre pelo virtualenv `.venv` (Python 3.12),
já criado neste repositório (ignorado pelo git):

```powershell
.venv\Scripts\python.exe manage.py runserver
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py test
```

Se o `.venv` precisar ser recriado (ex.: outra máquina), sempre criar o
virtualenv **já com o nome final** (não criar com outro nome e renomear —
isso quebra os caminhos internos do venv no Windows):

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
```

## Deploy

```powershell
python manage.py migrate
python manage.py collectstatic --noinput
```

### Containerização (Docker + Nginx no droplet `fnp-web`)

`Dockerfile`, `docker-compose.yml`, `entrypoint.sh`, `.dockerignore` e
`.gitattributes` (força LF em `*.sh` — editar `entrypoint.sh` no Windows sem
isso quebra o container Linux) já estão no repo, prontos para uso; nenhuma
mudança de código foi necessária (`DATABASE_URL`/`dj-database-url`,
`psycopg2-binary`, `gunicorn` e `whitenoise` já estavam em
`requirements.txt`/`settings.py`). Ambiente real confirmado no dashboard da
DigitalOcean: droplet `fnp-web` (NYC1, 2 GB RAM, IP `142.93.205.222`) e
banco gerenciado `fnp-database` (NYC3, PostgreSQL, 4 GB RAM / 2 vCPU / 60 GiB,
já existente — **não criar cluster novo**, usar 1 database + 1 role
dedicados nele, ver seção "Banco de produção" abaixo). Domínio de produção
confirmado: **legislativo.fnp.org.br**.

Dois arquivos de apoio já prontos, com os valores reais preenchidos (só
faltam os segredos):

- `.env.production.example` — template do `.env` do droplet, já com
  `ALLOWED_HOSTS=legislativo.fnp.org.br` e o `DATABASE_URL` com os hosts
  público e privado reais do `fnp-database`
- `deploy/nginx-legislativo.conf` — bloco Nginx isolado pronto para copiar,
  já com `server_name legislativo.fnp.org.br` e os `alias` batendo com
  `STATIC_ROOT`/`MEDIA_ROOT` do `settings.py`

Passos a rodar via SSH no droplet (fora do alcance do Claude Code — sem
acesso SSH ao servidor):

1. **Reconhecimento antes de tudo**: `free -h`, `docker ps`, `docker stats --no-stream`
   no `fnp-web` para confirmar headroom real de RAM antes de subir mais um
   container (a documentação pode estar desatualizada quanto ao que já roda
   lá). Droplet (NYC1) e banco (NYC3) estão em regiões diferentes — o painel
   do `fnp-database` oferece host de rede pública e host de rede VPC
   privada (`private-fnp-database-do-user-...`), mas isso só é alcançável
   se as VPCs das duas regiões estiverem peered. Testar as duas rotas a
   partir do próprio droplet antes de decidir (`nc -zv <host> 25060` ou
   tentar `psql` direto em cada uma) — preferir a privada se conectar
   (menor latência, não depende de allowlist de IP público), com fallback
   pra pública (`sslmode=require`, com o droplet nas Trusted Sources).
   De qualquer forma, medir a latência real com `\timing` no `psql` antes
   de assumir que não importa.
2. Adicionar o droplet `fnp-web` em **Trusted Sources** do `fnp-database`
   (aba Settings do banco no dashboard DO) — sem isso a conexão é recusada
   mesmo com credencial correta.
3. Criar a role/database dedicados (`legislativo_app` / `legislativo`) — ver
   "Banco de produção" abaixo.
4. Clonar o repo no droplet via Deploy Key SSH read-only, criar o `.env` de
   produção manualmente no servidor a partir de `.env.production.example`
   (não vem do clone — nunca commitar o `.env` real),
   `docker compose build && docker compose up -d`.
5. Validar por túnel SSH (`ssh -L 8004:localhost:8004 root@142.93.205.222`,
   abrir `http://localhost:8004` local) **antes** de tocar no Nginx público.
6. Só depois, instalar `deploy/nginx-legislativo.conf` (instruções de
   instalação no próprio arquivo) — `nginx -t` antes de `systemctl reload
   nginx`, já que um erro aqui derruba os outros sistemas
   também. TLS via certbot, domínio apontado no Cloudflare.

## Popular o banco com dados reais

### 1. Dados históricos do app legado (legislativo-fnp.web.app)

O app anterior guardava 104 proposições curadas (com temas, notícias e
histórico) num projeto Firestore público (`legislativo-fnp`). Para trazer
esses dados para o banco atual:

```powershell
python manage.py sync_legado_firestore
```

- É idempotente (usa `update_or_create` pelo título da proposição), então
  pode ser rodado de novo sem duplicar registros.
- Use `--keep-json caminho.json` para guardar uma cópia do JSON baixado.
- Use `--dry-run` para validar sem gravar no banco.

**Esse comando precisa ser executado manualmente em cada ambiente** (dev,
produção) — não roda sozinho no deploy, já que depende de uma chamada de
rede externa ao Firestore.

### 2. Atualização contínua via API da Câmara dos Deputados

```powershell
python manage.py sync_camara --keywords "municípios,municipal,prefeituras,FPM" --watch 1800
```

`--watch N` mantém o processo rodando em loop, sincronizando a cada N
segundos — pensado para rodar como serviço/processo persistente (ex.:
supervisor/systemd no droplet), já que a Câmara e o Senado não oferecem
webhook de atualização em tempo real.

**Rodando como serviço permanente:** ver template em `deploy/sync-camara.service`
(systemd) com as instruções de instalação no próprio arquivo. Se o app rodar
em Docker no droplet (`fnp-web`), prefira um serviço adicional no
`docker-compose.yml` usando a mesma imagem da aplicação — exemplo comentado
também está no template. Nenhuma das duas opções está instalada em produção
ainda; isso precisa ser feito por quem tem acesso SSH ao droplet.

## Banco de produção (PostgreSQL / DigitalOcean)

A variável `DATABASE_URL` já é lida pelo `settings.py` via `dj-database-url`.
Defina-a no `.env` de produção com a connection string real do Postgres —
sem essa variável, o app usa SQLite.

Cluster gerenciado já existente: `fnp-database` (4 GB RAM / 2 vCPU / 60 GiB,
"Primary only" — sem standby node hoje; padrão da casa é 1 cluster
compartilhado, N databases, 1 por sistema — não criar cluster novo). Rodar
como `doadmin` via `psql` (a partir do droplet ou console do banco no
dashboard DO) **só para este passo** — a credencial `doadmin`/`defaultdb` é
administrativa do cluster inteiro (compartilhada com outros sistemas da
FNP) e nunca deve ir para o `.env` da aplicação; a app sempre roda com a
role dedicada criada abaixo (privilégio mínimo, só no database `legislativo`):

```sql
CREATE ROLE legislativo_app LOGIN PASSWORD '<gerar com: openssl rand -hex 24>';
CREATE DATABASE legislativo OWNER legislativo_app;
REVOKE ALL ON DATABASE legislativo FROM PUBLIC;
GRANT ALL ON DATABASE legislativo TO legislativo_app;
-- conectando no database "legislativo":
GRANT ALL ON SCHEMA public TO legislativo_app;
ALTER SCHEMA public OWNER TO legislativo_app;
```

Connection string (Connection Details do `fnp-database` no dashboard,
trocando database/usuário para os de cima):

```text
postgresql://legislativo_app:<senha>@<host-do-cluster>:25060/legislativo?sslmode=require
```

Guardar em dois lugares: `.env` do droplet (uso) e Bitwarden (backup) —
nunca no git.

## Login (conta própria + Google)

A autenticação usa `django-allauth`. Cadastro/login/logout já funcionam com
e-mail e senha (`/contas/login/`, `/contas/signup/`, `/contas/logout/`).

Para o botão "Continuar com Google" funcionar de verdade, é preciso criar um
OAuth Client no Google Cloud Console:

1. <https://console.cloud.google.com/apis/credentials> → "Criar credenciais" →
   "ID do cliente OAuth" → tipo "Aplicativo da Web".
2. Em "Origens JavaScript autorizadas", adicionar o domínio do app (ex.:
   `https://painel.fnp.org.br`).
3. Em "URIs de redirecionamento autorizados", adicionar
   `https://<seu-dominio>/contas/google/login/callback/`.
4. Copiar o Client ID e o Client Secret gerados para `GOOGLE_CLIENT_ID` e
   `GOOGLE_CLIENT_SECRET` no `.env` de cada ambiente.

Sem essas variáveis preenchidas, o botão do Google aparece mas o login via
Google não completa (erro do próprio Google, não do nosso app).

## Validações locais recomendadas antes de publicar

```powershell
python manage.py check
python manage.py test apps.legislativo
python manage.py collectstatic --noinput
```

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

## Banco de produção (PostgreSQL / DigitalOcean)

A variável `DATABASE_URL` já é lida pelo `settings.py` via `dj-database-url`.
Defina-a no `.env` de produção com a connection string real do Postgres
(DigitalOcean ou outro provedor) — sem essa variável, o app usa SQLite.

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

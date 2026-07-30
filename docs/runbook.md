# Runbook

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

## Validações locais recomendadas antes de publicar

```powershell
python manage.py check
python manage.py test apps.legislativo
python manage.py collectstatic --noinput
```

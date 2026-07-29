# Painel Legislativo FNP

Este repositório contém o backend Django e o frontend server-renderizado para o Painel Legislativo da Frente Nacional de Prefeitas e Prefeitos.

## Objetivo

Construir um rewrite Django do painel legislativo existente, seguindo o padrão de arquitetura do projeto Radar Brasil.

## Estrutura

- `apps/` — apps Django por domínio
- `setup/` — configuração do projeto Django (settings, urls, wsgi/asgi)
- `templates/` — templates Django
- `base_templates/` — blocos compartilhados de layout
- `static/` — assets estáticos
- `docs/` — documentação do projeto

## Instalação

1. Criar e ativar um virtualenv Python 3.11+
2. `pip install -r requirements.txt`
3. Copiar `.env.example` para `.env`
4. `python manage.py migrate`
5. `python manage.py runserver`

## Desenvolvimento

- Use `python manage.py runserver` para executar localmente.
- Crie um superuser com `python manage.py createsuperuser`.
- Testes: `pytest`

## Fluxo de repositórios

Este projeto usa dois remotes com papéis distintos:

- `origin` → repositório de desenvolvimento no perfil pessoal: `brunofnp/legislativo-fnp`
- `production` → repositório de produção na organização: `dadosfnp/legislativo-fnp`

### Branches

- `next` → branch principal de desenvolvimento
- `main` → branch de produção

### Fluxo diário

1. Trabalhe sempre na branch `next`.
2. Faça commits locais normalmente.
3. Envie as alterações para o desenvolvimento:
   `git push origin next`
4. Quando estiver pronto para produção, faça merge ou cherry-pick da branch `next` para `main` no repositório de produção e envie:
   `git push production main`

### Sincronização rápida

- Verificar status:
  `git status`
- Trocar para a branch de desenvolvimento:
  `git checkout next`
- Atualizar a branch local com o remoto:
  `git pull origin next`

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

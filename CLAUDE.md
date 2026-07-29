# CLAUDE.md — Contexto do Projeto Legislativo FNP

> Arquivo de contexto para sessões com Claude Code. Atualizado ao final de cada expediente.
> Última atualização: 2026-07-29

---

## Visão Geral

**Legislativo FNP** é uma plataforma Django para acompanhamento legislativo voltada ao monitoramento de proposições em tramitação no Congresso Nacional e ao impacto para municípios. A proposta é reunir um painel institucional, visual profissional e fluxo de participação colaborativa para a Frente Nacional de Prefeitas e Prefeitos.

URL de produção: GitHub Pages/hosting definido pela organização (branch `main` do remoto `production`)
Branch de desenvolvimento ativo: `next`

---

## Stack Tecnológica

| Camada | Tecnologia |
|---|---|
| Backend | Django 4.2.x · Python 3.14 |
| Banco (dev) | SQLite |
| Banco (prod) | PostgreSQL (planejado para futuro) |
| Templates | Django Templates + CSS/JS vanilla |
| Estáticos | WhiteNoise |
| Dados | Modelos Django + importação via management commands |
| UI | HTML semântico, CSS customizado, JavaScript vanilla |
| Testes | Django TestCase + pytest |

---

## Estrutura de Arquivos

```
apps/
  legislativo/
    admin.py
    models.py
    views.py
    urls.py
    forms.py
    tests.py
    management/
      commands/
        ingest_legislativo.py
static/
  css/
    style.css
  js/
    main.js
  favicon.svg
templates/
  base.html
  legislativo/
    home.html
    proposicao_detail.html
    participacao_list.html
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
- modelar proposições, macrotemas, temas, comentários, participação e histórico
- renderizar a homepage com cards de briefing legislativo
- exibir detalhes de proposições em modal
- suportar fluxo de participação e comentários

### Padrão atual de UI

- Layout institucional com identidade visual FNP
- Home com hero, métricas, filtro por tema, busca e cards de briefing
- Modal de detalhes com conteúdo executivo e contexto de tramitação
- Estilo responsivo, pensado para desktop e mobile

### Funcionalidades já implementadas

- Home com listagem de proposições
- Filtros por texto e macrotema
- Estatísticas resumidas por total, pauta, urgentes e alta prioridade
- Modal de detalhes via JS e API interna
- Endpoint SSE/polling para atualização de dados em tempo real
- Estrutura preparada para comentários e participação cidadã/forum

---

## Modelos principais

### Proposicao

Campos principais:
- `titulo`
- `casa`
- `status_tramitacao`
- `local`
- `pauta`
- `urgente`
- `aprovada`
- `parada`
- `prioridade_fnp`
- `tema`
- `macrotema`
- `ementa_resumida`
- `proximos_eventos`
- `interlocutores`
- `ultima_movimentacao`
- `link`
- `posicionamento_fnp`
- `acoes_incidencia`
- `riscos_oportunidades`

### Macrotema / Tema

- `Macrotema` organiza a classificação editorial das proposições
- `Tema` representa subcategorias mais específicas

### Participacao / Comentario

- `Participacao` permite registrar contribuições, sugestões, dúvidas ou indicações
- `Comentario` é a base para um futuro fórum/participação estruturada

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

## Regras de colaboração

1. **Nunca** adicionar `Co-Authored-By: Claude` em commits
2. **Nunca** inserir "Generated with Claude Code" em PRs ou commits
3. O autor dos commits deve ser `brunofnp`
4. Manter documentação atualizada quando houver mudanças significativas
5. Priorizar compatibilidade mobile em todas as alterações
6. Usar `next` para desenvolvimento e `main` para produção

---

## Estado Atual do Projeto (2026-07-29)

### Branch atual: `next`

### Conquistas implementadas

- Estrutura inicial Django do painel legislativo criada e estabilizada
- Home com layout institucional e cards de briefing legislativo
- Filtros por busca e macrotema
- Estatísticas de proposições
- Modal de detalhes com carga dinâmica via API
- Estrutura para comentários e participação criada
- CSS responsivo aplicado para mobile e desktop
- Favicon e identidade visual básica configurados
- Testes de regressão adicionados para a homepage

### Itens validados

- `python manage.py check` → sem issues
- `python manage.py test apps.legislativo` → 2 testes OK
- `python manage.py collectstatic --noinput` → assets coletados com sucesso
- Home respondendo com status `200`

### Pendências e próximos passos

- integrar carga real de dados legislativos em vez de dados de exemplo
- evoluir o fluxo de participação para fórum mais robusto
- consolidar a camada de API para atualização dinâmica em tempo real
- revisar detalhes da identidade visual com base em referências institucionais reais

---

## Documentação Técnica

| Arquivo | Conteúdo |
|---|---|
| `README.md` | Visão geral do projeto e fluxo de repositórios |
| `docs/runbook.md` | Operação e procedimentos de execução |
| `docs/adr/0001-initial-architecture.md` | Arquitetura inicial do projeto |
| `CONTRIBUTING.md` | Padrões de contribuição |

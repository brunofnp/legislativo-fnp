# Design — Alertas individuais de proposições (MVP)

- **Data:** 2026-10-29
- **Autor:** Ronan Castro (Coordenação de Finanças Públicas e Assuntos Legislativos)
- **Status:** proposto (aguardando revisão)
- **Bloco:** 1 de 4 do sistema de monitoramento em camadas (ver "Fora de escopo")

## Contexto

O Painel Legislativo hoje mostra um monitoramento público único, curado pela equipe
do Legislativo. Não há como um colaborador acompanhar proposições específicas e ser
avisado quando elas se movem — ele precisa reabrir o painel e conferir à mão.

A visão completa (discutida em 2026-10-29) é um monitoramento em camadas: público,
interno por área (gerência) e individual, com workflow de aprovação da coordenação do
Legislativo (Ingrid Freitas) e alertas. Este spec cobre **apenas a primeira fatia**: o
**alerta individual** — a mais independente e a que entrega o pedido original ("sistema
de alerta no sistema e no e-mail do cadastrado, com a opção de receber atualizações por
e-mail").

## Objetivo

Permitir que um usuário aprovado **siga** proposições (lista por conta) e seja avisado
**no sistema** (sempre) e **por e-mail** (opcional, opt-in) quando uma proposição seguida
se movimenta.

## Decisões travadas

| Tema | Decisão |
|---|---|
| Quem pode seguir | Qualquer usuário **aprovado e logado** (equipe FNP, prefeitos, indicados, parlamentares). |
| Seguir × favoritar | **Separados.** O favoritar (estrela) continua por sessão, funciona anônimo. "Seguir" (sino) é ação nova por conta, só logado, e é o que gera alerta. |
| Canal no sistema | Sempre. Reusa o model `Notificacao` e a UI do sino do topo. |
| Canal e-mail | **Opt-in** por `Perfil.receber_email_atualizacoes` (padrão desligado). |
| Cadência do e-mail | **Na hora** — enviado quando a movimentação é detectada. Sem agendamento no servidor. |
| Envio de e-mail | Reusa o `GmailApiEmailBackend` já em produção. Best-effort: falha de e-mail nunca quebra o `save()`/ingest. |

## O que conta como "movimentação"

Mudança, no `save()` de uma `Proposicao` **já existente**, em qualquer um destes campos
(`CAMPOS_ALERTA`): `status_tramitacao`, `ultima_movimentacao`, `pauta`, `urgente`,
`aprovada`, `prioridade_fnp`.

- Proposição **nova** (created) não dispara alerta — ninguém a segue ainda.
- A detecção usa o mesmo padrão de diff do `EdicaoMeritoHistorico` (comparar valores
  anteriores com os novos).
- Pega todos os caminhos de escrita: `ingest_legislativo`, edição no Django Admin
  (`ProposicaoAdmin.save_model`) e qualquer `.save()` futuro.

## Arquitetura

Unidades pequenas e isoladas, seguindo os apps de domínio existentes.

### 1. Model `ProposicaoSeguida` (app `proposicoes`)

Watchlist por conta — separada do favoritar por sessão. Mora em `apps/proposicoes`
(é sobre proposições). A lógica de alerta (signal + e-mail) mora em `apps/comentarios`
(onde vive `Notificacao`), conectada no `comentarios/apps.py::ready()` — assim
`proposicoes` não importa `comentarios` (evita import circular).

```
ProposicaoSeguida
  usuario      FK AUTH_USER_MODEL  (related_name="proposicoes_seguidas")
  proposicao   FK Proposicao       (related_name="seguidores")
  criado_em    DateTimeField(auto_now_add=True)
  Meta: UniqueConstraint(usuario, proposicao)  # seguir é idempotente
```

- **O que faz:** registra que um usuário segue uma proposição.
- **Como se usa:** `toggle_seguir(request, pk)` (view), `proposicao.seguidores`, `user.proposicoes_seguidas`.
- **Depende de:** `Proposicao`, `Usuario`.

### 2. Campo `Perfil.receber_email_atualizacoes`

`BooleanField(default=False)`. Opt-in. Editável em `/perfil/` e no Admin.

### 3. `Notificacao` — dois campos novos

- `tipo = CharField(choices=[('comentario','Comentário'),('movimentacao','Movimentação')], default='movimentacao')`
  - As notificações de comentário existentes passam a `tipo='comentario'` (migração de dados).
  - Só `tipo='movimentacao'` gera e-mail.
- `enviado_email = BooleanField(default=False)` — marca o que já virou e-mail (evita reenvio; útil se a cadência virar resumo no futuro).

### 4. Detecção e disparo (signal)

`apps/comentarios/alertas.py` (ou `signals.py`):

- `pre_save(Proposicao)`: lê o estado anterior do banco e guarda o diff dos `CAMPOS_ALERTA`.
- `post_save(Proposicao)`: se não é `created` e houve diff, chama `notificar_seguidores(proposicao, mudancas)`.
- `notificar_seguidores`:
  1. Para cada `seguidor` (via `proposicao.seguidores`), cria uma `Notificacao`
     (`tipo='movimentacao'`, mensagem curta tipo "PEC 18/2025 mudou de status: …").
  2. Para cada seguidor com `perfil.receber_email_atualizacoes=True` e e-mail válido,
     envia um e-mail (best-effort, `try/except`, log em caso de falha) e marca
     `enviado_email=True`.
- **Robustez:** todo o bloco de e-mail é `try/except` e nunca propaga exceção para o
  `save()` — a `Notificacao` no sistema é a fonte da verdade; o e-mail é bônus.

### 5. E-mail

- `apps/comentarios/emails.py::enviar_email_alerta(usuario, proposicao, mudancas)`.
- Usa `EmailMultiAlternatives` com o backend padrão (`GmailApiEmailBackend` em prod).
- Template `templates/emails/alerta_movimentacao.{txt,html}`: título da proposição, o que
  mudou, link da ficha de tramitação (`proposicao.link`), link do painel e link do
  `/perfil/` para gerenciar/desativar (LGPD).

### 6. UI

- Botão **Seguir** (sino) no card (`_proposicao_card.html`) e no detalhe
  (`proposicao_detail.html`), só para usuário logado/aprovado. Toggle via
  `toggle_seguir` (POST, mesmo padrão de `toggle_favorito`).
- Checkbox **"Receber atualizações por e-mail"** em `/perfil/` (PerfilForm/PerfilDadosForm).
- As notificações aparecem no sino do topo que já existe (context_processor
  `notificacoes`) — nenhuma UI nova de listagem é necessária no MVP.
- Página opcional "Seguindo" (reaproveita o padrão de `favoritos_list`) — **fora do MVP**,
  anotada como melhoria.

## Fluxo de dados

```
ingest_legislativo / Admin edita Proposicao
        │  .save()
        ▼
pre_save captura diff dos CAMPOS_ALERTA ──► post_save detecta movimentação
        │
        ▼
notificar_seguidores(proposicao, mudancas)
        ├─► cria Notificacao(tipo=movimentacao) para cada seguidor  (sino, sempre)
        └─► se perfil.receber_email_atualizacoes: envia e-mail (best-effort)
```

## Tratamento de erros

- Falha de envio de e-mail: capturada, logada, não interrompe o `save()`/ingest; a
  notificação no sistema permanece.
- Usuário sem e-mail válido: pulado no envio, notificação no sistema normal.
- Seguir duas vezes: `UniqueConstraint` torna idempotente (toggle).

## Testes (padrão RequestFactory do projeto, em `apps/legislativo/tests.py`)

1. Seguir e deixar de seguir cria/remove `ProposicaoSeguida` (idempotente).
2. `save()` que muda um `CAMPO_ALERTA` cria `Notificacao(tipo=movimentacao)` para o seguidor.
3. `save()` que muda campo fora de `CAMPOS_ALERTA` **não** cria notificação.
4. Proposição nova (created) **não** notifica.
5. E-mail só é enviado para seguidor com `receber_email_atualizacoes=True`; falha de
   e-mail não quebra o `save()`.
6. Toggle do opt-in em `/perfil/` persiste o campo.
7. Notificação de comentário continua `tipo='comentario'` e não gera e-mail.

## Deploy / infra

- Migrações: novo model + 1 campo no `Perfil` + 2 campos no `Notificacao` (com migração de
  dados marcando as notificações antigas como `tipo='comentario'`).
- **Sem agendamento no servidor** (cadência "na hora").
- Entra por **PR na `main` do `dadosfnp/legislativo-fnp`** (mesmo fluxo da atualização de
  prioridades); a ingestão/execução em produção e o merge seguem decisão do time.
- Revisão de segurança recomendada (form público/novo endpoint `toggle_seguir`, envio de
  e-mail) — ver `security-and-hardening` no CLAUDE.md.

## Fora de escopo (próximos blocos)

- **Bloco 2 — Monitoramento em 3 escopos:** público / interno por área (gerência) /
  individual; model de acompanhamento por escopo.
- **Bloco 3 — Workflow de aprovação:** área submete inclusão/nota/posicionamento → Ingrid
  autoriza (via Adan/Ricardo) → publica.
- **Bloco 4 — Áreas e papéis:** gerências como áreas; coordenador/gerente/colaborador;
  monitoramento interno visível a todo o Legislativo + coordenação/gerência da área.
- Resumo diário de e-mail (se "na hora" se mostrar ruidoso — o campo `enviado_email` já
  prepara o caminho).
- Página "Seguindo" dedicada.

## Riscos e mitigações

- **Rajada de e-mail** quando o ingest atualiza muitas proposições seguidas de uma vez:
  aceitável no MVP (cada usuário segue poucas); se incomodar, trocar para resumo diário
  (código já preparado com `enviado_email`).
- **Auto-notificação** do editor que fez a mudança no Admin: baixo impacto; pode-se pular o
  autor numa iteração futura.
- **Volume de e-mail síncrono no ingest:** limitado por (seguidores × proposições seguidas
  que mudaram); best-effort com `try/except` evita travar o ingest.

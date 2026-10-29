# Design — Cadastro de proposição no painel (com aprovação)

- **Data:** 2026-10-29
- **Autor:** Ronan Castro (Coordenação de Finanças Públicas e Assuntos Legislativos)
- **Status:** proposto (aguardando revisão)
- **Relação:** fatia do sistema de monitoramento em camadas; traz uma primeira versão do
  workflow de aprovação (bloco 3). Independente do spec de alertas individuais.

## Contexto

Hoje proposições entram no painel só por `ingest_legislativo` (JSON curado) ou pelo Django
Admin (Root/Administrador FNP). Não há como a equipe da FNP **incluir uma proposição pelo
próprio painel**, de forma simples. A coordenação do Legislativo quer um cadastro enxuto,
em que se digita apenas a identidade da proposição e o sistema busca o resto na fonte
oficial.

## Objetivo

Permitir que um colaborador da FNP cadastre uma proposição no painel informando **só tipo,
número e ano**; o sistema **busca automaticamente** os dados oficiais (Câmara e Senado) e
cria a proposição. Submissões de colaboradores comuns entram **pendentes** e só aparecem no
painel público após **aprovação** da coordenação do Legislativo. Submissões de aprovadores
são publicadas direto.

## Decisões travadas

| Tema | Decisão |
|---|---|
| Entrada do formulário | Só **tipo** (PL, PEC, PLP, PLN, MPV…), **número** e **ano**. |
| Busca automática | **Câmara + Senado** (tenta Câmara; se não achar, Senado). O usuário não escolhe a casa. |
| Quem pode cadastrar | **Equipe FNP** (`Perfil.classe_usuario = Equipe FNP`) **ou** membro do grupo **Administrador FNP** (cobre o Ricardo/Contatos, externo), logado e aprovado. Público externo (prefeito/parlamentar) não vê o cadastro. |
| Fila de aprovação | Submissão de colaborador comum → **pendente**. Submissão de aprovador → **publicada direto**. |
| Quem aprova | Grupo **Administrador FNP** (Ingrid, Ronan, Adan, Ricardo). Ingrid é a autoridade; Adan/Ricardo operam. |
| Onde aprova | **Tela no próprio painel** ("Pendentes de aprovação"), fora do Django Admin. |
| Curadoria (posicionamento, prioridade, ações) | Fora deste slice — feita depois (Admin ou fluxo próprio). |

## Papéis

- **Colaborador FNP** (Equipe FNP, não aprovador): cadastra → pendente.
- **Aprovador** (grupo Administrador FNP): cadastra → publica direto; aprova/rejeita pendentes.

## Fluxo

```
Colaborador FNP abre "Cadastrar proposição"  →  digita tipo + número + ano
        │
        ▼
Busca oficial (Câmara; fallback Senado) → título, casa, status, local,
        última movimentação, ementa, link (ficha de tramitação)
        │
        ├─ submetido por aprovador?  → status_publicacao = 'publicada'
        └─ senão                     → status_publicacao = 'pendente'
        │
        ▼
Pendentes aparecem em "Pendentes de aprovação" (só aprovadores)
        ├─ Aprovar  → 'publicada' (registra aprovador + data)
        └─ Rejeitar → 'rejeitada' (registra + motivo opcional)
        │
        ▼
Painel público mostra só status_publicacao = 'publicada'
```

## Arquitetura

### 1. Campos novos em `Proposicao`

```
status_publicacao  CharField(choices=[pendente, publicada, rejeitada], default='publicada')
submetido_por      FK User null  (quem cadastrou pelo painel; null para ingest/admin)
aprovado_por       FK User null
aprovado_em        DateTimeField null
motivo_rejeicao    TextField blank
```

- **Migração de dados:** todas as proposições existentes (as 113) e as criadas por
  `ingest_legislativo`/Admin recebem `status_publicacao='publicada'` (o default já cobre).
  O cadastro pelo painel é o único caminho que grava `pendente`.

### 2. Módulo de busca oficial — `apps/proposicoes/fontes.py`

Funções puras e testáveis, reutilizáveis pelo cadastro e pelo `sync_camara`:

- `buscar_camara(tipo, numero, ano) -> dados | None`
  API Dados Abertos da Câmara: `GET /proposicoes?siglaTipo=&numero=&ano=` → `id` →
  `GET /proposicoes/{id}` (ementa, situação, órgão, última movimentação). Link =
  `https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={id}`.
- `buscar_senado(tipo, numero, ano) -> dados | None`
  API Dados Abertos do Senado (endpoints verificados em 2026-10-29):
  `GET https://legis.senado.leg.br/dadosabertos/processo?sigla=&numero=&ano=` (traz
  `codigoMateria`, `ementa`, `autoria`, `dataSituacaoAtual`) ou
  `GET .../materia/{sigla}/{numero}/{ano}`. Link =
  `https://www25.senado.leg.br/web/atividade/materias/-/materia/{codigoMateria}`.
- `buscar_proposicao(tipo, numero, ano) -> dados | None`: tenta Câmara, depois Senado;
  normaliza para o mesmo dicionário (título `SIGLA N/ANO`, casa, status, local, última
  movimentação, ementa, link).

### 3. Views / URLs (app `legislativo`)

- `cadastrar_proposicao` (GET formulário, POST processa) — login + Equipe FNP.
  Idempotente por título (`update_or_create`): se já existe, atualiza a ficha e avisa
  "já está no painel".
- `proposicoes_pendentes` (lista) — só aprovadores.
- `aprovar_proposicao(pk)` / `rejeitar_proposicao(pk)` (POST) — só aprovadores.
- Navegação: item **"Cadastrar"** para Equipe FNP; **"Pendentes (N)"** para aprovadores.

### 4. Visibilidade pública (ponto crítico)

Todas as consultas públicas (home, listagens, busca, cards, `api_proposicoes_cards`,
detalhe, favoritos, "em alta") passam a filtrar `status_publicacao='publicada'`. Centralizar
num manager/queryset (`Proposicao.publicadas`) para não esquecer nenhum ponto. A tela de
pendentes é a única que mostra `pendente`.

### 5. Formulário

`CadastroProposicaoForm`: `tipo` (ChoiceField com as siglas suportadas), `numero`
(IntegerField), `ano` (IntegerField, validação 1988–ano atual+1). Sem campos de mérito.

## Tratamento de erros

- Não encontrada em nenhuma fonte → erro no formulário: "Proposição não encontrada; confira
  tipo, número e ano."
- API oficial fora do ar / timeout → erro amigável, sem criar registro incompleto; permite
  tentar de novo.
- Título já existente → não duplica; atualiza a ficha e informa.

## Testes (padrão RequestFactory, em `apps/legislativo/tests.py`)

1. `buscar_camara`/`buscar_senado` normalizam o retorno (com `requests` mockado).
2. `buscar_proposicao` cai para o Senado quando a Câmara não acha.
3. Cadastro por colaborador comum → `pendente`; por aprovador → `publicada`.
4. Proposição não encontrada → formulário com erro, nada criado.
5. Views públicas (home/listagem/detalhe) **não** mostram `pendente`/`rejeitada`.
6. `aprovar_proposicao`/`rejeitar_proposicao` mudam o status e registram autor/data;
   não-aprovador recebe 403.
7. Idempotência: cadastrar título existente não duplica.

## Deploy / infra

- Migrações: campos novos em `Proposicao` + migração de dados marcando as existentes como
  `publicada`.
- Chamadas HTTP a APIs externas (Câmara/Senado) no fluxo de cadastro — timeout curto,
  best-effort, nunca deixam registro pela metade.
- Entra por **PR na `main` do `dadosfnp/legislativo-fnp`**; merge e deploy seguem o time.
- **Revisão de segurança** (novo formulário público-interno, endpoints de aprovação, chamada
  a API externa) — ver `security-and-hardening` no CLAUDE.md.

## Fora de escopo (próximos blocos)

- Curadoria rica (posicionamento, prioridade, ações, riscos) pelo painel — hoje via Admin.
- Monitoramento **interno por área** e submissão das áreas para o público (blocos 2 e 4).
- Aviso aos aprovadores quando chega submissão — integra com o spec de **alertas**
  (reusa `Notificacao`); pode ser acoplado quando os dois slices existirem.
- Senado: campos mais ricos (tramitação detalhada) além de ementa/situação/link.

## Riscos e mitigações

- **Esquecer um ponto de visibilidade pública** e vazar pendentes: mitigado centralizando
  em `Proposicao.publicadas` e cobrindo com teste (item 5).
- **Divergência de formato entre Câmara e Senado:** `buscar_proposicao` normaliza para um
  dicionário único; testes com mock de cada fonte.
- **Mudança de contrato das APIs oficiais:** isolado em `fontes.py`; falha vira erro
  amigável, não quebra o painel.

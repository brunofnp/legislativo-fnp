# Sentinela Tributária (CBS/IBS) — design

Data: 2026-11-05

## Objetivo
Avisar o Legislativo da FNP sempre que **subir uma proposição nova sobre CBS/IBS**
(reforma tributária) no Congresso — sino + e-mail — e já deixar a matéria na fila
de curadoria. Palavras-chave **editáveis** pela equipe (sem código).

## Decisões (confirmadas com o usuário)
1. **Gatilho:** varredura automática das APIs oficiais (não espera alguém cadastrar).
2. **Destino:** cria a proposição como **pendente** (fila de Pendentes) + alerta.
3. **Destinatários:** todo o Leg da FNP — sino **e e-mail sempre** (institucional,
   independe do opt-in individual).
4. **Palavras-chave configuráveis:** admin adiciona/remove termos.
5. Parte 1 (alerta individual das proposições monitoradas) **não muda** — já existe
   (seguir → sino + e-mail opt-in); só confirmação de pipeline.

## App próprio: `sentinela`
Novo app Django (evita colisão de migração com os PRs abertos #4/#5).

### Modelos
- `TermoSentinela`: `termo`, `ativo`, `criado_em`. Lista de palavras-chave da
  varredura (seed: CBS, IBS, "Contribuição sobre Bens e Serviços", "Imposto sobre
  Bens e Serviços", "reforma tributária", "IVA", "Imposto Seletivo", "LC 214",
  "comitê gestor do IBS", "split payment"). Editável no admin.
- `ItemSentinelaVisto`: `fonte`, `id_externo`, `titulo`, `visto_em`,
  único por (fonte, id_externo). Evita re-alertar o mesmo item.

### Fontes (`fontes.py`)
- **Câmara** (`dadosabertos` `/proposicoes?keywords=`): robusto, fonte principal.
- **Senado**: gancho best-effort; a busca por palavra do dadosabertos foi
  descontinuada — entra quando houver endpoint novo. Nunca quebra (try/except → []).

### Comando: `sentinela_tributaria [--baseline] [--dry-run] [--dias N]`
1. Lê os termos ativos.
2. Busca candidatos (Câmara + Senado) apresentados nos últimos N dias (default 15).
3. Filtra pela **ementa** (confirma o termo no texto — os acrônimos CBS/IBS dão
   falso-positivo) e **dedupe** (ItemSentinelaVisto e proposição já no painel por link).
4. `--baseline`: marca os atuais como vistos **sem** alertar/criar (primeira execução).
5. Para cada nova: cria `Proposicao` **pendente** (título = número oficial, casa,
   ementa, link da ficha, macrotema "Reforma Tributária") e alerta todo o Leg:
   `Notificacao(tipo='sentinela')` + e-mail (sempre).
6. Nunca publica sozinho — respeita a curadoria (igual ao `sync-camara`, desligado).

### Notificação / e-mail
- `comentarios.Notificacao` ganha `TIPO_SENTINELA` (migração comentarios/0012).
- E-mail via backend Gmail já em produção; templates `emails/alerta_sentinela.{txt,html}`.
- Destinatários = time FNP (`is_staff` ou `Perfil.classe_usuario == equipe_fnp`).

### Agendamento
Cron diário na droplet (Bruno) ou `/schedule`. Primeira execução: `--baseline`.

## Fora de escopo
- Senado por palavra-chave (endpoint oficial descontinuado).
- Publicar automaticamente (curadoria é humana, via fila de Pendentes).
- Outros temas além do tributário (mas os termos são genéricos: basta cadastrar).

## Testes
Fontes mockadas: match novo cria pendente + notifica Leg + e-mail; baseline não
alerta; dedupe (já visto / já no painel); ementa sem termo é ignorada; dry-run não
grava; termos inativos não são buscados.

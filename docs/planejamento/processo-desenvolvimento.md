# Jarvis-1 — Processo de Desenvolvimento

**Versão:** 1.0
**Data:** 2026-06-07
**Status:** Documento vivo — referência oficial de processo
**Inspirado em:** metodologia do Projeto Alice (gap analysis, agentes de dev, DOR/DOD, risk registry)

---

## Sumário
0. [Ritual de Início de Fase](#kickoff)
1. [Filosofia](#filosofia)
2. [Agentes de Desenvolvimento](#agentes)
3. [Convenções](#convencoes)
4. [Git Flow](#gitflow)
5. [Estratégia de Testes](#testes)
6. [Política de Logging](#logging)
7. [Release Management](#release)
8. [Risk Registry](#riscos)

---

## 0. Ritual de Início de Fase {#kickoff}

> **Regra de processo (obrigatória).** Nenhuma fase começa a codar antes de ser **adaptada a este
> modelo**. O PLANO.md descreve a *intenção* da fase; o ritual abaixo a converte em backlog
> executável e coerente com o resto do projeto. Conduzido pelo `project-owner` + `architect`.

Ao iniciar a Fase N:
1. **Reler o PLANO.md** da fase e confrontar com o estado real do código (o que já existe / mudou).
2. **Análise de adequação:** a fase ainda faz sentido dado o que aprendemos nas fases anteriores?
   Há decisão nova (ex.: pesquisa, correção de modelo) que altera o escopo? Registrar desvios.
3. **Coerência com o resto do projeto:** a fase prepara o que as fases seguintes assumem? Não
   antecipa nem deixa buraco? Dependências entre fases explicitadas.
4. **Design estrutural único (architect):** decidir UMA vez a estrutura-alvo que as features da fase
   vão compartilhar (ex.: máquina de estados do `main.py`), para as features plugarem nela em vez de
   cada uma reescrever o mesmo código.
5. **Fatiar em features** `feat/<nome>` com DOR/DOD, encadeadas por dependência (atualizar
   `roadmap-features.md`).
6. **Revisar o Risk Registry** (§8): quais RSK esta fase toca? Mitigação ativa para cada um.
7. **Confirmar decisões de UX/escopo com o usuário** antes de codar (não decidir sozinho).
8. Só então: `git checkout develop && git checkout -b feat/<primeira-feature>`.

O resultado do ritual é um **Relatório de Status da Fase** (formato no `project-owner`) aprovado
antes da primeira linha de código.

---

## 1. Filosofia {#filosofia}

> **Fluidez primeiro, depois arsenal.** A v0.1.0 prova que o pipeline funciona. As dores são de
> *interação* (latência, wake word, alucinação), não de capacidade. Consertamos a experiência
> antes de empilhar ferramentas — mantendo o cérebro **local e grátis** (zero tokens pagos).

Princípios:
- **Determinismo sobre mágica:** preferir gate por classificador + regra fixa a confiar em ML probabilístico para decisões binárias.
- **Cada feature é usável:** nenhuma fase entrega algo meio-construído pior que a anterior.
- **Validação por uso real + log:** sem suíte pesada de E2E; smoke test + pytest em lógica pura + conversa real.
- **Escopo da fase é lei:** não antecipar features futuras (evita refactor e desperdício).

---

## 2. Agentes de Desenvolvimento {#agentes}

> **Distinção:** estes são agentes de **desenvolvimento** (rodam no Claude Code, ajudam a CONSTRUIR
> o Jarvis). Não confundir com os **tools/skills runtime** do Jarvis (o que o assistente USA — ver
> `roadmap-features.md`). O orquestrador é `.claude/agents/project-owner.md`.

| ID | Agente | Propósito | Quando invocar |
|----|--------|-----------|----------------|
| AD01 | **architect** | Garante que a feature se encaixa nas camadas (áudio→wake→vad→stt→llm→tts) e respeita o gate classificador→gerador | Antes de qualquer decisão estrutural |
| AD02 | **coder** | Implementa em Python 3.12 seguindo convenções; código que roda no Windows (cp1252-safe) | Após architect aprovar o design |
| AD03 | **reviewer** | Revisa com checklist (correção, latência, encoding, async, logging, testes) | OBRIGATÓRIO após cada entrega do coder |
| AD04 | **tester** | Escreve pytest para lógica pura; valida DOD; smoke `check_deps.py` | Em paralelo ao coder (TDD) ou logo após |
| AD05 | **documenter** | Atualiza PLANO.md, CLAUDE.md, CHANGELOG, docstrings | Ao fim de feature que muda comportamento observável |
| AD06 | **release-manager** | Semver, changelog a partir de commits, tag `v0.N.0`, merge develop→main | Ao fechar uma fase |
| AD07 | **optimizer** | Mede e melhora latência (wake, STT, LLM TTFT, TTS RTF, turno total) | Quando feature afeta latência percebida |
| AD08 | **risk-mitigator** | Mantém o Risk Registry; ativa mitigação quando risco sobe de nível | Início de cada fase + quando risco materializa |

**Checklist do reviewer (AD03):**
```
[ ] Roda no Windows: sem caractere não-ASCII em print(); encoding="utf-8" em todo open()
[ ] Sem silêncio puro indo ao Whisper (gate antes)
[ ] Chamadas longas ao llama-server são streaming / não travam o loop
[ ] Todo except tem LOGGER/print de erro com contexto
[ ] Latência dentro do orçamento (ver CLAUDE.md) quando aplicável
[ ] Tem teste correspondente (pytest) OU justificativa (código de I/O puro)
[ ] check_deps.py continua 22/22
[ ] Sem TODO/FIXME órfão; logs de debug marcados como efêmeros
[ ] Segue o escopo da feature — nada de fase futura
```

---

## 3. Convenções {#convencoes}

### 3.1 Commits (Conventional Commits)
```
<tipo>(<escopo>): <descrição em pt-BR, imperativo>

Tipos:  feat fix refactor test docs perf chore style
Escopos: audio wake vad stt llm tts tools config main ci docs

Exemplos:
  feat(wake): integrar openWakeWord com modelo hey_jarvis
  fix(stt): ligar vad_filter para cortar alucinacao de silencio
  perf(llm): medir TTFT do Qwen3-8B em Vulkan
  test(vad): cobrir limiar de fim de fala do Silero
```

### 3.2 Naming Python
```python
def transcrever_comando(...)        # snake_case funções
class WakeWordDetector: ...          # PascalCase classes
MAX_SILENCE_MS = 300                 # UPPER_SNAKE constantes
_estado_interno = ...                # prefixo _ para privado
```

### 3.3 Estrutura de testes
```
tests/
├── test_vad.py          # limiares de fim de fala, gate
├── test_wake.py         # detecção de wake word (com áudios fixos)
├── test_stt_filter.py   # pós-filtro de alucinação (compression_ratio, blocklist)
├── test_tools.py        # parsing de tool calls
└── fixtures/            # WAVs curtos: silencio.wav, hey_jarvis.wav, comando.wav
```

---

## 4. Git Flow {#gitflow}

```
main                      — releases estáveis, sempre taggeada (v0.1.0, v0.2.0...)
└── develop               — integração contínua das features
    ├── feat/owww-wake    — feature branch (curta, < poucos dias)
    ├── feat/silero-vad
    └── fix/...

Regras:
- Toda feature parte de develop:  git checkout develop && git checkout -b feat/<nome>
- Merge da feature em develop ao satisfazer o DOD (--no-ff para preservar história)
- develop → main SÓ ao fechar a fase, seguido de tag v0.N.0
- Hotfix crítico: hotfix/<nome> a partir de main, merge em main E develop
- Nunca force-push em main ou develop
```

**Esquema de versões (alinhado às fases do PLANO.md):**
```
v0.1.0  Fase 0  — Fundação Windows (CONCLUÍDA)
v0.2.0  Fase 1  — Fluidez (wake word, VAD, barge-in, anti-alucinação)
v0.3.0  Fase 2  — Tool calling (template Qwen3, KV q8_0, system prompt)
v0.4.0  Fase 3  — Ferramentas + segurança (confirmação de voz)
v0.5.0  Fase 4  — Browser (Playwright)
v0.6.0  Fase 5  — Online (Open-Meteo)
v0.7.0  Fase 6  — MCP
Patches: v0.2.1, v0.2.2... para fixes dentro da fase
```

---

## 5. Estratégia de Testes {#testes}

Pirâmide enxuta (projeto solo, sem CI pesado no início):
```
        / conversa real \      ← poucos: validação manual por uso + log
       /  smoke / deps    \    ← check_deps.py (ambiente 22/22)
      /    pytest (puro)    \   ← muitos: VAD, pós-filtro, parsing, config
```

- **Unit (pytest):** lógica determinística — limiares de VAD, pós-filtro de alucinação
  (`compression_ratio > 2.4`, blocklist), parsing de tool calls, leitura de config.
- **Áudio fixo:** fixtures WAV curtos (`silencio.wav`, `hey_jarvis.wav`) para testar wake/VAD sem microfone.
- **Smoke:** `check_deps.py` deve seguir 22/22 após qualquer mudança de ambiente.
- **Validação final:** conversa real + inspeção de log (padrão do projeto).

**DOD mínimo por fase:** funcionalidade-alvo demonstrada em conversa real + testes de lógica pura passando + sem regressão no smoke.

---

## 6. Política de Logging {#logging}

Sistema multi-camada assíncrono → sem log robusto, debugar depende de reproduzir manualmente.

| Categoria | O que logar | Exemplo |
|-----------|-------------|---------|
| `[EVENT]` | entrada/saída de eventos do loop | `[EVENT] estado IDLE -> ESCUTANDO (wake=0.71)` |
| `[CALL]` | chamadas externas com latência | `[CALL] llama-server TTFT=820ms tokens=142 status=OK` |
| `[PROC]` | processamentos não-triviais | `[PROC] VAD endpoint — silencio=320ms, fim de fala` |
| `[FLOW]` | dados entre camadas | `[FLOW] STT -> LLM: "que horas sao"` |
| `[TIME]` | tempo por etapa do turno | `[TIME] turno=1.8s (stt=0.6 llm=0.9 tts=0.3)` |

Regras:
1. Todo `except` loga o erro com contexto (proibido catch silencioso).
2. **No console Windows: nada de não-ASCII** (sem emoji/→/✓) — quebra em cp1252.
3. Logs de debug são **efêmeros**: marcados `[debug]`, removidos quando a feature estabiliza.
4. Níveis: ERROR (falha) · WARN (recuperável) · INFO (lifecycle) · DEBUG (diagnóstico, off em release).

---

## 7. Release Management {#release}

```
1. DOD da fase = 100%  ✅
2. pytest passa + check_deps 22/22  ✅
3. Latência dentro dos orçamentos (CLAUDE.md)  ✅
4. CHANGELOG.md + docs atualizados  ✅
5. Merge develop -> main (--no-ff)
6. git tag -a v0.N.0 -m "Fase N: <nome>"
7. (opcional) git push origin main develop --tags
8. Conversa real de sanidade
```

---

## 8. Risk Registry {#riscos}

Classificação: Prob × Impacto → BLOCK / Act / Watch / Accept (matriz do Alice).

| ID | Risco | Prob | Impacto | Mitigação | Fase |
|----|-------|------|---------|-----------|------|
| RSK01 | Alucinação do Whisper em silêncio/pausa | Alta | Alto | Gate por openWakeWord+Silero (classificador não gera texto) + pós-filtro `compression_ratio`/`no_speech_prob` + blocklist | 1 |
| RSK02 | openWakeWord "hey_jarvis" sem test set → falso-aceite/rejeite | Média | Médio | `vad_threshold` nativo + verifier de 2º estágio + ajuste de limiar por uso real; fallback Whisper p/ "jarvis" | 1 |
| RSK03 | Template Qwen3 não descreve tools → tool calls ruins | Alta | Alto | `--chat-template-file` corrigido (Hermes/Unsloth) + `--jinja` + `--verbose` p/ inspeção | 2 |
| RSK04 | KV q4_0 degrada tool calling | Média | Alto | `--cache-type-k/v q8_0` (cabe nos 8GB) | 2 |
| RSK05 | Latência de turno > 2s mata a fluidez | Média | Alto | Medir TTFT/RTF (optimizer); streaming sentença-a-sentença; endpointing Silero corta tempo morto | 1 |
| RSK06 | Barge-in falha por ruído do Jabra (matou na v0) | Média | Médio | Trocar VAD-RMS por Silero VAD no `mic_vad_background` | 1 |
| RSK07 | Mic do Jabra "dorme" (liga/desliga) | Média | Médio | Keepalive de saída contínuo (0.05s) + detecção de mic morto + reconexão com aviso sonoro | 1 |
| RSK08 | Subprocessos órfãos (llama-server) | Baixa | Médio | `stop_server` + `atexit`; nunca matar à força sem tentar graceful | todas |
| RSK09 | Encoding cp1252 quebra I/O no Windows | Média | Médio | `encoding="utf-8"` sempre; sem não-ASCII em print() | todas |
| RSK10 | Escopo cresce → meio-construído pior que v0.1.0 | Média | Alto | Feature curta com DOD claro; cada merge em develop é usável | todas |

Processo: revisar registry no início de cada fase; ativar mitigação quando risco sobe; post-mortem quando materializa.

---

## Referências
- Projeto Alice — `processo-desenvolvimento.md`, `regras.md`, `agentes.md` (metodologia-base)
- `docs/WHISPER_SILENCE_ANALYSIS.md` — fundamentação de RSK01 com fontes primárias
- [openWakeWord](https://github.com/dscripka/openWakeWord) — `vad_threshold`, modelo hey_jarvis, frames 80ms
- [Silero VAD](https://github.com/snakers4/silero-vad) — endpointing

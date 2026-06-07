# Jarvis-1 — Roadmap de Features por Ciclo (Git Flow)

**Versão:** 1.0
**Data:** 2026-06-07
**Base:** `docs/PLANO.md` (fases) + `docs/planejamento/processo-desenvolvimento.md` (processo)

> Cada **feature** = uma branch `feat/<nome>` partindo de `develop`, com DOR (pronto p/ começar) e
> DOD (pronto p/ merge). Uma **fase** fecha quando todas as suas features estão em `develop`, o DOD
> da fase é validado em conversa real, e então `develop → main` + tag `v0.N.0`.

Legenda DOR = *Definition of Ready* · DOD = *Definition of Done*.

---

## FASE 1 — FLUIDEZ → `v0.2.0` (próxima)

**Objetivo:** tornar a interação fluida e robusta. Eliminar lag de ativação, tempo morto e
alucinação. Esta é a fase que faz o Jarvis "funcionar bem pra caramba" no dia a dia.

**Ordem das features (encadeadas por dependência):**

### F1.1 — `feat/owww-wake` · Wake word dedicado (openWakeWord)
- **Substitui:** o loop Whisper-de-2.5s em `listen_for_wakeword()` (`main.py`).
- **Por quê:** openWakeWord é **classificador** (saída 0–1), não gera texto → **elimina** a
  alucinação de wake word (RSK01) por construção.
- **Como (verificado):** `Model(wakeword_models=["hey_jarvis.onnx"], inference_framework="onnx",
  vad_threshold=0.5)`; frames de **1280 samples (~80ms)** @16kHz; `model.predict(frame)` → dict de
  scores; ativa quando score > limiar. O `vad_threshold` **já integra Silero VAD nativo** como gate.
- **DOR:** baixar `hey_jarvis.onnx` + deps do openWakeWord; áudio contínuo 16kHz já existe (`read_mic_chunk`).
- **DOD:**
  - [ ] Ativa com "Hey Jarvis" de forma quase instantânea (< 50ms/frame)
  - [ ] **Zero** ativações com texto-fantasma em silêncio (rodar 5 min em silêncio → 0 falsos)
  - [ ] Remove os `print` de debug do loop antigo (limpeza pendente da v0.1.0)
  - [ ] `test_wake.py` com fixtures (`hey_jarvis.wav` ativa, `silencio.wav`/`ruido.wav` não)
  - [ ] Fallback documentado: manter Whisper p/ "jarvis" se o usuário recusar a frase

### F1.2 — `feat/silero-endpoint` · Endpointing com Silero VAD
- **Substitui:** RMS + 1.2s de silêncio em `record_until_silence()` (`audio.py`).
- **Por quê:** detectar fim de fala no instante exato corta ~1.5s de tempo morto por turno (RSK05).
- **DOR:** F1.1 mergeada; `silero-vad` instalado (ONNX).
- **DOD:**
  - [ ] Transcrição dispara < 300ms após o usuário parar de falar
  - [ ] Não corta no meio de pausa curta de pensamento (limiar `min_silence_ms` calibrado)
  - [ ] `test_vad.py` cobre limiar positivo/negativo/boundary com fixtures

### F1.3 — `feat/stt-antialuc` · Pós-filtro determinístico de alucinação
- **Adiciona:** camada de rejeição após o Whisper de comando (defesa em profundidade).
- **Como (verificado):** rejeitar segmento se `compression_ratio > 2.4` (repetição) **ou**
  `no_speech_prob > 0.6` **ou** texto ∈ blocklist conhecida ("legendas pela comunidade amara.org",
  "até o próximo vídeo", etc.). `vad_filter=True` já ligado em `stt.py`.
- **DOR:** F1.2 mergeada.
- **DOD:**
  - [ ] Frases-fantasma do log da v0 são rejeitadas (teste com texto fixo)
  - [ ] Fala real válida nunca é rejeitada (sem falso-negativo nos fixtures)
  - [ ] `test_stt_filter.py` cobre os 3 critérios

### F1.4 — `feat/barge-in` · Barge-in confiável + robustez de mic
- **Substitui:** VAD-RMS em `mic_vad_background()` por Silero (RSK06); adiciona detecção de mic morto (RSK07).
- **DOR:** F1.2 mergeada (Silero disponível).
- **DOD:**
  - [ ] Dá para interromper a fala do Jarvis falando por cima (sem disparar com ruído do Jabra)
  - [ ] Mic morto é detectado → reconecta → **avisa com som** (não fica surdo calado)
  - [ ] Keepalive de saída mantém Jabra acordado (0.05s) sem artefatos

### F1.5 — `feat/eval-qwen3-4b` · Avaliar Qwen3-4B Q8_0
- **Adiciona:** baixar `Qwen3-4B-Instruct-2507-Q8_0`; comparar tok/s e TTFT vs 8B no uso real.
- **Justificativa:** 4B Q8_0 é mais rápido que 8B Q4_K_M sem degradar tool calling (ver PLANO.md).
- **DOR:** F1.1–F1.4 mergeadas (pipeline fluido p/ comparar feel).
- **DOD:**
  - [ ] TTFT e tok/s medidos (optimizer) para 4B-Q8 vs 8B-Q4
  - [ ] Decisão registrada em `docs/memory/project_jarvis1_context.md`
  - [ ] Modelo escolhido configurado por default

**DOD da FASE 1 (gate para `v0.2.0`):** ativar com "Hey Jarvis" é instantâneo; resposta começa
< 1s após parar de falar; barge-in funciona; mic morto avisa; **zero alucinação em silêncio**;
4B vs 8B comparado e decidido. → merge `develop→main`, tag `v0.2.0`.

---

## FASE 2 — TOOL CALLING → `v0.3.0`

**Objetivo:** Qwen3 emite tool calls confiáveis. Base do arsenal agêntico.

| Feature | Branch | Entrega |
|---------|--------|---------|
| F2.1 | `feat/qwen3-template` | `--chat-template-file` Hermes/Unsloth + `--jinja` + KV `q8_0` (RSK03/04) |
| F2.2 | `feat/inline-toolcall` | Detecção inline de tool_calls no stream (bloqueia só quando ferramenta emitida) |
| F2.3 | `feat/system-prompt` | Reescrever `_build_system_prompt`: declarar capacidades (estilo Hermes, pt-BR, conciso) |

**DOD da fase:** pedir algo que exige ferramenta mostra `[TOOL] nome(args)` no log; resposta sem ferramenta segue fluida.

---

## FASE 3 — FERRAMENTAS + SEGURANÇA → `v0.4.0`

| Feature | Branch | Entrega |
|---------|--------|---------|
| F3.1 | `feat/tool-fs` | `fs.py` — ler/listar/escrever/mover/deletar (stdlib) |
| F3.2 | `feat/tool-window` | janelas via `pygetwindow`+`pywin32` (Windows) |
| F3.3 | `feat/tool-input` | teclado/mouse via `pyautogui`/`pynput` |
| F3.4 | `feat/tool-system` | CPU/RAM/bateria/volume via `psutil` + datetime |
| F3.5 | `feat/safety` | `safety.py` — confirmação por voz em ações destrutivas + allowlist `run_shell` |
| F3.6 | `feat/tool-uia` | (ganho Windows) UI Automation via `uiautomation`/`pywinauto` p/ ler apps desktop |

**DOD da fase:** "abra o Firefox" abre; "apague tal arquivo" **pede confirmação** por voz.

---

## FASE 4 — BROWSER (Playwright) → `v0.5.0`
`feat/browser-playwright`: `navegar`/`ler_pagina`(a11y tree)/`clicar`/`digitar`/`voltar`, sessão persistente com cleanup. Resolve o caso "ver o clima no site" que falhou na v0.

## FASE 5 — ONLINE → `v0.6.0`
`feat/weather-openmeteo` (geocoding + forecast, sem chave) · `feat/web-fetch` (via MCP fetch ou wrapper).

## FASE 6 — MCP → `v0.7.0`
`feat/mcp-bridge`: subir servers Python (fetch/git/time) via stdio, converter schema MCP→TOOL_DEFINITIONS, despachar p/ TOOL_HANDLERS, ciclo de vida com cleanup. Sem Node.

---

## Tools/Skills runtime do Jarvis (o que o assistente USA)
> Análogo às "skills" do Alice. Crescem por fase. Padrão atual: `TOOL_DEFINITIONS` + `TOOL_HANDLERS`
> em `src/tools/__init__.py`. Cada tool nova segue o mesmo contrato (schema + handler + descrição OS-aware).

| Domínio | Tool | Fase |
|---------|------|------|
| shell | `run_shell` (PowerShell/bash, com allowlist) | 0 / 3 |
| arquivos | `fs.*` (ler/listar/escrever/mover/deletar) | 3 |
| desktop | `window.*`, `input.*`, `system.*` | 3 |
| browser | `browser.*` (Playwright a11y) | 4 |
| online | `weather.*`, `web.*` | 5 |
| mcp | servers fetch/git/time | 6 |

---

## Fluxo operacional de cada ciclo (resumo)
```
1. git checkout develop && git pull
2. git checkout -b feat/<nome>           # parte de develop
3. (architect) valida camada/design
4. (coder) implementa + (tester) pytest em paralelo
5. (reviewer) checklist obrigatório
6. (optimizer) mede latência se aplicável
7. DOD da feature satisfeito → merge --no-ff em develop; deletar branch
8. ao fechar todas as features da fase → DOD da fase em conversa real
9. (release-manager) develop→main + tag v0.N.0 + CHANGELOG
```

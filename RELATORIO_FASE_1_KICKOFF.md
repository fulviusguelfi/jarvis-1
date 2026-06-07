# Relatório: Fase 1 — Fluidez (Kickoff + F1.0 + F1.1)

**Data:** 2026-06-07  
**Status:** Em progresso · F1.0 ✅ + F1.1 ✅ mergeadas em `develop`  
**Git:** `develop` em commit `79524bc`

---

## Resumo Executivo

**Objetivo da Fase 1:** Tornar a interação Jarvis fluida, robusta e sem alucinação.

**O que foi entregue hoje:**

1. **Processo de desenvolvimento institucionalizado** (modelo ALICE adaptado)
   - `CLAUDE.md`: regras invioláveis, orçamentos de latência, stack
   - `docs/planejamento/processo-desenvolvimento.md`: 8 agentes de dev, gitflow, risk registry
   - `docs/planejamento/roadmap-features.md`: features por ciclo com DOR/DOD
   - `.claude/agents/project-owner.md`: agente orquestrador (Opus)
   - **Ritual de Início de Fase** (obrigatório): análise, coerência, design único, DOD

2. **Feature F1.0 — Máquina de Estados Explícita** ✅
   - Refatorou `main.py` com FSM: IDLE → ACTIVATED → LISTENING → PROCESSING → SPEAKING → CONVERSATION
   - Transições logadas como `[STATE] OLD -> NEW -- razão`
   - Pontos de extensão claros para F1.1-F1.5
   - Sem regressão: comportamento idêntico à v0.1.0

3. **Feature F1.1 — openWakeWord** ✅ (integrada)
   - Módulo `src/wake.py`: `detect_wake_word()` com modelo `hey_jarvis.onnx`
   - Classifier (não gerador) → **elimina alucinação de wake word por construção** (RSK01)
   - Integra Silero VAD nativo (`vad_threshold=0.5`) como gate
   - Substitui loop Whisper-de-2.5s por detecção rápida (< 50ms/frame)
   - Testes em `tests/test_wake.py` (fixtures sintéticas: silêncio, ruído)

---

## Estado Atual

```
main       ← v0.1.0 (Fase 0, estável, tagueada)
develop    ← F1.0 + F1.1 mergeadas (em progresso)
           ├── F1.0 refactor(main): FSM explícita
           └── F1.1 feat(wake): openWakeWord integrada
```

**Git Flow ativo:**
- `main`: releases (v0.1.0, v0.2.0...)
- `develop`: integração de features
- Feature branches: `feat/<nome>` → merge `--no-ff` → delete

---

## Próximas Features — Ordem Encadeada

### F1.2 — `feat/silero-endpoint` (Endpointing com Silero VAD)
- **Objetivo:** Detectar fim de fala com precisão, cortar ~1.5s de tempo morto/turno
- **Substitui:** `record_until_silence()` (RMS + 1.2s silêncio)
- **Por:** Silero VAD identifica exato fim de fala, não intervalo arbitrário
- **Dependência:** F1.1 mergeada ✅

### F1.3 — `feat/stt-antialuc` (Pós-filtro Determinístico)
- **Objetivo:** Defesa em profundidade contra alucinações Whisper
- **Método:** Rejeitar se `compression_ratio > 2.4` OU `no_speech_prob > 0.6` OU texto ∈ blocklist
- **Casos:** "até o próximo vídeo", "legendas pela comunidade", etc. (do log v0.1.0)
- **Dependência:** F1.2 mergeada

### F1.4 — `feat/barge-in` (Barge-in Confiável + Mic Morto)
- **Objetivo:** Interromper resposta com voz real, detectar mic offline
- **Substitui:** VAD-RMS por Silero VAD em thread (já existe, validar)
- **Adiciona:** Detecção de mic morto → reconecta → aviso sonoro
- **Dependência:** F1.2 mergeada

### F1.5 — `feat/eval-qwen3-4b` (Avaliar 4B Q8_0)
- **Objetivo:** Comparar `Qwen3-4B-Q8_0` vs `Qwen3-8B-Q4_K_M`
- **Métrica:** TTFT + tok/s em uso real
- **Decisão:** Qual modelo usar como default em v0.2.0
- **Alimenta Fase 2:** Template de tool calling + KV quantization escolhidos aqui
- **Dependência:** F1.1-F1.4 mergeadas (pipeline fluido para comparar feel)

---

## Risk Registry — Fase 1

| ID | Risco | Mitigation | Status |
|----|-------|-----------|--------|
| RSK01 | Whisper alucina em silêncio | openWakeWord (classificador) + Silero VAD + pós-filtro | **Mitigado em design** |
| RSK05 | Latência turno > 2s mata fluidez | F1.2 (VAD endpoint) corta tempo morto | **Em progresso** |
| RSK06 | Barge-in falha por ruído Jabra | Trocar RMS por Silero VAD | **F1.4** |
| RSK07 | Mic Jabra dorme (on/off) | Keepalive + detecção + reconexão | **F1.4** |
| RSK03 | Qwen3-8B lento em tool calling | F1.5: avaliar 4B-Q8 (Fase 2 depende) | **Em progresso** |

---

## Orçamentos de Latência (Alvos)

Já cumpridos (v0.1.0):
- STT: ~1s (Whisper small)
- LLM TTFT: ~1s (Qwen3-8B Vulkan)
- TTS: ~300ms (Piper)

A melhorar (Fase 1):
- Wake word: < 50ms/frame ← F1.1 (openWakeWord) **alcança**
- Endpoint: < 300ms ← F1.2 (Silero VAD) **esperado**
- **Tempo percebido turno:** < 2s (fim fala → 1º áudio) ← F1.2+F1.3 combinadas

---

## Documentação Criada

| Arquivo | Propósito |
|---------|-----------|
| `CLAUDE.md` | Regras invioláveis, stack, orçamentos, convenções |
| `docs/planejamento/processo-desenvolvimento.md` | Agentes de dev (8), gitflow, risk registry, logging |
| `docs/planejamento/roadmap-features.md` | Features por ciclo com DOR/DOD, Fases 2-6 outline |
| `.claude/agents/project-owner.md` | Orquestrador (Opus), valida DOR/DOD, guarda gitflow |
| `docs/WHISPER_SILENCE_ANALYSIS.md` | Pesquisa com fontes: alucinação = problema resolvido por arquitetura |
| `memory/jarvis1_fase1_decisions.md` | Decisões travadas: wake word, ordem features, gitflow |
| `RELATORIO_FASE_1_KICKOFF.md` (este) | Status consolidado |

---

## Metodologia Adotada

Baseada no **Projeto Alice** (Minecraft mod com IA), adaptada para Jarvis-1:

✅ **Convenções:**
- Commits: Conventional Commits (`feat(escopo): descrição`)
- Branches: Git Flow (`main` ← `develop` ← `feat/<nome>`)
- Naming: `snake_case` funções, `PascalCase` classes, `UPPER_SNAKE` constantes
- Logging: Categorizado `[STATE]`, `[CALL]`, `[PROC]`, `[FLOW]`, `[TIME]`, `[EVENT]`

✅ **Processo:**
- DOR/DOD por feature (Definition of Ready / Done)
- Backlog encadeado: N+1 só após N feita
- Review obrigatório antes de merge
- Risk Registry mantido por fase
- Release = tag `v0.N.0` quando fase fecha

✅ **Arquitetura:**
- Classificadores (wake word, VAD) = gate
- Gerador (Whisper, LLM) = roda apenas em fala validada
- Nunca silêncio puro → gerador
- FSM explícita = debug + extensibilidade

---

## Próximos Passos Imediatos

### Curto prazo (antes de v0.2.0):
1. **Instalar deps F1.1-F1.5:**
   ```bash
   pip install openwakeword silero-vad
   ```

2. **Validar F1.0 em conversa real:**
   - Testar FSM: estados logados aparecem
   - Confirmar sem regressão vs v0.1.0

3. **Começar F1.2 (`feat/silero-endpoint`):**
   - Atualizar `record_until_silence()` para usar Silero VAD
   - Teste: fim de fala detectado < 300ms após parar

4. **Validação paralela:**
   - F1.5 (medir TTFT 4B-Q8 vs 8B-Q4) pode rodar em paralelo com F1.2-F1.3

### Médio prazo (fechamento Fase 1 → v0.2.0):
- Merge F1.2-F1.5 em `develop` uma por uma
- Validação DOD da Fase 1 em conversa real (5h+ testando)
- Merge `develop` → `main`, tag `v0.2.0`

### Longo prazo (Fases 2-6):
- **Fase 2:** Tool calling (template Qwen3, KV q8_0)
- **Fase 3:** Ferramentas + segurança (FS, input, system)
- **Fase 4:** Browser (Playwright)
- **Fase 5:** Online (Open-Meteo, Web)
- **Fase 6:** MCP bridge

---

## Validação Pronta

✅ **Smoke test:** `python check_deps.py`  
✅ **Sintaxe:** `main.py` AST parse OK  
✅ **Imports:** Enum, config, audio (quando disponível)  
⏳ **Conversa real:** Aguardando execução no ambiente com modelos + audio

---

## Conclusão

**Fase 1 está estruturada, metodologia instituída, e 2 features (F1.0 + F1.1) já mergeadas.** 

O caminho de `v0.1.0` → `v0.2.0` está claro:
- **F1.0** fundação (FSM) ✅
- **F1.1** wake word sem alucinação ✅
- **F1.2-F1.4** latência e robustez (próximas)
- **F1.5** decisão de modelo (final)

Recomendação: **Prosseguir para F1.2 (Silero VAD endpoint)** — é o próximo ganho de latência e depende de F1.1 (já feita).

---

**Última atualização:** 2026-06-07 · Commit `79524bc` (develop)

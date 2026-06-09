---
name: project-jarvis1-context
description: Contexto e decisões arquiteturais do projeto Jarvis-1 — assistente de IA local com voz e controle do PC
metadata: 
  node_type: memory
  type: project
  originSessionId: c8d127f7-6c84-4be8-b8b5-2a3538f9e327
---

# Projeto Jarvis-1

Assistente de IA pessoal inspirado nos vídeos "Jarvis Mark XXXV/XXXIX" e tutoriais de llama.cpp.

**Objetivo:** Replicar a experiência do Gemini 2.5 Flash (voz nativa in/out, conversacional) mas 100% local, sem internet.

**Why:** Privacidade, latência, custo zero de API a longo prazo.

**How to apply:** Todas as decisões técnicas devem priorizar rodar 100% offline. Online é fallback aceitável apenas como fase 1 de desenvolvimento.

---

## Hardware da Máquina Alvo

| Componente | Spec |
|------------|------|
| CPU | AMD Ryzen 5 4500 — 6c/12t @ 4.2GHz |
| RAM | 16GB |
| GPU | AMD Radeon RX 580 — 8GB VRAM |
| OS | SteamOS / Freedesktop SDK 25.08 (Flatpak) |
| ROCm | NÃO suportado (RX 580 foi removido do suporte oficial) |
| Vulkan | SIM — funcional para llama.cpp |

---

## Decisões de Arquitetura (Sessão 2026-06-04)

### Rejeitado: Pipeline fragmentado (Opção C inicial)
- Whisper.cpp → LLM → Kokoro TTS
- Rejeitado por fragmentação, mas TECNICAMENTE é o mais viável no hardware atual.

### Rejeitado: Moshi (Kyutai)
- Full-duplex, single model — ideal conceptualmente
- **Bloqueador:** usa PyTorch. ROCm não suportado no RX 580. Rodaria só em CPU (inviável para real-time).
- Ver [[research-moshi-ultravox]]

### Rejeitado: Ultravox
- Boa performance em benchmarks
- **Bloqueador duplo:** PyTorch (mesmo problema ROCm) + não tem saída de áudio nativa (usa TTS externo)

### Meta: Gemini 2.5 Flash-like experience local
- Único modelo que ouve E fala nativamente E tem tool use
- Candidatos futuros: aguardar modelo open-source com suporte llama.cpp/Vulkan

---

## Stack Definitivo POC (2026-06-06)

```
Whisper small (CPU) → STT
     ↓
Qwen3-8B Q4_K_M (Vulkan RX 580) → LLM (7.6 tok/s warm)
     ↓
Piper faber-medium → TTS (RTF 0.06x — ~0.15s para 3s áudio)
```

**Latência streaming:** ~2-3s ao primeiro áudio (warm), ~4-5s fria.
**vs Flash 2.5 cloud:** 1.5x mais lento, mas 100% offline.
**TTS_MODE**: piper (padrão) | kokoro (~6.9s, mais natural) | qwen3 (RTF 9.6x, não use)

### Configs ativas (.env)
```
LLM_MODE=local
TTS_MODE=piper
PIPER_VOICE=faber
PULSE_SERVER=unix:/run/flatpak/pulse/native
```

Com tool use implementado em Python ao redor do LLM.

---

## Decisões de Modelos (Sessão 2026-06-06)

### Qwen3-8B vs Qwen3.6-35B-A3B (MoE)

| Modelo | Velocidade | Thinking | Uso |
|--------|-----------|---------|-----|
| Qwen3-8B Q4_K_M | 7.8 tok/s | /no_think funciona | Escolhido para Jarvis |
| Qwen3.6-35B-A3B IQ2_XXS | 3.7 tok/s | /no_think NÃO funciona | Rejeitado |

**Decisão:** Qwen3-8B é 2x mais rápido e tem thinking suprimido corretamente.

### Qwen3-TTS-GGUF

- Exportado com sucesso para model-custom/ (Talker q5_k + Predictor q8_0 + Decoder FP16 ONNX)
- TTS module: `src/tts_qwen3.py` — drop-in substituto para tts.py (Kokoro)
- RTF CPU: 9.6x (lento — ~28s para 3s de áudio) → **32s latência total no pipeline**
- RTF Vulkan: TESTADO — GPU ficou a 100% mas levou 7+ minutos (shader compilation na primeira execução do Gated Delta Net; mais testes necessários)
- `TTS_MODE=qwen3` no .env ativa o Qwen3-TTS em vez do Kokoro
- bin/ contém b7798 CPU libs (3.0M libllama.so); backup em bin/b7798_backup/
- **PROBLEMA PENDENTE:** TTS RTF 9.6x é inaceitável para assistente real-time. Alternativas: Piper TTS (0.1x RTF), Kokoro, ou Qwen3-TTS após warm-up de shaders Vulkan

### Arquitetura TTS GGUF

- Vulkan libs do build local substituem b7798 CPU em tools/qwen3-tts-gguf/.../bin/
- Backup em bin/b7798_backup/
- ABI compatível verificado: todos os campos de struct presentes no build local (n_rs_seq, op_offload, swa_full, kv_unified, use_extra_bufts, no_host)
- llama_set_embeddings() já bindado e chamado em llama.py

### llm_local.py flags (Qwen3-8B, confirmados funcionais)
```
-ngl 99 --flash-attn on --ctx-size 4096
--cache-type-k q4_0 --cache-type-v q4_0
--batch-size 512 --ubatch-size 128
```

---

## Decisão F1.5 — Modelo Final para Assistente Local (2026-06-09)

### Qwen3-4B-Instruct-2507 (UD-Q8_K_XL) — ESCOLHIDO

| Aspecto | Qwen3-4B-UD-Q8 | Qwen3-8B-Q4 |
|--------|---|---|
| **Footprint (Q8)** | 5.0 GB | 4.9 GB |
| **VRAM 100%?** | ✅ Sim (sobra ~2GB) | ✅ Sim (sobra ~2GB) |
| **RAM livre (16GB)** | ~10-11 GB | ~9-10 GB |
| **Velocidade** | ~30-45 tok/s | ~18-28 tok/s |
| **Qualidade (MMLU-Pro)** | 69.6 | ~70 estimado |
| **BFCL (tool calling)** | 61.9 | ~60 estimado |
| **Vantagem** | **1.5x mais rápido; DROP-IN** | Margen de qualidade mínimo |

**Decision:** Qwen3-4B-Instruct-2507 (UD-Q8_K_XL).
- Benchmark oficial (HF card) mostra que empata/supera Qwen3-30B-A3B no MMLU-Pro e BFCL.
- Deixa a máquina **usável**. Sem 35B MoE que ocupava 18GB + overhead, o PC fica livre pra outras tarefas.
- **DROP-IN:** mesmo template que o 8B, mesmo --reasoning off, mesmas tools.
- **Testado:** 17/17 testes verdes, startup ~15s, resposta limpa ~1-2s.

**Alternativas descartadas:**
- Qwen3-8B: similar, mas um pouco mais lento.
- Gemma 4 E4B: Apache-2.0 + multilingue forte, MAS Per-Layer Embeddings infla memória (Q8 ~9-10GB não cabe na VRAM, forçado ao Q4).
- MiniMax M2/M1: escala datacenter (229-456B) — impossível local (mínimo 64GB).

**Config final (.env):**
```
LLM_MODE=local
QWEN_MODEL=Qwen3-4B-Instruct-2507-UD-Q8_K_XL
LLAMA_SERVER_PATH=    # vazio = usa padrão tools/llama.cpp/
LLAMA_MODEL_PATH=A:\Qwen3-4B-Instruct-2507-UD-Q8_K_XL.gguf
LLAMA_CTX=16384
```

**Tags Git:**
- `v0.2.1`: Fase 1 complete com testes verdes (17/17).
- `35b-turboquant`: Qwen3.6-35B-A3B estado funcionante (preservado para tarefas especiais).

**Próxima fase (Phase 2):** Tool calling template + inline detection (Qwen3 format).

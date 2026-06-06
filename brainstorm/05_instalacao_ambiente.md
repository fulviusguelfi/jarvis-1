# Instalação do Ambiente — Jarvis-1

> Última atualização: 2026-06-04

---

## Ferramentas Compiladas

### llama.cpp (Vulkan) ✅
- **Localização:** `tools/llama.cpp/`
- **Build:** `cmake -B build -DGGML_VULKAN=ON -DCMAKE_PREFIX_PATH=tools/vulkan-deps`
- **Binários úteis em** `tools/llama.cpp/build/bin/`:
  - `llama-cli` — chat interativo
  - `llama-server` — servidor HTTP OpenAI-compatible
  - `llama-mtmd-cli` — multimodal (áudio input)
  - `llama-tts` — TTS nativo
  - `llama-bench` — benchmark
- **GPU detectada:** `AMD Radeon RX 580 Series (RADV POLARIS10) — 8192 MiB`
- **ICD necessário:** `VK_ICD_FILENAMES=/usr/lib/x86_64-linux-gnu/GL/default/lib/vulkan/icd.d/radeon_icd.x86_64.json`

### llama.cpp-omni (Vulkan) ✅
- **Localização:** `tools/llama.cpp-omni/`
- **Fork:** https://github.com/tc-mb/llama.cpp-omni
- **Build:** `cmake -B build -DGGML_VULKAN=ON -DCMAKE_PREFIX_PATH=tools/vulkan-deps`
- **Binários úteis em** `tools/llama.cpp-omni/build/bin/`:
  - `llama-omni-cli` — CLI full para MiniCPM-o 4.5
  - `llama-omni-test-duplex` — teste duplex
  - `llama-omni-single-test-audio` — teste áudio simplex
- **Vulkan:** `GGML_VULKAN=ON` confirmado no CMakeCache

### SPIRV-Headers (dependência Vulkan)
- **Localização:** `tools/SPIRV-Headers/` (fonte) + `tools/vulkan-deps/` (instalado)
- Necessário para compilar o backend Vulkan do ggml

---

## Modelos

### MiniCPM-o 4.5
- **Localização:** `models/minicpmo-4.5/`
- **Repo HuggingFace:** `openbmb/MiniCPM-o-4_5-gguf`
- **Quantização:** Q4_K_M (backbone LLM)
- **Total a baixar:** ~7.4 GB

| Arquivo | Tamanho | Função | Status |
|---------|---------|--------|--------|
| `MiniCPM-o-4_5-Q4_K_M.gguf` | 4.7 GB | LLM backbone (Qwen3-8B Q4) | ✅ completo |
| `audio/MiniCPM-o-4_5-audio-F16.gguf` | 630 MB | Encoder de áudio (Whisper) | ✅ completo |
| `tts/MiniCPM-o-4_5-tts-F16.gguf` | 1.1 GB | Modelo TTS (LLaMA-based) | ✅ completo |
| `tts/MiniCPM-o-4_5-projector-F16.gguf` | 14 MB | Projetor TTS | ✅ completo |
| `token2wav-gguf/encoder.gguf` | 145 MB | Codec de áudio | ✅ completo |
| `token2wav-gguf/flow_extra.gguf` | 14 MB | Extra do flow | ✅ completo |
| `token2wav-gguf/flow_matching.gguf` | 437 MB | Flow matching vocoder | ⏳ incompleto (406 MB) |
| `token2wav-gguf/hifigan2.gguf` | 79 MB | HiFiGAN vocoder | ❌ faltando |
| `token2wav-gguf/prompt_cache.gguf` | 202 MB | Cache de prompt | ❌ faltando |

**Nota:** pasta correta é `token2wav-gguf/` (não `token2wav/` como inicialmente documentado)

---

## Variáveis de Ambiente Necessárias

```bash
export VK_ICD_FILENAMES=/usr/lib/x86_64-linux-gnu/GL/default/lib/vulkan/icd.d/radeon_icd.x86_64.json
```

---

## Comandos de Teste

```bash
# Teste MiniCPM-o completo (rodar a partir de tools/llama.cpp-omni/)
cd tools/llama.cpp-omni/
export VK_ICD_FILENAMES=/usr/lib/x86_64-linux-gnu/GL/default/lib/vulkan/icd.d/radeon_icd.x86_64.json
export LD_LIBRARY_PATH=./build/bin:$LD_LIBRARY_PATH

./build/bin/llama-omni-cli \
  -m /home/deck/projects/prototipes/jarvis-1/models/minicpmo-4.5/MiniCPM-o-4_5-Q4_K_M.gguf \
  -ngl 99 -c 2048

# Output em: tools/omni/output/round_000/
#   tts_wav/wav_*.wav  — arquivos de áudio gerados
#   llm_debug/chunk_*/llm_text.txt — texto da resposta por chunk
```

---

## Testes Realizados

### Teste Vulkan — Qwen3-0.6B (2026-06-05) ✅

**Resultado: GPU acelerada com sucesso no RX 580**

```bash
export VK_ICD_FILENAMES=/usr/lib/x86_64-linux-gnu/GL/default/lib/vulkan/icd.d/radeon_icd.x86_64.json
/home/deck/projects/prototipes/jarvis-1/tools/llama.cpp/build/bin/llama-cli \
  -m models/qwen3-0.6b/Qwen3-0.6B-Q4_0.gguf \
  --n-gpu-layers 99 --ctx-size 512 \
  --prompt "Responda em português: Qual é a capital do Brasil?" \
  -n 80 --temp 0.1 --no-display-prompt --single-turn
```

| Métrica | Resultado |
|---------|-----------|
| Prompt processing | **512.3 t/s** |
| Token generation | **219.1 t/s** |
| Modelo | Qwen3-0.6B-Q4_0 (409 MB) |
| GPU layers | 99/99 (tudo na VRAM) |
| Hardware | RX 580 8GB (RADV POLARIS10) |

**Observações:**
- Flag correta para não-interativo: `--single-turn` (não `--single-run`)
- Modelo "thinking" (Chain-of-Thought): gera `<think>...</think>` antes da resposta
- Resposta correta: identificou Brasília como capital

---

### Teste MiniCPM-o 4.5 Pipeline Completo (2026-06-05) ✅

**Pipeline áudio-para-áudio 100% local funcionando no RX 580.**

Executado de dentro de `tools/llama.cpp-omni/` com `-ngl 99 -c 2048`.

| Etapa | Resultado |
|-------|-----------|
| Modelo carregado | Backbone 4.7GB + APM 630MB + TTS 1.1GB + Token2Wav |
| Backend GPU | Vulkan (RADV POLARIS10) |
| LLM decode | ~13s para ~250 tokens de resposta |
| TTS + T2W | RTF ~0.85 (gera 1s de áudio em ~0.85s) |
| Total pipeline | ~31s para ~25s de áudio de saída |
| Texto da resposta | `tools/omni/output/round_000/llm_debug/chunk_*/llm_text.txt` |
| Áudio de saída | `tools/omni/output/round_000/tts_wav/wav_*.wav` (26 arquivos) |
| VRAM | Cabe nos 8GB — sem OOM |

**Resposta gerada (teste padrão em chinês):**
> "从前有座山，山里有座庙，庙里有个老和尚和一个小和尚。老和尚总是给小和尚讲故事，讲着讲着就讲到从前有座山…"

**Observações:**
- Sistema prompt do fork está em chinês — precisa ser customizado para pt-BR
- Sem `--no-tts`: o texto da resposta NÃO é impresso no terminal (vai para `text_queue` SSE); usar chunks do `llm_debug/`
- `--no-tts`: gera tokens mas descarta texto — útil só para benchmark de velocidade do LLM

---

## Sobre MiniCPM-o 4.5 e Código

Backbone = **Qwen3-8B** → excelente para código.
- Python, JS, C++, SQL, shell — todos suportados
- Nível de performance próximo ao Qwen3-8B puro
- Em HumanEval: ~60-65% (referência para 8B)
- Útil para: gerar scripts de automação, explicar código na tela, refactoring

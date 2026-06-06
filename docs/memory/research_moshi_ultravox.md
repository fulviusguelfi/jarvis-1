---
name: research-moshi-ultravox
description: Pesquisa com fontes reais sobre todos os modelos full-duplex conhecidos — viabilidade no RX 580
metadata: 
  node_type: memory
  type: project
  originSessionId: c8d127f7-6c84-4be8-b8b5-2a3538f9e327
---

# Pesquisa: Modelos Full-Duplex Speech — Panorama Completo
*Data: 2026-06-04 | Fontes: web search + HuggingFace Hub + papers*

---

## Tabela Comparativa Geral

| Modelo | Params | Full-Duplex | Áudio OUT nativo | Backend | VRAM mín. | RX 580 viável? |
|--------|--------|-------------|-----------------|---------|-----------|---------------|
| **Moshi** (Kyutai) | 7B | ✅ | ✅ | PyTorch | ~8GB | ❌ ROCm |
| **PersonaPlex** (NVIDIA) | 7B | ✅ | ✅ | PyTorch+CUDA | A100 80GB | ❌ CUDA |
| **MiniCPM-o 4.5** (OpenBMB) | 9B | ✅ | ✅ | llama.cpp-omni / PyTorch | 11GB (int4) | ❌ VRAM+Vulkan |
| **F-Actor** (Zuefle) | 1B | ✅ | ✅ | PyTorch (Llama 3.2) | pequeno | ❓ CPU apenas |
| **Raon-SpeechChat** (KRAFTON) | 9B | ✅ | ✅ | PyTorch+CUDA | 16GB+ | ❌ CUDA |
| **OmniFlatten** | ~7B | ✅ | ✅ | PyTorch | ? | ❌ sem pesos públicos |
| **Ultravox v0.7** | 8B | ❌ half | ❌ TTS externo | PyTorch | ? | ❌ ROCm |
| **Qwen3-Omni** (llama.cpp) | ? | ❌ | ❌ (Talker não impl.) | llama.cpp | 8GB+ | ✅ STT apenas |

---

## Detalhes por Modelo

### Moshi (Kyutai)
- Full-duplex real, ~200ms latência, open-source, pesos públicos
- **Contra principal:** PyTorch → ROCm → RX 580 não suportado
- Inglês apenas, contexto 2min + 4K tokens, sem tool use
- Fonte: https://github.com/kyutai-labs/moshi

### PersonaPlex (NVIDIA)
- Built on Moshi, add voice/persona control, 7B
- **Contra principal:** requer A100/H100 NVIDIA — hardware de data center
- Fonte: https://huggingface.co/nvidia/personaplex-7b-v1

### MiniCPM-o 4.5 (OpenBMB) — CANDIDATO MAIS PROMISSOR A LONGO PRAZO
- Full-duplex real (vê + ouve + fala simultaneamente), 9B, GGUF disponível
- llama.cpp-omni (fork de llama.cpp) com suporte a full-duplex
- **Problema 1:** llama.cpp-omni detecta apenas CUDA e Metal — Vulkan não documentado
- **Problema 2:** int4 mínimo = 11GB VRAM — RX 580 tem 8GB → não cabe nem em Q4
- Q4_K_M do backbone = 5GB, mas encoder de áudio (Whisper) + decoder (CosyVoice2) adicionam ~6GB
- Fonte: https://github.com/tc-mb/llama.cpp-omni | https://huggingface.co/openbmb/MiniCPM-o-4_5-gguf

### F-Actor (Maike Züfle, Jan 2026)
- 1B params (Llama 3.2-1B), instruction-following, open-source, leve
- Full-duplex, treino com apenas 2000h de dados
- **Viabilidade:** tamanho permite CPU — mas áudio real-time em CPU pode ter latência
- Fonte: https://github.com/MaikeZuefle/f-actor | https://huggingface.co/maikezu/f-actor

### Raon-SpeechChat-9B (KRAFTON)
- 9B, Qwen3 base, full-duplex extension, inglês+coreano
- **Contra:** CUDA 12.x + 16GB VRAM mínimo documentado
- Fonte: https://huggingface.co/KRAFTON/Raon-SpeechChat-9B

### Ultravox v0.7 (Fixie AI)
- Melhor benchmark de compreensão de áudio (91.8 Big Bench Audio)
- **NÃO tem saída de áudio nativa** — TTS sempre externo
- Half-duplex (turn-based)
- Fonte: https://huggingface.co/fixie-ai/ultravox-v0_4

---

## llama.cpp — Estado Atual para Áudio

| Capacidade | Status |
|-----------|--------|
| Áudio INPUT (STT) via mtmd | ✅ Funcional (Qwen3-Omni, MERaLiON-2, Gemma4) |
| Áudio OUTPUT (TTS/speech gen) | ❌ Em planejamento — issue #21956 |
| Vulkan no RX 580 (LLM texto) | ✅ Funcional |
| Vulkan + áudio full-duplex | ❌ Não disponível |

Fonte: https://awesomeagents.ai/news/llama-cpp-three-audio-models-48-hours/

---

## Conclusão para Hardware RX 580 (8GB VRAM, sem ROCm)

**Nenhum modelo full-duplex roda com aceleração GPU no RX 580 hoje.**

- Todos usam PyTorch (ROCm) ou CUDA
- MiniCPM-o 4.5 é o mais próximo (llama.cpp-omni + GGUF) mas precisa 11GB VRAM e não tem Vulkan documentado
- F-Actor (1B) poderia rodar em CPU mas latência para áudio real-time é incerta

**Pipeline (Whisper.cpp + llama.cpp Vulkan + Kokoro TTS) permanece a única opção GPU-acelerada viável hoje.**

**Candidato para upgrade futuro:** MiniCPM-o 4.5 quando/se llama.cpp-omni ganhar suporte Vulkan, ou com uma GPU com 12GB+ VRAM.

# Pesquisa: Modelos de Áudio — Full-Duplex e Speech-to-Speech

> Pesquisa realizada em: 2026-06-04
> Fontes: HuggingFace Hub, arXiv papers, GitHub, web search

---

## O Que Queremos

Um único modelo que:
1. Ouça áudio em tempo real (sem STT separado)
2. Gere áudio de resposta (sem TTS separado)
3. Full-duplex: ouvir enquanto fala (não turn-based)
4. Rode no hardware disponível (RX 580, 8GB VRAM, sem ROCm)

---

## Modelos Full-Duplex Conhecidos

### Moshi (Kyutai Labs)
- **Pesos:** Públicos no HuggingFace (`kyutai/moshiko-pytorch-bf16`)
- **Params:** 7B
- **Full-duplex:** ✅ real — ouve enquanto fala
- **Latência:** ~200ms
- **Áudio nativo in+out:** ✅
- **Backend:** PyTorch
- **Idioma:** Inglês apenas (multilingual previsto)
- **Contexto:** 2 min áudio + 4K tokens
- **Tool use:** ❌
- **RX 580:** ❌ — PyTorch requer ROCm, não suportado no RX 580
- **Fonte:** https://github.com/kyutai-labs/moshi

---

### PersonaPlex (NVIDIA)
- **Pesos:** `nvidia/personaplex-7b-v1` no HuggingFace
- **Params:** 7B (baseado em Moshi)
- **Full-duplex:** ✅
- **Backend:** PyTorch + CUDA (A100/H100 necessário)
- **RX 580:** ❌ — requer hardware de data center
- **Fonte:** https://huggingface.co/nvidia/personaplex-7b-v1

---

### MiniCPM-o 4.5 (OpenBMB) — CANDIDATO MAIS PROMISSOR A LONGO PRAZO
- **Pesos:** `openbmb/MiniCPM-o-4_5` + GGUF em `openbmb/MiniCPM-o-4_5-gguf`
- **Params:** 9B (SigLip2 + Whisper-medium + CosyVoice2 + Qwen3-8B)
- **Full-duplex:** ✅ real — vê + ouve + fala simultaneamente
- **Áudio nativo in+out:** ✅
- **Backend:** llama.cpp-omni (fork de llama.cpp) + PyTorch
- **GGUF disponível:** ✅ — Q4_K_M = 5GB backbone
- **Vulkan no llama.cpp-omni:** ❓ não documentado, mas pode ser compilado com `-DGGML_VULKAN=1` (o submodule ggml suporta Vulkan)
- **VRAM mínima:** 11GB (int4 total, incluindo encoders de áudio) — **RX 580 tem 8GB**
- **CPU offload parcial:** possível, mas latência para áudio real-time é incerta
- **Bloqueador principal:** VRAM insuficiente (8GB vs 11GB mínimo)
- **Fontes:**
  - https://huggingface.co/openbmb/MiniCPM-o-4_5-gguf
  - https://github.com/tc-mb/llama.cpp-omni

---

### F-Actor (Maike Züfle, Jan 2026)
- **Pesos:** `maikezu/f-actor` no HuggingFace
- **Params:** 1B (Llama 3.2-1B base)
- **Full-duplex:** ✅
- **Áudio out:** ✅
- **Backend:** PyTorch (Transformers)
- **Diferencial:** Instruction-following, treino com apenas 2000h, open-source
- **RX 580:** ❓ — tamanho permite CPU; latência real-time incerta
- **Fonte:** https://github.com/MaikeZuefle/f-actor

---

### Raon-SpeechChat-9B (KRAFTON)
- **Pesos:** `KRAFTON/Raon-SpeechChat-9B`
- **Params:** 9B (Qwen3 base)
- **Full-duplex:** ✅ extension
- **Backend:** PyTorch + CUDA (16GB+ VRAM)
- **RX 580:** ❌
- **Fonte:** https://huggingface.co/KRAFTON/Raon-SpeechChat-9B

---

### Ultravox v0.7 (Fixie AI)
- **Pesos:** `fixie-ai/ultravox-v0_4`
- **Full-duplex:** ❌ — half-duplex (turn-based)
- **Áudio out nativo:** ❌ — TTS sempre externo (ElevenLabs, Cartesia, etc.)
- **Benchmark:** 91.8 Big Bench Audio (melhor de speech-understanding em 2026)
- **Descartado:** não é single model para áudio in+out
- **Fonte:** https://huggingface.co/fixie-ai/ultravox-v0_4

---

## Estado do llama.cpp para Áudio (jun 2026)

| Capacidade | Status |
|-----------|--------|
| Áudio INPUT (STT) via mtmd | ✅ — Qwen3-Omni, MERaLiON-2, Gemma4 Audio |
| Áudio OUTPUT (TTS/síntese) | ❌ — em planejamento, issue #21956 |
| Full-duplex nativo | ❌ — não existe ainda |
| Vulkan no RX 580 para LLM texto | ✅ — funcional |

**Dois PRs importantes mergeados em 2026:**
- Wave32 Flash Attention para AMD (fev 2026)
- Graphics queue para AMD (mar 2026)

---

## Conclusão da Pesquisa

Nenhum modelo full-duplex roda com aceleração GPU no RX 580 hoje.
Todos usam PyTorch (ROCm) ou CUDA — nenhum tem Vulkan funcional.

**Experimento pendente:** compilar llama.cpp-omni com `-DGGML_VULKAN=1` e testar MiniCPM-o 4.5 Q4 com CPU offload parcial.

# Arquitetura e Decisões — Jarvis-1

> Última atualização: 2026-06-04

---

## Opções Consideradas e Status

### Opção A — API Cloud pura (Gemini 2.5 Flash)
- Ouve + fala nativamente, um só modelo, melhor experiência
- **Status: META FINAL** — queremos isso sem internet
- **Descartada para agora:** requer internet

### Opção B — Modelo Full-Duplex Local (Moshi / MiniCPM-o)
- Single model, áudio in+out nativo
- **Status: bloqueada no hardware atual**
  - Moshi/outros: PyTorch + ROCm → RX 580 não suportado
  - MiniCPM-o 4.5: llama.cpp-omni mas precisa 11GB VRAM (temos 8GB)
  - **Experimento pendente:** testar llama.cpp-omni com `-DGGML_VULKAN=1` + CPU offload

### Opção C — Pipeline Fragmentado Local
- Whisper.cpp (STT) + llama.cpp/Vulkan (LLM) + Kokoro TTS
- **Status: MAIS VIÁVEL HOJE** para GPU-acelerado
- Único path com GPU no RX 580 (via Vulkan)
- Fragmentação é a desvantagem

### Opção D — Híbrido (eliminada)
- Descartada pelo usuário — não faz sentido como fase

---

## Arquitetura Atual Escolhida — Fase 1

```
┌────────────────────────────────────────────────────────────┐
│  ENTRADA DE VOZ                                            │
│  Microfone → Whisper.cpp (local, CPU)                      │
└───────────────────────┬────────────────────────────────────┘
                        │ texto
┌───────────────────────▼────────────────────────────────────┐
│  CÉREBRO                                                   │
│  Sabiazinho-3 / Sabiá-3  (Maritaca API)                    │
│  ↳ Tool use / function calling para controle do PC         │
│  Fallback offline: Qwen3 14B Q4 via llama.cpp + Vulkan     │
└───────────────────────┬────────────────────────────────────┘
                        │ texto + tool calls
┌───────────────────────▼────────────────────────────────────┐
│  SAÍDA E AÇÕES                                             │
│  Voz: Kokoro TTS → PulseAudio (local, CPU)                 │
│  PC: xdotool / subprocess / pyautogui (Linux)              │
└────────────────────────────────────────────────────────────┘
```

---

## Stack de Componentes

| Componente | Tecnologia | Roda onde | Status |
|-----------|-----------|-----------|--------|
| STT | Whisper.cpp | CPU local | a implementar |
| LLM online | Sabiazinho-3 via API Maritaca | cloud | a implementar |
| LLM offline | Qwen3 14B Q4 via llama.cpp + Vulkan | RX 580 | a implementar |
| TTS | Kokoro TTS | CPU local | a implementar |
| Tool: shell | subprocess Python | local | a implementar |
| Tool: tela | xdotool / pyautogui | local | a implementar |
| Tool: screenshot | scrot / PIL | local | a implementar |
| Memória curto prazo | histórico de conversa em memória | local | a implementar |
| Memória longo prazo | SQLite + vetores | local | a planejar |

---

## Experimentos Pendentes

1. **llama.cpp-omni com Vulkan:** compilar com `-DGGML_VULKAN=1`, testar MiniCPM-o 4.5 Q4 com `--n-gpu-layers N` no RX 580
2. **Benchmark Whisper.cpp no hardware:** medir latência STT para escolher modelo (tiny/base/small)
3. **Benchmark Kokoro TTS:** medir latência para manter conversação fluida
4. **Benchmark Qwen3 14B Q4 no Vulkan:** medir tokens/s para uso offline

---

## Próximos Passos

- [ ] Montar estrutura inicial do projeto (pastas, dependências)
- [ ] Implementar loop básico: microfone → Whisper → Maritaca → Kokoro → speaker
- [ ] Adicionar primeiro tool: `run_shell`
- [ ] Testar experimento llama.cpp-omni + Vulkan

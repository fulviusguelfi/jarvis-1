# Jarvis-1 — Guia de Retomada (após troca de SO)

> Este documento existe porque a máquina onde o Jarvis foi desenvolvido será formatada.
> O código está no git; **`models/` (27GB) e `tools/` (11GB) NÃO estão** e precisam ser reconstruídos.
> Leia também: [docs/PLANO.md](docs/PLANO.md) (próxima fase) e [docs/memory/](docs/memory/) (contexto, hardware, pesquisa).

---

## 1. Onde estamos

- **v1 FUNCIONA**: assistente de voz local, half-duplex, validado em conversa real (wake word "Jarvis" → comando → resposta falada, com janela de follow-up e frase de dispensa "obrigado Jarvis").
- **Pipeline atual**: Whisper small (CPU) → Qwen3-8B Q4_K_M (Vulkan/RX580) → Piper TTS (faber). Latência ~2-3s warm.
- **Próxima fase planejada**: fluidez primeiro (wake word dedicado, endpointing, barge-in) e depois arsenal agêntico (ferramentas, browser, MCP). Tudo em [docs/PLANO.md](docs/PLANO.md).

## 2. Hardware-alvo

AMD Ryzen 5 4500 · 16GB RAM · **Radeon RX 580 8GB (sem ROCm, só Vulkan)**. Ver [docs/memory/project_jarvis1_context.md](docs/memory/project_jarvis1_context.md).

## 3. Reconstrução do ambiente no novo SO

### 3.1 Dependências Python (pip)
v1 (necessário pra rodar hoje):
```
faster-whisper>=1.2  piper-tts>=1.4  av  ctranslate2  onnxruntime  requests  numpy
```
Planejadas (fase agêntica — ver PLANO.md):
```
openwakeword  silero-vad  pynput  EWMHlib  mss  psutil  playwright  mcp
```

### 3.2 llama.cpp com Vulkan (cérebro local)
Compilar llama.cpp com backend **Vulkan** (NÃO ROCm — RX580 não suporta). Passos detalhados em [brainstorm/05_instalacao_ambiente.md](brainstorm/05_instalacao_ambiente.md). Binário esperado em `tools/llama.cpp/build/bin/llama-server`.

Flags que funcionam (ver [src/llm_local.py](src/llm_local.py)):
```
-ngl 99 --flash-attn on --ctx-size 4096
--cache-type-k q8_0 --cache-type-v q8_0   # PLANO: era q4_0; q4_0 degrada tool calling
--batch-size 512 --ubatch-size 128 --jinja
```
⚠️ **`VK_ICD` em [src/config.py:18](src/config.py#L18) é específico da máquina** — no novo SO, achar o ICD do RADV (`find / -name 'radeon_icd*.json'`) e atualizar `VK_ICD_FILENAMES`.

### 3.3 Modelos a baixar (HuggingFace)
| Pasta destino | Modelo | Uso |
|---|---|---|
| `models/qwen3-8b/Qwen3-8B-Q4_K_M.gguf` | Qwen3-8B Q4_K_M GGUF | LLM atual |
| `models/qwen3-4b/` (planejado) | **Qwen3-4B-Instruct-2507 Q4_K_M GGUF** | eval de velocidade (PLANO F1) |
| `models/piper/` | Piper `pt_BR-faber-medium` (.onnx + .json) | TTS atual |
| (auto) | faster-whisper `small` | STT (baixa sozinho no 1º uso) |
| (planejado) | openWakeWord `hey_jarvis` (onnx) + Silero VAD (onnx) | wake word + endpointing |

Modelos da v1 anterior que **não precisam voltar** (becos sem saída, ver memória): `qwen3.6-35b-a3b` (lento, /no_think quebrado), `qwen3-tts` (RTF 9.6x), `minicpmo-4.5` (não cabe na VRAM), `kokoro` (lento).

### 3.4 Áudio (PulseAudio via Flatpak + headset Jabra)
⚠️ **`PULSE_SINK` no `.env` é específico da máquina/headset** — no novo SO, listar com `pactl list short sinks` e atualizar. Toda a lógica de Bluetooth está em [src/audio.py](src/audio.py); gotchas aprendidos:
- Usar `paplay --raw` (não ffmpeg) pra saída — ffmpeg descarta áudio antes do BT acordar.
- Thread de keepalive de silêncio mantém o Jabra acordado.
- Stream de mic contínuo evita o PipeWire suspender o source.
- `PULSE_SERVER=unix:/run/flatpak/pulse/native` (ajustar se sair do Flatpak).

### 3.5 `.env`
Copiar de `.env.example` e preencher. Valores da máquina antiga (referência):
```
LLM_MODE=local
TTS_MODE=piper
PIPER_VOICE=faber
PULSE_SERVER=unix:/run/flatpak/pulse/native
PULSE_SINK=<RE-DERIVAR no novo SO via 'pactl list short sinks'>
MARITACA_API_KEY=<opcional, só p/ modo cloud>
```

## 4. Como rodar (v1)
```
cd jarvis-1
python3 src/main.py
# Diga "Jarvis" para ativar. Ctrl+C para sair.
```

## 5. Próximos passos (resumo do PLANO.md)
1. **Fase 1 — Fluidez**: openWakeWord ("Hey Jarvis"), endpointing com Silero VAD, barge-in confiável, recuperação de mic, avaliar Qwen3-4B.
2. **Fase 2 — Tool calling**: `--chat-template-file` corrigido p/ Qwen3, KV q8_0, system prompt que habilita ferramentas.
3. **Fase 3 — Ferramentas nativas + segurança** (confirmação de voz em ações destrutivas).
4. **Fase 4 — Browser** (Playwright, accessibility tree — a "visão" real).
5. **Fase 5 — Online** (Open-Meteo, fetch) e **Fase 6 — Ponte MCP** (servers Python).

Riscos e mitigações detalhados em [docs/PLANO.md](docs/PLANO.md). Fatos do ambiente verificados estão lá — mas **re-validar no novo SO** (AT-SPI, libs do Chromium, ICD Vulkan, sink de áudio podem mudar).

## 6. Credenciais
Token do GitHub estava em `~/.config/jarvis-1/credentials` (será apagado). Gerar novo em github.com/settings/tokens se precisar fazer push no novo SO. Processo de deploy em [docs/memory/reference_github_deploy.md](docs/memory/reference_github_deploy.md).

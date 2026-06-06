# Jarvis-1 — Guia de Retomada (migração para WINDOWS)

> A máquina de desenvolvimento (SteamOS/Linux) será formatada e o projeto continuará no **Windows**.
> O código está no git; **`models/` (27GB) e `tools/` (11GB) NÃO estão** e serão reconstruídos.
> ⚠️ **MUITA COISA MUDA NO WINDOWS** — principalmente áudio. A seção 3 mapeia tudo.
> Leia também: [docs/PLANO.md](docs/PLANO.md) (próxima fase) e [docs/memory/](docs/memory/) (contexto, hardware, pesquisa).

---

## 1. Onde estamos

- **v1 FUNCIONA no Linux**: assistente de voz local, half-duplex (wake word "Jarvis" → comando → resposta falada, follow-up e dispensa "obrigado Jarvis").
- **Pipeline**: Whisper small (CPU) → Qwen3-8B Q4_K_M (Vulkan/RX580) → Piper TTS. Latência ~2-3s.
- **A lógica do pipeline é portável; a camada de SO (áudio, paths, Vulkan) NÃO.** Ver mapa abaixo.

## 2. Hardware-alvo (igual)

AMD Ryzen 5 4500 · 16GB RAM · **Radeon RX 580 8GB**. No Windows o RX 580 roda **Vulkan via driver AMD Adrenalin** (sem ROCm, igual). Ver [docs/memory/project_jarvis1_context.md](docs/memory/project_jarvis1_context.md).

---

## 3. MAPA DE MIGRAÇÃO Linux → Windows

| Componente | Linux (v1 atual) | **Windows (o que fazer)** | Arquivo afetado |
|---|---|---|---|
| **Captura de mic** | ffmpeg `-f pulse` + `pactl suspend-source` + stream contínuo | **`sounddevice`** (PortAudio, pip) — `RawInputStream` 16kHz mono. Adeus pactl/ffmpeg. | `src/audio.py` (REESCREVER) |
| **Saída de áudio** | `paplay --raw` + keepalive de silêncio (gambiarra BT) | **`sounddevice`** `OutputStream`. Manter stream contínuo p/ Jabra não dormir. | `src/audio.py` (REESCREVER) |
| **Seleção de device** | `PULSE_SINK` / `PULSE_SERVER` (env) | `sounddevice.query_devices()` → escolher Jabra por nome/índice | `src/config.py`, `.env` |
| **LLM Vulkan** | compilar llama.cpp + `VK_ICD_FILENAMES` apontando p/ RADV | **Baixar binário pré-compilado** `llama-*-bin-win-vulkan-x64.zip` (releases ggml-org/llama.cpp). `llama-server.exe`. Sem VK_ICD (loader do Windows acha sozinho). | `src/llm_local.py`, `src/config.py` |
| **STT (Whisper)** | faster-whisper CPU int8 | **Igual** — faster-whisper roda no Windows. | — |
| **TTS (Piper)** | piper-tts pip | **Igual** — piper-tts roda no Windows. | — |
| **Shell tool** | `bash -c` (`shell=True`) | **PowerShell/cmd** — ajustar `run_shell`. | `src/tools/shell.py` |
| **Wake word (plano)** | openWakeWord ONNX | **Igual** (ONNX cross-platform). | — |
| **VAD/barge-in (plano)** | silero-vad ONNX | **Igual** (ONNX cross-platform). | — |
| **Janelas (plano)** | EWMHlib (X11) | **`pygetwindow` + `pywin32`** | `src/tools/window.py` |
| **Input teclado/mouse (plano)** | pynput (XTEST) | **`pyautogui` / `pynput`** (backend Win32) | `src/tools/input.py` |
| **Ver a tela de apps desktop (plano)** | ❌ AT-SPI não funcionava no sandbox | ✅ **MELHORA: `uiautomation`/`pywinauto`** (UI Automation) expõe a árvore de acessibilidade de apps Windows. Agora é viável. | `src/tools/screen.py` |
| **Browser (plano)** | Playwright | **Igual** — `playwright install chromium`. | `src/tools/browser.py` |
| **MCP (plano)** | servers Python (mcp pip) | **Igual** (Python); servers Node exigem Node p/ Windows. | `src/tools/mcp_bridge.py` |

**Resumo:** o que precisa de trabalho real no Windows é **`src/audio.py` (reescrita completa)**, ajustes em `config.py`/`llm_local.py` (paths + Vulkan) e `tools/shell.py` (PowerShell). O resto da pilha agêntica do PLANO fica igual ou **mais fácil** (UI Automation).

---

## 4. Setup no Windows (passo a passo)

### 4.1 Base
1. Instalar **Python 3.11+** (marcar "Add to PATH"). Recomendo criar venv: `python -m venv .venv && .venv\Scripts\activate`.
2. Instalar **driver AMD Adrenalin** atualizado (traz o runtime Vulkan do RX 580).
3. `pip install -r requirements.txt` + `pip install sounddevice` (substitui a camada de áudio Linux).

### 4.2 LLM — llama.cpp Vulkan (sem compilar)
- Baixar release Windows Vulkan de github.com/ggml-org/llama.cpp/releases → extrair em `tools\llama.cpp\` → usar `llama-server.exe`.
- Flags (mesmas, ajustar p/ tool calling — ver PLANO):
  `-ngl 99 --flash-attn on --ctx-size 4096 --cache-type-k q8_0 --cache-type-v q8_0 --batch-size 512 --ubatch-size 128 --jinja`
- Validar que a GPU aparece: `llama-server.exe --list-devices` (deve listar o RX 580 via Vulkan).

### 4.3 Modelos a baixar (HuggingFace)
| Pasta | Modelo | Uso |
|---|---|---|
| `models\qwen3-8b\Qwen3-8B-Q4_K_M.gguf` | Qwen3-8B Q4_K_M GGUF | LLM atual |
| `models\qwen3-4b\` (plano) | Qwen3-4B-Instruct-2507 Q4_K_M GGUF | eval de velocidade |
| `models\piper\` | Piper `pt_BR-faber-medium` (.onnx + .json) | TTS |
| (auto) | faster-whisper `small` | STT (baixa no 1º uso) |
| (plano) | openWakeWord `hey_jarvis` + Silero VAD (ONNX) | wake word + VAD |

NÃO rebaixar (becos sem saída — ver memória): qwen3.6-35b-a3b, qwen3-tts, minicpmo-4.5, kokoro.

### 4.4 Áudio (a parte que mais muda)
- Listar devices: `python -c "import sounddevice; print(sounddevice.query_devices())"` → anotar índice do **Jabra** (entrada e saída).
- Reescrever `src/audio.py` sobre `sounddevice`: `RawInputStream` contínuo p/ captura (16kHz, mono, int16) e `OutputStream` p/ playback. Manter um stream de saída aberto/contínuo como keepalive do Jabra.
- `.env`: trocar `PULSE_*` por algo como `AUDIO_INPUT_DEVICE=<idx>` / `AUDIO_OUTPUT_DEVICE=<idx>`.

### 4.5 `.env` (novo formato Windows)
```
LLM_MODE=local
TTS_MODE=piper
PIPER_VOICE=faber
AUDIO_INPUT_DEVICE=<idx do Jabra mic>     # de sounddevice.query_devices()
AUDIO_OUTPUT_DEVICE=<idx do Jabra fone>
# MARITACA_API_KEY=...   (opcional, só modo cloud)
```
Remover do `config.py`: `VK_ICD`, `PULSE_SERVER`. Ajustar paths para `os.path.join` (já é portável) e o caminho do `llama-server.exe`.

## 5. Como rodar (após setup)
```
.venv\Scripts\activate
python src\main.py
```

## 6. Próximos passos (PLANO.md) — válido no Windows
1. **Fase 0 (NOVA p/ Windows): portar `audio.py` p/ sounddevice + ajustar paths/Vulkan/shell.** Pré-requisito de tudo.
2. **Fase 1 — Fluidez**: openWakeWord ("Hey Jarvis"), endpointing Silero VAD, barge-in, recuperação de mic, avaliar Qwen3-4B.
3. **Fase 2 — Tool calling**: `--chat-template-file` Qwen3, KV q8_0, system prompt habilitando ferramentas.
4. **Fase 3 — Ferramentas + segurança** (confirmação de voz em ações destrutivas) — no Windows ganha **UI Automation** p/ ler apps desktop.
5. **Fase 4 — Browser** (Playwright) · **Fase 5 — Online** (Open-Meteo) · **Fase 6 — MCP** (servers Python).

⚠️ **Re-validar no Windows** os "fatos do ambiente" do PLANO.md (eram do sandbox Linux): libs do Chromium, Vulkan, devices de áudio, e **R5 muda** — UI Automation substitui o AT-SPI que faltava.

## 7. Credenciais
Token GitHub (`~/.config/jarvis-1/credentials`) será apagado. No Windows, instalar `git` + `gh` (ou usar PAT novo) p/ dar push. Processo em [docs/memory/reference_github_deploy.md](docs/memory/reference_github_deploy.md).

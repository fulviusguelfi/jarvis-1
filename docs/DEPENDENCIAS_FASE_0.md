# Jarvis-1 — Dependências Completas (Fase 0)

> Checklist de todas as dependências Python, binários, e modelos necessários para rodar a Fase 0 no Windows.

---

## 1. Python + Ambiente Virtual

| Item | Versão | Fonte | Status |
|------|--------|-------|--------|
| **Python** | 3.11+ | python.org | ✅ Obrigatório |
| **pip** | latest | bundled com Python | ✅ Obrigatório |
| **venv** | stdlib | stdlib Python | ✅ Obrigatório |

**Setup:**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
```

---

## 2. Dependências Python (requirements.txt)

### Instalação
```powershell
pip install -r requirements.txt
```

### Lista Detalhada

| Pacote | Versão | Dependência | Motivo | Status |
|--------|--------|------------|--------|--------|
| **numpy** | ≥1.26.0 | Core | arrays, processamento de áudio | ✅ Fase 0 |
| **sounddevice** | ≥0.4.6 | **NOVO** | captura/playback áudio (Windows) | ✅ Fase 0 |
| **faster-whisper** | ≥1.2.0 | Core | STT (Whisper small, CPU) | ✅ Fase 0 |
| **ctranslate2** | ≥4.7.0 | Whisper | backend de STT | ✅ Fase 0 |
| **piper-tts** | ≥1.4.0 | Core | TTS (RTF ~0.06x) | ✅ Fase 0 |
| **requests** | ≥2.32.0 | LLM | HTTP p/ llama-server | ✅ Fase 0 |
| **av** | ≥14.0.0 | Whisper | demuxing de áudio | ✅ Fase 0 |
| **onnxruntime** | ≥1.26.0 | Future | infra p/ wake word + VAD | ⏳ Fase 1 |

### Comandos de Validação

```powershell
# Instalar
pip install -r requirements.txt

# Verificar versões
pip list | findstr -E "numpy|sounddevice|faster-whisper|piper-tts|onnxruntime|requests|ctranslate2|av"

# Testar imports
python -c "
import numpy
import sounddevice
import faster_whisper
import piper
import onnxruntime
import requests
import ctranslate2
print('✓ Todos os imports OK')
"
```

---

## 3. Binários Externos

### 3.1 llama.cpp (LLM + Vulkan)

| Item | Versão | Fonte | Localização | Status |
|------|--------|-------|-------------|--------|
| **llama-server.exe** | latest | github.com/ggml-org/llama.cpp/releases | `tools/llama.cpp/` | ✅ Fase 0 |
| **Vulkan Runtime** | via AMD Driver | AMD Adrenalin | sistema | ✅ Fase 0 |

**Download:**
```
https://github.com/ggml-org/llama.cpp/releases
→ Procurar: "windows-vulkan" na tag mais recente
→ Exemplo: llama-b4588-bin-win-vulkan-x64.zip
→ Extrair em: tools/llama.cpp/
```

**Validação:**
```powershell
cd tools/llama.cpp
.\llama-server.exe --list-devices
# Deve listar: "Radeon RX 580" ou similar
```

### 3.2 AMD Driver (Vulkan)

| Item | Versão | Fonte | Status |
|------|--------|-------|--------|
| **AMD Adrenalin Driver** | latest | amd.com/support | ✅ Obrigatório |
| **Vulkan Runtime** | bundled | AMD Driver | ✅ Automático |

**Instalação:**
1. https://www.amd.com/en/support
2. Buscar por "Radeon RX 580"
3. Download "AMD Adrenalin Edition"
4. Instalar (inclui Vulkan runtime)
5. Restart Windows

**Validação:**
```powershell
# No Device Manager → Display adapters
# Deve aparecer: "Radeon RX 580" com status ✓
```

---

## 4. Modelos (HuggingFace)

### 4.1 Qwen3-8B LLM

| Item | Arquivo | Tamanho | Formato | Localização | Status |
|------|---------|---------|---------|-------------|--------|
| **Qwen3-8B LLM** | `Qwen3-8B-Instruct-Q4_K_M.gguf` | ~5.5GB | GGUF | `models/qwen3-8b/` | ✅ Fase 0 |

**Download:**
```
https://huggingface.co/bartowski/Qwen3-8B-Instruct-GGUF
→ File: Qwen3-8B-Instruct-Q4_K_M.gguf (~5.5GB)
→ Salvar em: models/qwen3-8b/Qwen3-8B-Q4_K_M.gguf
```

**Validação:**
```powershell
ls models/qwen3-8b/
# Deve existir: Qwen3-8B-Q4_K_M.gguf (~5.5GB)
```

### 4.2 Piper TTS (faber-medium)

| Item | Arquivo | Tamanho | Formato | Localização | Status |
|------|---------|---------|---------|-------------|--------|
| **Piper Voice** | `pt_BR-faber-medium.onnx` | ~40MB | ONNX | `models/piper/pt_BR-faber-medium/` | ✅ Fase 0 |
| **Piper Config** | `pt_BR-faber-medium.onnx.json` | ~5KB | JSON | `models/piper/pt_BR-faber-medium/` | ✅ Fase 0 |

**Download:**
```
https://huggingface.co/rhasspy/piper-voices/tree/main/pt/pt_BR/faber
→ Files:
   1. pt_BR-faber-medium.onnx (~40MB)
   2. pt_BR-faber-medium.onnx.json
→ Salvar em: models/piper/pt_BR-faber-medium/
```

**Validação:**
```powershell
ls models/piper/pt_BR-faber-medium/
# Deve existir:
#   pt_BR-faber-medium.onnx
#   pt_BR-faber-medium.onnx.json
```

### 4.3 Whisper (Auto-download)

| Item | Arquivo | Tamanho | Status |
|------|---------|---------|--------|
| **Whisper small** | (auto) | ~140MB | ⏳ Auto-download na 1ª execução |

**Localização:** `~/.cache/huggingface/hub/models--openai--whisper-small/`

**Validação:**
```powershell
python -c "from src.stt import _get_model; _get_model()"
# Primeira execução: download ~140MB
# Próximas execuções: usa cache
```

---

## 5. Configuração (Arquivos)

### 5.1 .env

| Var | Exemplo | Obrigatório | Origem |
|-----|---------|------------|--------|
| `LLM_MODE` | `local` | ✅ Sim | user (escolher: local/cloud) |
| `TTS_MODE` | `piper` | ✅ Sim | user (piper/kokoro/qwen3) |
| `PIPER_VOICE` | `faber` | ✅ Sim | user (faber/cadu/jeff) |
| `AUDIO_INPUT_DEVICE` | `1` | ✅ Sim | user (sounddevice.query_devices()) |
| `AUDIO_OUTPUT_DEVICE` | `2` | ✅ Sim | user (sounddevice.query_devices()) |

**Criar .env:**
```powershell
Copy-Item .env.example .env
# Editar manualmente com seus valores
```

**Encontrar device indices:**
```powershell
python -c "import sounddevice; print(sounddevice.query_devices())"
# Procurar por "Jabra" e anotar índices
```

### 5.2 Exemplo .env (Windows)

```ini
# Modo offline (recomendado)
LLM_MODE=local
TTS_MODE=piper
PIPER_VOICE=faber

# Áudio — substituir com seus índices
AUDIO_INPUT_DEVICE=1
AUDIO_OUTPUT_DEVICE=2
```

---

## 6. Verificação Completa (Checklist)

### Python + Ambiente
- [ ] Python 3.11+ instalado: `python --version`
- [ ] venv ativado: `(.venv)` no prompt
- [ ] pip atualizado: `pip --version`

### Dependências Python
- [ ] `pip install -r requirements.txt` OK
- [ ] `python -c "import numpy; import sounddevice; ..."`

### Binários
- [ ] `tools/llama.cpp/llama-server.exe` existe
- [ ] `llama-server.exe --list-devices` mostra RX 580
- [ ] AMD Driver instalado (Device Manager)

### Modelos
- [ ] `models/qwen3-8b/Qwen3-8B-Q4_K_M.gguf` (~5.5GB)
- [ ] `models/piper/pt_BR-faber-medium/` (2 arquivos)
- [ ] Whisper (vai auto-download na 1ª vez)

### Configuração
- [ ] `.env` criado a partir de `.env.example`
- [ ] `AUDIO_INPUT_DEVICE` e `AUDIO_OUTPUT_DEVICE` corretos
- [ ] `python -c "import sounddevice; print(sounddevice.query_devices())"` mostra Jabra

### Scripts de Teste
- [ ] `python check_deps.py` → 0 falhas
- [ ] `python -c "from src.stt import _get_model; _get_model()"` OK
- [ ] `python -c "from src.tts_piper import _get_voice; _get_voice()"` OK
- [ ] `python -c "from src.llm_local import ensure_server; ensure_server()"` OK

---

## 7. Espaço em Disco Necessário

| Item | Tamanho | Localização |
|------|---------|-------------|
| **Python + venv** | ~500MB | `.venv/` |
| **pip packages** | ~1.5GB | `.venv/Lib/site-packages/` |
| **Qwen3-8B GGUF** | ~5.5GB | `models/qwen3-8b/` |
| **Piper TTS** | ~40MB | `models/piper/` |
| **Whisper cache** | ~140MB | `~/.cache/huggingface/` |
| **llama.cpp** | ~200MB | `tools/llama.cpp/` |
| **Repositório + docs** | ~100MB | `.` |
| **TOTAL** | **~8GB** | — |

**Recomendação:** Ter pelo menos **10GB livres** para margem.

---

## 8. Versões Alternativas (Opcional, Fase 1+)

Para futuras otimizações:

| Pacote | Fase | Propósito | Status |
|--------|------|----------|--------|
| **openwakeword** | 1 | wake word "Hey Jarvis" | ⏳ Próximo |
| **silero-vad** | 1 | endpointing + barge-in | ⏳ Próximo |
| **pynput** | 3 | automação teclado/mouse | ⏳ Fase 3 |
| **pygetwindow** | 3 | controle de janelas (Windows) | ⏳ Fase 3 |
| **pywinauto** | 3 | UI automation (Windows) | ⏳ Fase 3 |
| **playwright** | 4 | browser automation | ⏳ Fase 4 |
| **mcp** | 6 | ponte MCP servers | ⏳ Fase 6 |

---

## 9. Troubleshooting de Dependências

| Erro | Causa | Solução |
|------|-------|---------|
| `ModuleNotFoundError: sounddevice` | pip install incompleto | `pip install sounddevice==0.4.6` |
| `CUDA not found` (Whisper) | irrelevante (usamos CPU) | Ignora, continua normal |
| `Vulkan not available` | AMD Driver desatualizado | Atualizar AMD Adrenalin |
| `No audio device found` | sounddevice não vê Jabra | Verificar índices com `query_devices()` |
| `Modelo não encontrado` | caminho errado | Verificar estrutura em [seção 4](#4-modelos-huggingface) |
| `llama-server timeout` | binário 32-bit ou incompatível | Baixar versão Vulkan 64-bit |

---

## 10. Resumo Rápido (TL;DR)

```powershell
# 1. Setup Python
python -m venv .venv
.venv\Scripts\Activate.ps1

# 2. Instalar deps Python
pip install -r requirements.txt

# 3. Baixar binários
# → llama-server.exe em tools/llama.cpp/

# 4. Baixar modelos
# → Qwen3-8B em models/qwen3-8b/
# → Piper TTS em models/piper/pt_BR-faber-medium/

# 5. Configurar áudio
python -c "import sounddevice; print(sounddevice.query_devices())"
# → Anotar índices do Jabra
Copy-Item .env.example .env
# → Editar .env com índices

# 6. Validar
python check_deps.py

# 7. Rodar!
python src/main.py
```

✅ **FASE 0 COMPLETA!** Pronto para Fase 1.


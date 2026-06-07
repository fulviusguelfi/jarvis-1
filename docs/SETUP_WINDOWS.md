# Jarvis-1 — Setup Windows (Fase 0 completa)

> Guia passo-a-passo para rodar Jarvis-1 no Windows 11 com RX 580.

---

## 1. Pré-requisitos

- **Windows 11 Pro** (ou Home, funciona igual)
- **Python 3.11+** (com `Add to PATH` selecionado durante instalação)
- **Git** (para clonar o repo e fazer push)
- **AMD Driver (Adrenalin)** atualizado — traz runtime Vulkan para RX 580
- **27GB livres** para modelos + 11GB para tools

---

## 2. Setup Python e Dependências

### 2.1 Criar e ativar venv
```powershell
cd c:\Users\Usuario\VSCodeProjects\jarvis-1
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Se receber erro de execução, execute:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 2.2 Instalar dependências
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

**Deps principais:**
- `faster-whisper` — STT (CPU, auto-download do modelo)
- `piper-tts` — TTS (rápido, 0.06x RTF)
- `sounddevice` — captura/playback de áudio (PortAudio)
- `onnxruntime` — para future phases (wake word, VAD)

---

## 3. llama.cpp (LLM com Vulkan)

### 3.1 Baixar binário pré-compilado
1. Vá para: https://github.com/ggml-org/llama.cpp/releases
2. Procure a versão mais recente com **"windows-vulkan"** no nome
3. Exemplo: `llama-b4588-bin-win-vulkan-x64.zip`
4. Extrair em: `c:\Users\Usuario\VSCodeProjects\jarvis-1\tools\llama.cpp\`

Estrutura esperada:
```
tools/
  llama.cpp/
    llama-server.exe
    llama-cli.exe
    (outras libs)
```

### 3.2 Validar Vulkan
```powershell
cd c:\Users\Usuario\VSCodeProjects\jarvis-1\tools\llama.cpp
.\llama-server.exe --list-devices
```

Deve listar o **Radeon RX 580** ou similar. Se não aparecer, o driver AMD Adrenalin não está instalado corretamente.

---

## 4. Modelos (HuggingFace)

### 4.1 Baixar Qwen3-8B
Criar pasta: `models\qwen3-8b\`

**Link:** https://huggingface.co/bartowski/Qwen3-8B-Instruct-GGUF

Baixar: `Qwen3-8B-Instruct-Q4_K_M.gguf` (~5.5GB)

Colocar em: `models\qwen3-8b\Qwen3-8B-Q4_K_M.gguf`

### 4.2 Baixar Piper TTS
Criar pasta: `models\piper\pt_BR-faber-medium\`

**Link:** https://huggingface.co/rhasspy/piper-voices/tree/main/pt/pt_BR/faber

Baixar os 2 arquivos:
- `pt_BR-faber-medium.onnx` (~40MB)
- `pt_BR-faber-medium.onnx.json` (config)

Colocar em: `models\piper\pt_BR-faber-medium\`

### 4.3 Whisper (auto-download)
Não precisa fazer nada — `faster-whisper` baixa sozinho no primeiro uso (~140MB para "small").

---

## 5. Configurar Áudio (sounddevice)

### 5.1 Listar devices
```powershell
python -c "import sounddevice; print(sounddevice.query_devices())"
```

Procure o **Jabra** na lista. Exemplo de saída:
```
0: Speakers (Realtek High Definition Audio), MME
1: Jabra Speak 750 - input, Multimedia
2: Jabra Speak 750 - output, Multimedia
3: ...
```

Anote os **índices** do Jabra input e output.

### 5.2 Criar `.env`
```powershell
Copy-Item .env.example .env
```

Editar `.env` e preencher:
```
LLM_MODE=local
TTS_MODE=piper
PIPER_VOICE=faber
AUDIO_INPUT_DEVICE=1
AUDIO_OUTPUT_DEVICE=2
```

(Substitua 1 e 2 pelos índices corretos do Jabra)

---

## 6. Validar Setup

### 6.1 Verificar imports
```powershell
python src\config.py && echo "Config OK"
python -c "import sounddevice; import faster_whisper; import piper; print('Imports OK')"
```

### 6.2 Testar STT (Whisper)
```powershell
python -c "
from src.stt import _get_model
model = _get_model()
print('Whisper carregado OK')
"
```

### 6.3 Testar TTS (Piper)
```powershell
python -c "
from src.tts_piper import synthesize
samples, rate = synthesize('Olá mundo')
print(f'TTS OK: {len(samples)} samples em {rate} Hz')
"
```

### 6.4 Testar Áudio
```powershell
python -c "
import sounddevice as sd
import numpy as np
# Toca tom de teste por 1s
tone = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 22050)).astype(np.float32)
sd.play(tone, 22050)
sd.wait()
print('Áudio OK')
"
```

### 6.5 Testar llama-server Vulkan
```powershell
cd c:\Users\Usuario\VSCodeProjects\jarvis-1
python -c "from src.llm_local import ensure_server; ensure_server()"
```

Leva ~15s na primeira vez. Se sucesso:
```
[llama-server] Carregando modelo em VRAM (pode demorar ~15s)...
[llama-server] Pronto.
```

---

## 7. Rodar Jarvis-1

```powershell
python src\main.py
```

Esperado:
1. `[modo LLM: local | TTS: piper]` — modo OK
2. Pré-carregamento de Whisper + TTS
3. `✓ Microfone OK (-X dB)` — mic detectado
4. `Pronto. Aguardando wake word 'Jarvis'...`
5. Diga **"Jarvis"** para ativar
6. Diga seu comando (ex: "qual é a hora?")
7. Escute a resposta em voz

---

## 8. Troubleshooting

| Erro | Causa | Solução |
|------|-------|--------|
| `ModuleNotFoundError: sounddevice` | Não instalado | `pip install sounddevice` |
| `llama-server not found` | Binário não baixado | Ver seção 3.1 |
| `Modelo não encontrado` | Arquivo em lugar errado | Verificar estrutura de pastas |
| `Microfone silencioso` | Device errado ou não selecionado | Revisar `.env` e `sounddevice.query_devices()` |
| `Vulkan not available` | Driver AMD não instalado | Instalar AMD Adrenalin drivers |
| `ONNX error` | onnxruntime desatualizado | `pip install --upgrade onnxruntime` |

---

## 9. Próximos Passos (Fase 1+)

Após validar que Fase 0 funciona:

1. **Fase 1 — Fluidez:** openWakeWord + Silero VAD
2. **Fase 2 — Tool calling:** habilitar no LLM
3. **Fase 3 — Ferramentas:** filesystem, janelas, input
4. Ver [docs/PLANO.md](PLANO.md) para detalhes

---

## Checklist Final

- [ ] Python 3.11+ instalado e no PATH
- [ ] `pip install -r requirements.txt` OK
- [ ] llama-server.exe baixado e testado
- [ ] Qwen3-8B GGUF em `models/qwen3-8b/`
- [ ] Piper TTS em `models/piper/pt_BR-faber-medium/`
- [ ] `.env` preenchido com device indices corretos
- [ ] `sounddevice.query_devices()` mostra Jabra
- [ ] STT, TTS e Áudio testados
- [ ] `python src/main.py` funciona
- [ ] Wake word "Jarvis" detectado
- [ ] Resposta em voz recebida

Pronto! 🎉

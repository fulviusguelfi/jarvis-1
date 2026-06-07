# Jarvis-1 — Guia Rápido (Fase 0)

> Deploy em 5 passos no Windows 11.

---

## 🚀 Quick Start

```powershell
# 1. Setup venv
python -m venv .venv
.venv\Scripts\Activate.ps1

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Baixar llama-server.exe (Vulkan)
# → https://github.com/ggml-org/llama.cpp/releases
# → Procure: "windows-vulkan" na tag mais recente
# → Extraia em: tools/llama.cpp/

# 4. Baixar modelos
# Qwen3-8B:
#   https://huggingface.co/bartowski/Qwen3-8B-Instruct-GGUF
#   → Qwen3-8B-Instruct-Q4_K_M.gguf (~5.5GB)
#   → models/qwen3-8b/Qwen3-8B-Q4_K_M.gguf

# Piper TTS:
#   https://huggingface.co/rhasspy/piper-voices/tree/main/pt/pt_BR/faber
#   → pt_BR-faber-medium.onnx + .json
#   → models/piper/pt_BR-faber-medium/

# 5. Configurar áudio
python -c "import sounddevice; print(sounddevice.query_devices())"
# → Anotar índices do Jabra
Copy-Item .env.example .env
# → Editar .env com AUDIO_INPUT_DEVICE e AUDIO_OUTPUT_DEVICE

# 6. Validar (opcional)
python check_deps.py

# 7. RODAR! 🎉
python src/main.py
```

---

## 📋 Checklist Rápido

- [ ] Python 3.11+
- [ ] `pip install -r requirements.txt`
- [ ] `tools/llama.cpp/llama-server.exe` baixado
- [ ] `models/qwen3-8b/Qwen3-8B-Q4_K_M.gguf` (~5.5GB)
- [ ] `models/piper/pt_BR-faber-medium/` (2 arquivos)
- [ ] `.env` preenchido com device indices
- [ ] `python check_deps.py` → OK

---

## 🔧 Troubleshooting Rápido

| Problema | Solução |
|----------|---------|
| `ModuleNotFoundError: sounddevice` | `pip install sounddevice` |
| `No module named 'src'` | Rodar do diretório raiz: `python src/main.py` |
| `Microfone silencioso` | `python -c "import sounddevice; print(sounddevice.query_devices())"` e ajuste `.env` |
| `Vulkan not found` | Instalar AMD Adrenalin drivers |
| `llama-server timeout` | Verificar path em `src/config.py` |

---

## 📚 Documentação Completa

- **[docs/SETUP_WINDOWS.md](docs/SETUP_WINDOWS.md)** — Guia passo-a-passo (7 seções)
- **[docs/FASE_0_COMPLETA.md](docs/FASE_0_COMPLETA.md)** — Resumo técnico das mudanças
- **[docs/DEPENDENCIAS_FASE_0.md](docs/DEPENDENCIAS_FASE_0.md)** — Checklist detalhado de dependências
- **[docs/PLANO.md](docs/PLANO.md)** — Roadmap de fases (Fase 1+)

---

## ✅ Validation

Após setup, validar com:

```powershell
python check_deps.py
```

Esperado: **0 falhas**.

---

## 🎯 O que é a Fase 0?

Portagem completa de Linux → Windows:
- ✅ `audio.py` reescrita (ffmpeg/pactl → sounddevice)
- ✅ `config.py` ajustada (remove VK_ICD Linux)
- ✅ `llm_local.py` suporta Windows paths
- ✅ `shell.py` suporta PowerShell
- ✅ `requirements.txt` com sounddevice
- ✅ Documentação completa

**Próximo:** Fase 1 (openWakeWord, Silero VAD, fluidez)

---

## 💬 Uso

```powershell
python src/main.py

# Espere:
# [modo LLM: local | TTS: piper]
# ✓ Microfone OK
# Pronto. Aguardando wake word 'Jarvis'...

# Diga: "Jarvis"
# Diga seu comando: "qual é a hora?"
# Escuta a resposta em voz

# Para sair: Ctrl+C
```

---

**Pronto! Agora você pode rodar Jarvis-1 no Windows 11. 🎉**

Dúvidas? Veja os docs acima.

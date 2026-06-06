import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Carrega .env se existir
_env_file = os.path.join(BASE_DIR, ".env")
if os.path.exists(_env_file):
    with open(_env_file) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())
MODELS_DIR = os.path.join(BASE_DIR, "models")
TOOLS_DIR = os.path.join(BASE_DIR, "tools")

# Vulkan ICD para RX 580
VK_ICD = "/usr/lib/x86_64-linux-gnu/GL/default/lib/vulkan/icd.d/radeon_icd.x86_64.json"

# STT — faster-whisper
WHISPER_MODEL = "small"  # tiny|base|small|medium — tradeoff latência/qualidade
WHISPER_LANGUAGE = "pt"
WHISPER_DEVICE = "cpu"   # cpu (RX 580 sem ROCm)
WHISPER_COMPUTE_TYPE = "int8"

# LLM — Maritaca API (online, fallback para local)
MARITACA_API_KEY = os.environ.get("MARITACA_API_KEY", "")
MARITACA_MODEL = "sabiazinho-3"
MARITACA_BASE_URL = "https://chat.maritaca.ai/api"
MARITACA_MAX_TOKENS = 512
MARITACA_TEMPERATURE = 0.7

# LLM local (offline) — llama.cpp + Vulkan
LLAMA_CLI = os.path.join(TOOLS_DIR, "llama.cpp/build/bin/llama-cli")
LLAMA_MODEL = os.path.join(MODELS_DIR, "qwen3-8b/Qwen3-8B-Q4_K_M.gguf")

# Modo LLM: "cloud" (Maritaca API) | "local" (llama-server + Vulkan)
LLM_MODE = os.environ.get("LLM_MODE", "cloud")

# TTS — "piper" (RTF 0.06x, rápido) | "kokoro" (RTF 0.38x, mais natural) | "qwen3" (RTF 9.6x, qualidade máxima)
TTS_MODE = os.environ.get("TTS_MODE", "piper")

# TTS — Kokoro ONNX (legado)
KOKORO_LANG = "pt-br"    # português brasileiro
KOKORO_VOICE = "pf_dora" # voz padrão; outros: af_heart, am_adam

# Áudio
AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1
AUDIO_RECORD_SECONDS = 5    # máximo por fala
AUDIO_SILENCE_THRESHOLD = 0.02  # RMS para detectar fim de fala
AUDIO_SILENCE_DURATION = 1.0    # segundos de silêncio para encerrar gravação
PULSE_SERVER = "unix:/run/flatpak/pulse/native"

# Sistema
def _build_system_prompt() -> str:
    from datetime import datetime
    now = datetime.now().strftime("%d de %B de %Y, %H:%M")
    return f"""Você é Jarvis, assistente de IA pessoal rodando localmente no computador do usuário.
Data e hora atual: {now}.
Você pode executar comandos no computador, abrir aplicativos e responder perguntas.
Responda sempre em português brasileiro, de forma concisa e natural para voz.
Use frases curtas, de no máximo 20 palavras. Não use listas, bullets ou markdown — apenas texto corrido."""

SYSTEM_PROMPT = _build_system_prompt()

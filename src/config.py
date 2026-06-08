import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_env_file = os.path.join(BASE_DIR, ".env")
if os.path.exists(_env_file):
    with open(_env_file, encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())
MODELS_DIR = os.path.join(BASE_DIR, "models")
TOOLS_DIR = os.path.join(BASE_DIR, "tools")

_IS_WINDOWS = sys.platform.startswith("win")
_IS_LINUX = sys.platform.startswith("linux")

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

# Ler modelo de .env (QWEN_MODEL)
_qwen_model_name = os.environ.get("QWEN_MODEL", "Qwen3-8B-Q4_K_M.gguf")
# Adicionar .gguf se não tiver
if not _qwen_model_name.endswith(".gguf"):
    _qwen_model_name += ".gguf"

# Detectar subdiretório baseado no nome do modelo
if "35B" in _qwen_model_name:
    _qwen_subdir = "qwen3-35b"
elif "4B" in _qwen_model_name:
    _qwen_subdir = "qwen3-4b"
else:
    _qwen_subdir = "qwen3-8b"

# Caminho do .gguf: override absoluto via LLAMA_MODEL_PATH (ex.: modelo no disco A:),
# senão monta a partir de MODELS_DIR.
_llama_model_override = os.environ.get("LLAMA_MODEL_PATH", "").strip()
if _llama_model_override:
    LLAMA_MODEL = _llama_model_override
else:
    LLAMA_MODEL = os.path.join(MODELS_DIR, _qwen_subdir, _qwen_model_name)

# Binário do llama-server (TurboQuant + Vulkan). Sem fallback: se vazio, usa o padrão em tools/.
LLAMA_SERVER_PATH = os.environ.get("LLAMA_SERVER_PATH", "").strip()

# Flags do llama-server (defaults = vídeo TurboQuant).
LLAMA_NCMOE = os.environ.get("LLAMA_NCMOE", "36").strip()
LLAMA_CTX = os.environ.get("LLAMA_CTX", "4096").strip()
LLAMA_CTK = os.environ.get("LLAMA_CTK", "q8_0").strip()
LLAMA_CTV = os.environ.get("LLAMA_CTV", "q8_0").strip()

# MoE (Mixture of Experts) detectado pelo nome do modelo — habilita --n-cpu-moe.
LLAMA_IS_MOE = "35B" in os.path.basename(LLAMA_MODEL)

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
AUDIO_RECORD_SECONDS = 5
AUDIO_SILENCE_THRESHOLD = 0.02
AUDIO_SILENCE_DURATION = 1.0

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

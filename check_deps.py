#!/usr/bin/env python3
"""
Verificador de dependências — Fase 0 Windows
Testa se o ambiente está pronto para rodar Jarvis-1.
"""
import sys
import os

print("=" * 60)
print("Jarvis-1 — Verificação de Dependências (Windows Fase 0)")
print("=" * 60)

checks_passed = 0
checks_failed = 0

def check(name: str, condition: bool, details: str = "") -> None:
    global checks_passed, checks_failed
    status = "✓" if condition else "✗"
    color = "\033[92m" if condition else "\033[91m"
    reset = "\033[0m"

    if sys.platform.startswith("win"):
        status_str = f"[{status}]" if condition else "[X]"
    else:
        status_str = f"{color}{status}{reset}"

    print(f"{status_str} {name}")
    if details:
        print(f"    → {details}")

    if condition:
        checks_passed += 1
    else:
        checks_failed += 1

# 1. Python versão
print("\n[Python]")
check("Python 3.11+", sys.version_info >= (3, 11), f"Atual: {sys.version_info.major}.{sys.version_info.minor}")

# 2. Windows (esperado)
print("\n[OS]")
check("Windows", sys.platform.startswith("win"), f"Plataforma: {sys.platform}")

# 3. Imports Python
print("\n[Imports Python]")
deps = {
    "numpy": None,
    "sounddevice": None,
    "faster_whisper": None,
    "piper": None,
    "onnxruntime": None,
    "requests": None,
    "ctranslate2": None,
}

for dep, _ in deps.items():
    try:
        __import__(dep)
        check(f"pip: {dep}", True)
    except ImportError:
        check(f"pip: {dep}", False, "Execute: pip install -r requirements.txt")

# 4. Arquivos
print("\n[Estrutura de Pastas]")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")
TOOLS_DIR = os.path.join(BASE_DIR, "tools")

check(f"Pasta models/", os.path.isdir(MODELS_DIR))
check(f"Pasta tools/", os.path.isdir(TOOLS_DIR))

# 5. Modelos
print("\n[Modelos (HuggingFace)]")
qwen_path = os.path.join(MODELS_DIR, "qwen3-8b", "Qwen3-8B-Q4_K_M.gguf")
piper_path = os.path.join(MODELS_DIR, "piper", "pt_BR-faber-medium", "pt_BR-faber-medium.onnx")

check(
    "Qwen3-8B GGUF",
    os.path.exists(qwen_path),
    f"Procurando: {qwen_path}"
)
check(
    "Piper TTS",
    os.path.exists(piper_path),
    f"Procurando: {piper_path}"
)

# 6. llama-server.exe
print("\n[LLM (llama.cpp + Vulkan)]")
llama_exe = os.path.join(TOOLS_DIR, "llama.cpp", "llama-server.exe")
check(
    "llama-server.exe",
    os.path.exists(llama_exe),
    f"Procurando: {llama_exe}"
)

# 7. Config
print("\n[Configuração]")
env_file = os.path.join(BASE_DIR, ".env")
check(
    ".env arquivo",
    os.path.exists(env_file),
    "Copie .env.example → .env e preencha com índices de áudio"
)

if os.path.exists(env_file):
    with open(env_file) as f:
        env_vars = {line.split("=")[0].strip(): line.split("=")[1].strip()
                   for line in f if "=" in line and not line.startswith("#")}

    check("LLM_MODE definido", "LLM_MODE" in env_vars)
    check("TTS_MODE definido", "TTS_MODE" in env_vars)
    check("AUDIO_INPUT_DEVICE definido", "AUDIO_INPUT_DEVICE" in env_vars)
    check("AUDIO_OUTPUT_DEVICE definido", "AUDIO_OUTPUT_DEVICE" in env_vars)

# 8. Áudio (sounddevice)
print("\n[Áudio (sounddevice)]")
try:
    import sounddevice as sd
    devices = sd.query_devices()
    device_list = str(devices)
    has_jabra = "jabra" in device_list.lower()
    check("sounddevice funcionando", True, f"{len(devices)} devices detectados")
    check("Headset Jabra detectado", has_jabra, "Execute: python -c \"import sounddevice; print(sounddevice.query_devices())\"")
except Exception as e:
    check("sounddevice funcionando", False, str(e))

# 9. Teste de imports internos
print("\n[Imports Jarvis]")
sys.path.insert(0, os.path.join(BASE_DIR, "src"))
try:
    import config
    check("config.py importável", True)
except Exception as e:
    check("config.py importável", False, str(e))

try:
    import audio
    check("audio.py importável (sounddevice)", True)
except Exception as e:
    check("audio.py importável", False, str(e))

try:
    from llm_local import ensure_server
    check("llm_local.py importável", True)
except Exception as e:
    check("llm_local.py importável", False, str(e))

# 10. Resumo
print("\n" + "=" * 60)
print(f"RESULTADO: {checks_passed} OK, {checks_failed} FALHAS")

if checks_failed == 0:
    print("\n✓ Ambiente pronto! Execute: python src/main.py")
    sys.exit(0)
else:
    print(f"\n✗ {checks_failed} verificação(ões) falharam.")
    print("  Ver detalhes acima.")
    sys.exit(1)

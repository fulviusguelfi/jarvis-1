#!/usr/bin/env python3
"""Setup de modelos para Jarvis-1 v0.2.0.

Baixa TODOS os modelos necessários ANTES de rodar o Jarvis.
Determinístico: falha com erro claro se algo não conseguir baixar.
"""
import os
import sys
import subprocess
import zipfile
import shutil
from pathlib import Path
from urllib.request import urlopen

print("=" * 70)
print("JARVIS-1 — Setup de Modelos (v0.2.0)")
print("=" * 70)
print()

project_root = Path(__file__).parent
models_dir = project_root / "models"

# Criar diretórios
print("[1/3] Criando estrutura de diretórios...")
(models_dir / "openWakeWord").mkdir(parents=True, exist_ok=True)
print("      OK")

# F1.1: openWakeWord hey_jarvis — caminho REAL usado por src/wake.py
print("[2/4] Verificando openWakeWord hey_jarvis_v0.1.onnx...")
oww_model = (project_root / ".venv" / "Lib" / "site-packages" / "openwakeword"
             / "resources" / "models" / "hey_jarvis_v0.1.onnx")

if oww_model.exists():
    print(f"      [OK] JA EXISTE: {oww_model}")
    print(f"           ({oww_model.stat().st_size / (1024*1024):.1f} MB)")
else:
    print(f"      [FALTA] {oww_model}")
    print(f"      Este e o arquivo que src/wake.py carrega. Reinstale openWakeWord:")
    print(f"      pip install --force-reinstall openwakeword")
    sys.exit(1)

# Verificar dependências Python
print("[3/4] Verificando dependências...")
deps_ok = True
required = {
    "numpy": "pip install numpy",
    "requests": "pip install requests",
    "sounddevice": "pip install sounddevice",
    "librosa": "pip install librosa",
    "openwakeword": "pip install openwakeword",
    "silero_vad": "pip install silero-vad",
    "faster_whisper": "pip install faster-whisper",
    "piper": "pip install piper-tts",
    "onnxruntime": "pip install onnxruntime",
    "transformers": "pip install transformers",  # Smart Turn v3 (WhisperFeatureExtractor)
}

for module, install_cmd in required.items():
    try:
        __import__(module)
        print(f"      [OK] {module}")
    except ImportError:
        print(f"      [MISSING] {module} nao instalado")
        print(f"               Execute: {install_cmd}")
        deps_ok = False

if not deps_ok:
    print()
    print("[ERRO] Faltam dependencias Python.")
    print("Execute: pip install -r requirements.txt")
    sys.exit(1)

# LLM local: binario llama-server (turbo) e modelo .gguf
print("[4/4] Verificando LLM local (llama-server + modelo)...")
sys.path.insert(0, str(project_root / "src"))
import config as _cfg

if _cfg.LLM_MODE == "local":
    _server = _cfg.LLAMA_SERVER_PATH or os.path.join(
        str(project_root), "tools", "llama.cpp", "llama-server.exe")
    if os.path.exists(_server):
        print(f"      [OK] llama-server: {_server}")
    else:
        print(f"      [FALTA] llama-server: {_server}")
        print(f"             Compile o fork TurboQuant ou ajuste LLAMA_SERVER_PATH no .env.")
        sys.exit(1)
    if os.path.exists(_cfg.LLAMA_MODEL):
        print(f"      [OK] modelo: {_cfg.LLAMA_MODEL}")
    else:
        print(f"      [FALTA] modelo: {_cfg.LLAMA_MODEL}")
        print(f"             Ajuste LLAMA_MODEL_PATH/QWEN_MODEL no .env.")
        sys.exit(1)
else:
    print(f"      [INFO] LLM_MODE={_cfg.LLM_MODE} (nao-local) — pulando checagem do llama-server.")

# F1.6.2: Smart Turn v3 (endpoint semantico) — ONNX ~8MB
print("[5/5] Verificando Smart Turn v3 (endpoint semantico)...")
_turn_dir = models_dir / "smart-turn"
_turn_model = _turn_dir / "smart-turn-v3.2-cpu.onnx"
if _turn_model.exists():
    print(f"      [OK] JA EXISTE: {_turn_model} ({_turn_model.stat().st_size/1024:.0f} KB)")
else:
    print(f"      [FALTA] Baixando {_turn_model.name} de pipecat-ai/smart-turn-v3...")
    _turn_dir.mkdir(parents=True, exist_ok=True)
    _url = "https://huggingface.co/pipecat-ai/smart-turn-v3/resolve/main/smart-turn-v3.2-cpu.onnx"
    try:
        import requests
        _r = requests.get(_url, timeout=120, stream=True)
        _r.raise_for_status()
        with open(_turn_model, "wb") as _f:
            for _ch in _r.iter_content(8192):
                _f.write(_ch)
        print(f"      [OK] Baixado ({_turn_model.stat().st_size/1024:.0f} KB)")
    except Exception as _e:
        print(f"      [ERRO] Falha ao baixar Smart Turn: {_e}")
        print(f"             Baixe manualmente: {_url}")
        sys.exit(1)

print()
print("=" * 70)
print("[OK] Setup concluído com sucesso!")
print("=" * 70)
print()
print("Próximo passo: rodar Jarvis")
print("  python src/main.py")
print()

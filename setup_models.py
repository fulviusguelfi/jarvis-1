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

# F1.1: openWakeWord hey_jarvis.onnx
print("[2/3] Baixando openWakeWord hey_jarvis.onnx...")
oww_dir = models_dir / "openWakeWord"
oww_model = oww_dir / "hey_jarvis.onnx"

if oww_model.exists():
    print(f"      JA EXISTE: {oww_model}")
else:
    print("      Baixando de GitHub...")
    oww_url = "https://github.com/dscripka/openWakeWord/releases/download/v0.6.0/hey_jarvis.onnx"
    try:
        with urlopen(oww_url) as response:
            content = response.read()
        with open(oww_model, "wb") as f:
            f.write(content)
        size_mb = len(content) / (1024 * 1024)
        print(f"      OK ({size_mb:.1f} MB)")
    except Exception as e:
        print(f"      [ERRO] Nao conseguiu baixar: {e}")
        print(f"      Manual: Baixe de {oww_url}")
        print(f"      E coloque em: {oww_model}")
        sys.exit(1)

# Verificar dependências Python
print("[3/3] Verificando dependências...")
deps_ok = True
required = {
    "sounddevice": "pip install sounddevice",
    "openwakeword": "pip install openwakeword",
    "silero_vad": "pip install silero-vad",
    "faster_whisper": "pip install faster-whisper",
    "piper": "pip install piper-tts",
}

for module, install_cmd in required.items():
    try:
        __import__(module)
        print(f"      ✓ {module}")
    except ImportError:
        print(f"      ✗ {module} nao instalado")
        print(f"        Execute: {install_cmd}")
        deps_ok = False

if not deps_ok:
    print()
    print("[ERRO] Faltam dependências Python.")
    print("Execute: pip install -r requirements.txt")
    sys.exit(1)

print()
print("=" * 70)
print("[OK] Setup concluído com sucesso!")
print("=" * 70)
print()
print("Próximo passo: rodar Jarvis")
print("  python src/main.py")
print()

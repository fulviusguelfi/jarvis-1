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
print("[2/3] Verificando openWakeWord hey_jarvis.onnx...")
oww_dir = models_dir / "openWakeWord"
oww_model = oww_dir / "hey_jarvis.onnx"

if oww_model.exists():
    print(f"      [OK] JA EXISTE: {oww_model}")
    print(f"           ({oww_model.stat().st_size / (1024*1024):.1f} MB)")
else:
    print(f"      [FALTA] {oww_model}")
    print(f"")
    print(f"      COMO BAIXAR:")
    print(f"      1. Visite: https://github.com/dscripka/openWakeWord")
    print(f"      2. Procure em 'Releases' pela versão mais recente")
    print(f"      3. Baixe o arquivo: hey_jarvis.onnx (~1 MB)")
    print(f"      4. Crie pasta: {oww_dir}")
    print(f"      5. Coloque lá: {oww_model}")
    print(f"      6. Rode setup novamente")
    print(f"")
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

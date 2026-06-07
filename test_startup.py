#!/usr/bin/env python3
"""Teste rápido de startup — validar que tudo carrega sem erro."""
import sys
sys.path.insert(0, 'src')

print("=" * 60)
print("TESTE DE STARTUP — Jarvis-1 v0.2.0")
print("=" * 60)
print()

# 1. Config
print("[1/6] Carregando config...")
try:
    from config import MARITACA_API_KEY, LLM_MODE, TTS_MODE
    print(f"  LLM_MODE={LLM_MODE}, TTS_MODE={TTS_MODE}")
    print("  [OK]")
except Exception as e:
    print(f"  [ERRO] {e}")
    sys.exit(1)

# 2. Audio
print("[2/6] Inicializando audio...")
try:
    from audio import _get_mic_stream
    print("  [OK] audio pronto")
except Exception as e:
    print(f"  [ERRO] {e}")
    sys.exit(1)

# 3. STT
print("[3/6] Carregando Whisper...")
try:
    from stt import _get_model as get_whisper
    model = get_whisper()
    print(f"  [OK] Whisper carregado")
except Exception as e:
    print(f"  [ERRO] {e}")
    sys.exit(1)

# 4. Wake word
print("[4/6] Testando openWakeWord...")
try:
    from wake import _get_model as get_wake
    try:
        model = get_wake()
        print("  [OK] openWakeWord carregado (hey_jarvis.onnx)")
    except FileNotFoundError as e:
        print(f"  [AVISO] {e}")
        print("  Continuando sem openWakeWord (fallback para Whisper)")
except Exception as e:
    print(f"  [ERRO] {e}")
    # Não fatal, continuamos

# 5. TTS
print("[5/6] Carregando TTS...")
try:
    if TTS_MODE == "piper":
        from tts_piper import _get_voice
        _get_voice()
    print(f"  [OK] TTS ({TTS_MODE}) pronto")
except Exception as e:
    print(f"  [ERRO] {e}")
    sys.exit(1)

# 6. LLM
print("[6/6] Testando LLM...")
try:
    if LLM_MODE == "local":
        from llm_local import LocalLLMClient
        client = LocalLLMClient()
        print("  [OK] LLM local pronto")
    else:
        print(f"  [INFO] LLM_MODE={LLM_MODE} (será testado em runtime)")
except Exception as e:
    print(f"  [AVISO] {e}")

print()
print("=" * 60)
print("[OK] STARTUP VALIDADO - Pronto para rodar!")
print("=" * 60)
print()
print("Execute: python src/main.py")
print()

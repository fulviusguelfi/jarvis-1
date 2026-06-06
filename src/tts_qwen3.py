"""
TTS via Qwen3-TTS-GGUF — substituto drop-in para tts.py (Kokoro).
Interface: synthesize(text) → (samples_float32, sample_rate)
"""
import os
import sys
import numpy as np

from config import BASE_DIR

_TTS_DIR = os.path.join(BASE_DIR, "tools/qwen3-tts-gguf")
_MODEL_DIR = os.path.join(_TTS_DIR, "model-custom")

if _TTS_DIR not in sys.path:
    sys.path.insert(0, _TTS_DIR)

# Voz e instrução padrão para o Jarvis
_SPEAKER = "Ryan"
_LANGUAGE = "portuguese"
_INSTRUCT = "Calm, helpful AI assistant voice. Clear articulation."

_engine = None
_stream = None


def _get_stream():
    global _engine, _stream
    if _stream is not None:
        return _stream

    from qwen3_tts_gguf.inference import TTSEngine
    print("[TTS-Qwen3] Carregando motor (pode demorar ~20s)...")
    _engine = TTSEngine(
        model_dir=_MODEL_DIR,
        onnx_provider="CPUExecutionProvider",
        llm_use_gpu=False,
        verbose=False,
    )
    if not _engine:
        raise RuntimeError("Qwen3-TTS engine não inicializou")

    _stream = _engine.create_stream()
    print("[TTS-Qwen3] Pronto.")
    return _stream


def synthesize(text: str, speaker: str = _SPEAKER, language: str = _LANGUAGE,
               instruct: str = _INSTRUCT, speed_hint: float = 1.0) -> tuple[np.ndarray, int]:
    """Converte texto em áudio. Retorna (samples_float32, sample_rate=24000)."""
    if not text.strip():
        return np.zeros(0, dtype=np.float32), 24000

    from qwen3_tts_gguf.inference import TTSConfig
    config = TTSConfig(
        max_steps=400,
        temperature=0.6,
        sub_temperature=0.6,
        seed=42,
        sub_seed=45,
        streaming=False,
    )

    stream = _get_stream()
    result = stream.custom(
        text=text,
        speaker=speaker,
        instruct=instruct,
        language=language,
        config=config,
    )

    if result is None or result.audio is None:
        print(f"[TTS-Qwen3] Síntese falhou para: {text[:60]}")
        return np.zeros(0, dtype=np.float32), 24000

    audio = result.audio.astype(np.float32)
    duration = len(audio) / 24000
    print(f"[TTS-Qwen3] {len(text)} chars → {duration:.1f}s de áudio")
    return audio, 24000


def shutdown():
    global _engine, _stream
    if _engine is not None:
        _engine.shutdown()
        _engine = None
        _stream = None

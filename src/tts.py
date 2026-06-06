import os
import numpy as np
from config import KOKORO_VOICE, KOKORO_LANG, BASE_DIR

_MODEL_PATH = os.path.join(BASE_DIR, "models/kokoro/kokoro-v1.0.onnx")
_VOICES_PATH = os.path.join(BASE_DIR, "models/kokoro/voices-v1.0.bin")

_kokoro = None


def _get_kokoro():
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro
        print("[TTS] Carregando Kokoro...")
        _kokoro = Kokoro(_MODEL_PATH, _VOICES_PATH)
        print("[TTS] Pronto.")
    return _kokoro


def synthesize(text: str, voice: str = KOKORO_VOICE, speed: float = 1.1) -> tuple[np.ndarray, int]:
    """Converte texto em áudio. Retorna (samples_float32, sample_rate)."""
    if not text.strip():
        return np.zeros(0, dtype=np.float32), 24000

    kokoro = _get_kokoro()
    samples, rate = kokoro.create(text, voice=voice, speed=speed, lang=KOKORO_LANG)
    print(f"[TTS] {len(text)} chars → {len(samples)/rate:.1f}s de áudio")
    return samples, rate

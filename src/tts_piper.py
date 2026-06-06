"""
TTS via Piper — sintetizador ultra-rápido (RTF ~0.06x).
Interface: synthesize(text) → (samples_float32, sample_rate)
"""
import os
import sys
import wave
import io
import numpy as np
from config import BASE_DIR

# Modelos disponíveis: "faber" (mais natural) | "cadu" (mais rápido)
PIPER_VOICE = os.environ.get("PIPER_VOICE", "faber")

_MODELS = {
    "faber": "pt_BR-faber-medium",
    "cadu":  "pt_BR-cadu-medium",
    "jeff":  "pt_BR-jeff-medium",
}

_voice = None


def _get_voice():
    global _voice
    if _voice is not None:
        return _voice

    from piper import PiperVoice
    model_name = _MODELS.get(PIPER_VOICE, _MODELS["faber"])
    model_dir = os.path.join(BASE_DIR, "models/piper", model_name)
    model_path = os.path.join(model_dir, f"{model_name}.onnx")
    config_path = f"{model_path}.json"

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Modelo Piper não encontrado: {model_path}")

    print(f"[TTS-Piper] Carregando {model_name}...")
    _voice = PiperVoice.load(model_path, config_path=config_path, use_cuda=False)
    print("[TTS-Piper] Pronto.")
    return _voice


def synthesize(text: str, speed: float = 1.0) -> tuple[np.ndarray, int]:
    """Converte texto em áudio. Retorna (samples_float32, sample_rate)."""
    if not text.strip():
        return np.zeros(0, dtype=np.float32), 22050

    voice = _get_voice()
    rate = voice.config.sample_rate

    buf = io.BytesIO()
    with wave.open(buf, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        voice.synthesize_wav(text, wf)

    buf.seek(44)  # pular header WAV
    raw = buf.read()
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    print(f"[TTS-Piper] {len(text)} chars → {len(samples)/rate:.1f}s de áudio")
    return samples, rate


def shutdown():
    global _voice
    _voice = None

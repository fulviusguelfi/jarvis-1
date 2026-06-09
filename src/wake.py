"""openWakeWord 'Hey Jarvis' via pipeline oficial (melspectrogram -> embedding -> wake).

F1.1: classificador puro (score 0-1). Nao gera texto -> impossivel alucinar (RSK01).
Streaming: main.py alimenta frames de 80ms (1280 samples @16kHz) continuamente.
"""
import numpy as np
from pathlib import Path

_model = None
_WAKE = "hey_jarvis_v0.1"
_THRESHOLD = 0.5  # score > limiar = ativado


def _get_model():
    """Carrega o Model oficial do openWakeWord (lazy). Pipeline ONNX completo."""
    global _model
    if _model is not None:
        return _model

    import openwakeword
    from openwakeword.model import Model

    res = Path(openwakeword.__file__).parent / "resources" / "models"
    wake_path = res / f"{_WAKE}.onnx"
    if not wake_path.exists():
        raise FileNotFoundError(f"Modelo de wake nao encontrado: {wake_path}")
    if not (res / "melspectrogram.onnx").exists() or not (res / "embedding_model.onnx").exists():
        raise FileNotFoundError(
            "Feature models do openWakeWord ausentes. Rode:\n"
            '  python -c "import openwakeword.utils as u; u.download_models()"'
        )

    _model = Model(wakeword_models=[str(wake_path)], inference_framework="onnx")
    print("[wake] openWakeWord hey_jarvis carregado (pipeline oficial ONNX)")
    return _model


def _to_int16(audio: np.ndarray) -> np.ndarray:
    """Normaliza para int16 mono (openWakeWord espera int16 @16kHz)."""
    audio = np.asarray(audio).flatten()
    if audio.dtype == np.int16:
        return audio
    a = audio.astype(np.float32)
    if np.max(np.abs(a)) <= 1.5:          # float normalizado [-1, 1]
        a = a * 32767.0
    return np.clip(a, -32768, 32767).astype(np.int16)


def get_score(audio_frames: np.ndarray, sample_rate: int = 16000) -> float:
    """Score 0-1 do wake 'hey_jarvis' para o(s) frame(s) dados."""
    model = _get_model()
    scores = model.predict(_to_int16(audio_frames))
    return float(scores.get(_WAKE, 0.0))


def detect_wake_word(audio_frames: np.ndarray, sample_rate: int = 16000) -> bool:
    """True se 'Hey Jarvis' detectado (score > limiar). DETERMINISTICO: so bool."""
    return get_score(audio_frames, sample_rate) > _THRESHOLD


def reset() -> None:
    """Limpa o buffer de streaming (usar entre sessoes independentes / testes)."""
    if _model is not None:
        _model.reset()

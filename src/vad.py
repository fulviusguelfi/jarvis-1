"""Silero VAD - Voice Activity Detection para endpointing preciso.

F1.2: Substitui RMS em record_until_silence() por Silero VAD (ONNX).
Detecta fim de fala com precisao, elimina tempo morto de 1.2s -> ~300ms.
"""
import numpy as np
from pathlib import Path

# Lazy load
_model = None
_sample_rate = 16000


def _get_model():
    """Carrega modelo Silero VAD (lazy load)."""
    global _model
    if _model is not None:
        return _model

    try:
        import onnxruntime as ort
    except ImportError:
        raise ImportError(
            "onnxruntime nao instalado. Execute: pip install onnxruntime"
        )

    try:
        import silero_vad
    except ImportError:
        raise ImportError(
            "silero-vad nao instalado. Execute: pip install silero-vad"
        )

    # Silero VAD carrega automaticamente o modelo ONNX
    _model = silero_vad.load_silero_vad()
    return _model


def detect_voice(
    audio_frames: np.ndarray,
    sample_rate: int = 16000,
    threshold: float = 0.5
) -> bool:
    """
    Detecta se ha voz nos frames de audio.

    Args:
        audio_frames: numpy array (mono, int16 ou float32)
        sample_rate: taxa de amostragem
        threshold: limiar de probabilidade (0-1)

    Returns:
        True se ha voz com confianca > threshold
    """
    model = _get_model()

    # Normalizar para float32 [-1, 1]
    if audio_frames.dtype == np.int16:
        audio = audio_frames.astype(np.float32) / 32768.0
    else:
        audio = audio_frames.astype(np.float32)

    # Silero VAD espera tensor ONNX, usar o wrapper
    try:
        # Modo simples: processar frame inteiro
        confidence = model(audio, sample_rate)
        return confidence > threshold
    except Exception as e:
        # Fallback: se erro, assumir silencio (conservador)
        print(f"[vad] erro ao rodar Silero VAD: {e}")
        return False


def get_confidence(
    audio_frames: np.ndarray,
    sample_rate: int = 16000
) -> float:
    """Retorna score bruto do Silero VAD (0-1) para debug."""
    model = _get_model()

    if audio_frames.dtype == np.int16:
        audio = audio_frames.astype(np.float32) / 32768.0
    else:
        audio = audio_frames.astype(np.float32)

    try:
        confidence = model(audio, sample_rate)
        return float(confidence)
    except Exception:
        return 0.0


def record_until_silence_vad(
    stream,
    sample_rate: int = 16000,
    max_duration: float = 10.0,
    silence_threshold: float = 0.5,
    min_silence_duration: float = 0.5,
) -> list[np.ndarray]:
    """
    Grava ate Silero VAD detectar fim de fala.

    Args:
        stream: sounddevice InputStream aberto
        sample_rate: taxa de amostragem
        max_duration: duracao maxima de gravacao
        silence_threshold: limiar Silero VAD (< threshold = silencio)
        min_silence_duration: tempo minimo de silencio para considerar fim (segundos)

    Returns:
        Lista de frames (numpy arrays) gravados
    """
    import time

    model = _get_model()
    frames = []
    silence_start = None
    start = time.time()
    spoke = False
    chunk_size = int(sample_rate * 0.08)  # 80ms chunks para Silero

    try:
        while True:
            elapsed = time.time() - start
            if elapsed >= max_duration:
                break

            data, _ = stream.read(chunk_size)
            frames.append(data)

            # Normalizar para float32 [-1, 1]
            audio = data.astype(np.float32) / 32768.0

            # Silero VAD
            try:
                confidence = model(audio, sample_rate)
            except Exception:
                confidence = 0.0

            # Log para debug (pode remover em producao)
            # print(f"[vad-debug] confidence={confidence:.2f}")

            # Detectar transicao voz -> silencio
            if confidence > silence_threshold:
                spoke = True
                silence_start = None
            elif spoke:
                if silence_start is None:
                    silence_start = time.time()
                elif time.time() - silence_start >= min_silence_duration:
                    break

    except Exception as e:
        print(f"[audio-vad] erro durante gravacao: {e}")

    return frames

"""OpenWakeWord - deteccao de wake word dedicado com Silero VAD integrado."""
import numpy as np
from pathlib import Path

# Lazy load para nao crashear se openWakeWord nao estiver instalado
_model = None
_sample_rate = 16000


def _get_model():
    """Carrega o modelo openWakeWord hey_jarvis (lazy load)."""
    global _model
    if _model is not None:
        return _model

    try:
        from openwakeword.model import Model
    except ImportError:
        raise ImportError(
            "openWakeWord nao instalado. Execute: pip install openwakeword"
        )

    # Caminho relativo ao diretorio src/
    model_dir = Path(__file__).parent.parent / "models" / "openWakeWord"
    model_path = model_dir / "hey_jarvis.onnx"

    if not model_path.exists():
        raise FileNotFoundError(
            f"Modelo hey_jarvis.onnx nao encontrado em {model_path}. "
            "Baixe de: https://github.com/dscripka/openWakeWord"
        )

    # Inicializar modelo com VAD nativo + Speex suppression (melhor em ruido BT)
    _model = Model(
        wakeword_models=[str(model_path)],
        inference_framework="onnx",
        vad_threshold=0.5,  # Silero VAD integrado como gate
        enable_speex_noise_suppression=True,
    )
    return _model


def detect_wake_word(audio_frames: np.ndarray, sample_rate: int = 16000) -> bool:
    """
    Detecta "Hey Jarvis" em frames de audio.

    Args:
        audio_frames: numpy array de audio (mono, int16 ou float32)
        sample_rate: sample rate (padrão 16kHz)

    Returns:
        True se detectado com confianca > limiar
    """
    model = _get_model()

    # Normalizar para float32 [-1, 1] se int16
    if audio_frames.dtype == np.int16:
        audio_frames = audio_frames.astype(np.float32) / 32768.0

    # openWakeWord espera frames de ~80ms a 16kHz = 1280 samples
    # Se frame eh maior, processar em chunks de 1280
    frame_size = int(sample_rate * 0.08)  # 80ms @ 16kHz = 1280 samples

    # Processar frame unico (ou trocar por chunks se necessario)
    if len(audio_frames) < frame_size:
        # Pad com zeros se frame eh muito pequeno
        audio_frames = np.pad(
            audio_frames, (0, frame_size - len(audio_frames)), mode="constant"
        )
    elif len(audio_frames) > frame_size:
        # Truncar (ou processar em chunks - simplificado para F1.1)
        audio_frames = audio_frames[:frame_size]

    # Predizione do modelo retorna dict: {"hey_jarvis": score_0-1, ...}
    scores = model.predict(audio_frames)

    # Buscar score de "hey_jarvis" (exato ou similar chave)
    hey_jarvis_score = scores.get("hey_jarvis", 0.0)

    # Limiar empirico: > 0.5 eh muito permissivo, > 0.7 eh bem conservador
    # Usar 0.6 como balance
    return hey_jarvis_score > 0.6


def get_score(audio_frames: np.ndarray, sample_rate: int = 16000) -> float:
    """Retorna score bruto do modelo (0-1) para debug."""
    model = _get_model()

    if audio_frames.dtype == np.int16:
        audio_frames = audio_frames.astype(np.float32) / 32768.0

    frame_size = int(sample_rate * 0.08)
    if len(audio_frames) < frame_size:
        audio_frames = np.pad(
            audio_frames, (0, frame_size - len(audio_frames)), mode="constant"
        )
    elif len(audio_frames) > frame_size:
        audio_frames = audio_frames[:frame_size]

    scores = model.predict(audio_frames)
    return scores.get("hey_jarvis", 0.0)

"""OpenWakeWord - deteccao de wake word dedicado com Silero VAD integrado.

F1.1: Com fallback para Whisper se openWakeWord nao estiver disponivel.
"""
import numpy as np
from pathlib import Path

# Lazy load para nao crashear se openWakeWord nao estiver instalado
_model = None
_sample_rate = 16000


def _get_model():
    """Carrega o modelo openWakeWord hey_jarvis (lazy load).

    Retorna None em fallback (modelo nao encontrado ou nao instalado).
    """
    global _model
    if _model is not None:
        return _model

    try:
        from openwakeword.model import Model
    except ImportError:
        print("[wake] openWakeWord nao instalado — fallback para Whisper")
        return None

    # Caminho relativo ao diretorio src/
    model_dir = Path(__file__).parent.parent / "models" / "openWakeWord"
    model_path = model_dir / "hey_jarvis.onnx"

    if not model_path.exists():
        print(f"[wake] Modelo hey_jarvis.onnx nao encontrado em {model_path}")
        print("[wake] Fallback para Whisper (baixe o modelo para ativar openWakeWord)")
        return None

    try:
        # Inicializar modelo com VAD nativo + Speex suppression (melhor em ruido BT)
        _model = Model(
            wakeword_models=[str(model_path)],
            inference_framework="onnx",
            vad_threshold=0.5,  # Silero VAD integrado como gate
            enable_speex_noise_suppression=True,
        )
        print("[wake] openWakeWord hey_jarvis carregado com sucesso")
        return _model
    except Exception as e:
        print(f"[wake] Erro ao carregar modelo: {e}")
        print("[wake] Fallback para Whisper")
        return None


def detect_wake_word(audio_frames: np.ndarray, sample_rate: int = 16000) -> bool:
    """
    Detecta "Hey Jarvis" em frames de audio com openWakeWord.
    Retorna False em fallback (modelo nao disponivel).

    Args:
        audio_frames: numpy array de audio (mono, int16 ou float32)
        sample_rate: sample rate (padrao 16kHz)

    Returns:
        True se detectado com confianca > limiar
    """
    model = _get_model()

    # Fallback: se modelo nao disponivel, retorna False
    # (main.py volta a usar listen_for_wakeword_original que usa Whisper)
    if model is None:
        return False

    # Normalizar para float32 [-1, 1] se int16
    if audio_frames.dtype == np.int16:
        audio_frames = audio_frames.astype(np.float32) / 32768.0

    # openWakeWord espera frames de ~80ms a 16kHz = 1280 samples
    frame_size = int(sample_rate * 0.08)  # 80ms @ 16kHz = 1280 samples

    # Processar frame unico
    if len(audio_frames) < frame_size:
        # Pad com zeros se frame eh muito pequeno
        audio_frames = np.pad(
            audio_frames, (0, frame_size - len(audio_frames)), mode="constant"
        )
    elif len(audio_frames) > frame_size:
        # Truncar
        audio_frames = audio_frames[:frame_size]

    try:
        # Predizione do modelo retorna dict: {"hey_jarvis": score_0-1, ...}
        scores = model.predict(audio_frames)

        # Buscar score de "hey_jarvis"
        hey_jarvis_score = scores.get("hey_jarvis", 0.0)

        # Limiar: 0.6 como balance entre falsos positivos e falsos negativos
        return hey_jarvis_score > 0.6
    except Exception as e:
        print(f"[wake] erro ao rodar modelo: {e}")
        return False


def get_score(audio_frames: np.ndarray, sample_rate: int = 16000) -> float:
    """Retorna score bruto do modelo (0-1) para debug."""
    model = _get_model()

    if model is None:
        return 0.0

    if audio_frames.dtype == np.int16:
        audio_frames = audio_frames.astype(np.float32) / 32768.0

    frame_size = int(sample_rate * 0.08)
    if len(audio_frames) < frame_size:
        audio_frames = np.pad(
            audio_frames, (0, frame_size - len(audio_frames)), mode="constant"
        )
    elif len(audio_frames) > frame_size:
        audio_frames = audio_frames[:frame_size]

    try:
        scores = model.predict(audio_frames)
        return scores.get("hey_jarvis", 0.0)
    except Exception:
        return 0.0

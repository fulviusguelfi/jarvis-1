"""OpenWakeWord - hey_jarvis classifier via ONNX Runtime direto.

F1.1: Carrega modelo ONNX sem dependencias internas que faltam.
Classificador puro: impossível alucinar (retorna só 0-1 score).
"""
import numpy as np
from pathlib import Path
import librosa

_model = None
_sample_rate = 16000
_mel_sample_rate = 16000
_n_mels = 16
_n_fft = 512


def _get_model():
    """Carrega hey_jarvis.onnx direto via onnxruntime (sem openWakeWord wrapper).

    Isso evita dependências de melspectrogram, speexdsp_ns, etc.
    """
    global _model
    if _model is not None:
        return _model

    try:
        import onnxruntime as ort
    except ImportError:
        raise ImportError("onnxruntime nao instalado. Execute: pip install onnxruntime")

    # Procurar modelo em site-packages/openwakeword/resources/models/
    venv_path = Path(__file__).parent.parent / ".venv" / "Lib" / "site-packages" / "openwakeword" / "resources" / "models" / "hey_jarvis_v0.1.onnx"

    if not venv_path.exists():
        raise FileNotFoundError(
            f"Modelo nao encontrado: {venv_path}\n"
            f"Verifique que hey_jarvis_v0.1.onnx esta em site-packages/openwakeword/resources/models/"
        )

    try:
        _model = ort.InferenceSession(
            str(venv_path),
            providers=["CPUExecutionProvider"]
        )
        print("[wake] openWakeWord hey_jarvis carregado com sucesso (ONNX direto)")
        return _model
    except Exception as e:
        raise RuntimeError(f"[ERRO] Nao conseguiu carregar ONNX: {e}")


def _audio_to_melspec(audio_frames: np.ndarray, sample_rate: int = 16000) -> np.ndarray:
    """Converte audio raw para mel-spectrogram [1, 16, 96]."""
    # Gerar mel-spectrogram
    mel_spec = librosa.feature.melspectrogram(
        y=audio_frames,
        sr=sample_rate,
        n_fft=_n_fft,
        n_mels=_n_mels,
        fmax=8000,
    )

    # Converter para dB
    mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)

    # Normalizar [-80, 0] -> [0, 1]
    mel_spec_db = (mel_spec_db + 80) / 80
    mel_spec_db = np.clip(mel_spec_db, 0, 1)

    # Reshape para [1, n_mels, time_steps]
    mel_spec_db = mel_spec_db.reshape(1, _n_mels, -1).astype(np.float32)

    return mel_spec_db


def detect_wake_word(audio_frames: np.ndarray, sample_rate: int = 16000) -> bool:
    """Detecta "Hey Jarvis" via modelo ONNX classificador (F1.1).

    DETERMINÍSTICO: Retorna bool (probabilidade > 0.6).
    Sem fallback, sem alucinacao (classificador nao gera texto).
    """
    session = _get_model()

    # Normalizar para float32 [-1, 1]
    if audio_frames.dtype == np.int16:
        audio_frames = audio_frames.astype(np.float32) / 32768.0

    # Frame de 80ms @ 16kHz = 1280 samples
    frame_size = int(sample_rate * 0.08)
    if len(audio_frames) < frame_size:
        audio_frames = np.pad(
            audio_frames, (0, frame_size - len(audio_frames)), mode="constant"
        )
    elif len(audio_frames) > frame_size:
        audio_frames = audio_frames[:frame_size]

    # Converter para mel-spectrogram
    mel_spec = _audio_to_melspec(audio_frames, sample_rate)

    try:
        # ONNX input/output names
        input_name = session.get_inputs()[0].name
        output_name = session.get_outputs()[0].name

        # Rodar inferencia
        scores = session.run([output_name], {input_name: mel_spec})[0]

        # scores = [batch_size, num_classes]
        hey_jarvis_score = float(scores[0][0]) if scores.shape[1] == 1 else float(scores[0][1])

        # Limiar: 0.6
        return hey_jarvis_score > 0.6
    except Exception as e:
        raise RuntimeError(f"[ERRO] Erro ao rodar modelo ONNX: {e}")


def get_score(audio_frames: np.ndarray, sample_rate: int = 16000) -> float:
    """Retorna score bruto (0-1) para debug."""
    session = _get_model()

    if audio_frames.dtype == np.int16:
        audio_frames = audio_frames.astype(np.float32) / 32768.0

    frame_size = int(sample_rate * 0.08)
    if len(audio_frames) < frame_size:
        audio_frames = np.pad(
            audio_frames, (0, frame_size - len(audio_frames)), mode="constant"
        )
    elif len(audio_frames) > frame_size:
        audio_frames = audio_frames[:frame_size]

    mel_spec = _audio_to_melspec(audio_frames, sample_rate)

    try:
        input_name = session.get_inputs()[0].name
        output_name = session.get_outputs()[0].name
        scores = session.run([output_name], {input_name: mel_spec})[0]
        return float(scores[0][0]) if len(scores[0]) == 1 else float(scores[0][1])
    except Exception:
        return 0.0

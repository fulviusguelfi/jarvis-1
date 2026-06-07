"""OpenWakeWord - deteccao de wake word dedicado com Silero VAD integrado.

F1.1: DETERMINÍSTICO — exige hey_jarvis.onnx presente. Sem fallback invisível.
"""
import numpy as np
from pathlib import Path

# Lazy load para nao crashear se openWakeWord nao estiver instalado
_model = None
_sample_rate = 16000


def _get_model():
    """Carrega o modelo openWakeWord hey_jarvis (lazy load).

    FALHA COM ERRO CLARO se modelo não existe.
    Sem fallback invisível — usuário precisa baixar hey_jarvis.onnx.
    """
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
            f"\n"
            f"[ERRO CRÍTICO] Modelo hey_jarvis.onnx nao encontrado!\n"
            f"\n"
            f"Caminho esperado: {model_path}\n"
            f"\n"
            f"SOLUÇÃO:\n"
            f"1. Baixe de: https://github.com/dscripka/openWakeWord/releases\n"
            f"   Procure por: hey_jarvis.onnx (v0.6.0+)\n"
            f"2. Crie o diretorio: {model_dir}\n"
            f"3. Coloque o arquivo lá\n"
            f"4. Tente novamente\n"
            f"\n"
            f"F1.1 exige openWakeWord funcionando. Sem fallback invisível.\n"
        )

    try:
        # Inicializar modelo com VAD nativo + Speex suppression
        _model = Model(
            wakeword_models=[str(model_path)],
            inference_framework="onnx",
            vad_threshold=0.5,  # Silero VAD integrado como gate
            enable_speex_noise_suppression=True,
        )
        print("[wake] openWakeWord hey_jarvis carregado com sucesso")
        return _model
    except Exception as e:
        raise RuntimeError(
            f"[ERRO] Nao conseguiu carregar modelo openWakeWord: {e}\n"
            f"Verifique se o arquivo {model_path} é válido.\n"
        )


def detect_wake_word(audio_frames: np.ndarray, sample_rate: int = 16000) -> bool:
    """
    Detecta "Hey Jarvis" com openWakeWord (F1.1).

    DETERMINÍSTICO: Retorna bool ou falha com exceção clara.
    Sem fallback invisível para Whisper.

    Args:
        audio_frames: numpy array de audio (mono, int16 ou float32)
        sample_rate: taxa de amostragem (padrao 16kHz)

    Returns:
        True se "Hey Jarvis" detectado com confianca > limiar

    Raises:
        FileNotFoundError: Se modelo hey_jarvis.onnx nao encontrado
        RuntimeError: Se modelo nao conseguir carregar
    """
    model = _get_model()  # Falha com erro claro se nao existe

    # Normalizar para float32 [-1, 1] se int16
    if audio_frames.dtype == np.int16:
        audio_frames = audio_frames.astype(np.float32) / 32768.0

    # openWakeWord espera frames de ~80ms a 16kHz = 1280 samples
    frame_size = int(sample_rate * 0.08)

    # Processar frame unico
    if len(audio_frames) < frame_size:
        audio_frames = np.pad(
            audio_frames, (0, frame_size - len(audio_frames)), mode="constant"
        )
    elif len(audio_frames) > frame_size:
        audio_frames = audio_frames[:frame_size]

    try:
        # Predizione do modelo retorna dict: {"hey_jarvis": score_0-1, ...}
        scores = model.predict(audio_frames)

        # Buscar score de "hey_jarvis"
        hey_jarvis_score = scores.get("hey_jarvis", 0.0)

        # Limiar: 0.6 como balance entre falsos positivos e falsos negativos
        return hey_jarvis_score > 0.6
    except Exception as e:
        raise RuntimeError(
            f"[ERRO] Erro ao rodar openWakeWord: {e}\n"
            f"O modelo pode estar corrompido. Tente baixar novamente.\n"
        )


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

    try:
        scores = model.predict(audio_frames)
        return scores.get("hey_jarvis", 0.0)
    except Exception:
        return 0.0

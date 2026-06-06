from faster_whisper import WhisperModel
from config import WHISPER_MODEL, WHISPER_LANGUAGE, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE

_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        print(f"[STT] Carregando Whisper {WHISPER_MODEL}...")
        _model = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE_TYPE)
        print("[STT] Pronto.")
    return _model


def transcribe(wav_path: str) -> str:
    """Transcreve áudio WAV para texto. Retorna string vazia se nada detectado."""
    model = _get_model()
    segments, info = model.transcribe(
        wav_path,
        language=WHISPER_LANGUAGE,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 300},
    )
    text = " ".join(s.text.strip() for s in segments).strip()
    if info.duration > 0:
        print(f"[STT] {info.duration:.1f}s → '{text}'")
    return text

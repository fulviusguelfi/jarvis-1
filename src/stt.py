from faster_whisper import WhisperModel
from config import WHISPER_MODEL, WHISPER_LANGUAGE, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE
from stt_filter import filter_transcription  # F1.3: Pós-filtro anti-alucinação

_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        print(f"[STT] Carregando Whisper {WHISPER_MODEL}...")
        _model = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE_TYPE)
        print("[STT] Pronto.")
    return _model


def transcribe(wav_path: str, apply_filter: bool = True) -> str:
    """
    Transcreve áudio WAV para texto com pós-filtro contra alucinação.

    F1.3: Após Whisper processar, aplica 3 critérios de rejeição:
    - compression_ratio > 2.4 (muito repetitivo)
    - texto em blocklist (frases fantasma conhecidas)
    - padrões óbvios (80%+ palavras iguais)

    Retorna string vazia se alucinação detectada.
    """
    model = _get_model()
    segments, info = model.transcribe(
        wav_path,
        language=WHISPER_LANGUAGE,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 300},
    )
    text = " ".join(s.text.strip() for s in segments).strip()

    # F1.3: Aplicar pós-filtro
    if apply_filter:
        text = filter_transcription(text)

    if info.duration > 0:
        print("[STT] {:.1f}s -> '{}'".format(info.duration, text))
    return text

"""Smart Turn v3 — endpoint semantico (F1.6.2).

Classificador DETERMINISTICO (mesma filosofia do wake word): dado o audio da fala
ate agora, prediz a probabilidade de o turno estar COMPLETO (humano terminou de
falar). Tolera pausa de pensamento: se foi so uma pausa, a prob fica baixa ->
o loop continua escutando em vez de cortar.

Modelo: pipecat-ai/smart-turn-v3 (encoder Whisper-tiny + classifier, ONNX int8 ~8MB,
~12ms CPU, 23 idiomas incl. pt-BR). Preprocessing OFICIAL: WhisperFeatureExtractor
(transformers) — igual ao inference.py do repo, sem replicacao/suposicao.
"""
import os
import numpy as np
from config import TURN_THRESHOLD

_session = None
_fe = None

_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "models", "smart-turn", "smart-turn-v3.2-cpu.onnx",
)
_MAX_SECONDS = 8


def _load():
    """Lazy-load do ONNX + feature extractor. Erro claro se faltar (sem fallback)."""
    global _session, _fe
    if _session is not None:
        return

    import onnxruntime as ort
    from transformers import WhisperFeatureExtractor

    if not os.path.exists(_MODEL_PATH):
        raise FileNotFoundError(
            f"Modelo Smart Turn nao encontrado: {_MODEL_PATH}\n"
            f"Rode: python setup_models.py (baixa o ONNX do pipecat-ai/smart-turn-v3)."
        )

    _fe = WhisperFeatureExtractor(chunk_length=_MAX_SECONDS)
    _session = ort.InferenceSession(_MODEL_PATH, providers=["CPUExecutionProvider"])
    print("[turn] Smart Turn v3 carregado (endpoint semantico)")


def predict_prob(audio_int16: np.ndarray, sample_rate: int = 16000) -> float:
    """Probabilidade (0-1) de o turno estar COMPLETO ('terminei de falar')."""
    _load()

    audio = np.asarray(audio_int16).flatten()
    if audio.dtype == np.int16:
        audio = audio.astype(np.float32) / 32768.0
    else:
        audio = audio.astype(np.float32)

    # Manter os ULTIMOS 8s (a pista de fim-de-turno esta no final da fala).
    max_samples = _MAX_SECONDS * sample_rate
    if len(audio) > max_samples:
        audio = audio[-max_samples:]

    inputs = _fe(
        audio,
        sampling_rate=sample_rate,
        return_tensors="np",
        padding="max_length",
        max_length=max_samples,
        truncation=True,
        do_normalize=True,
    )
    feats = inputs["input_features"].astype(np.float32)
    logit = _session.run(None, {"input_features": feats})[0]
    return float(logit.ravel()[0])  # ONNX ja aplica sigmoid -> e probabilidade


def predict_endpoint(audio_int16: np.ndarray, sample_rate: int = 16000) -> tuple[bool, float]:
    """(completo: bool, prob: float). completo = prob > TURN_THRESHOLD."""
    p = predict_prob(audio_int16, sample_rate)
    return (p > TURN_THRESHOLD, p)

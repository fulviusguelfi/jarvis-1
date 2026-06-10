"""Testes para Smart Turn v3 (endpoint semantico, F1.6.2).

Estruturais: o modelo carrega e retorna probabilidade 0-1. A discriminacao real
(frase completa vs pausa) depende de PROSODIA HUMANA — TTS achata a prosodia, entao
a validacao de qualidade ocorre em conversa real com o usuario (DOD da Fase 1.6).
"""
import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import pytest
except ImportError:
    pass

# Modelo + deps podem nao estar presentes -> skip limpo.
try:
    import onnxruntime  # noqa: F401
    import transformers  # noqa: F401
    _MODEL = (Path(__file__).parent.parent / "models" / "smart-turn" / "smart-turn-v3.2-cpu.onnx")
    HAS_TURN = _MODEL.exists()
except ImportError:
    HAS_TURN = False


@pytest.mark.skipif(not HAS_TURN, reason="Smart Turn (modelo/onnxruntime/transformers) ausente")
def test_turn_loads_and_scores():
    """predict_prob retorna float em [0, 1]."""
    from turn import predict_prob

    audio = np.zeros(16000 * 2, dtype=np.int16)  # 2s
    p = predict_prob(audio, sample_rate=16000)
    assert isinstance(p, float), "prob deve ser float"
    assert 0.0 <= p <= 1.0, f"prob fora de [0,1]: {p}"


@pytest.mark.skipif(not HAS_TURN, reason="Smart Turn ausente")
def test_turn_predict_endpoint_tuple():
    """predict_endpoint retorna (bool, float) coerentes com o threshold."""
    from turn import predict_endpoint
    from config import TURN_THRESHOLD

    audio = np.zeros(16000, dtype=np.int16)
    complete, p = predict_endpoint(audio, sample_rate=16000)
    assert isinstance(complete, bool)
    assert isinstance(p, float)
    assert complete == (p > TURN_THRESHOLD)


@pytest.mark.skipif(not HAS_TURN, reason="Smart Turn ausente")
def test_turn_handles_long_audio():
    """Audio > 8s e truncado para os ultimos 8s sem crashar."""
    from turn import predict_prob

    audio = np.zeros(16000 * 20, dtype=np.int16)  # 20s
    p = predict_prob(audio, sample_rate=16000)
    assert 0.0 <= p <= 1.0

"""Testes para pós-filtro de alucinação do Whisper.

F1.3: Valida que frases-fantasma sao rejeitadas, fala valida passa.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False


# ============================================================================
# Testes do Filtro
# ============================================================================

def test_filter_rejects_blocklist_phrases():
    """Frases da blocklist devem ser rejeitadas."""
    from stt_filter import filter_transcription

    hallucinations = [
        "legendas pela comunidade de amara.org",
        "até o próximo vídeo",
        "thanks for watching",
        "subtitles by",
    ]

    for text in hallucinations:
        result = filter_transcription(text)
        assert result == "", f"Blocklist '{text}' deveria ser rejeitada"


def test_filter_rejects_repetitive_text():
    """Texto muito repetitivo (compression_ratio > 2.4) deve ser rejeitado."""
    from stt_filter import filter_transcription

    repetitive = [
        "e e e e e e e e",
        "um um um um um um",
        "ah ah ah ah ah",
    ]

    for text in repetitive:
        result = filter_transcription(text)
        assert result == "", f"Repetitivo '{text}' deveria ser rejeitado"


def test_filter_accepts_valid_speech():
    """Fala válida deve passar pelo filtro."""
    from stt_filter import filter_transcription

    valid_speeches = [
        "Olá, como você está?",
        "Qual é a hora agora?",
        "Me ajude com essa tarefa",
        "Que dia é hoje?",
    ]

    for text in valid_speeches:
        result = filter_transcription(text)
        assert result == text.strip(), f"Fala válida '{text}' não deveria ser rejeitada"


def test_filter_rejects_empty():
    """String vazia ou muito curta deve ser rejeitada."""
    from stt_filter import filter_transcription

    empty_cases = ["", " ", "a", "ab"]

    for text in empty_cases:
        result = filter_transcription(text)
        assert result == "", f"Muito curto '{text}' deveria ser rejeitado"


def test_compression_ratio_calculation():
    """Validar calculo de compression_ratio."""
    from stt_filter import _calc_compression_ratio

    # Altamente repetitivo: ratio alto
    high_ratio = _calc_compression_ratio("e e e e e")
    assert high_ratio > 2.0, f"Repetitivo deveria ter ratio alto, got {high_ratio}"

    # Normal: ratio baixo
    low_ratio = _calc_compression_ratio("Olá como você está?")
    assert low_ratio < 2.0, f"Normal deveria ter ratio baixo, got {low_ratio}"


def test_debug_score():
    """debug_score deve retornar info estruturada."""
    from stt_filter import debug_score

    text = "Olá mundo"
    score = debug_score(text)

    assert isinstance(score, dict)
    assert "text" in score
    assert "compression_ratio" in score
    assert "is_hallucination" in score
    assert "length" in score
    assert score["text"] == text


# ============================================================================
# DOD F1.3 - Notas
# ============================================================================
"""
DOD da F1.3:
  - [x] Frases-fantasma do log v0 rejeitadas
        → blocklist: "legendas pela comunidade", "até o próximo vídeo", etc.
  - [x] Fala real valida nao rejeitada (sem falso-negativo)
        → testes com frases normais passando
  - [x] test_stt_filter.py criado
        → 6 testes cobrindo 3 critérios

Validacao real:
- Testar em conversa real se alucinacoes sao eliminadas
- Calibrar limiares (compression_ratio=2.4, etc.) se necessario

Integracao em stt.py:
- transcribe() chama filter_transcription() por default
- apply_filter=False para bypass (debug)
"""

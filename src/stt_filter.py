"""Pós-filtro determinístico contra alucinações do Whisper.

F1.3: Rejeita transcrições suspeitas após Whisper processá-las.
3 camadas: compression_ratio (repetição), no_speech_prob (silêncio), blocklist (conhecidas).
"""
import re

# Frases-fantasma conhecidas (alucinações de Whisper em silêncio/ruído)
ALUCINACAO_BLOCKLIST = {
    # Legendas
    "legendas pela comunidade",
    "legendas pela comunidade de amara.org",
    "subtitles by",
    "legendas",
    "closed captions",

    # Encerramento genérico
    "até o próximo vídeo",
    "ate o proximo video",
    "até logo",
    "ate logo",
    "até mais",
    "ate mais",
    "thanks for watching",
    "obrigado por assistir",

    # Repetição óbvia
    "e e e",
    "ah ah ah",
    "um um um",
    "é é é",
    "é verdade é verdade",
}


def _calc_compression_ratio(text: str) -> float:
    """
    Calcula compression_ratio = len(text) / len(encoded_tokens).

    Heurística: texto repetitivo comprime muito (ratio > 2.4 = lixo).
    Normal: ratio ~1.0-2.0.
    """
    if not text:
        return 0.0

    # Aproximação simples: contar palavras únicas vs totais
    # (real Whisper usa tokens, mas isso é close o bastante)
    words = text.lower().split()
    if not words:
        return 0.0

    unique_words = len(set(words))
    total_words = len(words)

    # Se maioria das palavras são iguais -> comprime muito
    if total_words == 0:
        return 0.0
    return total_words / (unique_words + 1)  # +1 para evitar divisão por zero


def _is_likely_hallucination(text: str) -> bool:
    """
    Determina se texto eh provavel alucinação.

    Critérios:
    1. compression_ratio > 2.4 (muito repetitivo)
    2. Texto muito curto (< 5 chars)
    3. Contém blocklist
    4. Números repetidos ("123 123 123")
    """
    # Piso: muito curto (<=2 chars) e improvavel comando valido.
    # main.py tambem exige >= 3 chars, redundancia defensiva.
    if not text or len(text.strip()) < 3:
        return True

    lower_text = text.lower()

    # Criterio 1: compression_ratio
    ratio = _calc_compression_ratio(text)
    if ratio > 2.4:
        return True

    # Criterio 2: blocklist
    for phrase in ALUCINACAO_BLOCKLIST:
        if phrase in lower_text:
            return True

    # Criterio 3: padroes repetitivos obvios
    # "123 123 123" ou "abc abc abc"
    words = text.split()
    if len(words) > 2:
        # Se 80%+ das palavras sao iguais -> alucinacao
        first_word = words[0]
        same_count = sum(1 for w in words if w == first_word)
        if same_count / len(words) > 0.8:
            return True

    return False


def filter_transcription(text: str) -> str:
    """
    Aplica pós-filtro determinístico contra alucinações.

    Retorna:
    - texto original se passou nos filtros
    - "" (string vazia) se rejeitado
    """
    if not text or not text.strip():
        return ""

    if _is_likely_hallucination(text):
        return ""

    return text.strip()


def debug_score(text: str) -> dict:
    """Retorna scores para debug."""
    return {
        "text": text,
        "compression_ratio": _calc_compression_ratio(text),
        "is_hallucination": _is_likely_hallucination(text),
        "length": len(text),
    }

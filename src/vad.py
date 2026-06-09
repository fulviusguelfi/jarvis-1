"""Silero VAD - Voice Activity Detection para endpointing preciso.

F1.2: Substitui RMS em record_until_silence() por Silero VAD (torch JIT).
Detecta fim de fala com precisao, elimina tempo morto de 1.2s -> ~300ms.
"""
import numpy as np
import torch

# Lazy load
_model = None
_sample_rate = 16000


def _get_model():
    """Carrega modelo Silero VAD (lazy load) — torch JIT."""
    global _model
    if _model is not None:
        return _model

    try:
        import silero_vad
    except ImportError:
        raise ImportError(
            "silero-vad nao instalado. Execute: pip install silero-vad"
        )

    # Silero VAD: carrega modelo JIT (onnx=False, default). Espera torch.Tensor.
    _model = silero_vad.load_silero_vad(onnx=False)
    return _model


def detect_voice(
    audio_frames: np.ndarray,
    sample_rate: int = 16000,
    threshold: float = 0.5
) -> bool:
    """
    Detecta se ha voz nos frames de audio.

    Nota: Silero v6 exige exatamente 512 samples @16kHz ou 256 @8kHz.
    Se audio_frames for maior, processa em chunks e retorna True se qualquer
    chunk passa do threshold.

    Args:
        audio_frames: numpy array (mono, int16 ou float32)
        sample_rate: taxa de amostragem
        threshold: limiar de probabilidade (0-1)

    Returns:
        True se ha voz com confianca > threshold (em qualquer chunk)
    """
    model = _get_model()

    # Normalizar para float32 [-1, 1]
    if audio_frames.dtype == np.int16:
        audio = audio_frames.astype(np.float32) / 32768.0
    else:
        audio = audio_frames.astype(np.float32)

    # Silero v6: janela fixa (512 @16kHz, 256 @8kHz)
    chunk_size = 512 if sample_rate == 16000 else 256

    try:
        # Se audio e menor que chunk_size, pad com zeros
        if len(audio) < chunk_size:
            audio = np.pad(audio, (0, chunk_size - len(audio)), mode='constant')

        # Processar em chunks; retorna True se qualquer chunk passa do threshold
        for i in range(0, len(audio), chunk_size):
            chunk = audio[i:i+chunk_size]
            if len(chunk) < chunk_size:
                chunk = np.pad(chunk, (0, chunk_size - len(chunk)), mode='constant')

            audio_tensor = torch.from_numpy(chunk).float()
            confidence = model(audio_tensor, sample_rate)
            if float(confidence) > threshold:
                return True

        return False

    except Exception as e:
        print(f"[vad] erro ao rodar Silero VAD: {e}")
        return False


def get_confidence(
    audio_frames: np.ndarray,
    sample_rate: int = 16000
) -> float:
    """
    Retorna score bruto do Silero VAD (0-1) para debug.
    Se audio > chunk_size, processa o 1º chunk.
    """
    model = _get_model()

    if audio_frames.dtype == np.int16:
        audio = audio_frames.astype(np.float32) / 32768.0
    else:
        audio = audio_frames.astype(np.float32)

    chunk_size = 512 if sample_rate == 16000 else 256

    try:
        # Pegar 1º chunk (ou pad se menor)
        chunk = audio[:chunk_size]
        if len(chunk) < chunk_size:
            chunk = np.pad(chunk, (0, chunk_size - len(chunk)), mode='constant')

        audio_tensor = torch.from_numpy(chunk).float()
        confidence = model(audio_tensor, sample_rate)
        return float(confidence)
    except Exception:
        return 0.0


def _frames_to_int16(frames: list) -> np.ndarray:
    """Concatena os frames capturados em um vetor int16 1D (a fala ate agora)."""
    if not frames:
        return np.zeros(0, dtype=np.int16)
    return np.concatenate([f.flatten() for f in frames]).astype(np.int16)


def record_until_turn_end(
    stream,
    sample_rate: int = 16000,
    max_duration: float | None = None,
    speech_threshold: float = 0.5,
) -> list[np.ndarray]:
    """
    Endpointing tolerante (F1.6): Silero VAD detecta candidato a silencio; se o
    Smart Turn estiver disponivel, ele CONFIRMA se o humano realmente terminou —
    pausas de pensamento nao cortam a fala.

    Cascata:
      1. VAD por chunk de 512 (voz/silencio).
      2. So encerra apos fala minima (ignora blips de eco).
      3. Em silencio: se Smart Turn ligado, pergunta "terminou?" a cada SHORT_SILENCE;
         senao, encerra no VAD_MIN_SILENCE.
      4. Fallback duro (VAD_HARD_SILENCE) garante que nunca trava.

    Returns: lista de frames (numpy arrays) gravados.
    """
    import time
    from config import (
        VAD_MIN_SILENCE_MS, VAD_MAX_UTTERANCE_S, VAD_MIN_SPEECH_MS,
        VAD_HARD_SILENCE_MS, TURN_ENABLED, SHORT_SILENCE_MS,
    )

    if max_duration is None:
        max_duration = VAD_MAX_UTTERANCE_S

    # Smart Turn (F1.6.2) — opcional: se o modulo/modelo nao existir, cai pra VAD puro.
    turn_fn = None
    if TURN_ENABLED:
        try:
            from turn import predict_endpoint
            turn_fn = predict_endpoint
        except Exception as e:
            print(f"[turn] Smart Turn indisponivel, usando so VAD: {e}")

    model = _get_model()
    frames = []
    silence_start = None
    start = time.time()
    spoke = False
    voiced_ms = 0.0
    turn_checked_at = 0.0  # ultimo nivel de silencio (ms) em que consultamos o Smart Turn
    capture_chunk = int(sample_rate * 0.08)
    vad_chunk_size = 512 if sample_rate == 16000 else 256
    chunk_ms = vad_chunk_size / sample_rate * 1000.0

    try:
        vad_buffer = np.array([], dtype=np.float32)

        while time.time() - start < max_duration:
            data, _ = stream.read(capture_chunk)
            frames.append(data)
            vad_buffer = np.concatenate(
                [vad_buffer, data.astype(np.float32).flatten() / 32768.0]
            )

            while len(vad_buffer) >= vad_chunk_size:
                chunk = vad_buffer[:vad_chunk_size]
                vad_buffer = vad_buffer[vad_chunk_size:]
                try:
                    conf = float(model(torch.from_numpy(chunk).float(), sample_rate))
                except Exception:
                    conf = 0.0

                if conf > speech_threshold:
                    spoke = True
                    voiced_ms += chunk_ms
                    silence_start = None
                    turn_checked_at = 0.0
                    continue

                if not spoke:
                    continue

                # ---- em silencio, apos ter falado ----
                if silence_start is None:
                    silence_start = time.time()
                sil_ms = (time.time() - silence_start) * 1000.0

                # gate de fala minima: ignora blips curtos (eco)
                if voiced_ms < VAD_MIN_SPEECH_MS:
                    continue

                # fallback duro: nunca trava esperando
                if sil_ms >= VAD_HARD_SILENCE_MS:
                    return frames

                if turn_fn is not None:
                    # confirma com Smart Turn a cada SHORT_SILENCE de silencio crescente
                    if sil_ms - turn_checked_at >= SHORT_SILENCE_MS:
                        turn_checked_at = sil_ms
                        try:
                            complete, _p = turn_fn(_frames_to_int16(frames), sample_rate)
                        except Exception as e:
                            print(f"[turn] erro no Smart Turn: {e}")
                            complete = sil_ms >= VAD_MIN_SILENCE_MS
                        if complete:
                            return frames
                else:
                    # so VAD: encerra no silencio minimo
                    if sil_ms >= VAD_MIN_SILENCE_MS:
                        return frames

    except Exception as e:
        print(f"[audio-vad] erro durante gravacao: {e}")

    return frames


# Compat: nome antigo aponta para a nova funcao (endpointing tolerante).
def record_until_silence_vad(stream, sample_rate=16000, max_duration=None,
                             silence_threshold=0.5, min_silence_duration=None):
    return record_until_turn_end(stream, sample_rate=sample_rate,
                                 max_duration=max_duration,
                                 speech_threshold=silence_threshold)

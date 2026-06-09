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


def record_until_silence_vad(
    stream,
    sample_rate: int = 16000,
    max_duration: float = 10.0,
    silence_threshold: float = 0.5,
    min_silence_duration: float = 0.5,
) -> list[np.ndarray]:
    """
    Grava ate Silero VAD detectar fim de fala.

    Args:
        stream: sounddevice InputStream aberto
        sample_rate: taxa de amostragem
        max_duration: duracao maxima de gravacao
        silence_threshold: limiar Silero VAD (< threshold = silencio)
        min_silence_duration: tempo minimo de silencio para considerar fim (segundos)

    Returns:
        Lista de frames (numpy arrays) gravados
    """
    import time

    model = _get_model()
    frames = []
    silence_start = None
    start = time.time()
    spoke = False
    capture_chunk = int(sample_rate * 0.08)  # 80ms p/ captura (sounddevice)
    vad_chunk_size = 512 if sample_rate == 16000 else 256  # Silero exige tamanho exato

    try:
        vad_buffer = np.array([], dtype=np.float32)

        while True:
            elapsed = time.time() - start
            if elapsed >= max_duration:
                break

            data, _ = stream.read(capture_chunk)
            frames.append(data)

            # Normalizar para float32 [-1, 1] e garantir 1D
            # (sounddevice retorna shape (N, channels) — flatten para (N,))
            audio = data.astype(np.float32).flatten() / 32768.0

            # Acumular no buffer VAD (sempre 1D)
            vad_buffer = np.concatenate([vad_buffer, audio])

            # Processar chunks de VAD enquanto ha buffer suficiente
            confidence = 0.0
            while len(vad_buffer) >= vad_chunk_size:
                chunk = vad_buffer[:vad_chunk_size]
                vad_buffer = vad_buffer[vad_chunk_size:]

                try:
                    audio_tensor = torch.from_numpy(chunk).float()
                    confidence = float(model(audio_tensor, sample_rate))
                except Exception:
                    confidence = 0.0

                # Detectar transicao voz -> silencio
                if confidence > silence_threshold:
                    spoke = True
                    silence_start = None
                elif spoke:
                    if silence_start is None:
                        silence_start = time.time()
                    elif time.time() - silence_start >= min_silence_duration:
                        return frames

    except Exception as e:
        print(f"[audio-vad] erro durante gravacao: {e}")

    return frames

import tempfile
import os
import time
import threading
import numpy as np
import sounddevice as sd
import wave
from config import AUDIO_SAMPLE_RATE, AUDIO_CHANNELS, AUDIO_RECORD_SECONDS
from vad import record_until_silence_vad  # F1.2: Silero VAD endpointing

# Áudio sempre no dispositivo padrão do SO: não passamos `device=`, então o
# sounddevice usa sd.default.device, que o PortAudio resolve para o default do SO.

_mic_stream: sd.InputStream | None = None
_out_stream: sd.OutputStream | None = None
_stream_lock = threading.Lock()

def _find_jabra_device() -> int | None:
    """Procura por Jabra Link 380 ou dispositivo padrão com entrada."""
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        if 'jabra' in dev['name'].lower() and dev['max_input_channels'] > 0:
            return i
    return sd.default.device[0]

def _get_mic_stream() -> sd.InputStream:
    """Mantém um stream contínuo de mic aberto (Jabra ou padrão)."""
    global _mic_stream
    with _stream_lock:
        if _mic_stream is None or _mic_stream.closed:
            device_idx = _find_jabra_device()
            _mic_stream = sd.InputStream(
                device=device_idx,
                samplerate=AUDIO_SAMPLE_RATE,
                channels=AUDIO_CHANNELS,
                dtype=np.int16,
                blocksize=8192,
            )
            _mic_stream.start()
            # Limpar buffer inicial
            _mic_stream.read(AUDIO_SAMPLE_RATE)
        return _mic_stream


def _get_out_stream() -> sd.OutputStream:
    """Mantém stream de saída aberto (keepalive para Bluetooth, device padrão do SO)."""
    global _out_stream
    with _stream_lock:
        if _out_stream is None or _out_stream.closed:
            _out_stream = sd.OutputStream(
                samplerate=22050,
                channels=AUDIO_CHANNELS,
                dtype=np.int16,
                blocksize=4096,
            )
            _out_stream.start()
        return _out_stream


def read_mic_chunk(seconds: float = 2.5) -> bytes:
    """Lê chunk contínuo do mic."""
    stream = _get_mic_stream()
    chunk_samples = int(AUDIO_SAMPLE_RATE * seconds)
    try:
        data, overflowed = stream.read(chunk_samples)
        if overflowed:
            print("[audio] aviso: buffer overflow no mic")
        print("[audio-debug] Lido {} samples em {:.1f}s".format(len(data), seconds))
        return data.tobytes()
    except Exception as e:
        print("[audio-debug] ERRO ao ler mic: {}".format(e))
        return b'\x00' * (chunk_samples * 2)


def stop_mic_stream():
    """Para o stream contínuo de mic."""
    global _mic_stream
    with _stream_lock:
        if _mic_stream is not None:
            _mic_stream.stop()
            _mic_stream.close()
            _mic_stream = None


def record(duration: float = AUDIO_RECORD_SECONDS, out_path: str | None = None) -> str:
    """Grava áudio e salva em WAV."""
    path = out_path or tempfile.mktemp(suffix=".wav")
    stream = _get_mic_stream()
    frames = []
    samples = int(AUDIO_SAMPLE_RATE * duration)

    try:
        while len(frames) < samples:
            data, _ = stream.read(min(16384, samples - len(frames)))
            frames.append(data)
    except Exception as e:
        print(f"[audio] erro durante gravação: {e}")

    if frames:
        audio = np.vstack(frames) if len(frames) > 1 else frames[0]
    else:
        audio = np.zeros((0, AUDIO_CHANNELS), dtype=np.int16)

    with wave.open(path, "w") as wf:
        wf.setnchannels(AUDIO_CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(AUDIO_SAMPLE_RATE)
        wf.writeframes(audio.tobytes())

    return path


def record_until_silence(
    max_duration: float = AUDIO_RECORD_SECONDS,
    silence_db: float = -40.0,  # Param legado (ignorado agora, para compatibilidade)
    silence_secs: float = 1.2,  # Param legado (ignorado agora, para compatibilidade)
    out_path: str | None = None,
    vad_method: str = "silero"  # "silero" ou "rms" (legado)
) -> str:
    """
    Grava audio até detectar fim de fala.

    F1.2: Substituiu RMS por Silero VAD para endpointing preciso (< 300ms vs 1.2s).
    Params silence_db e silence_secs sao ignorados (legado).
    """
    path = out_path or tempfile.mktemp(suffix=".wav")
    stream = _get_mic_stream()

    if vad_method == "silero":
        # F1.2: novo metodo com Silero VAD
        frames = record_until_silence_vad(
            stream,
            sample_rate=AUDIO_SAMPLE_RATE,
            max_duration=max_duration,
            silence_threshold=0.5,  # Limiar Silero VAD
            min_silence_duration=0.5,  # 500ms de silencio = fim de fala
        )
    else:
        # Fallback RMS (legado, para compat)
        frames = []
        silence_start = None
        start = time.time()
        spoke = False
        chunk_size = int(AUDIO_SAMPLE_RATE * 0.1)

        try:
            while True:
                elapsed = time.time() - start
                if elapsed >= max_duration:
                    break

                data, _ = stream.read(chunk_size)
                frames.append(data)

                samples = data.astype(np.float32) / 32768.0
                rms = float(np.sqrt(np.mean(samples ** 2)))
                rms_db = 20 * np.log10(rms + 1e-9)

                if rms_db > silence_db:
                    spoke = True
                    silence_start = None
                elif spoke:
                    if silence_start is None:
                        silence_start = time.time()
                    elif time.time() - silence_start >= silence_secs:
                        break
        except Exception as e:
            print(f"[audio] erro durante gravacao RMS: {e}")

    if frames:
        audio = np.vstack(frames) if len(frames) > 1 else frames[0]
    else:
        audio = np.zeros((0, AUDIO_CHANNELS), dtype=np.int16)

    with wave.open(path, "w") as wf:
        wf.setnchannels(AUDIO_CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(AUDIO_SAMPLE_RATE)
        wf.writeframes(audio.tobytes())

    return path


def play(wav_path: str) -> None:
    """Toca um arquivo WAV."""
    with wave.open(wav_path, "rb") as wf:
        data = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
    sd.play(data, AUDIO_SAMPLE_RATE)
    sd.wait()


def start_bt_keepalive(sample_rate: int = 22050) -> None:
    """Mantém stream de saída aberto como keepalive para Bluetooth."""
    stream = _get_out_stream()

    def _feed():
        silence_block = np.zeros(int(sample_rate * 0.05), dtype=np.int16)
        while True:
            try:
                if stream.closed:
                    break
                stream.write(silence_block)
                time.sleep(0.05)
            except Exception:
                break

    threading.Thread(target=_feed, daemon=True).start()


def stop_bt_keepalive() -> None:
    """Para stream de keepalive."""
    global _out_stream
    with _stream_lock:
        if _out_stream is not None:
            try:
                _out_stream.stop()
                _out_stream.close()
            except Exception:
                pass
            _out_stream = None


def play_samples(samples: np.ndarray, sample_rate: int) -> None:
    """Toca array numpy."""
    sd.play(samples, sample_rate)
    sd.wait()


def play_samples_interruptible(
    samples: np.ndarray,
    sample_rate: int,
    stop_event: threading.Event,
    chunk_secs: float = 0.05
) -> bool:
    """Toca em chunks, pode ser interrompido por stop_event."""
    chunk_samples = int(sample_rate * chunk_secs)
    stream = _get_out_stream()
    interrupted = False

    try:
        for i in range(0, len(samples), chunk_samples):
            if stop_event.is_set():
                interrupted = True
                break
            chunk = samples[i:i + chunk_samples]
            pcm = (chunk * 32767).astype(np.int16)
            stream.write(pcm)
    except Exception as e:
        print(f"[audio] erro ao tocar: {e}")

    return interrupted


def mic_vad_background(
    stop_event: threading.Event,
    trigger_event: threading.Event,
    rms_threshold: float = 0.025,
    consecutive_needed: int = 3
) -> None:
    """Thread de fundo: detecta voz do mic."""
    stream = _get_mic_stream()
    chunk_samples = int(AUDIO_SAMPLE_RATE * 0.08)
    consecutive = 0

    try:
        while not stop_event.is_set():
            data, _ = stream.read(chunk_samples)
            arr = data.astype(np.float32) / 32768.0
            rms = float(np.sqrt(np.mean(arr ** 2)))

            if rms > rms_threshold:
                consecutive += 1
                if consecutive >= consecutive_needed:
                    trigger_event.set()
                    break
            else:
                consecutive = max(0, consecutive - 1)
    except Exception as e:
        print(f"[audio] erro no VAD: {e}")

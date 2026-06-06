import subprocess
import tempfile
import os
import time
import threading
import numpy as np
from config import PULSE_SERVER, AUDIO_SAMPLE_RATE, AUDIO_CHANNELS, AUDIO_RECORD_SECONDS

PULSE_SINK = os.environ.get("PULSE_SINK", "default")
_ffmpeg_env = {**os.environ, "PULSE_SERVER": PULSE_SERVER}

# Stream contínuo de mic — evita que PipeWire suspenda o source entre gravações
_mic_stream_proc: subprocess.Popen | None = None
_mic_stream_lock = threading.Lock()


def _get_mic_stream() -> subprocess.Popen:
    """Mantém um único ffmpeg de captura rodando continuamente."""
    global _mic_stream_proc
    with _mic_stream_lock:
        if _mic_stream_proc is None or _mic_stream_proc.poll() is not None:
            # Força source ativo antes de abrir stream
            subprocess.run(
                ["pactl", "suspend-source", "default", "false"],
                env=_ffmpeg_env, capture_output=True
            )
            _mic_stream_proc = subprocess.Popen(
                ["ffmpeg", "-loglevel", "quiet",
                 "-f", "pulse", "-i", "default",
                 "-ar", str(AUDIO_SAMPLE_RATE), "-ac", "1",
                 "-f", "s16le", "pipe:1"],
                env=_ffmpeg_env,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
            )
        return _mic_stream_proc


def read_mic_chunk(seconds: float = 2.5) -> bytes:
    """Lê um chunk de PCM s16le do stream contínuo de mic."""
    proc = _get_mic_stream()
    chunk_bytes = int(AUDIO_SAMPLE_RATE * seconds) * 2
    data = proc.stdout.read(chunk_bytes)
    if len(data) < chunk_bytes:
        # Stream morreu — reiniciar na próxima chamada
        global _mic_stream_proc
        _mic_stream_proc = None
        return b'\x00' * chunk_bytes
    return data


def stop_mic_stream():
    """Para o stream contínuo (chamar ao mudar para record_until_silence)."""
    global _mic_stream_proc
    with _mic_stream_lock:
        if _mic_stream_proc is not None:
            _mic_stream_proc.terminate()
            try:
                _mic_stream_proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                _mic_stream_proc.kill()
            _mic_stream_proc = None


def record(duration: float = AUDIO_RECORD_SECONDS, out_path: str | None = None) -> str:
    """Grava áudio do microfone via ffmpeg+PulseAudio. Retorna path do WAV."""
    path = out_path or tempfile.mktemp(suffix=".wav")
    cmd = [
        "ffmpeg", "-y",
        "-f", "pulse",
        "-i", "default",
        "-t", str(duration),
        "-ar", str(AUDIO_SAMPLE_RATE),
        "-ac", str(AUDIO_CHANNELS),
        path
    ]
    subprocess.run(cmd, env=_ffmpeg_env, capture_output=True, check=True)
    return path


def record_until_silence(
    max_duration: float = AUDIO_RECORD_SECONDS,
    silence_db: float = -40.0,
    silence_secs: float = 1.2,
    out_path: str | None = None
) -> str:
    """Grava até detectar silêncio ou atingir max_duration. Retorna path do WAV."""
    path = out_path or tempfile.mktemp(suffix=".wav")
    raw_path = path + ".raw"

    # Grava raw PCM em tempo real e para quando detecta silêncio
    # Usa chunks de 0.1s e faz VAD por energia RMS
    chunk_size = int(AUDIO_SAMPLE_RATE * 0.1)
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-f", "pulse", "-i", "default",
         "-ar", str(AUDIO_SAMPLE_RATE), "-ac", "1", "-f", "s16le", raw_path],
        env=_ffmpeg_env, stderr=subprocess.DEVNULL
    )

    silence_start = None
    start = time.time()
    spoke = False

    try:
        while True:
            elapsed = time.time() - start
            if elapsed >= max_duration:
                break

            time.sleep(0.1)

            try:
                size = os.path.getsize(raw_path)
            except FileNotFoundError:
                continue

            if size < chunk_size * 2:
                continue

            with open(raw_path, "rb") as f:
                f.seek(max(0, size - chunk_size * 2))
                data = f.read(chunk_size * 2)

            samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
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
    finally:
        proc.terminate()
        proc.wait()

    # Converter raw PCM para WAV
    subprocess.run(
        ["ffmpeg", "-y", "-f", "s16le", "-ar", str(AUDIO_SAMPLE_RATE), "-ac", "1",
         "-i", raw_path, path],
        capture_output=True
    )
    os.unlink(raw_path)
    return path


def play(wav_path: str) -> None:
    """Toca um arquivo WAV via paplay (sincronizado com hardware)."""
    subprocess.run(["paplay", wav_path], env=_ffmpeg_env, capture_output=True)


def _samples_to_wav_bytes(samples: np.ndarray, sample_rate: int) -> bytes:
    """Converte float32 samples para bytes WAV completo."""
    import io, wave as _wave
    buf = io.BytesIO()
    pcm = (samples * 32767).astype(np.int16)
    with _wave.open(buf, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()


_BT_WAKEUP_SECS = 0.15  # silêncio pré-roll reduzido (headset kept-alive)

# Thread que mantém o headset BT acordado com silêncio contínuo
_keepalive_proc: subprocess.Popen | None = None
_keepalive_lock = threading.Lock()


def start_bt_keepalive(sample_rate: int = 22050) -> None:
    """Inicia stream silencioso para manter headset BT acordado."""
    global _keepalive_proc
    with _keepalive_lock:
        if _keepalive_proc is not None and _keepalive_proc.poll() is None:
            return
        _keepalive_proc = subprocess.Popen(
            ["paplay", "--raw", f"--rate={sample_rate}", "--channels=1",
             "--format=s16le", "--latency-msec=500"],
            env=_ffmpeg_env, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        # Envia blocos de silêncio em thread separada
        def _feed():
            silence_block = b'\x00' * int(sample_rate * 0.5) * 2  # 500ms por vez
            while True:
                try:
                    if _keepalive_proc.poll() is not None:
                        break
                    _keepalive_proc.stdin.write(silence_block)
                    _keepalive_proc.stdin.flush()
                    time.sleep(0.4)
                except Exception:
                    break
        threading.Thread(target=_feed, daemon=True).start()


def stop_bt_keepalive() -> None:
    global _keepalive_proc
    with _keepalive_lock:
        if _keepalive_proc is not None:
            try:
                _keepalive_proc.terminate()
                _keepalive_proc.wait(timeout=1)
            except Exception:
                pass
            _keepalive_proc = None


def _bt_wakeup(sample_rate: int, proc_stdin) -> None:
    """Envia silêncio mínimo antes do áudio."""
    silence = b'\x00' * int(sample_rate * _BT_WAKEUP_SECS) * 2
    try:
        proc_stdin.write(silence)
        proc_stdin.flush()
    except Exception:
        pass


def play_samples(samples: np.ndarray, sample_rate: int) -> None:
    """Toca array numpy via paplay com pré-roll de silêncio para Bluetooth."""
    proc = subprocess.Popen(
        ["paplay", "--raw", f"--rate={sample_rate}", "--channels=1", "--format=s16le"],
        env=_ffmpeg_env, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL
    )
    _bt_wakeup(sample_rate, proc.stdin)
    pcm = (samples * 32767).astype(np.int16).tobytes()
    proc.stdin.write(pcm)
    proc.stdin.close()
    proc.wait()


def play_samples_interruptible(
    samples: np.ndarray,
    sample_rate: int,
    stop_event: threading.Event,
    chunk_secs: float = 0.05
) -> bool:
    """
    Toca amostras em chunks com pré-roll BT. Para se stop_event for setado.
    Retorna True se foi interrompido antes do fim.
    """
    pcm = (samples * 32767).astype(np.int16).tobytes()
    cmd = ["paplay", "--raw", f"--rate={sample_rate}", "--channels=1", "--format=s16le"]
    proc = subprocess.Popen(cmd, env=_ffmpeg_env, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    _bt_wakeup(sample_rate, proc.stdin)

    chunk_bytes = int(sample_rate * chunk_secs) * 2  # 16-bit = 2 bytes/sample
    offset = 0
    interrupted = False

    try:
        while offset < len(pcm):
            if stop_event.is_set():
                interrupted = True
                break
            chunk = pcm[offset:offset + chunk_bytes]
            try:
                proc.stdin.write(chunk)
                proc.stdin.flush()
            except BrokenPipeError:
                break
            offset += chunk_bytes
    finally:
        try:
            proc.stdin.close()
        except Exception:
            pass
        if interrupted:
            # Interrompido pelo usuário — mata imediatamente
            proc.terminate()
            try:
                proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                proc.kill()
        else:
            # Deixa o paplay terminar de tocar antes de retornar
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()

    return interrupted


def mic_vad_background(
    stop_event: threading.Event,
    trigger_event: threading.Event,
    rms_threshold: float = 0.025,
    consecutive_needed: int = 3
) -> None:
    """
    Thread de fundo: monitora microfone e seta trigger_event ao detectar voz.
    Encerra quando stop_event for setado ou voz for detectada.
    """
    cmd = [
        "ffmpeg", "-loglevel", "quiet",
        "-f", "pulse", "-i", "default",
        "-ar", str(AUDIO_SAMPLE_RATE), "-ac", "1",
        "-f", "s16le", "pipe:1"
    ]
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=_ffmpeg_env
    )

    chunk_samples = int(AUDIO_SAMPLE_RATE * 0.08)  # 80ms chunks
    chunk_bytes = chunk_samples * 2
    consecutive = 0

    try:
        while not stop_event.is_set():
            data = proc.stdout.read(chunk_bytes)
            if len(data) < chunk_bytes:
                break
            arr = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
            rms = float(np.sqrt(np.mean(arr ** 2)))

            if rms > rms_threshold:
                consecutive += 1
                if consecutive >= consecutive_needed:
                    trigger_event.set()
                    break
            else:
                consecutive = max(0, consecutive - 1)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=1)
        except subprocess.TimeoutExpired:
            proc.kill()

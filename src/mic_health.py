"""Monitoramento de saúde do microfone.

F1.4: Detecta se mic desconectou (Jabra offline) e avisa com som.
Mantém stream sempre responsivo.
"""
import threading
import time
import numpy as np
from audio import _get_mic_stream, play_samples


def monitor_mic_health(
    check_interval: float = 5.0,
    on_mic_dead_callback=None
) -> threading.Event:
    """
    Thread de fundo: monitora se mic está vivo.

    Se mic ficar morto (stream closed ou erro na leitura),
    chama callback (default: tocar tom de aviso).

    Args:
        check_interval: segundos entre checks
        on_mic_dead_callback: funcao(event) chamada se mic morre

    Returns:
        threading.Event que pode ser setado para parar o monitor
    """
    stop_event = threading.Event()

    def _monitor():
        last_successful_read = time.time()
        notification_sent = False

        while not stop_event.is_set():
            try:
                # Tentar ler chunk pequeno
                stream = _get_mic_stream()
                if stream.closed:
                    if not notification_sent:
                        print("[mic-health] AVISO: Mic desconectado (stream fechado)")
                        if on_mic_dead_callback:
                            on_mic_dead_callback()
                        notification_sent = True
                else:
                    # Stream aberto, tenta ler
                    try:
                        chunk_samples = 160  # 10ms @ 16kHz
                        data, overflowed = stream.read(chunk_samples)
                        last_successful_read = time.time()
                        notification_sent = False
                    except Exception as e:
                        print(f"[mic-health] Erro ao ler stream: {e}")
                        if not notification_sent:
                            if on_mic_dead_callback:
                                on_mic_dead_callback()
                            notification_sent = True

            except Exception as e:
                print(f"[mic-health] Erro no monitor: {e}")

            time.sleep(check_interval)

    thread = threading.Thread(target=_monitor, daemon=True)
    thread.start()
    return stop_event


def play_mic_dead_notification():
    """Toca tom de aviso: "mic morreu"."""
    rate = 22050
    # Tom descendente (alarme suave)
    t = np.linspace(0, 0.3, int(rate * 0.3))
    freq_start = 800
    freq_end = 400
    # Rampa de frequência
    freq = freq_start - (freq_start - freq_end) * (t / t[-1])
    tone = 0.3 * np.sin(2 * np.pi * freq * t)
    tone = (tone * 32767).astype(np.int16)

    play_samples(tone, rate)
    print("[mic-health] ALERTA: Mic desconectado! Reconectando...")

#!/usr/bin/env python3
"""Jarvis - assistente de voz local. Stack: Whisper + Qwen3-8B Vulkan + Piper TTS + FSM."""
import sys
import os
import threading
import signal
import numpy as np
from enum import Enum

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import MARITACA_API_KEY, LLM_MODE, TTS_MODE
from audio import (
    record,
    record_until_silence,
    read_mic_chunk,
    stop_mic_stream,
    play_samples,
    play_samples_interruptible,
    mic_vad_background,
    start_bt_keepalive,
    stop_bt_keepalive,
)
from config import AUDIO_SAMPLE_RATE
from stt import transcribe, _get_model as _get_whisper
from wake import detect_wake_word  # F1.1: openWakeWord
from mic_health import monitor_mic_health, play_mic_dead_notification  # F1.4: Mic health
if TTS_MODE == "qwen3":
    from tts_qwen3 import synthesize
elif TTS_MODE == "piper":
    from tts_piper import synthesize
else:
    from tts import synthesize  # kokoro
from tools import TOOL_DEFINITIONS

# ============================================================================
# Máquina de Estados (FSM)
# ============================================================================

class JarvisState(Enum):
    """Estados da máquina de estados do Jarvis."""
    IDLE = "IDLE"                           # Aguardando wake word
    ACTIVATED = "ACTIVATED"                 # Wake word detectada
    LISTENING_COMMAND = "LISTENING_COMMAND" # Gravando comando após wake word
    PROCESSING = "PROCESSING"               # LLM processando o comando
    SPEAKING = "SPEAKING"                   # Jarvis falando a resposta (com barge-in)
    CONVERSATION = "CONVERSATION"           # Modo de conversa contínua
    LISTENING_FOLLOW = "LISTENING_FOLLOW"   # Gravando próxima pergunta em conversa
    EXIT = "EXIT"                           # Encerrando


class JarvisFSM:
    """Máquina de estados do Jarvis. Coordena transições e logging."""

    def __init__(self):
        self.state = JarvisState.IDLE
        self.lock = threading.Lock()

    def transition(self, new_state: JarvisState, reason: str = ""):
        """Transição de estado com logging."""
        with self.lock:
            old = self.state
            self.state = new_state
            reason_str = f" — {reason}" if reason else ""
            print(f"[STATE] {old.value} -> {new_state.value}{reason_str}")

    def get_state(self) -> JarvisState:
        """Obtém estado atual."""
        with self.lock:
            return self.state


# ============================================================================
# Constantes e funções auxiliares
# ============================================================================

# WAKE_WORDS removido: F1.1 usa openWakeWord modelo (hey_jarvis.onnx)

DISMISS_PHRASES = {
    "obrigado jarvis", "obrigado, jarvis", "valeu jarvis", "valeu, jarvis",
    "pode ir", "pode ir jarvis", "dispensado", "até mais jarvis",
    "até logo jarvis", "tchau jarvis", "ok jarvis obrigado",
    "obrigado", "valeu", "até mais", "até logo", "tchau",
}
WAKE_CHUNK_SECS = 2.5  # janela de escuta para wake word


def _make_client():
    if LLM_MODE == "local":
        from llm_local import LocalLLMClient
        return LocalLLMClient()
    from llm import LLMClient
    return LLMClient()


def check_config():
    if LLM_MODE == "cloud" and not MARITACA_API_KEY:
        print("ERRO: MARITACA_API_KEY nao definida.")
        sys.exit(1)


def _ack():
    """Confirma wake word com voz e tom audivel."""
    # Tom bip duplo
    rate = 22050
    t = np.linspace(0, 0.08, int(rate * 0.08))
    bip = 0.6 * np.sin(2 * np.pi * 1000 * t) * np.exp(-t * 30)
    silence = np.zeros(int(rate * 0.05), dtype=np.float32)
    tone = np.concatenate([bip, silence, bip]).astype(np.float32)
    play_samples(tone, rate)
    # Fala curta de confirmacao
    samples, sr = synthesize("Sim?")
    play_samples(samples, sr)


def _is_dismiss(text: str) -> bool:
    t = text.strip().lower().rstrip(".,!?")
    return any(d in t for d in DISMISS_PHRASES)


def _say_dismiss():
    import random
    respostas = ["De nada!", "Disponha!", "Ate logo!", "Pode contar comigo."]
    samples, rate = synthesize(random.choice(respostas))
    play_samples(samples, rate)


def _check_mic() -> bool:
    """Verifica se o mic esta capturando. Avisa se silencioso."""
    pcm = read_mic_chunk(1.0)
    peak = np.max(np.abs(np.frombuffer(pcm, dtype=np.int16).astype(np.float32))) / 32768
    peak_db = 20 * np.log10(peak + 1e-9)
    if peak_db < -60:
        print("[AVISO] Microfone silencioso. Verifique o headset Jabra:")
        print("  - Mova o dongle para porta USB traseira da placa-mae")
        print("  - Pressione o botao do headset para acorda-lo")
        print("  - O Jarvis vai continuar tentando - diga 'Jarvis' quando resolver\n")
        return False
    print("[OK] Microfone OK ({:.0f}dB)".format(peak_db))
    return True


def listen_for_wakeword_chunk() -> bool:
    """
    Detecta "Hey Jarvis" com openWakeWord (F1.1).

    SEM FALLBACK INVISÍVEL: Se openWakeWord falhar, falha com erro CLARO.
    Usuario sempre sabe qual erro aconteceu e por que no log.
    """
    import numpy as np

    pcm = read_mic_chunk(0.08)  # 80ms exato para openWakeWord
    audio_int16 = np.frombuffer(pcm, dtype=np.int16)
    return detect_wake_word(audio_int16, sample_rate=AUDIO_SAMPLE_RATE)


def speak_streaming(text_generator, interrupted_event: threading.Event) -> tuple[bool, str]:
    """
    Consome gerador LLM e faz TTS sentenca a sentenca com interrupcao por voz real.
    Modo barge-in: se usuario falar durante a resposta, para e volta ao listening.
    """
    stop_vad = threading.Event()
    user_spoke = threading.Event()

    # VAD com threshold alto para ignorar ruido BT - exige 640ms de voz continua
    vad_thread = threading.Thread(
        target=mic_vad_background,
        args=(stop_vad, user_spoke),
        kwargs={"rms_threshold": 0.06, "consecutive_needed": 8},
        daemon=True,
    )
    vad_thread.start()

    buffer = ""
    full_response = ""
    interrupted = False

    try:
        for chunk in text_generator:
            print(chunk, end="", flush=True)
            buffer += chunk
            full_response += chunk

            if user_spoke.is_set():
                interrupted = True
                break

            flushed = False
            for delim in (".", "!", "?", ";"):
                if delim in buffer:
                    before, _, after = buffer.partition(delim)
                    to_speak = (before + delim).strip()
                    buffer = after
                    if len(to_speak) > 5:
                        samples, rate = synthesize(to_speak)
                        play_samples(samples, rate)
                        if user_spoke.is_set():
                            interrupted = True
                    flushed = True
                    break

            if not flushed and len(buffer) > 80 and "," in buffer:
                before, _, after = buffer.partition(",")
                to_speak = (before + ",").strip()
                buffer = after
                if len(to_speak) > 5:
                    samples, rate = synthesize(to_speak)
                    play_samples(samples, rate)
                    if user_spoke.is_set():
                        interrupted = True

        if buffer.strip() and not interrupted:
            samples, rate = synthesize(buffer.strip())
            play_samples(samples, rate)

    finally:
        stop_vad.set()
        vad_thread.join(timeout=2)

    if interrupted:
        interrupted_event.set()
    return interrupted, full_response


# ============================================================================
# Main: Maquina de Estados Explicita
# ============================================================================

def main():
    check_config()

    client = _make_client()
    for td in TOOL_DEFINITIONS:
        client.register_tool(td)
    print(f"[modo LLM: {LLM_MODE} | TTS: {TTS_MODE}]")

    print("\n=== Jarvis iniciado ===")
    print("Diga 'Jarvis' para ativar. Ctrl+C para sair.\n")

    print("Pre-carregando modelos...")
    _get_whisper()
    if TTS_MODE == "qwen3":
        from tts_qwen3 import _get_stream as _tts_init
    elif TTS_MODE == "piper":
        from tts_piper import _get_voice as _tts_init
    else:
        from tts import _get_kokoro as _tts_init
    _tts_init()

    # Health check do mic
    print("Verificando microfone...")
    _check_mic()

    # Mantem headset BT acordado com silencio continuo
    start_bt_keepalive()

    # F1.4: Monitorar saude do mic (detectar desconexao Jabra)
    mic_monitor_stop = monitor_mic_health(
        check_interval=5.0,
        on_mic_dead_callback=play_mic_dead_notification
    )

    print("Pronto. Aguardando wake word 'Hey Jarvis'...\n")

    # FSM
    fsm = JarvisFSM()
    fsm.transition(JarvisState.IDLE, "startup")

    def handle_exit(sig, frame):
        print("\n[Jarvis] Sessao encerrada.")
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit)

    # ========================================================================
    # Loop principal: FSM explicita
    # ========================================================================
    while fsm.get_state() != JarvisState.EXIT:

        # ====== ESTADO: IDLE ======
        if fsm.get_state() == JarvisState.IDLE:
            print(" ouvindo... ", end="", flush=True)

            if listen_for_wakeword_chunk():
                fsm.transition(JarvisState.ACTIVATED, "wake word detectada")
            else:
                continue

        # ====== ESTADO: ACTIVATED ======
        if fsm.get_state() == JarvisState.ACTIVATED:
            stop_mic_stream()
            _ack()
            fsm.transition(JarvisState.LISTENING_COMMAND, "pronto para comando")

        # ====== ESTADO: LISTENING_COMMAND ======
        if fsm.get_state() == JarvisState.LISTENING_COMMAND:
            print("[MIC] Pode falar...")
            wav_path = record_until_silence(max_duration=10.0)
            fsm.transition(JarvisState.PROCESSING, "transcrevendo comando")

            text = transcribe(wav_path)
            os.unlink(wav_path)

            if not text or len(text.strip()) < 3:
                print("(nao entendi, aguardando wake word...)")
                fsm.transition(JarvisState.IDLE, "comando vazio")
                continue

            # Remover "jarvis" do inicio do texto se estava no comando
            clean = text.strip()
            for w in ["Jarvis,", "Jarvis", "jarvis,"]:
                if clean.lower().startswith(w.lower()):
                    clean = clean[len(w):].strip()

            if not clean:
                fsm.transition(JarvisState.IDLE, "comando vazio apos remover jarvis")
                continue

            # Frase de dispensa? Responde e volta ao modo de espera
            if _is_dismiss(clean):
                _say_dismiss()
                print("[dispensado - aguardando 'Jarvis']")
                fsm.transition(JarvisState.IDLE, "usuario dispensou")
                continue

            print(f"Voce: {clean}")
            print("Jarvis: ", end="", flush=True)
            fsm.transition(JarvisState.SPEAKING, "respondendo comando")

            interrupted_event = threading.Event()
            interrupted, _ = speak_streaming(client.chat(clean), interrupted_event)
            print()

            if interrupted:
                print("[barge-in detectado]")
                fsm.transition(JarvisState.CONVERSATION, "barge-in durante resposta")
            else:
                fsm.transition(JarvisState.CONVERSATION, "resposta concluida")

        # ====== ESTADO: CONVERSATION ======
        # Janela de conversa: ouve proximas perguntas sem precisar dizer "Jarvis"
        # Sai da janela se dispensado ou sem fala por 10s
        while fsm.get_state() == JarvisState.CONVERSATION:
            print("[MIC] Pode continuar...")
            fsm.transition(JarvisState.LISTENING_FOLLOW, "aguardando proxima pergunta")

            wav_follow = record_until_silence(max_duration=10.0)
            fsm.transition(JarvisState.PROCESSING, "transcrevendo seguimento")

            text_follow = transcribe(wav_follow)
            os.unlink(wav_follow)

            if not text_follow or len(text_follow.strip()) < 3:
                print("[sem fala - voltando ao modo de espera]")
                fsm.transition(JarvisState.IDLE, "timeout em conversa continua")
                break

            clean_follow = text_follow.strip()

            if _is_dismiss(clean_follow):
                _say_dismiss()
                print("[dispensado - aguardando 'Jarvis']")
                fsm.transition(JarvisState.IDLE, "usuario dispensou em conversa")
                break

            print(f"Voce: {clean_follow}")
            print("Jarvis: ", end="", flush=True)
            fsm.transition(JarvisState.SPEAKING, "respondendo em conversa")

            ev = threading.Event()
            speak_streaming(client.chat(clean_follow), ev)
            print()

            fsm.transition(JarvisState.CONVERSATION, "resposta concluida em conversa")


if __name__ == "__main__":
    main()

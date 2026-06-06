#!/usr/bin/env python3
"""Jarvis — assistente de voz local. Stack: Whisper + Qwen3-8B Vulkan + Piper TTS + wake word."""
import sys
import os
import threading
import signal
import numpy as np

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
    PULSE_SINK,
    _ffmpeg_env,
)
from config import AUDIO_SAMPLE_RATE
from stt import transcribe, _get_model as _get_whisper
if TTS_MODE == "qwen3":
    from tts_qwen3 import synthesize
elif TTS_MODE == "piper":
    from tts_piper import synthesize
else:
    from tts import synthesize  # kokoro
from tools import TOOL_DEFINITIONS

WAKE_WORDS = {"jarvis", "jarbis", "jarvis,", "jarvis!"}  # variações de pronúncia

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
        print("ERRO: MARITACA_API_KEY não definida.")
        sys.exit(1)


def _ack():
    """Confirma wake word com voz e tom audível."""
    # Tom bip duplo
    rate = 22050
    t = np.linspace(0, 0.08, int(rate * 0.08))
    bip = 0.6 * np.sin(2 * np.pi * 1000 * t) * np.exp(-t * 30)
    silence = np.zeros(int(rate * 0.05), dtype=np.float32)
    tone = np.concatenate([bip, silence, bip]).astype(np.float32)
    play_samples(tone, rate)
    # Fala curta de confirmação
    samples, sr = synthesize("Sim?")
    play_samples(samples, sr)


def _is_dismiss(text: str) -> bool:
    t = text.strip().lower().rstrip(".,!?")
    return any(d in t for d in DISMISS_PHRASES)


def _say_dismiss():
    import random
    respostas = ["De nada!", "Disponha!", "Até logo!", "Pode contar comigo."]
    samples, rate = synthesize(random.choice(respostas))
    play_samples(samples, rate)


def _check_mic() -> bool:
    """Verifica se o mic está capturando. Tenta forçar ativação se silencioso."""
    import subprocess as _sp
    from audio import _ffmpeg_env
    # Força source a sair do IDLE
    _sp.run(["pactl", "suspend-source", "default", "false"],
            env=_ffmpeg_env, capture_output=True)
    pcm = read_mic_chunk(1.0)
    peak = np.max(np.abs(np.frombuffer(pcm, dtype=np.int16).astype(np.float32))) / 32768
    peak_db = 20 * np.log10(peak + 1e-9)
    if peak_db < -60:
        print("⚠️  AVISO: microfone silencioso. Verifique o headset Jabra:")
        print("   • Mova o dongle para porta USB traseira da placa-mãe")
        print("   • Pressione o botão do headset para acordá-lo")
        print("   • O Jarvis vai continuar tentando — diga 'Jarvis' quando resolver\n")
        return False
    print(f"✓ Microfone OK ({peak_db:.0f}dB)")
    return True


def listen_for_wakeword() -> bool:
    """
    Lê chunk do stream contínuo e verifica se 'jarvis' foi dito.
    Usa stream contínuo para manter o mic sempre ativo.
    Retorna True se wake word detectada.
    """
    import tempfile, wave as _wave, io
    pcm = read_mic_chunk(WAKE_CHUNK_SECS)

    # Escreve WAV em memória para o Whisper
    buf = io.BytesIO()
    with _wave.open(buf, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(AUDIO_SAMPLE_RATE)
        wf.writeframes(pcm)
    buf.seek(0)

    tmp = tempfile.mktemp(suffix=".wav")
    with open(tmp, "wb") as f:
        f.write(buf.getvalue())

    model = _get_whisper()
    segs, _ = model.transcribe(tmp, language="pt", vad_filter=False)
    text = " ".join(s.text.strip().lower() for s in segs)
    os.unlink(tmp)

    if any(w in text for w in WAKE_WORDS):
        print(f"\n[wake] '{text.strip()}' → ativado!")
        return True
    return False


def speak_streaming(text_generator, interrupted_event: threading.Event) -> tuple[bool, str]:
    """Consome gerador LLM e faz TTS sentença a sentença com interrupção por voz real."""
    stop_vad = threading.Event()
    user_spoke = threading.Event()

    # VAD com threshold alto para ignorar ruído BT — exige 640ms de voz contínua
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


def main():
    check_config()

    client = _make_client()
    for td in TOOL_DEFINITIONS:
        client.register_tool(td)
    print(f"[modo LLM: {LLM_MODE} | TTS: {TTS_MODE}]")

    print("\n=== Jarvis iniciado ===")
    print("Diga 'Jarvis' para ativar. Ctrl+C para sair.\n")

    print("Pré-carregando modelos...")
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

    # Mantém headset BT acordado com silêncio contínuo
    start_bt_keepalive()

    print("Pronto. Aguardando wake word 'Jarvis'...\n")

    def handle_exit(sig, frame):
        print("\n[Jarvis] Sessão encerrada.")
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit)

    _idle_chunks = 0
    while True:
        print("💤 ouvindo... ", end="", flush=True)

        if not listen_for_wakeword():
            _idle_chunks += 1
            if _idle_chunks % 10 == 0:
                # A cada 25s sem detecção, força mic a acordar
                import subprocess as _sp
                _sp.run(["pactl", "suspend-source", "default", "false"],
                        env=_ffmpeg_env, capture_output=True)
            continue
        _idle_chunks = 0

        # Wake word detectada — para stream contínuo, confirma e grava comando
        stop_mic_stream()
        _ack()
        print("🎤 Pode falar...")
        wav_path = record_until_silence(max_duration=10.0)
        text = transcribe(wav_path)
        os.unlink(wav_path)

        if not text or len(text.strip()) < 3:
            print("(não entendi, aguardando wake word...)")
            continue

        # Remover "jarvis" do início do texto se estava no comando
        clean = text.strip()
        for w in ["Jarvis,", "Jarvis", "jarvis,"]:
            if clean.lower().startswith(w.lower()):
                clean = clean[len(w):].strip()

        if not clean:
            continue

        # Frase de dispensa? Responde e volta ao modo de espera
        if _is_dismiss(clean):
            _say_dismiss()
            print("[dispensado — aguardando 'Jarvis']")
            _idle_chunks = 0
            continue

        print(f"Você: {clean}")
        print("Jarvis: ", end="", flush=True)

        interrupted_event = threading.Event()
        interrupted, _ = speak_streaming(client.chat(clean), interrupted_event)
        print()

        # Janela de conversa: ouve próximas perguntas sem precisar dizer "Jarvis"
        # Sai da janela se dispensado ou sem fala por 10s
        while True:
            print("🎤 Pode continuar...")
            wav_follow = record_until_silence(max_duration=10.0)
            text_follow = transcribe(wav_follow)
            os.unlink(wav_follow)

            if not text_follow or len(text_follow.strip()) < 3:
                print("[sem fala — voltando ao modo de espera]")
                break

            clean_follow = text_follow.strip()

            if _is_dismiss(clean_follow):
                _say_dismiss()
                print("[dispensado — aguardando 'Jarvis']")
                break

            print(f"Você: {clean_follow}")
            print("Jarvis: ", end="", flush=True)
            ev = threading.Event()
            speak_streaming(client.chat(clean_follow), ev)
            print()

        _idle_chunks = 0


if __name__ == "__main__":
    main()

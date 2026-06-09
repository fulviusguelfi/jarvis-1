"""
LLM local via llama-server (llama.cpp + Vulkan RX 580).
Drop-in para LLMClient quando offline — mesma interface de gerador.
"""
import json
import os
import subprocess
import time
import threading
import atexit
import requests
import sys
from typing import Generator
from config import LLAMA_MODEL, SYSTEM_PROMPT, LLAMA_SERVER_PATH, LLAMA_CTX

TOOLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")

# Binário do llama-server: usa LLAMA_SERVER_PATH se setado, senão o padrão em tools/.
if LLAMA_SERVER_PATH:
    LLAMA_SERVER = LLAMA_SERVER_PATH
elif sys.platform.startswith("win"):
    LLAMA_SERVER = os.path.join(TOOLS_DIR, "llama.cpp", "llama-server.exe")
else:
    LLAMA_SERVER = os.path.join(TOOLS_DIR, "llama.cpp/build/bin/llama-server")

_HOST = "127.0.0.1"
_PORT = 8080
_BASE = f"http://{_HOST}:{_PORT}"

_server_proc: subprocess.Popen | None = None
_server_lock = threading.Lock()


def _server_alive() -> bool:
    try:
        return requests.get(f"{_BASE}/health", timeout=1).status_code == 200
    except Exception:
        return False


def ensure_server() -> None:
    """Inicia llama-server se não estiver rodando. Bloqueia até pronto."""
    global _server_proc
    with _server_lock:
        if _server_alive():
            return

        if not os.path.exists(LLAMA_SERVER):
            raise FileNotFoundError(
                f"llama-server nao encontrado: {LLAMA_SERVER}\n"
                f"Verifique tools/llama.cpp/ ou ajuste LLAMA_SERVER_PATH no .env."
            )
        if not os.path.exists(LLAMA_MODEL):
            raise FileNotFoundError(f"Modelo nao encontrado: {LLAMA_MODEL}")

        env = os.environ.copy()
        # Modelo denso pequeno cabe 100% na VRAM do RX 580: offload total, KV f16
        # padrao (sem flash-attn -> sem o problema de subgroup do Vulkan na RX 580).
        cmd = [
            LLAMA_SERVER,
            "--model", LLAMA_MODEL,
            "-ngl", "99",
            "--ctx-size", str(LLAMA_CTX),
            "--batch-size", "512",
            "--ubatch-size", "128",
            "--host", _HOST,
            "--port", str(_PORT),
            "--parallel", "1",
            "--reasoning", "off",   # garante resposta direta (sem <think>)
            "--jinja",
        ]
        print("[llama-server] Iniciando (Vulkan)...")
        print(f"[llama-server] Binario: {LLAMA_SERVER}")
        print(f"[llama-server] Modelo: {LLAMA_MODEL}  (ctx={LLAMA_CTX})")
        _server_proc = subprocess.Popen(cmd, env=env)

        for _ in range(120):
            time.sleep(1)
            if _server_proc.poll() is not None:
                raise RuntimeError(
                    f"llama-server encerrou no startup (exit={_server_proc.returncode}). "
                    f"Veja o output acima (provavel falta de VRAM: baixe LLAMA_CTX no .env)."
                )
            if _server_alive():
                print("[llama-server] Pronto.")
                return

        stop_server()
        raise RuntimeError("llama-server nao iniciou em 120s")


def stop_server() -> None:
    """Para o llama-server de forma graciosa; mata se nao encerrar. Idempotente."""
    global _server_proc
    proc = _server_proc
    if proc is None:
        return
    _server_proc = None
    try:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    except Exception as e:
        print(f"[llama-server] stop_server() — erro ao encerrar: {e}")


# Garante que o llama-server nao fique orfao quando o processo Python sair.
atexit.register(stop_server)


class LocalLLMClient:
    """Cliente LLM local — mesma interface de gerador que LLMClient."""

    def __init__(self):
        self.history: list[dict] = []
        self.tools: list[dict] = []

    def register_tool(self, tool_def: dict) -> None:
        self.tools.append(tool_def)

    def clear_history(self) -> None:
        self.history = []

    def chat(self, user_message: str) -> Generator[str, None, None]:
        ensure_server()

        if user_message:
            self.history.append({"role": "user", "content": user_message})

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + self.history

        payload: dict = {
            "model": "local",
            "messages": messages,
            "max_tokens": 1024,
            # Amostragem recomendada pelo model card (Qwen3.6 instruct/non-thinking).
            # presence_penalty evita os loops de repeticao ("da da da...").
            "temperature": 0.7,
            "top_p": 0.8,
            "top_k": 20,
            "presence_penalty": 1.5,
            "stream": True,
            # Redundancia: alem do --reasoning off no servidor, pede thinking desligado.
            "chat_template_kwargs": {"enable_thinking": False},
        }
        if self.tools:
            payload["tools"] = self.tools

        clean_response = ""   # resposta sem blocos <think> (vai pro historico e pro TTS)
        tool_calls: list[dict] = []
        # Estado do filtro anti-<think> (defesa extra; --reasoning off ja deve limpar).
        _inside_think = False
        _hold = ""
        _TAIL = 7  # cauda segurada p/ tags partidas entre chunks (len de <think>/</think>)

        with requests.post(
            f"{_BASE}/v1/chat/completions",
            json=payload,
            headers={"Authorization": "Bearer local"},
            stream=True,
            timeout=300,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                line = line.decode("utf-8")
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue

                if not chunk.get("choices"):
                    continue

                delta = chunk["choices"][0].get("delta", {})
                finish = chunk["choices"][0].get("finish_reason")

                if delta.get("content"):
                    _hold += delta["content"]
                    emit = ""
                    while _hold:
                        if _inside_think:
                            j = _hold.find("</think>")
                            if j == -1:
                                _hold = _hold[-_TAIL:] if len(_hold) > _TAIL else _hold
                                break
                            _hold = _hold[j + len("</think>"):]
                            _inside_think = False
                        else:
                            i = _hold.find("<think>")
                            if i == -1:
                                if len(_hold) > _TAIL:
                                    emit += _hold[:-_TAIL]
                                    _hold = _hold[-_TAIL:]
                                break
                            emit += _hold[:i]
                            _hold = _hold[i + len("<think>"):]
                            _inside_think = True
                    if emit:
                        clean_response += emit
                        yield emit

                if delta.get("tool_calls"):
                    for tc in delta["tool_calls"]:
                        idx = tc.get("index", 0)
                        while len(tool_calls) <= idx:
                            tool_calls.append(
                                {"id": "", "type": "function",
                                 "function": {"name": "", "arguments": ""}}
                            )
                        if tc.get("id"):
                            tool_calls[idx]["id"] = tc["id"]
                        if "function" in tc:
                            tool_calls[idx]["function"]["name"] += tc["function"].get("name") or ""
                            tool_calls[idx]["function"]["arguments"] += tc["function"].get("arguments") or ""

                if finish == "tool_calls":
                    pass

        # Flush do que sobrou no buffer (resposta sem </think> pendente).
        if _hold and not _inside_think:
            clean_response += _hold
            yield _hold

        if clean_response:
            self.history.append({"role": "assistant", "content": clean_response})

        if tool_calls:
            yield from self._handle_tool_calls(tool_calls)

    def _handle_tool_calls(self, tool_calls: list[dict]) -> Generator[str, None, None]:
        self.history.append({"role": "assistant", "content": None, "tool_calls": tool_calls})

        for tc in tool_calls:
            name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"]["arguments"])
            except json.JSONDecodeError:
                args = {}

            result = self._dispatch_tool(name, args)
            print(f"[TOOL] {name}({args}) → {result[:120]}")

            self.history.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result,
            })

        yield from self.chat("")

    def _dispatch_tool(self, name: str, args: dict) -> str:
        from tools import TOOL_HANDLERS
        handler = TOOL_HANDLERS.get(name)
        if handler is None:
            return f"Ferramenta '{name}' não encontrada."
        try:
            return handler(**args)
        except Exception as e:
            return f"Erro ao executar {name}: {e}"

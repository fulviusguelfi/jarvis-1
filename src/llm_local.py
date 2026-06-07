"""
LLM local via llama-server (llama.cpp + Vulkan RX 580).
Drop-in para LLMClient quando offline — mesma interface de gerador.
"""
import json
import os
import subprocess
import time
import threading
import requests
import sys
from typing import Generator
from config import LLAMA_MODEL, SYSTEM_PROMPT

TOOLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")

if sys.platform.startswith("win"):
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

        if not os.path.exists(LLAMA_MODEL):
            raise FileNotFoundError(f"Modelo não encontrado: {LLAMA_MODEL}")

        env = os.environ.copy()
        cmd = [
            LLAMA_SERVER,
            "--model", LLAMA_MODEL,
            "-ngl", "99",
            "--flash-attn", "on",
            "--ctx-size", "4096",
            "--cache-type-k", "q8_0",
            "--cache-type-v", "q8_0",
            "--batch-size", "512",
            "--ubatch-size", "128",
            "--host", _HOST,
            "--port", str(_PORT),
            "--parallel", "1",
            "--log-disable",
            "--jinja",
        ]
        print("[llama-server] Carregando modelo em VRAM (pode demorar ~15s)...")
        _server_proc = subprocess.Popen(
            cmd, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        for _ in range(90):
            time.sleep(1)
            if _server_alive():
                print("[llama-server] Pronto.")
                return

        _server_proc.terminate()
        raise RuntimeError("llama-server não iniciou em 90s")


def stop_server() -> None:
    global _server_proc
    if _server_proc:
        _server_proc.terminate()
        _server_proc = None


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
            # /no_think desativa o modo reasoning do Qwen3 para respostas diretas
            self.history.append({"role": "user", "content": f"{user_message} /no_think"})

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + self.history

        payload: dict = {
            "model": "local",
            "messages": messages,
            "max_tokens": 512,
            "temperature": 0.7,
            "stream": True,
        }
        if self.tools:
            payload["tools"] = self.tools

        full_response = ""
        tool_calls: list[dict] = []

        with requests.post(
            f"{_BASE}/v1/chat/completions",
            json=payload,
            headers={"Authorization": "Bearer local"},
            stream=True,
            timeout=60,
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
                    text = delta["content"]
                    full_response += text
                    yield text

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

        if full_response:
            self.history.append({"role": "assistant", "content": full_response})

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

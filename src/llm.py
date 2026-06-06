import json
import requests
from dataclasses import dataclass, field
from typing import Generator
from config import (
    MARITACA_API_KEY, MARITACA_MODEL, MARITACA_BASE_URL,
    MARITACA_MAX_TOKENS, MARITACA_TEMPERATURE, SYSTEM_PROMPT
)

# Preços Sabiazinho-3 em R$ por token (jun/2026)
_PRICE_INPUT_PER_TOKEN  = 1.00 / 1_000_000   # R$1/M
_PRICE_OUTPUT_PER_TOKEN = 3.00 / 1_000_000   # R$3/M


@dataclass
class CallStats:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0

    @property
    def cost_brl(self) -> float:
        return (self.prompt_tokens * _PRICE_INPUT_PER_TOKEN
                + self.completion_tokens * _PRICE_OUTPUT_PER_TOKEN)

    def __str__(self) -> str:
        cached = f", {self.cached_tokens} cached" if self.cached_tokens else ""
        return (f"[tokens: {self.prompt_tokens}in{cached} + "
                f"{self.completion_tokens}out = R${self.cost_brl:.5f}]")


@dataclass
class SessionStats:
    calls: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_cost_brl: float = 0.0

    def add(self, call: CallStats) -> None:
        self.calls += 1
        self.total_prompt_tokens += call.prompt_tokens
        self.total_completion_tokens += call.completion_tokens
        self.total_cost_brl += call.cost_brl

    def __str__(self) -> str:
        return (f"[sessão: {self.calls} chamadas | "
                f"{self.total_prompt_tokens}in + {self.total_completion_tokens}out tokens | "
                f"total R${self.total_cost_brl:.4f}]")


class LLMClient:
    def __init__(self):
        self.history: list[dict] = []
        self.tools: list[dict] = []
        self.session: SessionStats = SessionStats()

    def register_tool(self, tool_def: dict) -> None:
        self.tools.append(tool_def)

    def clear_history(self) -> None:
        self.history = []

    def chat(self, user_message: str) -> Generator[str, None, None]:
        """Envia mensagem, faz streaming da resposta. Yield de chunks de texto."""
        if user_message:
            self.history.append({"role": "user", "content": user_message})

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + self.history

        payload: dict = {
            "model": MARITACA_MODEL,
            "messages": messages,
            "max_tokens": MARITACA_MAX_TOKENS,
            "temperature": MARITACA_TEMPERATURE,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if self.tools:
            payload["tools"] = self.tools

        headers = {
            "Authorization": f"Key {MARITACA_API_KEY}",
            "Content-Type": "application/json",
        }

        full_response = ""
        tool_calls: list[dict] = []
        stats = CallStats()

        with requests.post(
            f"{MARITACA_BASE_URL}/chat/completions",
            json=payload,
            headers=headers,
            stream=True,
            timeout=30,
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

                # Captura usage no último chunk (stream_options include_usage)
                if chunk.get("usage"):
                    u = chunk["usage"]
                    stats.prompt_tokens     = u.get("prompt_tokens", 0)
                    stats.completion_tokens = u.get("completion_tokens", 0)
                    stats.cached_tokens     = (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
                    continue  # chunk de usage não tem conteúdo

                delta  = chunk["choices"][0].get("delta", {})
                finish = chunk["choices"][0].get("finish_reason")

                if delta.get("content"):
                    text = delta["content"]
                    full_response += text
                    yield text

                if delta.get("tool_calls"):
                    for tc in delta["tool_calls"]:
                        idx = tc.get("index", 0)
                        while len(tool_calls) <= idx:
                            tool_calls.append({"id": "", "type": "function",
                                               "function": {"name": "", "arguments": ""}})
                        if tc.get("id"):  # só atualiza se não for null/vazio
                            tool_calls[idx]["id"] = tc["id"]
                        if "function" in tc:
                            tool_calls[idx]["function"]["name"]      += tc["function"].get("name") or ""
                            tool_calls[idx]["function"]["arguments"] += tc["function"].get("arguments") or ""

                if finish == "tool_calls":
                    pass  # Deixa o loop continuar para capturar o chunk de usage antes de sair

        if full_response:
            self.history.append({"role": "assistant", "content": full_response})

        self.session.add(stats)
        print(f"\n  {stats}")
        print(f"  {self.session}")

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

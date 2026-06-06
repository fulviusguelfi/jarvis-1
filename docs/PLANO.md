# Jarvis-1 → Fluidez primeiro, depois arsenal agêntico (plano de implementação)

## Context

A v1 do Jarvis funciona (Whisper → Qwen3-8B/Vulkan → Piper TTS, half-duplex, validada em conversa real). As dores relatadas foram de **fluidez**, não de capacidade: *"tempo de resposta inaceitável"*, *"quero full-duplex"*, *"o mic liga e desliga"*. Por isso: **consertar a interação ANTES de empilhar ferramentas** — e só então dar ao Jarvis o arsenal agêntico (file system, janelas, browser, online), mantendo o **cérebro local e grátis** (zero tokens pagos).

Decisões do usuário: **fluidez primeiro**; **avaliar Qwen3-4B por velocidade**; **confirmar ações destrutivas**; **KV cache q8_0**.

---

## Fatos do ambiente (verificados nesta sessão — não re-derivar)

| Fato | Implicação |
|---|---|
| `--jinja` **já vem ligado por padrão** nesta build do llama-server | Tool calling não está bloqueado por falta de flag. Risco real é o *template*. |
| Build do llama-server tem `--chat-template-file`, `--chat-template`, `--reasoning-format`, `--tools` (built-in, não usar) | Podemos forçar template de tools corrigido. |
| `torch 2.12.0+cpu` + `onnxruntime 1.26.0` instalados | openWakeWord e Silero VAD rodam via ONNX, **sem GPU, sem dep nova**. |
| `mcp 1.27.2` + `mcp-server-fetch`/`-git`/`-time` (Python) instalados; **node/npx ausentes** | Ponte MCP usa servers **Python** (pip). Evitar servers Node. |
| **Todas as libs do Chromium presentes** (libnss3, libgbm, libgtk-3, libasound, libxkbcommon, libdrm…) | Playwright Python vai rodar; só falta `pip install playwright` + `playwright install chromium`. |
| **AT-SPI NÃO funciona** (import `Atspi` falha, sem socket a11y) e **tesseract ausente** | Leitura de UI **desktop** indisponível. Visão rica só no **browser** (a11y tree do Playwright). |
| Sessão **X11 + KDE** (`DISPLAY=:0`); KWin é EWMH-compliant; **xdotool/wmctrl ausentes** | Controle de janela via `EWMHlib`; automação de teclado/mouse via `pynput` (XTEST), não xdotool. |
| Sem package manager (sandbox Freedesktop/Flatpak); `pip` e `~/.local/bin` ok | Tudo pure-Python/pip, **zero root**. |
| Modelos baixados: `Qwen3-8B-Q4_K_M` (atual), `Qwen3-0.6B-Q4_0`. **4B NÃO baixado.** | Eval de velocidade: baixar `Qwen3-4B-Instruct-2507-Q4_K_M`; 0.6B serve só de referência (fraco p/ tool calling). |
| Qwen3 é **text-only** | "Ver a tela" = texto estruturado (a11y tree), nunca pixels. |

Pacotes a instalar via pip: `openwakeword`, `silero-vad`, `pynput`, `EWMHlib`, `mss`, `psutil`, `playwright`.

---

## Achados de documentação (com mitigação)

1. **Qwen3 tool calling no llama.cpp** tem gotcha conhecido: *"Template supports tool calls but does not natively describe tools"* → fallback gera resultados ruins. **Mitigação:** rodar com `--jinja` (default) **+ `--chat-template-file` com template Qwen3/Hermes corrigido** (Unsloth publicou); inspecionar com `--verbose`. *(llama.cpp#19872, unsloth Qwen3-Coder fixes)*
2. **KV q4_0 degrada tool calling** → **q8_0**. *(docs/function-calling.md)*
3. **STT em tempo real:** Silero VAD para endpointing + faster-whisper com lookahead <500ms → ~380-520ms end-to-end. Substituir o RMS+1.2s de silêncio por endpoint do Silero. *(ufal/whisper_streaming, faster-whisper)*
4. **openWakeWord** tem modelo pré-treinado **"hey jarvis"** (onnx+tflite, ~200k clips, runtime ONNX sem PyTorch). Single-word "jarvis" exigiria treino custom. *(dscripka/openWakeWord)*
5. **Playwright** opera por **accessibility tree, sem visão**; Chromium próprio no `~/.cache/ms-playwright`. *(playwright.dev/mcp)*
6. **Open-Meteo**: sem chave, `GET /v1/forecast?latitude=..&longitude=..&current=temperature_2m,...` + geocoding `GET /v1/search?name=`. *(open-meteo.com)*
7. **EWMHlib**: `getActiveWindow()`, `getClientList()`, `setActiveWindow(w)`, `setWmState(w,1,'_NET_WM_STATE_...')`, `display.flush()`. *(ewmh.readthedocs.io)*

---

## Fases

### Fase 1 — FLUIDEZ (a base) 🎯
- **Wake word dedicado:** `openwakeword` com modelo `hey_jarvis` (ONNX), frames de 80ms @16kHz lidos do stream contínuo já existente ([audio.py:38](src/audio.py#L38)). Remove o Whisper-em-loop de 2.5s ([main.py:106-136](src/main.py#L106-L136)) e o lag de ativação. **Decisão de UX:** adotar "Hey Jarvis" (frase do pré-treinado). Fallback: manter Whisper p/ "jarvis" só se o usuário recusar a frase.
- **Endpointing com Silero VAD:** substituir o RMS+1.2s de [audio.py:80-146](src/audio.py#L80-L146) por `silero-vad` (ONNX) detectando fim de fala → transcreve no instante que você para. Corta ~1.5s de tempo morto/turno.
- **Pipeline sobreposto:** manter o streaming sentença-a-sentença de `speak_streaming` ([main.py:139](src/main.py#L139)); garantir 1º fonema assim que a 1ª cláusula fecha.
- **Barge-in confiável:** trocar o VAD-RMS de `mic_vad_background` ([audio.py:288](src/audio.py#L288)) pelo Silero VAD — distingue voz de ruído do Jabra (o que matou o barge-in antes). Reativar interrupção durante a fala.
- **Robustez de áudio (embutida):** `read_mic_chunk` devolve silêncio quando o stream morre ([audio.py:43-47](src/audio.py#L43-L47)) → detectar mic morto, reconectar e **avisar com som** em vez de surdez calada.
- **Avaliar Qwen3-4B:** baixar `Qwen3-4B-Instruct-2507-Q4_K_M`; comparar feel (tok/s, latência ao 1º áudio) vs 8B no uso real; registrar decisão em `project_jarvis1_context`. (0.6B já baixado serve só de referência de teto de velocidade.)

### Fase 2 — Fundação do tool calling
- [src/llm_local.py:44-58](src/llm_local.py#L44-L58): `--cache-type-k/v q4_0` → `q8_0`; adicionar `--chat-template-file` apontando p/ template Qwen3-tools corrigido (commitado em `tools/templates/qwen3_tools.jinja`); `--jinja` explícito.
- **Detecção inline de tool call** (sem passe não-streaming bloqueante): acumular deltas de `tool_calls` no stream ([llm_local.py:150-162](src/llm_local.py#L150-L162)) e bloquear só quando uma ferramenta é de fato emitida — preserva fluidez no caso comum.
- [src/config.py](src/config.py): reescrever `_build_system_prompt` — hoje **proíbe** internet/ferramentas; passa a **declarar capacidades** e instruir uso (estilo Hermes, conciso, pt-BR, sem markdown na fala). Manter `/no_think`.

### Fase 3 — Ferramentas nativas + camada de segurança
Padrão já existe (`TOOL_HANDLERS`/`TOOL_DEFINITIONS` em [src/tools/__init__.py](src/tools/__init__.py)). Adicionar:
- `fs.py` (stdlib: ler/listar/escrever/mover/deletar).
- `window.py` (`EWMHlib`: listar/focar/mover/fechar janela).
- `apps.py` (`kstart`/`gtk-launch`/`.desktop` via `subprocess`).
- `input.py` (`pynput`: digitar/clicar — automação cega, sem leitura de UI).
- `system.py` (`psutil`: CPU/RAM/bateria/volume; `datetime` local).
- **`safety.py`:** classifica chamada — leitura/abrir = autônomo; destrutivo (deletar/mover/escrever/`run_shell` mutante) = Jarvis fala a ação e espera "sim" por voz. Allowlist de prefixos seguros p/ `run_shell` ([src/tools/shell.py](src/tools/shell.py)).

### Fase 4 — Browser (Playwright, accessibility tree) — a "visão" real
`pip install playwright && playwright install chromium`. `browser.py`: `navegar`/`ler_pagina`(snapshot a11y→texto)/`clicar`/`digitar`/`voltar`. Sessão persistente com cleanup em `atexit`. É o caminho que resolve o caso "ver o clima no site" da v1.

### Fase 5 — Ferramentas online (grátis, sem tokens de LLM)
- `weather.py`: Open-Meteo geocoding + forecast (sem chave).
- `web.py`: usar o **MCP `mcp-server-fetch` já instalado** via ponte (Fase 6) ou wrapper direto p/ busca/fetch.

### Fase 6 — Ponte MCP
`mcp_bridge.py` com SDK `mcp` (já instalado): subir servers Python via stdio (`mcp-server-fetch`/`-git`/`-time`), listar tools, converter schema MCP→`TOOL_DEFINITIONS`, despachar p/ `TOOL_HANDLERS`, ciclo de vida com cleanup. Sem Node.

---

## Registro de Riscos e Mitigações

| # | Risco | Sev. | Mitigação |
|---|---|---|---|
| R1 | Template Qwen3 não descreve tools → tool calls ruins | 🔴 | `--chat-template-file` corrigido + `--jinja` + `--verbose` p/ inspeção. |
| R2 | KV q4_0 degrada tool calling | 🟠 | q8_0 (cabe nos 8GB: pesos ~5GB + KV <1GB). |
| R3 | Tool calling em 8B/Q4 instável; **4B piora** | 🟠 | Se 4B errar tool call, manter 8B nos turnos com ferramenta. Poucas tools, schema claro, Hermes, `/no_think`. |
| R4 | Streaming quebra boundaries de tool call | 🟠 | Detecção inline; bloquear só quando ferramenta emitida. |
| R5 | **Sem visão de UI desktop** (AT-SPI/tesseract ausentes) | 🟠 | Escopo honesto: browser = leitura rica (Playwright a11y); desktop = só janela (ewmh) + input cego (pynput). OCR/VLM ficam fora (sem binário/VRAM). |
| R6 | "hey jarvis" ≠ "jarvis" sozinho | 🟡 | Adotar "Hey Jarvis"; fallback Whisper se recusado. |
| R7 | Sem package manager | 🟠 | Stack pure-Python/pip + Chromium autocontido. Zero root. |
| R8 | LLM local pode emitir comando perigoso | 🟠 | `safety.py`: confirmação por voz + allowlist. |
| R9 | Subprocessos órfãos (browser/MCP/llama) | 🟡 | Cleanup em `atexit`/sinal, padrão de `stop_server` ([llm_local.py:75](src/llm_local.py#L75)). |
| R10 | `EWMHlib`/`pynput` exigem X11 | 🟡 | Sessão é X11; abstrair atrás de `window.py`/`input.py`. |
| R11 | Escopo grande → meio-construído pior que v1 | 🟠 | Fluidez primeiro entrega ganho sentido já na Fase 1; cada fase é incremental e usável. |

---

## Verificação (uso real, sem suíte de testes automatizados)

- **F1:** ativar com "Hey Jarvis" é quase instantâneo; ao parar de falar a resposta começa em <1s de tempo morto; dá pra interromper a fala falando por cima; desconectar o Jabra dispara aviso sonoro; 4B vs 8B comparados e decisão registrada.
- **F2:** `llama-server` sobe com template corrigido; pedir algo que exige ferramenta mostra `[TOOL] nome(args)` no log ([llm_local.py:184](src/llm_local.py#L184)); resposta sem ferramenta segue fluida.
- **F3:** "abra o Firefox" abre; "apague tal arquivo" **pede confirmação**.
- **F4:** "veja o clima no clima tempo" navega, lê a árvore a11y, responde (caso que falhou na v1).
- **F5:** clima retorna dado real via Open-Meteo, sem API paga.
- **F6:** `mcp-server-time`/`-fetch` aparecem como ferramentas utilizáveis.

Validação é conversa real + inspeção de log. Sem código de teste.

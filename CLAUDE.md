# Jarvis-1 — Instruções para Claude Code

## Contexto
Assistente de voz local **100% offline** em Python, rodando em Windows 11.
Pipeline: microfone → wake word → STT → LLM → tools → TTS → alto-falante.
Desenvolvimento solo. Hardware fixo: Ryzen 5 4500 · 16GB RAM · **RX 580 8GB** (Vulkan) · headset **Jabra Link 380**.

## Documentos de Referência (ler antes de codar)
- `docs/PLANO.md` — plano agêntico por fases, riscos R1–R11, fatos do ambiente
- `docs/planejamento/processo-desenvolvimento.md` — convenções, agentes de dev, testes, gitflow, riscos
- `docs/planejamento/roadmap-features.md` — features por ciclo (DOR/DOD) e ordem de execução
- `docs/WHISPER_SILENCE_ANALYSIS.md` — análise de alucinações (decisão arquitetural da Fase 1)
- `CONTINUATION.md` — mapa de migração Linux→Windows
- `docs/memory/` — contexto, hardware, pesquisa

## Estado Atual — v0.1.0 (Fase 0 concluída)
Pipeline end-to-end funcional e validado em conversa real:
- **STT:** faster-whisper `small` (CPU, pt-BR) — `src/stt.py`
- **LLM:** Qwen3-8B Q4_K_M via llama.cpp + Vulkan (RX 580) — `src/llm_local.py`
- **TTS:** Piper `pt_BR-faber-medium` — `src/tts_piper.py`
- **Áudio:** sounddevice, device padrão do SO + auto-detecção Jabra — `src/audio.py`
- **Orquestração:** wake word "Jarvis" (Whisper em loop) → comando → resposta — `src/main.py`

**Limitação conhecida (alvo da Fase 1):** Whisper alucina em silêncio no loop de wake word
(`vad_filter=False` em `listen_for_wakeword`). Solução: openWakeWord (classificador, não gera texto).

## Arquitetura (camadas, fluxo top-down)
```
ÁUDIO-IN → WAKE WORD → VAD/ENDPOINT → STT → LLM (+TOOLS) → TTS → ÁUDIO-OUT
```
Princípio determinístico: **classificadores (openWakeWord, Silero VAD) fazem o gate; o
gerador (Whisper) só roda sobre fala já validada** — nunca sobre silêncio puro.

## Módulos (`src/`)
```
main.py        — loop principal, máquina de estados (espera→escuta→responde)
audio.py       — sounddevice: captura, playback, keepalive BT, VAD background
stt.py         — faster-whisper (transcrição de comando)
llm_local.py   — llama-server.exe (Vulkan), cliente streaming, tool calling
llm.py         — cliente cloud (Maritaca) — fallback opcional
tts_piper.py   — Piper TTS (padrão)
tts.py / tts_qwen3.py — TTS alternativos (kokoro / qwen3)
config.py      — leitura de .env (SEMPRE encoding="utf-8")
tools/         — TOOL_DEFINITIONS + TOOL_HANDLERS (run_shell etc.)
```

## Convenções
- **Commits:** Conventional Commits — `<tipo>(<escopo>): <descrição>`
  - Tipos: `feat`, `fix`, `refactor`, `test`, `docs`, `perf`, `chore`, `style`
  - Escopos: `audio`, `wake`, `vad`, `stt`, `llm`, `tts`, `tools`, `config`, `main`, `ci`, `docs`
- **Git Flow:** `main` (releases tagueadas) ← `develop` (integração) ← `feat/<nome>` (features curtas)
  - Feature branches partem de `develop` e voltam via merge ao concluir DOD
  - `develop` → `main` só ao fechar uma fase (tag `v0.N.0`)
  - Detalhes: `docs/planejamento/roadmap-features.md`
- **Naming Python:** `snake_case` funções/variáveis, `PascalCase` classes, `UPPER_SNAKE` constantes
- **Formatação:** 4 espaços, UTF-8, LF; `ruff` para lint quando configurado

## Regras Invioláveis
1. **NUNCA** usar caracteres não-ASCII (emoji, →, ✓) em `print()` — o console Windows é cp1252 e quebra. Usar `[OK]`, `->`, etc.
2. **SEMPRE** abrir arquivos de texto com `encoding="utf-8"` explícito (default Windows = cp1252).
3. Áudio **sempre** no dispositivo padrão do SO (sem `device=` fixo), com auto-detecção do Jabra como fallback.
4. **NUNCA** passar silêncio puro ao Whisper — o gate (wake word / VAD) é pré-requisito de toda transcrição.
5. Chamadas ao `llama-server` que bloqueiam devem ser streaming; nunca travar o loop principal sem feedback.
6. **NUNCA** `except` sem log — todo erro logado com contexto (`[CAT] modulo.func() — chave=valor`).
7. Seguir o escopo da **fase/feature atual** — não antecipar features de fases futuras.
8. Toda feature passa no teste correspondente e no smoke (`check_deps.py`) antes de merge.
9. Logs de debug (`[debug]`, `[audio-debug]`) são **efêmeros** — remover quando a feature estabilizar.
10. Antes de matar processos, preferir parada graciosa (`stop_server`, `atexit`); evitar órfãos (llama-server).

## Stack
- Python **3.12** (não usar o 3.14 do sistema), venv em `.venv`
- faster-whisper, openWakeWord (Fase 1), silero-vad, piper-tts, sounddevice, numpy
- llama.cpp `llama-server.exe` (build win-vulkan-x64) em `tools/llama.cpp/`
- pytest (testes), ruff (lint)

## Orçamentos de Latência (alvos da Fase 1 — "Fluidez")
```
Detecção de wake word (por frame 80ms):     < 50ms   (openWakeWord CPU)
Endpoint de fim de fala (Silero VAD):        < 300ms  após silêncio
STT de comando (~3s de áudio, Whisper small): < 1s
LLM 1º token (Qwen3-8B Vulkan):              < 1s
TTS 1ª sentença (Piper RTF ~0.06):           < 300ms
Tempo percebido (fim da fala → 1º áudio):    < 2s     (alvo)
```

## Comandos
```powershell
.venv\Scripts\Activate.ps1
python check_deps.py        # smoke test do ambiente (22/22)
python src\main.py          # rodar o assistente
```

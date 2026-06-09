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

## Estado Atual — v0.2.0 (Fase 1 concluída)
Pipeline end-to-end funcional com **wake word determinístico** e LLM 4B denso (leve, deixa a máquina livre):
- **Wake word:** openWakeWord hey_jarvis (ONNX classificador, 0-1 score) — `src/wake.py`
- **STT:** faster-whisper `small` (CPU, pt-BR, apenas sobre fala válida) — `src/stt.py`
- **VAD:** Silero VAD para endpointing (fim de fala detectado em <300ms) — `src/vad.py`
- **LLM:** Qwen3-4B-Instruct-2507 (Q8) via llama-server **padrão** + Vulkan (RX 580) — `src/llm_local.py`
  - Denso, cabe 100% na VRAM (~5GB). Binário padrão `tools/llama.cpp/` — sem turbo/flash-attn/n-cpu-moe.
- **Amostragem:** top_k=20, top_p=0.8, presence_penalty=1.5 (model card) — sem repetição
- **TTS:** Piper `pt_BR-faber-medium` — `src/tts_piper.py`
- **Áudio:** sounddevice, device padrão do SO + auto-detecção Jabra — `src/audio.py`
- **Orquestração:** openWakeWord → Silero VAD → STT → LLM → TTS — `src/main.py` (FSM 7 estados)

**Fase 1 concluída:** determinismo (sem fallback invisível), ~15-20 tok/s, ~15s startup, voz pt-BR coerente.

> O modelo MoE 35B (Qwen3.6-35B-A3B via TurboQuant) está **preservado na tag `35b-turboquant`**.
> Para restaurar: `git checkout 35b-turboquant` (exige o binário turbo em `A:\llama-cpp-turboquant\`).

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
- faster-whisper, openWakeWord (hey_jarvis_v0.1.onnx ONNX direto), silero-vad, piper-tts, sounddevice, numpy, librosa
- **llama-server padrão** (`tools/llama.cpp/llama-server.exe`, build win-vulkan-x64) — roda o 4B denso
  - Modelo: `Qwen3-4B-Instruct-2507-UD-Q8_K_XL.gguf` (Q8, ~5GB, cabe 100% na VRAM)
  - Flags: `-ngl 99 --ctx-size 16384 --reasoning off --jinja` (KV f16; sem turbo/flash-attn/n-cpu-moe)
  - O modelo/binário vivem em `A:\` (temporário, fora do git). `.env` aponta os caminhos.
- pytest (testes), ruff (lint)

## Orçamentos de Latência (Fase 1 — "Fluidez", verificado com Qwen3-4B Q8)
```
Detecção de wake word (por frame 80ms):           < 50ms   (openWakeWord ONNX CPU)
Endpoint de fim de fala (Silero VAD):              < 300ms  após silêncio
STT de comando (~3s áudio, Whisper small):         < 1.5s   (CPU)
LLM startup (carga do 4B na VRAM):                 ~15s     (1x por sessão)
LLM tokens (flow):                                  ~15-20 tok/s (Q8 na VRAM)
LLM resposta curta (fim a fim):                     ~1-2s
TTS 1ª sentença (Piper RTF ~0.06):                 < 300ms
```

## Patch Crítico: RX 580 + TurboQuant Flash Attention  (SÓ p/ o 35B — tag `35b-turboquant`)

> O setup atual (4B denso + binário padrão) **NÃO usa flash attention nem turbo**, então este
> patch é irrelevante para o dia a dia. Só importa se reconstruir o build turbo para rodar o 35B.

**Arquivo:** `A:\llama-cpp-turboquant\ggml\src\ggml-vulkan\ggml-vulkan.cpp` (linha ~2261)

**Problema:** RX 580 é Wave64-puro (`subgroup_min/max=64`). Alguns shaders de flash attention
pediam subgroup_size ≠64 → `GGML_ASSERT` e crash no warmup, mesmo após modelo carregado.

**Fix (aplicado):** Ao invés de abortar, clampear `required_subgroup_size` no range [min,max]:
```c
if (device->subgroup_size_control && required_subgroup_size > 0) {
    // Clampear ao range suportado pelo device
    if (required_subgroup_size < device->subgroup_min_size) 
        required_subgroup_size = device->subgroup_min_size;
    if (required_subgroup_size > device->subgroup_max_size) 
        required_subgroup_size = device->subgroup_max_size;
    pipeline_shader_stage_required_subgroup_size_create_info.requiredSubgroupSize = required_subgroup_size;
    pipeline_shader_create_info.setPNext(&pipeline_shader_stage_required_subgroup_size_create_info);
}
```

**Validação:** Resposta coerente em pt-BR prova que a matemática da FA está correta (não foi gambiarra).

## Comandos
```powershell
.venv\Scripts\Activate.ps1
python check_deps.py        # smoke test do ambiente (24/25; Jabra é hardware)
python setup_models.py      # valida wake word, deps, llama-server, modelo
python src\main.py          # rodar o assistente
jarvis.bat                  # (Desktop) setup + run + logging
```

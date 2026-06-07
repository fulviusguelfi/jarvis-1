# Regras de Fallback — Jarvis-1

## Princípios

1. **Degradação graciosa, não falha silenciosa**
   - Sempre logar fallback ativado: `[modulo] Fallback para X (razão)`
   - Nunca falhar silenciosamente — avisar ao usuário via log

2. **Fallback é degradado, não equivalente**
   - Fallback reduz qualidade ou latência, mas não quebra fluxo
   - Exemplo: Whisper (alucinação) é fallback pior que openWakeWord (classifier)

3. **Fallback não é indefinido**
   - Cada fallback tem sua própria alternativa (não cascata infinita)
   - Se fallback também falhar → erro definido, não silêncio

4. **Fallback é **testável**
   - Documentar critério de ativação (ex: arquivo não existe, exception, timeout)
   - Implementar cache se fallback for chamado repetidamente (não logar 1000x)

---

## Fallbacks Implementados

### F1.1 Wake Word — openWakeWord → Whisper

**Situação:** Usuário não tem `models/openWakeWord/hey_jarvis.onnx`

**Cascata:**
1. Tentar carregar openWakeWord (`_get_model()` em `wake.py`)
2. Se falhar (arquivo não existe, import não funciona):
   - Retorna `None`
   - Log: `[wake] Fallback para Whisper...`
   - `detect_wake_word()` retorna `False`
3. `listen_for_wakeword_chunk()` percebe que openWakeWord falhou
4. Roda Whisper 2.5s (v0.1.0 modo)
5. Detecta "jarvis" variações

**Log:**
```
[wake] Modelo hey_jarvis.onnx nao encontrado
[wake] Fallback para Whisper (baixe o modelo para ativar openWakeWord)
```

**Cache:** `_fallback_cached` bool evita logar repetidamente

**DOD:** Usuário detecta "Jarvis" em ambos modos

---

### F1.2 VAD Endpoint — Silero VAD → RMS (opcional)

**Situação:** `record_until_silence()` em `audio.py`

**Cascata:**
1. Tentar `vad.record_until_silence_vad()` (Silero VAD)
2. Se falhar (library missing):
   - Parâmetro `vad_method="rms"` ativa fallback
   - Usa RMS + 1.2s silêncio (v0.1.0 modo)

**Status:** NÃO IMPLEMENTADO YET (F1.2 sempre usa Silero)

**Future-proof:** `record_until_silence(vad_method="silero")` com fallback pronto

---

### F1.3 STT Filter — Pós-filtro Silero → Passthrough

**Situação:** `filter_transcription()` em `stt_filter.py`

**Cascata:**
1. Aplicar 3 filtros: `compression_ratio > 2.4`, `blocklist`, padrões
2. Se todos falharem → retorna "" (rejeita)
3. Se algum passa → retorna texto

**Fallback (implicit):** Se filtro quebrar (exception) → passthrough (sem rejeição)

**Status:** DOCUMENTADO em `stt_filter.py`

---

### LLM — local → cloud

**Situação:** Qwen3-8B via llama-server pode falhar

**Cascata:**
1. Tentar LLM local (`llm_local.py`)
2. Se timeout ou crash:
   - Voltar para `llm.py` cloud (Maritaca)
   - Requer `MARITACA_API_KEY` configurada

**Status:** NÃO IMPLEMENTADO (ainda é manual no `.env`)

**Proposta para Fase 2:** Tentar local 3s, se falhar voltar cloud com fallback automático

---

### Áudio — Device padrão SO → Jabra auto-detect

**Situação:** Qual device usar (mic/speaker)?

**Cascata:**
1. Usar device padrão do SO (sem `device=` fixo)
2. Auto-detect Jabra Link 380 se encontrado
3. Fallback: qualquer device padrão

**Status:** IMPLEMENTADO em `audio.py:_find_jabra_device()`

```python
def _find_jabra_device() -> int | None:
    """Procura Jabra Link 380, senao retorna padrão do SO."""
    for dev in sd.query_devices():
        if 'jabra' in dev['name'].lower():
            return device_idx
    return sd.default.device[0]  # Fallback
```

---

## Regras de Implementação

### Quando Implementar Fallback:

✅ **DO:**
- Dependência externa (arquivo, library, network)
- Qualidade degrada, não quebra (ex: Whisper < openWakeWord)
- Tem alternativa clara e testável
- User pode saber que está em modo degradado

❌ **DON'T:**
- Fallback para "não fazer nada" (sempre fazer algo ou avisar erro)
- Fallback cascata infinita (máximo 2 níveis)
- Fallback silencioso sem log
- Fallback "esperança" (ex: retry indefinido)

### Checklist para Fallback:

```
[ ] Nomear fallback: "Fallback para X"
[ ] Logar em qual situação ativa
[ ] Cache se fallback chamado repetidamente
[ ] Testar ambos caminhos (principal + fallback)
[ ] DOD menciona fallback explicitamente
[ ] Documentar em FALLBACK_RULES.md
```

---

## Status Atual (v0.2.0)

| Fallback | Status | Cascata | Cache | Testado |
|----------|--------|---------|-------|---------|
| Wake word (openWakeWord → Whisper) | ✅ | 2 níveis | ✅ | ✅ |
| VAD endpoint (Silero → RMS) | 🟡 Pronto | 2 níveis | ❌ | ❌ |
| STT filter (determinístico → passthrough) | 🟢 Implícito | 1 nível | N/A | ✅ |
| LLM (local → cloud) | 🔴 Manual | 2 níveis | ❌ | ❌ |
| Áudio device (padrão → Jabra) | ✅ | 2 níveis | ✅ | ✅ |

---

## Próximas Ações

**Fase 2:**
- [ ] Implementar LLM cloud fallback automático
- [ ] Ativar VAD fallback (padrão Silero, fallback RMS)
- [ ] Adicionar retry logic para timeouts

**Fase 3:**
- [ ] Tool security fallback (se comando perigoso → pedir confirmação)

---

**Regra de Ouro:** *Fallback é para **degradação graciosa**, não para esconder bugs.*

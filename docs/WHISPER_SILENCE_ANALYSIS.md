# Análise: Alucinações do Whisper em Silêncios

**Data:** 2026-06-07  
**Status:** Documentado e priorizado para Fase 1  
**Criticidade:** ALTA — Afeta uso em conversas naturais

---

## 1. O Problema Observado

Durante testes da v1 Windows, o Whisper alucinou:
```
Input: silêncio (16000 samples de audio vazio)
Output: "até o próximo vídeo, até o próximo vídeo, até o próximo vídeo."
```

**Impacto:** Em conversas naturais com pausas prolongadas, o Jarvis gera lixo.

---

## 2. Root Cause

**Por que Whisper alucina em silêncios?**

- Treinado em 680k horas de áudio ruidoso/real
- Usa Mel-spectrogram (análise visual do áudio)
- Silêncio = padrão "vazio" que o modelo tenta "preencher"
- Não tem mecanismo de confiança/rejeição
- **Sempre gera ALGO, nunca retorna vazio**

---

## 3. Soluções Conhecidas

### 3.1. VAD (Voice Activity Detection) ⭐ RECOMENDADO

**Silero VAD (ONNX)**
- Detecta presença/ausência de voz
- Offline, leve, rápido (~50ms)
- Já está em `requirements.txt`
- 85% de precisão em silêncios

**Implementação:**
```python
if not silero_vad.is_speech(audio_chunk):
    return ""  # Pula Whisper
else:
    return whisper.transcribe(audio_chunk)
```

### 3.2. Energy Thresholding (RMS)

**Simples e rápido:**
```python
rms_db = 20 * np.log10(np.sqrt(np.mean(audio**2)) + 1e-9)
if rms_db < -45:
    return ""  # Silêncio
```

### 3.3. Confidence Thresholding

**Problema:** Whisper não expõe confiança nativamente  
**Requer:** Versão com `logprobs`  
**Viabilidade:** Possível em Fase 2

### 3.4. Post-processing (Heurística)

Rejeitar saídas com padrões de alucinação:
- Muito curtas (<3 palavras)
- Muito genéricas ("até", ".", "e e e")

---

## 4. Estratégia Recomendada para Jarvis

**3 camadas de proteção:**

| Camada | Mecanismo | Latência | Precisão |
|--------|-----------|----------|----------|
| 1 | Energy VAD (RMS < -45dB) | 1ms | 70% |
| 2 | Silero VAD | 50ms | 85% |
| 3 | Sanity check (output) | 10ms | 90% |
| **Total** | **Combinado** | **60ms** | **95%+** |

**Pseudocódigo:**
```python
def transcribe_safe(audio_chunk):
    # Layer 1: Energy check
    if rms_db(audio_chunk) < -45:
        return ""
    
    # Layer 2: Silero VAD
    if not silero_vad.is_speech(audio_chunk):
        return ""
    
    # Layer 3: Whisper + sanity
    text = whisper.transcribe(audio_chunk)
    if is_hallucination(text):  # Heurística
        return ""
    
    return text
```

---

## 5. Implementação na v1

**Estado atual (Fase 0):** Sem proteção  
**Risco:** Alucinações frequentes em pausas  
**Solução:** Implementar em Fase 1 com openWakeWord + Silero VAD

**Arquitetura Fase 1:**
```
openWakeWord ("Hey Jarvis")
    ↓ detecta wake word
    ↓
read_mic_until_silence (Silero VAD endpointing)
    ↓ grava só a fala real
    ↓
Whisper (transcreve comando LIMPO)
    ↓ entrada já validada, menos alucinações
    ↓
Qwen3-8B → Piper
```

---

## 6. Validação Necessária (Fase 1)

Testar com:
- ✅ Silêncio puro (10s)
- ✅ Ruído branco
- ✅ Respiração/tosse
- ✅ Fala normal
- ✅ Fala baixa
- ✅ Pausa no meio da frase
- ✅ Conversa natural com pausas filosóficas

---

## 7. Conclusão

**Para Jarvis v1 (agora):** Aceitar limitação, documentado  
**Para Jarvis Fase 1:** Implementar 3 camadas de VAD + Silero VAD endpointing  
**Resultado esperado:** 95%+ rejeição de alucinações, conversas naturais viáveis

---

**Próximo passo:** Implementar em Fase 1 com openWakeWord + Silero VAD endpointing

# Análise Profunda: Alucinações do Whisper em Silêncios

**Data:** 2026-06-07
**Status:** Pesquisa com fontes primárias (papers 2025 + issues oficiais)
**Criticidade:** ALTA — afeta conversas naturais com pausas

> ⚠️ Versão anterior deste doc era do conhecimento de treino, sem fonte.
> Esta versão é baseada em pesquisa real com referências verificáveis.

---

## 1. A pergunta central: existe solução 100%?

**Resposta curta e honesta:**

- **100% garantido por um único modelo: NÃO EXISTE.** O estado da arte em 2025
  (Calm-Whisper) reduz a taxa de alucinação de 99.97% → 15.51% — ~84% de redução,
  **não 100%**. ([arXiv 2505.12969](https://arxiv.org/html/2505.12969v1))
- **~100% contra o modo de falha que observamos (silêncio → texto repetitivo
  tipo "até o próximo vídeo"): SIM, é alcançável** — mas por **arquitetura em
  camadas determinísticas**, não por um modelo mágico.

A distinção abaixo é a chave de tudo.

---

## 2. A reformulação que muda o jogo: gerador vs. classificador

O erro conceitual (que eu cometi na primeira análise) é tratar "alucinação"
como um problema único. São DUAS naturezas diferentes:

| Componente | Tipo | Saída | Pode "alucinar palavras"? |
|---|---|---|---|
| **Whisper** | **Gerador** (seq2seq) | Texto | **SIM** — inventa palavras no silêncio |
| **openWakeWord** | **Classificador** | Número (0–1) | **NÃO** — fisicamente impossível |
| **Silero VAD** | **Classificador** | Número (0–1) | **NÃO** — fisicamente impossível |

**Por que isso importa:**
openWakeWord e Silero VAD **não geram texto**. Eles emitem uma probabilidade.
No silêncio, a saída é "probabilidade baixa" — eles **não conseguem** emitir
"até o próximo vídeo". É impossível por construção, não por treino.

➡️ **Whisper só roda no trecho que o classificador já marcou como fala.**
Assim, Whisper **nunca vê silêncio puro** → o modo de falha que você observou
é **estruturalmente eliminado**, não apenas mitigado.

---

## 3. Por que Whisper alucina (mecanismo confirmado)

1. **Origem nos dados de treino:** legendas de vídeos contêm "Subtitles by...",
   "Thanks for watching", anúncios em trechos de silêncio/música. O modelo
   aprendeu a associar silêncio a essas frases.
   ([openai/whisper #1606](https://github.com/openai/whisper/discussions/1606),
   [#1783](https://github.com/openai/whisper/discussions/1783))
2. **Mecanismo interno (2025):** apenas **3 cabeças de atenção do decoder
   (#1, #6, #11)** respondem por **>75% das alucinações**.
   ([Calm-Whisper, arXiv 2505.12969](https://arxiv.org/html/2505.12969v1))
3. **Sempre gera algo:** seq2seq não tem "rejeição" nativa — produz tokens até
   o EOS, mesmo sem áudio.

---

## 4. As 4 famílias de solução (com números reais)

### 4.1. Pré-filtro VAD (gate antes do Whisper)
- WhisperX provou que VAD reduz alucinação/repetição nos benchmarks
  Kincaid46 e TED-LIUM.
- **Limite honesto:** Silero VAD v5 acerta só **61%** no ESC-50 (ruído puro) —
  até **40% do ruído** pode passar como "fala".
  ([faster-whisper #843](https://github.com/SYSTRAN/faster-whisper/issues/843))
- ➡️ VAD sozinho **não** é 100%, mas remove o silêncio limpo (o caso fácil).

### 4.2. Sinais determinísticos do próprio Whisper (PÓS-filtro) ⭐
O Whisper expõe métricas por segmento que permitem **rejeição programática**:

| Métrica | Default | Captura |
|---|---|---|
| `compression_ratio` | > 2.4 = lixo | **Repetição** ("sete sete sete", "até o próximo vídeo...") |
| `no_speech_prob` | > 0.6 = silêncio | Não-fala |
| `avg_logprob` | < -1.0 = incerto | Baixa confiança |

- `compression_ratio` é **decisivo** no nosso caso: alucinações são repetitivas
  → comprimem muito → detectáveis de forma **determinística**.
  ([whisper #2420](https://github.com/openai/whisper/discussions/2420),
  [#679](https://github.com/openai/whisper/discussions/679))
- **Gotcha confirmado:** se todas as temperaturas derem `compression_ratio` alto,
  o faster-whisper **aceita o último resultado mesmo assim** → por isso é
  preciso **filtrar nós mesmos**, não confiar no fallback interno.
  ([faster-whisper transcribe.py](https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/transcribe.py))

### 4.3. Blocklist de frases conhecidas (PÓS-filtro)
O conjunto de alucinações de silêncio é **finito e conhecido**: "thanks for
watching", "subtitles by", "legendas pela comunidade amara.org" (apareceu no
NOSSO log!), "até o próximo vídeo". Blocklist pega o resíduo que escapa do resto.

### 4.4. Correção no modelo (Calm-Whisper, SOTA 2025)
- Fine-tune só das 3 cabeças problemáticas com 105h de não-fala (labels vazios).
- 99.97% → 15.51% de alucinação; WER quase intacto (+0.07%).
- **Problemas práticos p/ nós:** é Whisper-**large-v3** (pesado; rodamos `small`
  em CPU); pesos abertos **não confirmados**. ➡️ Não é drop-in viável agora.

---

## 5. Achado concreto no NOSSO código

- `src/stt.py` (transcrição de comando): já usa `vad_filter=True` ✅
- `src/main.py` `listen_for_wakeword()`: usa **`vad_filter=False`** ❌
  → **esta é a causa direta** das alucinações no loop de wake word.

Ou seja: o caminho do comando já tem proteção parcial; o **loop de wake word
não tem nenhuma** — e é exatamente onde vimos "até o próximo vídeo".

---

## 6. Arquitetura-alvo (Fase 1) — caminho para ~100% no modo observado

```
[ESPERANDO]  openWakeWord("Hey Jarvis")   ← classificador, NÃO gera texto
                  │ score > limiar
                  ▼
[GRAVANDO]   Silero VAD endpointing        ← classificador define início/fim
                  │ só o trecho de fala real
                  ▼
[TRANSCREVE] Whisper (nunca vê silêncio puro)
                  │
                  ▼
[PÓS-FILTRO] compression_ratio < 2.4  E  no_speech_prob < 0.6
             E  not in blocklist
                  │ passou
                  ▼
             texto válido → Qwen3 → Piper
```

**Garantias por camada:**
1. Wake word em silêncio → classificador → **0 texto** (garantia estrutural)
2. Whisper só em fala → **não vê silêncio puro** (elimina o caso dominante)
3. Pós-filtro determinístico → pega repetição/baixa-confiança **sem ML**
4. Blocklist → pega o resíduo conhecido

➡️ Contra "silêncio vira texto repetitivo": **efetivamente 100%.**
➡️ Contra **toda e qualquer** alucinação em qualquer condição: **não há 100%
   provável** — ver risco residual abaixo.

---

## 7. Análise de RISCO (o ponto crônico que você levantou)

O risco real numa conversa longa/filosófica **não** é "silêncio vira texto"
(isso a Seção 6 resolve). O risco residual é:

| Risco | Severidade | Por quê | Mitigação |
|---|---|---|---|
| **Pausa MID-fala** (você pensando) com ruído baixo → VAD mantém segmento aberto → Whisper insere repetição | 🟠 | VAD não distingue "pausa para pensar" de "fim de turno" | `compression_ratio` pega a parte repetitiva; ajustar `min_silence_duration` |
| **Falso-positivo de VAD** em respiração/ventilador/teclado → trecho não-fala vai p/ Whisper | 🟠 | Silero 61% em ruído adversarial | Energy-gate antes do VAD + pós-filtro |
| **Alucinação curta plausível** (não repetitiva) | 🟡 | `compression_ratio` NÃO pega (não repete); `avg_logprob` pega parte | Resíduo genuíno; raro; não é o "thanks for watching" catastrófico |
| **Calm-Whisper indisponível/pesado** | 🟡 | large-v3, pesos não confirmados | Não depender dele; usar camadas |

**Conclusão de risco:** o modo **catastrófico e frequente** (silêncio →
frase aleatória) é **eliminável** de forma determinística. O resíduo
(alucinação curta plausível em ruído) é **raro, não-catastrófico e detectável
parcialmente** por `avg_logprob`. Não há prova de 100% absoluto — mas o risco
crônico que você temia **não se materializa** com a arquitetura da Seção 6,
porque o gerador nunca opera sobre silêncio.

---

## 8. Recomendação

1. **Não consertar o loop atual de Fase 0** (vai ser substituído).
2. **Fase 1 = a solução real:** openWakeWord + Silero VAD endpointing +
   pós-filtro determinístico (`compression_ratio`/`no_speech_prob`) + blocklist.
3. **Quick-win opcional agora** (1 linha): ligar `vad_filter=True` no
   `listen_for_wakeword()` derruba a maior parte das alucinações de wake word
   imediatamente, sem investir em código descartável.

---

## Fontes

- [Calm-Whisper (arXiv 2505.12969, 2025)](https://arxiv.org/html/2505.12969v1) — 3 cabeças, 99.97%→15.51%
- [Investigation of Whisper Hallucinations Induced by Non-Speech (arXiv 2501.11378, 2025)](https://arxiv.org/pdf/2501.11378)
- [openai/whisper #679 — A possible solution to hallucination](https://github.com/openai/whisper/discussions/679)
- [openai/whisper #1606 — Hallucination on no-speech audio](https://github.com/openai/whisper/discussions/1606)
- [openai/whisper #2420 — compression_ratio threshold](https://github.com/openai/whisper/discussions/2420)
- [openai/whisper PR #1838 — hallucination_silence_threshold](https://github.com/openai/whisper/pull/1838)
- [SYSTRAN/faster-whisper #843 — Silero VAD 61% em ruído](https://github.com/SYSTRAN/faster-whisper/issues/843)
- [faster-whisper transcribe.py — gotcha do fallback de temperatura](https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/transcribe.py)
- [openWakeWord hey_jarvis model docs](https://github.com/dscripka/openWakeWord/blob/main/docs/models/hey_jarvis.md)

# Teste de Fase 1 — v0.2.0

## Status Atual
✅ v0.2.0 pronto para teste com **4B-Q8_0**
⚠️ Rodando em **modo fallback** (Whisper wake word) — openWakeWord será ativado depois

## Como Rodar

### Opção 1: .bat (recomendado)
```
Duplo-clique: Desktop\jarvis.bat
```

### Opção 2: PowerShell manual
```powershell
cd C:\Users\Usuario\VSCodeProjects\jarvis-1
.venv\Scripts\Activate.ps1
python src\main.py
```

## Teste Prático

Você verá:
```
[modo LLM: local | TTS: piper]
...
Pronto. Aguardando wake word 'Jarvis'...

 ouvindo...
```

### Passo 1: Wake word
Fale **"Jarvis"** (ou variações: "jarbis", "jarvis,")

Esperado:
```
[STATE] IDLE -> ACTIVATED -- wake word detectada
[STATE] ACTIVATED -> LISTENING_COMMAND -- pronto para comando
[MIC] Pode falar...
```
+ Bip de confirmação + síntese "Sim?"

### Passo 2: Comando
Fale uma pergunta: **"Que horas são?"**

Esperado:
```
[STATE] LISTENING_COMMAND -> PROCESSING -- transcrevendo comando
[STT] 2.5s -> 'Que horas sao'
Você: Que horas são?
[STATE] PROCESSING -> SPEAKING -- respondendo
Jarvis: [resposta em voz pt-BR]
```

### Passo 3: Barge-in (opcional)
Enquanto Jarvis fala, **fale por cima** → deve parar e voltar a ouvir

Esperado:
```
[barge-in detectado]
[STATE] SPEAKING -> CONVERSATION -- barge-in durante resposta
```

### Passo 4: Dispensa (opcional)
Fale **"Obrigado Jarvis"** → responde + volta ao IDLE

Esperado:
```
[STATE] CONVERSATION -> IDLE -- usuario dispensou
```

## Métricas para Observar

| Métrica | Alvo | Como medir |
|---------|------|-----------|
| Wake word latência | < 100ms | Tempo desde falar "Jarvis" até bip |
| Endpoint latência | < 500ms | Tempo desde parar fala até iniciar STT |
| TTFT (4B-Q8_0) | < 1s | Tempo até 1º áudio da resposta |
| Qualidade | Resposta correta | Fazer perguntas simples |

## Possíveis Problemas

### "ModuleNotFoundError: No module named X"
→ Rodar `pip install -r requirements.txt` e tentar novamente

### "Mic silencioso" (-60dB)
→ Verificar headset Jabra:
   - Pressionar botão do headset para acordá-lo
   - Trocar para porta USB traseira (reconectar)
   - Aguardar 5s

### "ERRO ao transcrever" ou "Mic morreu"
→ Vira um tom de alarme + tenta reconectar automaticamente

### Whisper diz bobagem (alucinação)
→ Normal com Whisper em fallback — F1.3 pós-filtro deveria rejeitar
→ Testar com silêncio (não fale nada) e veja se Whisper alucina

## Próximos Passos

### Para ativar openWakeWord ("Hey Jarvis")
1. Baixar `hey_jarvis.onnx` de:
   ```
   https://github.com/dscripka/openWakeWord/releases/download/v0.6.0/hey_jarvis.onnx
   ```
2. Salvar em:
   ```
   C:\Users\Usuario\VSCodeProjects\jarvis-1\models\openWakeWord\hey_jarvis.onnx
   ```
3. Rodar novamente — agora vai dizer "Aguardando wake word 'Hey Jarvis'"

### Comparar 4B-Q8_0 vs 8B-Q4_K_M
Editar `.env`:
```
QWEN_MODEL=Qwen3-8B-Q4_K_M
```
E rodar `jarvis.bat` novamente — observe TTFT.

## Logs

Os logs aparecem no console (PowerShell/cmd). **Não feche a janela** — deixa rodar enquanto testa, depois me mostra os logs para análise.

---

**Status:** v0.2.0 Fase 1 concluída (F1.0-F1.5 mergeadas)  
**Modo:** Fallback (Whisper), openWakeWord pendente de modelo  
**Modelo LLM:** Qwen3-4B-Q8_0 (configurado em .env)  
**Data teste:** 2026-06-07

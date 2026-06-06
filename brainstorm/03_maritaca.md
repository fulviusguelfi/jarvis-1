# Maritaca AI — Pesquisa e Análise de Uso no Projeto

> Pesquisa realizada em: 2026-06-04

## O Que É

Startup brasileira (fundada 2022, Rodrigo Nogueira + Unicamp) especializada em modelos de linguagem em português.

## Modelos Disponíveis via API

| Modelo | Entrada | Saída | Característica |
|--------|---------|-------|----------------|
| **Sabiazinho-3** | R$1/M tokens | R$3/M tokens | Mais rápido, menor custo |
| **Sabiá-3** | R$5/M tokens | R$10/M tokens | Melhor qualidade |
| **Sabiá-3.1** | — | — | Mais avançado |
| **Sabiazinho-4** | preview | preview | Próxima geração |

- R$20 em créditos gratuitos ao criar conta
- API compatível com formato OpenAI
- **Function calling:** ✅

## Open Source?

- **Sabiá-7B:** ✅ pesos públicos em `maritaca-ai/sabia-7b` (HuggingFace)
  - Baseado em LLaMA-1-7B, fine-tuned em português
  - GGUF disponível via TheBloke
  - **Licença:** mesma do LLaMA-1 — somente pesquisa, não comercial
- **Sabiá-2 e Sabiá-3:** ❌ proprietários, somente API

## Capacidade de Voz/Áudio

- **API:** texto apenas — **sem speech-in ou speech-out**
- Microfone funciona no browser deles, não exposto na API
- Para uso no Jarvis: emparelhar com Whisper.cpp (STT local) + Kokoro TTS (local)

## Proposta de Uso no Jarvis-1

O usuário já paga a Maritaca → custo marginal mínimo.

```
Microfone → Whisper.cpp (STT local) → Sabiazinho-3 API → Kokoro TTS (local) → Alto-falante
                                            ↓
                                     Tool Use / Function Calling
                                            ↓
                                  llama.cpp + Vulkan (comandos pesados offline)
```

**Vantagens:**
- Português nativo excelente (melhor que modelos locais 7B)
- Custo muito baixo (Sabiazinho-3 é barato)
- Já tem conta e acesso
- Evoluível: trocar Maritaca por modelo local quando hardware permitir

**Desvantagens:**
- Depende de internet para o LLM
- Latência de rede adicionada
- Privacidade (tokens enviados para servidor externo)

## Fontes
- https://docs.maritaca.ai/pt/modelos
- https://www.maritaca.ai/post/sabiazinho-4
- https://huggingface.co/maritaca-ai/sabia-7b
- https://github.com/maritaca-ai/maritalk-api

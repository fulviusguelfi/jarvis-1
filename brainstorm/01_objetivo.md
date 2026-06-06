# Objetivo do Projeto Jarvis-1

## Visão

Assistente de IA pessoal que:
- **Ouve** a voz do usuário (sem botão de push-to-talk)
- **Fala** de volta com voz natural
- **Controla o PC** (abre apps, executa comandos, lê tela)
- **Raciocina** em português
- Roda **100% local** como meta final (sem internet)

## Inspiração

Quatro vídeos assistidos na sessão inaugural:

| Vídeo | Tema |
|-------|------|
| Jarvis Mark XXXV | IA que controla o PC inteiro |
| Jarvis Mark XXXIX | Modelo de IA local flexível |
| Qwen 3.6 35B em 8GB VRAM (pt-BR) | llama.cpp + inferência local eficiente |
| Running 35B on 6GB VRAM (llama.cpp) | Quantização e otimização de hardware |

## Referência de Experiência

**Gemini 2.5 Flash** — modelo que ouve e fala nativamente, sem pipeline fragmentado.
Queremos replicar essa experiência, sem depender de internet.

## Fases

1. **Fase 1 (agora):** Arquitetura híbrida — Maritaca API (texto) + Whisper local (STT) + Kokoro local (TTS)
2. **Fase 2:** Substituir Maritaca por modelo local com Vulkan (Qwen3 14B Q4)
3. **Fase 3 (meta):** Single model full-duplex local quando hardware/software permitir

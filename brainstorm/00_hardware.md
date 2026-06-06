# Hardware da Máquina Alvo

> Verificado em: 2026-06-04 via lscpu / lspci / sysfs

| Componente | Spec |
|------------|------|
| CPU | AMD Ryzen 5 4500 — 6 cores / 12 threads @ 4.2GHz |
| RAM | 16GB |
| GPU | AMD Radeon RX 580 (Ellesmere) — **8GB VRAM** |
| OS | SteamOS / Freedesktop SDK 25.08 (Flatpak) |
| Hostname | steamdeck (desktop, não handheld) |

## GPU — Situação de Aceleração

| Backend | Status | Motivo |
|---------|--------|--------|
| CUDA | ❌ | GPU NVIDIA ausente |
| ROCm (HIP) | ❌ | RX 580 (Polaris/GCN4) foi removido do suporte oficial AMD |
| **Vulkan** | ✅ | Funciona — dri renderD128 presente, drivers AMD mesa |
| OpenCL | ❓ | Não testado |

### Implicação direta
Qualquer modelo que exija PyTorch com ROCm **não roda com GPU** nesta máquina.
Modelos via **llama.cpp compilado com `-DGGML_VULKAN=1`** funcionam no RX 580.

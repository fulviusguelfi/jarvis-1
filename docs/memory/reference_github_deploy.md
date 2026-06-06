---
name: reference-github-deploy
description: Como criar repo GitHub via API curl e fazer push — credenciais e processo para o projeto Jarvis-1
metadata: 
  node_type: memory
  type: reference
  originSessionId: c8d127f7-6c84-4be8-b8b5-2a3538f9e327
---

# GitHub Deploy — Jarvis-1

## Credenciais
- **Usuário GitHub**: `fulviusguelfi`
- **Token PAT (scopes: repo)**: salvo em `~/.config/jarvis-1/credentials` (chmod 600, fora do git)
- **Email git**: ftitaneroguelfi@gmail.com

## Processo: criar repo via API + push

```bash
# 1. Ler token
source ~/.config/jarvis-1/credentials

# 2. Criar repo via API GitHub
curl -s -X POST https://api.github.com/user/repos \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  -d '{"name":"jarvis-1","description":"...","private":false,"auto_init":false}'

# 3. Configurar remote e push
cd /home/deck/projects/prototipes/jarvis-1
git remote add origin https://fulviusguelfi:$GITHUB_TOKEN@github.com/fulviusguelfi/jarvis-1.git
git push -u origin main
```

## Notas
- `gh` CLI está em `/home/deck/.local/bin/gh` — não está no PATH padrão dos shells do Claude
- `gh auth status` falha nos shells do Claude (keyring do sistema não acessível neste contexto)
- O token no hosts.yml (`~/.config/gh/hosts.yml`) está no keyring, não em plaintext
- Para usar `gh` nos shells do Claude: `export PATH="$PATH:/home/deck/.local/bin"`

## Links
- Ver [[project_jarvis1_context]] para contexto do projeto

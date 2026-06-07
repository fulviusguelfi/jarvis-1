# 🔧 Troubleshooting VSCode no Windows vs Linux

## Problema: VSCode funciona no Linux mas não no Windows

### 🎯 Causas Comuns

| Problema | Windows | Linux | Solução |
|----------|---------|-------|---------|
| **Permissões de arquivo** | ❌ Entende ACL mas git usa POSIX | ✅ POSIX nativo | `git config core.fileMode false` |
| **Line endings** | CRLF (padrão) | LF (padrão) | Configurar `.gitattributes` ou `core.safecrlf false` |
| **Nomes de arquivo** | ❌ Sensível a caso apenas em NTFS | ✅ Case-sensitive | Renomear se necessário |
| **Caracteres especiais** | ❌ Alguns bloqueados (`:*?"<>\|`) | ✅ Liberados | Evitar esses caracteres |
| **Git worktree/lock** | ❌ Às vezes fica preso | ✅ Raro | Remover `.git/index.lock` |
| **Antivírus** | ❌ Pode bloquear .git | ✅ Não interfere | Excluir projeto do antivírus |
| **Caminhos longos** | ❌ Limite de 260 chars | ✅ Sem limite | Ativar `core.longpaths` |

### 🔍 Diagnóstico Rápido

```powershell
# Windows - Verifique:
git config core.fileMode              # Deve ser: false
git config core.safecrlf              # Deve ser: false
git config core.longpaths             # Deve ser: true
git status                            # Nenhuma mudança fantasma
Get-Item .git\index.lock -ErrorAction SilentlyContinue  # NÃO deve existir
```

```bash
# Linux/WSL - Verifique:
git config core.fileMode
git config core.safecrlf
git status
ls -la .git/index.lock
```

---

## ✅ Soluções Rápidas

### 1️⃣ Executar o Script de Reparo Automático

**Windows:**
```powershell
.\fix-vscode-windows.ps1
```

**Linux/WSL:**
```bash
bash fix-vscode-linux.sh
```

### 2️⃣ Configuração Manual Completa

```powershell
# Windows
git config core.fileMode false
git config core.safecrlf false
git config core.longpaths true
git config core.precomposeunicode false

# Rescan
git add -A
git reset --hard HEAD
```

### 3️⃣ Remover Lock File Preso

```powershell
# Windows
if (Test-Path .git\index.lock) { Remove-Item .git\index.lock }

# Linux
rm -f .git/index.lock
```

### 4️⃣ Recriar índice do git

```bash
# Ambos os SOs
git rm -r --cached .
git add -A
git commit -m "Fix: reindex git after Windows/Linux migration"
```

---

## 🐛 Problemas Específicos

### "Permission denied" ao editar arquivo

**Causa:** VSCode rodando como usuário diferente ou arquivo read-only

**Solução:**
```powershell
# Windows - Dar permissão total
$path = "C:\Users\Usuario\VSCodeProjects\jarvis-1"
$acl = Get-Acl $path
$ar = New-Object System.Security.AccessControl.FileSystemAccessRule(
    [System.Security.Principal.WindowsIdentity]::GetCurrent().User,
    "FullControl",
    "ContainerInherit,ObjectInherit",
    "None",
    "Allow"
)
$acl.SetAccessRule($ar)
Set-Acl -Path $path -AclObject $acl
```

### Git diz que tudo mudou mas nada mudou

**Causa:** Problema com line endings ou permissões

**Solução:**
```bash
git add -A
git reset --hard
git clean -fd
```

### VSCode travado/lento ao abrir

**Causa:** Git indexing lento, antivírus escaneando, ou WSL não está rodando

**Solução:**
- **Windows nativo:** Excluir `.git` do Windows Defender
  ```powershell
  # Abrir: Windows Security → Virus & threat protection
  # → Manage settings → Add exclusions → pasta do projeto
  ```

- **WSL:** Usar extensão `Remote - WSL` no VSCode
  ```powershell
  code --remote wsl .
  ```

### "fatal: detected dubious ownership in repository"

**Causa:** Git acha que o repo foi modificado suspeita (Windows → Linux)

**Solução:**
```bash
git config --global --add safe.directory '*'
# OU específico:
git config safe.directory "$(pwd)"
```

---

## 🚀 Prevenção: `.gitattributes`

Crie um arquivo `.gitattributes` na raiz do projeto:

```
# Auto detect line endings
* text=auto

# Python
*.py text eol=lf
*.sh text eol=lf
*.bash text eol=lf

# Windows scripts (se tiver)
*.ps1 text eol=crlf
*.bat text eol=crlf
*.cmd text eol=crlf

# Markdown
*.md text eol=lf

# Documentação
*.txt text eol=lf
```

Depois:
```bash
git add .gitattributes
git add -A --renormalize
git commit -m "Normalize line endings"
```

---

## 💡 Recomendação para o seu projeto

Para **Jarvis-1**, que é multiplataforma:

1. ✅ **Já feito:** `git config core.fileMode false` (Windows não entende POSIX)
2. ⏳ **Recomendado:** Adicionar `.gitattributes` para padronizar LF em scripts
3. 🔧 **Usar:** WSL2 + VSCode Remote WSL se quiser experiência Linux no Windows

---

## 🆘 Se Nada Funcionar

Último recurso (apaga e reconstrói):

```powershell
# Windows
git stash                  # Salva mudanças locais
git fetch origin
git reset --hard origin/main
# Ou para branch atual:
git reset --hard "origin/$(git rev-parse --abbrev-ref HEAD)"
```

```bash
# Linux
git stash
git fetch origin
git reset --hard origin/main
```

---

## 📚 Referências

- [Git Configuration Reference](https://git-scm.com/docs/git-config)
- [Git on Windows](https://github.com/git-for-windows/git/wiki/FAQ)
- [VSCode Remote - WSL](https://code.visualstudio.com/docs/remote/wsl)
- [Line Endings (gitattributes)](https://git-scm.com/docs/gitattributes#_end_of_line_conversion)

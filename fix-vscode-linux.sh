#!/bin/bash
# Script para reparar problemas do VSCode em Linux/WSL

echo "🔧 Reparando VSCode em Linux/WSL..."

# 1. Desabilitar fileMode (já é default no Linux, mas garante)
echo -e "\n1️⃣  Configurando git..."
git config core.fileMode false
echo "   ✓ git config core.fileMode = false"

# 2. Rescan do repositório
echo -e "\n2️⃣  Rescaneando repositório..."
git add -A
git reset --hard
echo "   ✓ Repositório rescaneado"

# 3. Limpar cache do git
echo -e "\n3️⃣  Limpando cache do git..."
git gc --aggressive
echo "   ✓ Git garbage collection executado"

# 4. Reparar possíveis lock files
if [ -f .git/index.lock ]; then
    echo -e "\n⚠️  Removendo .git/index.lock..."
    rm .git/index.lock
    echo "   ✓ Lock file removido"
fi

# 5. Status
echo -e "\n4️⃣  Status do repositório:"
git status

# 6. Informações
echo -e "\n5️⃣  Informações do sistema:"
echo "   OS: $(uname -s)"
echo "   Kernel: $(uname -r)"
echo "   Git: $(git --version)"
echo "   Bash: $BASH_VERSION"
echo "   Repo path: $(pwd)"

echo -e "\n✨ Reparo concluído!"
echo -e "\n💡 Próximas ações:"
echo "   1. Feche e reabra o VSCode"
echo "   2. Se estiver em WSL, garanta que o WSL2 está rodando"
echo "   3. Instale a extensão 'WSL' no VSCode se usar WSL"

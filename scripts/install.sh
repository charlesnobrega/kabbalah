#!/usr/bin/env bash
# Kabbalah Installer for Linux (Bash)
# No emojis in terminal outputs to prevent display issues

set -e

echo "[*] Iniciando instalador do Kabbalah (Onda 12 - Linux)..."

# 1. Verificar versao do Python
if ! command -v python3 &> /dev/null; then
    echo "[!] Erro: Python 3 nao esta instalado ou nao foi adicionado ao PATH."
    exit 1
fi
echo "[+] Python encontrado: $(python3 --version)"

# 2. Criar ambiente virtual se nao existir
if [ ! -d ".venv" ]; then
    echo "[*] Criando ambiente virtual (.venv)..."
    python3 -m venv .venv
    echo "[+] Ambiente virtual criado com sucesso."
else
    echo "[+] Ambiente virtual (.venv) ja existe."
fi

# 3. Atualizar pip e instalar dependencias
echo "[*] Instalando dependencias do requirements.txt..."
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
echo "[+] Dependencias instaladas com sucesso."

# 4. Criar estrutura de diretorios locais do usuario (~/.kabbalah)
KABBALAH_DIR="$HOME/.kabbalah"
MEMORY_DIR="$KABBALAH_DIR/memory"

if [ ! -d "$MEMORY_DIR" ]; then
    echo "[*] Criando pastas de configuracao local em $MEMORY_DIR..."
    mkdir -p "$MEMORY_DIR"
    echo "[+] Pastas criadas."
else
    echo "[+] Pastas de configuracao local ja existem."
fi

# 5. Criar arquivo de chaves de cofre local de exemplo se nao existir
KEYS_FILE="$KABBALAH_DIR/keys.json"
if [ ! -f "$KEYS_FILE" ]; then
    echo "[*] Criando keys.json de exemplo..."
    cat <<EOF > "$KEYS_FILE"
{
  "OPENAI_API_KEY": "insira-sua-chave-aqui",
  "GOOGLE_API_KEY": "insira-sua-chave-aqui",
  "GROQ_API_KEY": "insira-sua-chave-aqui"
}
EOF
    echo "[+] keys.json criado em $KEYS_FILE. Adicione suas chaves de API nele."
else
    echo "[+] keys.json ja existe em $KEYS_FILE."
fi

# 6. Verificar Docker
if ! command -v docker &> /dev/null; then
    echo "[!] Aviso: Docker CLI nao esta instalado."
    echo "[!] O sandbox local estara desabilitado ate que o Docker seja instalado."
else
    echo "[+] Docker CLI encontrado: $(docker --version)"
    if ! docker ps &> /dev/null; then
        echo "[!] Aviso: O Daemon do Docker nao esta rodando ou nao possui permissao."
        echo "[!] O sandbox local estara desabilitado ate que o Daemon esteja ativo."
    else
        echo "[+] Docker Daemon rodando com sucesso (Sandbox ativa)."
    fi
fi

# 7. Verificar Ollama
if ! command -v curl &> /dev/null; then
    echo "[!] Aviso: curl nao instalado. Pulando verificacao do Ollama."
else
    if ! curl -s -o /dev/null -w "%{http_code}" http://localhost:11434/api/tags &> /dev/null; then
        echo "[!] Aviso: Ollama local nao esta rodando na porta 11434."
        echo "[!] O sistema de busca semantica usara fallback por substrings locais."
    else
        echo "[+] Ollama local encontrado e ativo."
        echo "[*] Verificando modelo de embeddings nomic-embed-text..."
        # Tentar puxar o modelo
        if ! curl -s http://localhost:11434/api/tags | grep -q "nomic-embed-text"; then
            echo "[*] Puxando modelo nomic-embed-text no Ollama..."
            curl -s -X POST http://localhost:11434/api/pull -d '{"model": "nomic-embed-text"}' > /dev/null
            echo "[+] Modelo nomic-embed-text carregado no Ollama."
        else
            echo "[+] Modelo nomic-embed-text ja carregado."
        fi
    fi
fi

echo "[+] Instalacao concluida! Kabbalah pronto para uso fisico no Linux."
echo "[*] Para iniciar a ponte MCP, rode: .venv/bin/python kabbalah_mcp_bridge.py"

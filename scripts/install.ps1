# Kabbalah Installer for Windows (PowerShell)
# Enforce CP1252/UTF-8 compat - No Emojis to prevent UnicodeEncodeError in Windows consoles

$ErrorActionPreference = "Stop"

Write-Host "[*] Iniciando instalador do Kabbalah (Onda 12 - Windows)..."

# 1. Verificar versao do Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[+] Python encontrado: $pythonVersion"
} catch {
    Write-Host "[!] Erro: Python nao esta instalado ou nao foi adicionado ao PATH."
    Exit 1
}

# 2. Criar ambiente virtual se nao existir
if (-not (Test-Path -Path ".venv")) {
    Write-Host "[*] Criando ambiente virtual (.venv)..."
    python -m venv .venv
    Write-Host "[+] Ambiente virtual criado com sucesso."
} else {
    Write-Host "[+] Ambiente virtual (.venv) ja existe."
}

# 3. Atualizar pip e instalar dependencias
Write-Host "[*] Instalando dependencias do requirements.txt..."
& .venv\Scripts\python.exe -m pip install --upgrade pip
& .venv\Scripts\python.exe -m pip install -r requirements.txt
Write-Host "[*] Instalando o pacote kabbalah (modo editavel) para expor a CLI..."
& .venv\Scripts\python.exe -m pip install -e .
Write-Host "[+] Dependencias e CLI instaladas com sucesso."

# 4. Criar estrutura de diretorios locais do usuario (~/.kabbalah)
$userHome = [System.Environment]::GetFolderPath("UserProfile")
$kabbalahDir = Join-Path $userHome ".kabbalah"
$memoryDir = Join-Path $kabbalahDir "memory"

if (-not (Test-Path -Path $memoryDir)) {
    Write-Host "[*] Criando pastas de configuracao local em $memoryDir..."
    New-Item -ItemType Directory -Force -Path $memoryDir | Out-Null
    Write-Host "[+] Pastas criadas."
} else {
    Write-Host "[+] Pastas de configuracao local ja existem."
}

# 5. Criar arquivo de chaves de cofre local de exemplo se nao existir
$keysFile = Join-Path $kabbalahDir "keys.json"
if (-not (Test-Path -Path $keysFile)) {
    Write-Host "[*] Criando keys.json de exemplo..."
    $defaultKeys = @{
        "OPENAI_API_KEY" = "insira-sua-chave-aqui"
        "GOOGLE_API_KEY" = "insira-sua-chave-aqui"
        "GROQ_API_KEY"   = "insira-sua-chave-aqui"
    }
    $defaultKeys | ConvertTo-Json | Out-File -FilePath $keysFile -Encoding utf8
    Write-Host "[+] keys.json criado em $keysFile. Adicione suas chaves de API nele."
} else {
    Write-Host "[+] keys.json ja existe em $keysFile."
}

# 6. Verificar Docker
$dockerRunning = $false
try {
    $dockerVersion = docker --version 2>&1
    Write-Host "[+] Docker CLI encontrado: $dockerVersion"
    
    # Verificar se o daemon esta rodando
    $dockerInfo = docker ps 2>&1
    $dockerRunning = $true
    Write-Host "[+] Docker Daemon rodando com sucesso (Sandbox ativa)."
} catch {
    Write-Host "[!] Aviso: Docker nao esta em execucao ou nao esta instalado."
    Write-Host "[!] O sandbox local estara desabilitado ate que o Docker seja iniciado."
}

# 7. Verificar Ollama
try {
    $ollamaTest = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 2
    Write-Host "[+] Ollama local encontrado e ativo."
    
    # Tentar puxar modelo de embeddings se nao existir
    Write-Host "[*] Verificando modelo de embeddings nomic-embed-text..."
    $models = $ollamaTest.models.name
    if ($models -notcontains "nomic-embed-text") {
        Write-Host "[*] Puxando modelo nomic-embed-text no Ollama..."
        Invoke-RestMethod -Uri "http://localhost:11434/api/pull" -Method Post -Body (ConvertTo-Json @{ "model" = "nomic-embed-text" }) -ContentType "application/json" | Out-Null
        Write-Host "[+] Modelo nomic-embed-text carregado no Ollama."
    } else {
        Write-Host "[+] Modelo nomic-embed-text ja carregado."
    }
} catch {
    Write-Host "[!] Aviso: Ollama local nao esta rodando na porta 11434."
    Write-Host "[!] O sistema de busca semantica usara fallback por substrings locais."
}

Write-Host "[+] Instalacao concluida! Kabbalah pronto para uso fisico no Windows."
Write-Host "[*] Para iniciar a ponte MCP, rode: .venv\Scripts\python.exe kabbalah_mcp_bridge.py"

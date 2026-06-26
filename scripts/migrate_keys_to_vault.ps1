# Migrar chaves API para o cofre seguro
# Uso: powershell -ExecutionPolicy Bypass -File migrate_keys_to_vault.ps1

$ErrorActionPreference = "Stop"

# Caminhos
$envFile = "E:\projetos\kabbalah\.env"
$vaultPath = "D:\Users\charl\.secrets\keys.json"
$backupPath = "D:\Users\charl\.secrets\keys.json.backup"

# Forcar UTF-8 no console
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "[*] Iniciando migracao de chaves para o cofre..."

# Verificar se o .env existe
if (-not (Test-Path $envFile)) {
    Write-Host "[!] Arquivo .env nao encontrado: $envFile"
    exit 1
}

# Ler o .env
$envContent = Get-Content $envFile -Encoding UTF8
Write-Host "[+] Lido arquivo .env"

# Extrair chaves
$keys = @{}

foreach ($line in $envContent) {
    if ($line -match '^([A-Z_]+_API_KEY)=(.+)$') {
        $keyName = $matches[1]
        $keyValue = $matches[2].Trim()

        # Ignorar placeholders
        if ($keyValue -match 'YOUR_KEY_HERE|sk-ant-\.\.\.') {
            Write-Host "[*] Ignorando placeholder: $keyName"
            continue
        }

        $keys[$keyName] = $keyValue
        Write-Host "[+] Chave encontrada: $keyName"
    }
}

if ($keys.Count -eq 0) {
    Write-Host "[!] Nenhuma chave valida encontrada no .env"
    exit 1
}

# Carregar ou criar o cofre
if (Test-Path $vaultPath) {
    Write-Host "[*] Cofre existente encontrado, fazendo backup..."
    Copy-Item $vaultPath $backupPath -Force
    $vault = Get-Content $vaultPath -Encoding UTF8 | ConvertFrom-Json
} else {
    Write-Host "[*] Criando novo cofre..."
    $vault = @{}
}

# Adicionar chaves ao cofre
foreach ($keyName in $keys.Keys) {
    $vault | Add-Member -MemberType NoteProperty -Name $keyName -Value $keys[$keyName] -Force
    Write-Host "[+] Migrada: $keyName"
}

# Salvar o cofre
$vaultJson = $vault | ConvertTo-Json -Depth 10
$vaultJson | Out-File -FilePath $vaultPath -Encoding UTF8 -Force
Write-Host "[+] Cofre salvo em: $vaultPath"

# Criar novo .env com placeholders
$newEnvContent = @(
    "# Provider API Keys - NEVER commit this file!",
    "# Copy this to .env and fill in your actual keys",
    "",
    "# OpenAI",
    "OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE",
    "",
    "# Google Gemini",
    "GOOGLE_API_KEY=YOUR_KEY_HERE",
    "",
    "# Groq",
    "GROQ_API_KEY=gsk-YOUR_KEY_HERE",
    "",
    "# Together",
    "TOGETHER_API_KEY=YOUR_KEY_HERE",
    "",
    "# DeepSeek",
    "DEEPSEEK_API_KEY=sk-YOUR_KEY_HERE",
    "",
    "# Mistral",
    "MISTRAL_API_KEY=YOUR_KEY_HERE",
    "",
    "# Anthropic (for later)",
    "ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE",
    "",
    "# Ollama (local)",
    "OLLAMA_BASE_URL=http://localhost:11434"
) -join "`r`n"

$newEnvContent | Out-File -FilePath $envFile -Encoding UTF8 -Force
Write-Host "[+] Arquivo .env limpo (apenas placeholders)"

Write-Host ""
Write-Host "[+] Migracao concluida com sucesso!"
Write-Host "[*] Backup do cofre: $backupPath"
Write-Host "[*] Chaves migradas: $($keys.Count)"
Write-Host ""
Write-Host "[!] IMPORTANTE: As chaves foram removidas do .env"
Write-Host "[!] Atualize o codigo para ler do cofre em: $vaultPath"

"""
Secrets Vault - Leitura segura de credenciais do cofre local.
NUNCA hardcode chaves. Sempre leia do cofre.
"""
import json
import os
from pathlib import Path
from typing import Optional

# Forcar UTF-8 no Windows
if os.sys.platform.startswith('win'):
    try:
        os.sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

VAULT_PATH = Path(r"D:\Users\charl\.secrets\keys.json")


def load_vault() -> dict:
    """Carrega o cofre de segredos."""
    if not VAULT_PATH.exists():
        raise FileNotFoundError(
            f"Cofre nao encontrado: {VAULT_PATH}\n"
            "Execute o script migrate_keys_to_vault.ps1 primeiro."
        )
    
    # Usar utf-8-sig para lidar com BOM do PowerShell
    with open(VAULT_PATH, 'r', encoding='utf-8-sig') as f:
        return json.load(f)


def get_secret(key_name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Obtem um segredo do cofre.
    
    Args:
        key_name: Nome da chave (ex: 'OPENAI_API_KEY')
        default: Valor padrao se nao encontrado
    
    Returns:
        Valor do segredo ou default
    
    Example:
        >>> api_key = get_secret('OPENAI_API_KEY')
        >>> client = OpenAI(api_key=api_key)
    """
    vault = load_vault()
    return vault.get(key_name, default)


def get_api_key(provider: str) -> str:
    """
    Obtem a chave API de um provider.
    
    Args:
        provider: Nome do provider (ex: 'openai', 'google', 'groq')
    
    Returns:
        Chave API
    
    Raises:
        KeyError: Se a chave nao existir
    
    Example:
        >>> key = get_api_key('openai')
        >>> client = OpenAI(api_key=key)
    """
    # Mapeamento de providers para nomes de chaves
    key_mapping = {
        'openai': 'OPENAI_API_KEY',
        'google': 'GOOGLE_API_KEY',
        'gemini': 'GOOGLE_API_KEY',
        'groq': 'GROQ_API_KEY',
        'together': 'TOGETHER_API_KEY',
        'deepseek': 'DEEPSEEK_API_KEY',
        'mistral': 'MISTRAL_API_KEY',
        'anthropic': 'ANTHROPIC_API_KEY',
    }
    
    provider_lower = provider.lower()
    key_name = key_mapping.get(provider_lower)
    
    if not key_name:
        raise KeyError(f"Provider desconhecido: {provider}")
    
    value = get_secret(key_name)
    
    if not value:
        raise KeyError(f"Chave nao encontrada no cofre: {key_name}")
    
    return value


# WAHA specific (conforme GEMINI.md)
def get_waha_api_key() -> str:
    """Obtem a chave do WAHA do cofre."""
    return get_api_key('waha')


# WAHA ports mapping (conforme GEMINI.md)
WAHA_PORTS = {
    'charles_pessoal': 3000,
    'liliane_esposa': 3001,
    'marketing': 3002,
    'suporte': 3003,
    'sistema': 3004,
    'reserva': 3005,
}


def get_waha_url(account: str = 'charles_pessoal') -> str:
    """
    Obtem a URL do WAHA para uma conta especifica.
    
    Args:
        account: Nome da conta (charles_pessoal, liliane_esposa, marketing, suporte, sistema, reserva)
    
    Returns:
        URL completa com autenticacao
    """
    port = WAHA_PORTS.get(account.lower(), 3000)
    api_key = get_waha_api_key()
    return f"http://127.0.0.1:{port}"


if __name__ == "__main__":
    # Teste do modulo
    print("[*] Testando leitura do cofre...")
    
    try:
        vault = load_vault()
        print(f"[+] Cofre carregado: {len(vault)} chaves")
        
        for key in ['OPENAI_API_KEY', 'GOOGLE_API_KEY', 'GROQ_API_KEY']:
            value = get_secret(key)
            if value:
                print(f"[+] {key}: {value[:20]}...")
            else:
                print(f"[!] {key}: NAO ENCONTRADA")
        
    except FileNotFoundError as e:
        print(f"[!] {e}")
    except Exception as e:
        print(f"[!] Erro: {e}")

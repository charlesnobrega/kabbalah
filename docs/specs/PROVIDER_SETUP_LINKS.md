# Provider Setup Links - Get API Keys

**Date**: 2026-04-10
**Status**: Ready to Setup

---

## Priority 1: Core Providers (Start Here)

### 1. OpenAI
**Status**: Paid (but has free trial credits)
**Setup Time**: 5 minutes
**Cost**: $0.01-0.05 per test

**Links**:
- 🔗 **Main**: https://platform.openai.com/
- 🔗 **Sign Up**: https://platform.openai.com/signup
- 🔗 **API Keys**: https://platform.openai.com/account/api-keys
- 🔗 **Documentation**: https://platform.openai.com/docs/api-reference
- 🔗 **Pricing**: https://openai.com/pricing
- 🔗 **Models**: https://platform.openai.com/docs/models

**Steps**:
1. Go to https://platform.openai.com/signup
2. Create account (or login if you have one)
3. Go to https://platform.openai.com/account/api-keys
4. Click "Create new secret key"
5. Copy the key (you'll only see it once!)
6. Save it as environment variable: `export OPENAI_API_KEY=sk-...`

**Models Available**:
- gpt-4 (most powerful)
- gpt-4-turbo (faster, cheaper)
- gpt-3.5-turbo (cheapest)

**Python SDK**:
```bash
pip install openai
```

---

### 2. Anthropic (Claude)
**Status**: Paid (but has free trial credits)
**Setup Time**: 5 minutes
**Cost**: $0.01-0.03 per test

**Links**:
- 🔗 **Main**: https://www.anthropic.com/
- 🔗 **Console**: https://console.anthropic.com/
- 🔗 **Sign Up**: https://console.anthropic.com/login
- 🔗 **API Keys**: https://console.anthropic.com/account/keys
- 🔗 **Documentation**: https://docs.anthropic.com/
- 🔗 **Pricing**: https://www.anthropic.com/pricing
- 🔗 **Models**: https://docs.anthropic.com/claude/reference/getting-started-with-the-api

**Steps**:
1. Go to https://console.anthropic.com/login
2. Create account (or login if you have one)
3. Go to https://console.anthropic.com/account/keys
4. Click "Create Key"
5. Copy the key
6. Save it as environment variable: `export ANTHROPIC_API_KEY=sk-ant-...`

**Models Available**:
- claude-3-opus-20240229 (most powerful)
- claude-3-sonnet-20240229 (balanced)
- claude-3-haiku-20240307 (fastest, cheapest)

**Python SDK**:
```bash
pip install anthropic
```

---

### 3. Ollama (Local - FREE!)
**Status**: Free (runs locally)
**Setup Time**: 10 minutes
**Cost**: $0 (runs on your machine)

**Links**:
- 🔗 **Main**: https://ollama.ai/
- 🔗 **Download**: https://ollama.ai/download
- 🔗 **Models**: https://ollama.ai/library
- 🔗 **Documentation**: https://github.com/ollama/ollama
- 🔗 **API**: https://github.com/ollama/ollama/blob/main/docs/api.md

**Steps**:
1. Go to https://ollama.ai/download
2. Download for your OS (Windows, Mac, Linux)
3. Install and run
4. Open terminal and run: `ollama pull llama2`
5. Run: `ollama serve` (starts on localhost:11434)
6. Set environment variable: `export OLLAMA_BASE_URL=http://localhost:11434`

**Models Available** (pick one):
- llama2 (7B, ~4GB)
- mistral (7B, ~4GB)
- neural-chat (7B, ~4GB)
- dolphin-mixtral (26B, ~16GB)

**Python SDK**:
```bash
pip install requests  # Ollama uses HTTP API
```

---

## Priority 2: Important Providers (After Priority 1)

### 4. Google Gemini
**Status**: Paid (but has free tier!)
**Setup Time**: 5 minutes
**Cost**: Free tier available, then $0.001-0.01 per test

**Links**:
- 🔗 **Main**: https://ai.google.dev/
- 🔗 **Get API Key**: https://ai.google.dev/tutorials/setup
- 🔗 **API Keys**: https://aistudio.google.com/app/apikey
- 🔗 **Documentation**: https://ai.google.dev/docs
- 🔗 **Pricing**: https://ai.google.dev/pricing
- 🔗 **Models**: https://ai.google.dev/models

**Steps**:
1. Go to https://aistudio.google.com/app/apikey
2. Click "Create API key"
3. Select or create a Google Cloud project
4. Copy the key
5. Save it as environment variable: `export GOOGLE_API_KEY=...`

**Models Available**:
- gemini-pro (text)
- gemini-pro-vision (text + images)
- gemini-1.5-pro (latest)
- gemini-1.5-flash (fastest)

**Python SDK**:
```bash
pip install google-generativeai
```

---

### 5. Groq (FREE!)
**Status**: Free tier available
**Setup Time**: 5 minutes
**Cost**: Free (with rate limits)

**Links**:
- 🔗 **Main**: https://groq.com/
- 🔗 **Console**: https://console.groq.com/
- 🔗 **Sign Up**: https://console.groq.com/login
- 🔗 **API Keys**: https://console.groq.com/keys
- 🔗 **Documentation**: https://console.groq.com/docs
- 🔗 **Pricing**: https://groq.com/pricing
- 🔗 **Models**: https://console.groq.com/docs/models

**Steps**:
1. Go to https://console.groq.com/login
2. Create account (or login)
3. Go to https://console.groq.com/keys
4. Click "Create API Key"
5. Copy the key
6. Save it as environment variable: `export GROQ_API_KEY=gsk-...`

**Models Available** (all free):
- mixtral-8x7b-32768 (fast, powerful)
- llama2-70b-4096 (powerful)
- gemma-7b-it (fast, lightweight)

**Python SDK**:
```bash
pip install groq
```

---

### 6. Together AI (FREE!)
**Status**: Free tier available
**Setup Time**: 5 minutes
**Cost**: Free (with rate limits)

**Links**:
- 🔗 **Main**: https://www.together.ai/
- 🔗 **Dashboard**: https://api.together.xyz/
- 🔗 **Sign Up**: https://api.together.xyz/signin
- 🔗 **API Keys**: https://api.together.xyz/settings/api-keys
- 🔗 **Documentation**: https://docs.together.ai/
- 🔗 **Pricing**: https://www.together.ai/pricing
- 🔗 **Models**: https://docs.together.ai/reference/models

**Steps**:
1. Go to https://api.together.xyz/signin
2. Create account (or login)
3. Go to https://api.together.xyz/settings/api-keys
4. Click "Generate API Token"
5. Copy the key
6. Save it as environment variable: `export TOGETHER_API_KEY=...`

**Models Available** (all free):
- meta-llama/Llama-2-70b-chat-hf
- mistralai/Mistral-7B-Instruct-v0.1
- NousResearch/Nous-Hermes-2-Mixtral-8x7B-DPO

**Python SDK**:
```bash
pip install together
```

---

### 7. DeepSeek
**Status**: Paid (but very cheap)
**Setup Time**: 5 minutes
**Cost**: $0.001-0.01 per test

**Links**:
- 🔗 **Main**: https://www.deepseek.com/
- 🔗 **Platform**: https://platform.deepseek.com/
- 🔗 **Sign Up**: https://platform.deepseek.com/sign_up
- 🔗 **API Keys**: https://platform.deepseek.com/api_keys
- 🔗 **Documentation**: https://platform.deepseek.com/docs
- 🔗 **Pricing**: https://platform.deepseek.com/pricing
- 🔗 **Models**: https://platform.deepseek.com/docs/models

**Steps**:
1. Go to https://platform.deepseek.com/sign_up
2. Create account (or login)
3. Go to https://platform.deepseek.com/api_keys
4. Click "Create API Key"
5. Copy the key
6. Save it as environment variable: `export DEEPSEEK_API_KEY=...`

**Models Available**:
- deepseek-chat (main model)
- deepseek-coder (for code)

**Python SDK**:
```bash
pip install openai  # DeepSeek uses OpenAI-compatible API
```

---

### 8. Mistral AI
**Status**: Paid (but has free tier)
**Setup Time**: 5 minutes
**Cost**: Free tier available, then $0.001-0.01 per test

**Links**:
- 🔗 **Main**: https://mistral.ai/
- 🔗 **Console**: https://console.mistral.ai/
- 🔗 **Sign Up**: https://console.mistral.ai/login
- 🔗 **API Keys**: https://console.mistral.ai/api-keys/
- 🔗 **Documentation**: https://docs.mistral.ai/
- 🔗 **Pricing**: https://mistral.ai/pricing/
- 🔗 **Models**: https://docs.mistral.ai/capabilities/function_calling/

**Steps**:
1. Go to https://console.mistral.ai/login
2. Create account (or login)
3. Go to https://console.mistral.ai/api-keys/
4. Click "Create API Key"
5. Copy the key
6. Save it as environment variable: `export MISTRAL_API_KEY=...`

**Models Available**:
- mistral-small (fast, cheap)
- mistral-medium (balanced)
- mistral-large (powerful)

**Python SDK**:
```bash
pip install mistralai
```

---

## Optional Priority 3 Providers

### 9. Replicate
**Links**: https://replicate.com/
**API Keys**: https://replicate.com/account/api-tokens
**Docs**: https://replicate.com/docs

### 10. HuggingFace
**Links**: https://huggingface.co/
**API Keys**: https://huggingface.co/settings/tokens
**Docs**: https://huggingface.co/docs

### 11. Azure OpenAI
**Links**: https://azure.microsoft.com/en-us/products/ai-services/openai-service/
**Docs**: https://learn.microsoft.com/en-us/azure/ai-services/openai/

### 12. LM Studio
**Links**: https://lmstudio.ai/
**Download**: https://lmstudio.ai/download
**Docs**: https://github.com/lmstudio-ai/lmstudio.ai

### 13. vLLM
**Links**: https://www.vllm.ai/
**Docs**: https://docs.vllm.ai/
**GitHub**: https://github.com/vllm-project/vllm

---

## Quick Setup Summary

### For Testing (Recommended Order):

**Step 1: Get Free/Cheap APIs** (15 minutes)
```bash
# 1. Ollama (FREE, local)
# Download from https://ollama.ai/download
# Run: ollama pull llama2
# Run: ollama serve

# 2. Groq (FREE tier)
# Go to https://console.groq.com/keys
# Create API key

# 3. Together (FREE tier)
# Go to https://api.together.xyz/settings/api-keys
# Create API key
```

**Step 2: Get Paid APIs** (10 minutes)
```bash
# 1. OpenAI (has free trial credits)
# Go to https://platform.openai.com/account/api-keys
# Create API key

# 2. Anthropic (has free trial credits)
# Go to https://console.anthropic.com/account/keys
# Create API key

# 3. Google Gemini (has free tier)
# Go to https://aistudio.google.com/app/apikey
# Create API key
```

**Step 3: Set Environment Variables**
```bash
# Create .env file
cat > .env << EOF
# Free/Cheap
OLLAMA_BASE_URL=http://localhost:11434
GROQ_API_KEY=gsk-...
TOGETHER_API_KEY=...

# Paid (but have free credits)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# Optional
DEEPSEEK_API_KEY=...
MISTRAL_API_KEY=...
EOF

# Load environment variables
source .env
```

---

## Testing Each Provider

### Test OpenAI
```bash
export OPENAI_API_KEY=sk-...
python -c "
from openai import OpenAI
client = OpenAI()
response = client.chat.completions.create(
    model='gpt-3.5-turbo',
    messages=[{'role': 'user', 'content': 'Say hello'}],
    max_tokens=10
)
print(response.choices[0].message.content)
"
```

### Test Anthropic
```bash
export ANTHROPIC_API_KEY=sk-ant-...
python -c "
from anthropic import Anthropic
client = Anthropic()
response = client.messages.create(
    model='claude-3-haiku-20240307',
    max_tokens=10,
    messages=[{'role': 'user', 'content': 'Say hello'}]
)
print(response.content[0].text)
"
```

### Test Ollama
```bash
# Make sure Ollama is running: ollama serve
python -c "
import requests
response = requests.post(
    'http://localhost:11434/api/generate',
    json={
        'model': 'llama2',
        'prompt': 'Say hello',
        'stream': False
    }
)
print(response.json()['response'])
"
```

### Test Groq
```bash
export GROQ_API_KEY=gsk-...
python -c "
from groq import Groq
client = Groq()
response = client.chat.completions.create(
    model='mixtral-8x7b-32768',
    messages=[{'role': 'user', 'content': 'Say hello'}],
    max_tokens=10
)
print(response.choices[0].message.content)
"
```

### Test Together
```bash
export TOGETHER_API_KEY=...
python -c "
import together
together.api_key = os.getenv('TOGETHER_API_KEY')
response = together.Complete.create(
    prompt='Say hello',
    model='meta-llama/Llama-2-70b-chat-hf',
    max_tokens=10
)
print(response['output']['choices'][0]['text'])
"
```

### Test Google Gemini
```bash
export GOOGLE_API_KEY=...
python -c "
import google.generativeai as genai
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
model = genai.GenerativeModel('gemini-pro')
response = model.generate_content('Say hello')
print(response.text)
"
```

### Test DeepSeek
```bash
export DEEPSEEK_API_KEY=...
python -c "
from openai import OpenAI
client = OpenAI(
    api_key=os.getenv('DEEPSEEK_API_KEY'),
    base_url='https://api.deepseek.com'
)
response = client.chat.completions.create(
    model='deepseek-chat',
    messages=[{'role': 'user', 'content': 'Say hello'}],
    max_tokens=10
)
print(response.choices[0].message.content)
"
```

### Test Mistral
```bash
export MISTRAL_API_KEY=...
python -c "
from mistralai.client import MistralClient
client = MistralClient(api_key=os.getenv('MISTRAL_API_KEY'))
response = client.chat(
    model='mistral-small',
    messages=[{'role': 'user', 'content': 'Say hello'}]
)
print(response.choices[0].message.content)
"
```

---

## Recommended Order to Get APIs

### Week 1 (Priority 1 - Start Here)
1. **Ollama** (FREE, local) - 10 min
2. **OpenAI** (Paid, has free credits) - 5 min
3. **Anthropic** (Paid, has free credits) - 5 min

### Week 2 (Priority 2 - Add These)
4. **Google Gemini** (Free tier) - 5 min
5. **Groq** (FREE tier) - 5 min
6. **Together** (FREE tier) - 5 min
7. **DeepSeek** (Cheap) - 5 min
8. **Mistral** (Free tier) - 5 min

### Week 3+ (Priority 3 - Optional)
9. Replicate
10. HuggingFace
11. Azure OpenAI
12. LM Studio
13. vLLM

---

## Total Setup Time

- **Priority 1**: 15 minutes
- **Priority 2**: 25 minutes
- **Priority 3**: 30 minutes
- **Total**: ~70 minutes

---

## Cost Estimate

| Provider | Cost | Notes |
|----------|------|-------|
| Ollama | FREE | Local, no API key |
| Groq | FREE | Free tier |
| Together | FREE | Free tier |
| OpenAI | $5-20 | Free trial credits |
| Anthropic | $5-20 | Free trial credits |
| Google Gemini | FREE | Free tier |
| DeepSeek | $1-5 | Very cheap |
| Mistral | FREE | Free tier |
| **Total** | **~$15-50** | **For testing** |

---

## Next Steps

1. **Start with Priority 1** (Ollama, OpenAI, Anthropic)
2. **Get API keys** using links above
3. **Test each provider** using test scripts above
4. **Save API keys** in .env file
5. **Move to Priority 2** when ready

---

**Ready to start? Pick one provider and get the API key!**


# API Key Security Guide

**CRITICAL**: Never share API keys in plain text!

---

## What You Did Wrong

You shared API keys in plain text in the chat. This is a **CRITICAL SECURITY RISK**.

**Anyone with these keys can:**
- Use your API quota
- Incur charges on your account
- Access your data
- Impersonate you

---

## What You Must Do NOW

### Step 1: Revoke All Exposed Keys

**OpenAI**:
1. Go to https://platform.openai.com/account/api-keys
2. Find the key you shared
3. Click the trash icon to delete it
4. Create a NEW key

**Google Gemini**:
1. Go to https://aistudio.google.com/app/apikey
2. Delete the exposed key
3. Create a NEW key

**Groq**:
1. Go to https://console.groq.com/keys
2. Delete the exposed key
3. Create a NEW key

**Together**:
1. Go to https://api.together.xyz/settings/api-keys
2. Delete the exposed key
3. Create a NEW key

**DeepSeek**:
1. Go to https://platform.deepseek.com/api_keys
2. Delete the exposed key
3. Create a NEW key

**Mistral**:
1. Go to https://console.mistral.ai/api-keys/
2. Delete the exposed key
3. Create a NEW key

### Step 2: Create New Keys

After deleting old keys, create new ones for each provider.

### Step 3: Update .env File

Create a `.env` file in your project root:

```bash
# Copy .env.example to .env
cp .env.example .env

# Edit .env with your NEW API keys
nano .env
```

### Step 4: Add to .gitignore

Make sure `.env` is in `.gitignore`:

```bash
# Add to .gitignore
echo ".env" >> .gitignore
echo ".env.local" >> .gitignore
echo ".env.*.local" >> .gitignore
```

---

## How to Use API Keys Safely

### ✅ DO THIS:

1. **Store in .env file** (never commit to git)
```bash
# .env
OPENAI_API_KEY=sk-proj-...
GOOGLE_API_KEY=...
```

2. **Load from environment**
```python
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
```

3. **Use in code**
```python
from openai import OpenAI
client = OpenAI(api_key=api_key)
```

### ❌ DON'T DO THIS:

1. **Never hardcode keys**
```python
# ❌ WRONG
api_key = "REDACTED_OPENAI_API_KEY"
```

2. **Never share in chat/email/Slack**
```
# ❌ WRONG
"Here's my API key: sk-proj-..."
```

3. **Never commit to git**
```bash
# ❌ WRONG
git add .env
git commit -m "Add API keys"
git push
```

4. **Never log API keys**
```python
# ❌ WRONG
print(f"Using API key: {api_key}")
logger.info(f"API key: {api_key}")
```

---

## .env File Setup

### Create .env File

```bash
# Copy the example
cp .env.example .env

# Edit with your NEW API keys
nano .env
```

### .env Content

```
# OpenAI
OPENAI_API_KEY=sk-proj-YOUR_NEW_KEY_HERE

# Google Gemini
GOOGLE_API_KEY=YOUR_NEW_KEY_HERE

# Groq
GROQ_API_KEY=gsk-YOUR_NEW_KEY_HERE

# Together
TOGETHER_API_KEY=YOUR_NEW_KEY_HERE

# DeepSeek
DEEPSEEK_API_KEY=sk-YOUR_NEW_KEY_HERE

# Mistral
MISTRAL_API_KEY=YOUR_NEW_KEY_HERE

# Anthropic (for later)
ANTHROPIC_API_KEY=sk-ant-YOUR_NEW_KEY_HERE
```

### .gitignore Setup

```bash
# Make sure .env is ignored
cat >> .gitignore << EOF

# Environment variables
.env
.env.local
.env.*.local
.env.prod
.env.test

# API Keys
*.key
*.pem
secrets/
EOF
```

---

## Python Code to Load Keys Safely

### Using python-dotenv

```bash
pip install python-dotenv
```

```python
import os
from dotenv import load_dotenv

# Load from .env file
load_dotenv()

# Get API keys
openai_key = os.getenv("OPENAI_API_KEY")
google_key = os.getenv("GOOGLE_API_KEY")
groq_key = os.getenv("GROQ_API_KEY")

# Check if keys are loaded
if not openai_key:
    raise ValueError("OPENAI_API_KEY not found in .env")

# Use the key
from openai import OpenAI
client = OpenAI(api_key=openai_key)
```

### Using environment variables directly

```bash
# Set in terminal
export OPENAI_API_KEY=sk-proj-...
export GOOGLE_API_KEY=...

# Or in .env and load with:
source .env
```

---

## Testing Safely

### Use test_providers.py

```bash
# Install dependencies
pip install python-dotenv openai google-generativeai groq together mistralai

# Create .env with your NEW keys
cp .env.example .env
nano .env

# Run tests
python test_providers.py
```

### Output Example

```
==================================================
LLM Provider Test Suite
==================================================

==================================================
Testing OpenAI...
==================================================
✅ OpenAI working!
Response: Hello

==================================================
Testing Google Gemini...
==================================================
✅ Google Gemini working!
Response: Hi

...

==================================================
SUMMARY
==================================================
OpenAI: ✅ PASS
Google Gemini: ✅ PASS
Groq: ✅ PASS
Together: ✅ PASS
DeepSeek: ✅ PASS
Mistral: ✅ PASS

Total: 6/6 providers working
```

---

## Checklist

- [ ] Revoked all exposed API keys
- [ ] Created NEW API keys for each provider
- [ ] Created .env file with NEW keys
- [ ] Added .env to .gitignore
- [ ] Tested with test_providers.py
- [ ] All providers working
- [ ] Never share API keys again

---

## If You Accidentally Exposed Keys

1. **Immediately revoke the key** (delete it from provider dashboard)
2. **Create a new key**
3. **Update .env file**
4. **Run tests to verify new key works**
5. **Never share keys again**

---

## Best Practices

1. **Use .env files** for local development
2. **Use environment variables** in production
3. **Use secrets management** (AWS Secrets Manager, HashiCorp Vault, etc.) for production
4. **Rotate keys regularly** (monthly or quarterly)
5. **Use different keys** for different environments (dev, test, prod)
6. **Monitor API usage** for suspicious activity
7. **Set API key permissions** to minimum required
8. **Never log API keys** in any logs or error messages

---

## Resources

- [OpenAI API Key Security](https://platform.openai.com/docs/guides/production-best-practices/api-keys)
- [Google Cloud Security Best Practices](https://cloud.google.com/docs/authentication/best-practices-applications)
- [OWASP API Security](https://owasp.org/www-project-api-security/)

---

**Remember: API keys are like passwords. Treat them with the same security as your bank password.**


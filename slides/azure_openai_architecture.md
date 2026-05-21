# Azure OpenAI Architecture — Training Reference

## 1. What is a Provider?

A **provider** is the cloud platform or company that **hosts and serves** an AI model for you.

| Provider | What they offer |
|----------|----------------|
| **OpenAI** (direct) | Models hosted on OpenAI's own infrastructure. You get an API key from `platform.openai.com`. |
| **Azure OpenAI** | The *same* OpenAI models (GPT-4o, GPT-4, etc.) but hosted inside **Microsoft Azure**. You manage them through the Azure portal. |
| **Other providers** | Anthropic (Claude), Google (Gemini), AWS Bedrock, Hugging Face, etc. |

### Key distinction

> The **model** (e.g. GPT-4o) is the same regardless of provider.  
> The **provider** determines: where your data goes, what compliance/security controls you get, how billing works, and what API endpoint you call.

### Why Azure as a provider?

- **Data residency**: your prompts and completions stay within your Azure tenant/region.
- **Enterprise security**: VNET integration, private endpoints, managed identity, RBAC.
- **Compliance**: SOC 2, HIPAA, GDPR controls inherited from Azure.
- **Billing**: consumed through your existing Azure subscription / EA agreement.
- **No data used for training**: Microsoft guarantees prompts are NOT used to retrain models.

---

## 2. What is an API?

An **API** (Application Programming Interface) is the **contract** that defines how your code talks to the model.

### The OpenAI REST API

Both OpenAI-direct and Azure OpenAI expose a **REST API** that follows the same schema:

```
POST /chat/completions
{
  "model": "gpt-4o",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ]
}
```

The response always comes back in the same JSON shape:

```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "Hi there! How can I help you?"
      }
    }
  ],
  "usage": { "prompt_tokens": 20, "completion_tokens": 9 }
}
```

### Difference in URL structure

| Provider | Endpoint URL |
|----------|-------------|
| OpenAI direct | `https://api.openai.com/v1/chat/completions` |
| Azure OpenAI | `https://{your-resource}.openai.azure.com/openai/deployments/{deployment-name}/chat/completions?api-version=2024-12-01-preview` |

Notice that Azure:
1. Uses **your own resource name** in the URL (not a shared endpoint).
2. Requires a **deployment name** (not just a model name).
3. Requires an **api-version** query parameter.

### Authentication differences

| Provider | Auth method |
|----------|-------------|
| OpenAI direct | Bearer token: `Authorization: Bearer sk-...` |
| Azure OpenAI | API key header: `api-key: <your-key>` **or** Azure AD / Managed Identity token |

---

## 3. What is a Deployed Endpoint in Azure?

This is the crucial concept that confuses people coming from OpenAI-direct.

### The Azure OpenAI resource hierarchy

```
Azure Subscription
  └── Resource Group (e.g. "rg-ai-training")
        └── Azure OpenAI Resource (e.g. "my-openai-service")
              └── Deployment (e.g. "gpt4o-deploy")
                    └── Model: gpt-4o (version 2024-08-06)
```

### Step by step

1. **Azure Subscription** — your billing boundary.
2. **Resource Group** — a logical container to group related resources.
3. **Azure OpenAI Resource** — creates your **unique endpoint URL** (`https://my-openai-service.openai.azure.com`). This is where your API key lives.
4. **Deployment** — you explicitly **deploy** a specific model version into this resource. The deployment has a name you choose (e.g. `gpt4o-deploy`). This is what you reference in API calls.

### Why deployments?

- You can have **multiple deployments** of different models (or even the same model with different configurations) under one resource.
- Each deployment can have its own **rate limits** (TPM — tokens per minute).
- You can **swap model versions** behind the same deployment name (blue/green upgrades).
- You control **which model version** you're on — no surprise upgrades.

### Deployment ≠ Model name

| Concept | Example | What it is |
|---------|---------|------------|
| Model | `gpt-4o` | The neural network architecture + weights |
| Deployment | `gpt4o-deploy` | Your named instance of that model, living at your endpoint |

You might name your deployment `gpt4o-deploy`, `production-model`, or anything. The actual API call uses the **deployment name**, not the model name.

---

## 4. Visual Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    YOUR APPLICATION                       │
│  (Python / LangChain / LangGraph / notebook)            │
└────────────────────────┬────────────────────────────────┘
                         │ HTTPS request
                         │ Header: api-key: xxxxx
                         ▼
┌─────────────────────────────────────────────────────────┐
│           AZURE OPENAI ENDPOINT                          │
│  https://{resource}.openai.azure.com                    │
│                                                          │
│  ┌─────────────────┐  ┌─────────────────┐              │
│  │ Deployment A    │  │ Deployment B    │              │
│  │ "gpt4o-deploy"  │  │ "gpt4-mini"    │              │
│  │ Model: gpt-4o   │  │ Model: gpt-4o-m│              │
│  │ TPM: 80K        │  │ TPM: 120K       │              │
│  └─────────────────┘  └─────────────────┘              │
└─────────────────────────────────────────────────────────┘
```

---

## 5. How This Repo Connects to Azure OpenAI

### The Config class (`config.py`)

```python
class Config:
    model = "gpt-4o"
    endpoint_uri = os.getenv("AZURE_OPENAI_ENDPOINT")       # ← the resource URL
    resource_group = os.getenv("RG_NAME")                   # ← Azure resource group
    api_key = os.getenv("AZURE_OPENAI_API_KEY")             # ← authentication
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")  # ← which deployment

    def get_llm(self):
        llm = AzureChatOpenAI(
            azure_endpoint=self.endpoint_uri,
            api_key=SecretStr(self.api_key),
            azure_deployment=self.deployment_name,
            api_version="2024-12-01-preview",
        )
        return llm
```

### Mapping to concepts

| Code | Concept | Example value |
|------|---------|---------------|
| `AZURE_OPENAI_ENDPOINT` | Your resource's base URL | `https://my-openai-service.openai.azure.com` |
| `AZURE_OPENAI_API_KEY` | Authentication to that resource | `abc123...` |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | The deployment you want to call | `gpt4o-deploy` |
| `api_version` | Which version of the Azure REST API to use | `2024-12-01-preview` |
| `AzureChatOpenAI` | LangChain wrapper class for Azure (vs `ChatOpenAI` for OpenAI-direct) | — |

### What LangChain does under the hood

When you call `llm.invoke(messages)`, LangChain:

1. Takes your messages list.
2. Serializes them into the OpenAI chat completions JSON format.
3. Sends a POST to: `{azure_endpoint}/openai/deployments/{deployment_name}/chat/completions?api-version=2024-12-01-preview`
4. Attaches the `api-key` header.
5. Parses the JSON response back into a LangChain `AIMessage` object.

---

## 6. OpenAI Direct vs Azure OpenAI — Side-by-Side

| Aspect | OpenAI Direct | Azure OpenAI |
|--------|--------------|--------------|
| **Endpoint** | `api.openai.com` | `{your-resource}.openai.azure.com` |
| **Auth** | Bearer token (`sk-...`) | API key header or Azure AD |
| **Model selection** | Pass `model` param in body | Pass deployment name in URL path |
| **Rate limits** | Account-level, set by OpenAI | You configure per-deployment TPM |
| **Data privacy** | OpenAI's policy applies | Your Azure tenant controls data |
| **Model updates** | Automatic (unless pinned) | You control when to upgrade |
| **LangChain class** | `ChatOpenAI` | `AzureChatOpenAI` |
| **Billing** | OpenAI credit card / billing | Azure subscription |
| **Network security** | Public internet only | Private endpoints, VNET possible |

---

## 7. The API Version Parameter

Azure OpenAI uses **dated API versions** (e.g. `2024-12-01-preview`).

- **GA versions** (e.g. `2024-10-21`): stable, production-ready.
- **Preview versions** (e.g. `2024-12-01-preview`): access to newest features (structured outputs, assistants v2, etc.) but may change.

This repo uses `2024-12-01-preview` to access the latest features like tool calling with structured outputs.

---

## 8. Environment Variables Required

For this repo to work, you need these in a `.env` file or exported:

```bash
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment-name
RG_NAME=your-resource-group-name
```

---

## 9. Key Talking Points for the Training

1. **"We're using GPT-4o, but through Azure"** — same model, enterprise wrapper.
2. **"The deployment is OUR instance"** — we control rate limits, versioning, and access.
3. **"LangChain abstracts the provider"** — switching from Azure to OpenAI-direct would only require changing the Config class (swap `AzureChatOpenAI` → `ChatOpenAI`). The rest of the agent code stays identical.
4. **"The API contract is the same"** — messages in, message out. The chat completions format is universal across providers.
5. **"Environment variables keep secrets out of code"** — never hardcode keys; load from `.env` or Azure Key Vault.

---

## 10. Common Misconceptions to Address

| Misconception | Reality |
|---------------|---------|
| "Azure OpenAI is a different model" | Same weights, same architecture. Just different hosting. |
| "I need to use the OpenAI Python SDK for Azure" | You *can*, but LangChain's `AzureChatOpenAI` handles it more cleanly for agent workflows. |
| "Deployment name = model name" | No! Deployment name is arbitrary. You could call it `banana` and it still runs GPT-4o. |
| "API version doesn't matter" | It does — features like tool calling and structured outputs require specific versions. |
| "The API key is tied to a model" | No — the key authenticates to the **resource**. One key can access all deployments under that resource. |

# AI Engineering Training

Hands-on training covering agentic AI design patterns using the OpenAI API (Azure-hosted).

The core patterns (reflection, tool use, planning) are implemented from scratch to expose the internal workings of agentic systems. A supplementary notebook showcases tool use within LangGraph. You will then apply what you've learned by building a multi-agent travel planner in a guided exercise notebook.

## Patterns Covered

| # | Pattern | Notebook | Format |
|---|---------|----------|--------|
| 1 | Reflection | `notebooks/patterns.ipynb` | Pre-built |
| 2 | Tool Use | `notebooks/patterns.ipynb` | Pre-built |
| 3 | Planning | `notebooks/patterns.ipynb` | Pre-built |
| 4 | Tool Use (LangGraph) | `notebooks/tool_and_memory.ipynb` | Pre-built |
| 5 | Multi-Agent | `notebooks/multi_agent_travel_planner-exercise.ipynb` | Guided exercise |

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Access to an Azure OpenAI resource will be shared during the training
- Git

## Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd AI_training
```

### 2. Install dependencies

```bash
uv sync
```

This creates a virtual environment and installs all required packages (OpenAI SDK, LangChain, ChromaDB, Gradio, etc.) as defined in `pyproject.toml`.

### 4. Set environment variables

Create a `.env` file in the project root (or export the variables directly):

```
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
AZURE_OPENAI_API_KEY=<your-key>
AZURE_OPENAI_DEPLOYMENT_NAME=<your-deployment-name>
```

These are read by `config.py` to configure the LLM client.

### 4. Install Playwright browsers (required for the multi-agent notebook)

```bash
uv run playwright install
```

### 5. Open the notebooks

Open any notebook in `notebooks/` with VS Code or Jupyter and follow the exercises in order.

## Project Structure

```
config.py          — LLM client configuration (Azure OpenAI)
prompts.py         — System prompts for all agents
tools.py           — Tool functions used in the tool-use pattern
notebooks/         — Training notebooks (start here)
data/              — Data files for exercises
```

## Troubleshooting

- **`ModuleNotFoundError`** — Make sure you ran `uv sync` and the virtual environment is active.
- **`API key not found`** — Verify your environment variables are set. If using a `.env` file, ensure your notebook loads it (e.g. `from dotenv import load_dotenv; load_dotenv()`).
- **Playwright errors** — Run `playwright install` to download the required browsers.
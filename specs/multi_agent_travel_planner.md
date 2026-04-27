# Multi-Agent Travel Planner — Technical Specification

## 1. Overview

Build a **multi-agent system** that acts as a virtual travel agency. A user interacts with a single chat interface; behind the scenes, an **orchestrator agent** delegates work to a team of **specialized agents**, each responsible for a distinct part of the travel planning process.

This project is designed as a learning demo. Each implementation step introduces a core concept of multi-agent architectures so you can understand *why* the pattern exists, not just *how* to wire it up.

### What You Will Learn

| Concept | Where It Appears |
|---|---|
| **Agent** — an LLM combined with tools and a system prompt that gives it a role | Every agent you build |
| **Orchestrator pattern** — one agent routes work to others | `OrchestratorAgent` |
| **Shared state** — a typed data structure that flows through the graph | `TravelPlannerState` |
| **Tool use** — letting an LLM call deterministic functions | All specialist agents |
| **Handoffs / delegation** — one agent deciding which sub-agent to invoke | Orchestrator → specialists |
| **Human-in-the-loop** — pausing the graph for user confirmation | Budget confirmation step |
| **Structured output** — forcing the LLM to return validated data | Itinerary & budget responses |
| **Graph-based control flow** — modelling the workflow as a state graph | LangGraph `StateGraph` |

---

## 2. Architecture

```
User
  │
  ▼
┌────────────────────┐
│  Orchestrator Agent │  ← talks to user, delegates tasks
└────────┬───────────┘
         │ handoff
   ┌─────┼──────────┐
   ▼     ▼          ▼
┌──────┐ ┌────────┐ ┌──────────┐
│Itinerary│ │Activities│ │  Budget  │
│ Agent   │ │  Agent   │ │  Agent   │
└──┬───┘ └──┬─────┘ └──┬───────┘
   │        │           │
   ▼        ▼           ▼
 Tools    Tools       Tools
```

### Agent Responsibilities

| Agent | Role | Example Tools |
|---|---|---|
| **Orchestrator** | Greets the user, gathers travel requirements (destination, dates, budget, interests), decides which specialist to invoke next, synthesizes the final plan. | *none — delegates only* |
| **Itinerary Agent** | Builds a day-by-day travel itinerary including transport and accommodation suggestions. | `search_flights`, `search_hotels` |
| **Activities Agent** | Suggests activities, restaurants, and experiences matching the user's interests and the itinerary dates. | `search_activities`, `search_restaurants` |
| **Budget Agent** | Estimates costs for each part of the trip, tracks the running total, and flags if the plan exceeds the user's budget. | `calculate_budget`, `convert_currency` |

---

## 3. Tech Stack

| Component | Library / Service |
|---|---|
| LLM | Azure OpenAI (`gpt-4o`) via `langchain-openai` |
| Agent framework | LangGraph (`StateGraph`) |
| Tool definitions | `langchain-core` `@tool` decorator |
| Configuration | `config.py` (`Config.get_llm()`) |
| Notebook runtime | Jupyter (VS Code) |

All dependencies are already declared in `pyproject.toml`.

---

## 4. State Definition

The shared state is the single source of truth that every agent reads from and writes to. Define it as a `TypedDict` so LangGraph can track it through the graph.

```python
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class TravelPlannerState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]   # full conversation history
    destination: str                                        # e.g. "Tokyo, Japan"
    travel_dates: dict                                      # {"start": "2026-06-01", "end": "2026-06-10"}
    budget: float                                           # user's max budget in USD
    interests: list[str]                                    # e.g. ["food", "hiking", "museums"]
    itinerary: list[dict]                                   # day-by-day plan built by Itinerary Agent
    activities: list[dict]                                   # suggested activities from Activities Agent
    budget_breakdown: dict                                  # cost estimates from Budget Agent
    current_agent: str                                      # tracks which specialist is active
```

### Why `add_messages`?

The `Annotated[..., add_messages]` reducer tells LangGraph to **append** new messages instead of replacing the list. This preserves the full conversation history as control passes between agents.

---

## 5. Tools

Tools are plain Python functions decorated with `@tool`. They give agents access to deterministic logic the LLM cannot perform on its own (search, math, external APIs).

For this demo, tools return **mock data** so the system works without real APIs. This keeps the focus on the multi-agent architecture.

### 5.1 Itinerary Tools

```python
@tool
def search_flights(origin: str, destination: str, date: str) -> list[dict]:
    """Search for available flights between two cities on a given date."""
    # Return mock flight options
    ...

@tool
def search_hotels(destination: str, checkin: str, checkout: str, budget_per_night: float) -> list[dict]:
    """Search for hotels in a destination within a nightly budget."""
    # Return mock hotel options
    ...
```

### 5.2 Activities Tools

```python
@tool
def search_activities(destination: str, interests: list[str], date: str) -> list[dict]:
    """Find activities matching user interests at the destination for a specific date."""
    ...

@tool
def search_restaurants(destination: str, cuisine_preferences: list[str], date: str) -> list[dict]:
    """Find restaurant recommendations at the destination."""
    ...
```

### 5.3 Budget Tools

```python
@tool
def calculate_budget(flights: list[dict], hotels: list[dict], activities: list[dict]) -> dict:
    """Calculate total estimated cost broken down by category."""
    ...

@tool
def convert_currency(amount: float, from_currency: str, to_currency: str) -> float:
    """Convert an amount between currencies using a fixed demo rate."""
    ...
```

---

## 6. Agent Definitions

Each agent is an LLM bound to its tools and a system prompt. Use `llm.bind_tools(tools)` to attach tools, then wrap it in a node function that reads/writes the shared state.

### 6.1 Node Function Pattern

Every agent node follows the same pattern:

```python
def agent_node(state: TravelPlannerState) -> dict:
    # 1. Build a system message describing the agent's role
    # 2. Invoke the LLM with state["messages"] + system message
    # 3. Return the updates to state (new messages, data fields)
```

### 6.2 System Prompts (guidance)

- **Orchestrator**: *"You are a friendly travel agent coordinator. Gather the user's destination, dates, budget, and interests. Once you have all details, delegate to the appropriate specialist. Combine their outputs into a final travel plan."*
- **Itinerary Agent**: *"You are a travel itinerary specialist. Given a destination and dates, use your tools to find flights and hotels, then build a day-by-day schedule."*
- **Activities Agent**: *"You are an activities specialist. Given a destination, dates, and user interests, suggest activities and restaurants for each day."*
- **Budget Agent**: *"You are a budget analyst. Given the proposed flights, hotels, and activities, calculate costs and report whether the plan is within budget."*

---

## 7. Graph Construction

### 7.1 Nodes

Register each agent as a node in the `StateGraph`:

```python
graph = StateGraph(TravelPlannerState)

graph.add_node("orchestrator", orchestrator_node)
graph.add_node("itinerary_agent", itinerary_node)
graph.add_node("activities_agent", activities_node)
graph.add_node("budget_agent", budget_node)
```

### 7.2 Routing

The orchestrator decides which specialist to call next. Implement this as a **conditional edge**:

```python
def route_from_orchestrator(state: TravelPlannerState) -> str:
    """Read state['current_agent'] set by the orchestrator and route accordingly."""
    agent = state.get("current_agent", "")
    if agent == "itinerary":
        return "itinerary_agent"
    elif agent == "activities":
        return "activities_agent"
    elif agent == "budget":
        return "budget_agent"
    else:
        return END  # back to user

graph.add_conditional_edges("orchestrator", route_from_orchestrator)
```

After each specialist finishes, control returns to the orchestrator to decide the next step:

```python
graph.add_edge("itinerary_agent", "orchestrator")
graph.add_edge("activities_agent", "orchestrator")
graph.add_edge("budget_agent", "orchestrator")
```

### 7.3 Entry Point

```python
graph.set_entry_point("orchestrator")
app = graph.compile()
```

### 7.4 Visual Summary

```
START → orchestrator ──┬──→ itinerary_agent ──→ orchestrator
                       ├──→ activities_agent ──→ orchestrator
                       ├──→ budget_agent ──────→ orchestrator
                       └──→ END (respond to user)
```

---

## 8. Conversation Loop

Wrap the compiled graph in a loop that feeds user input and prints agent responses:

```python
state = {
    "messages": [],
    "destination": "",
    "travel_dates": {},
    "budget": 0.0,
    "interests": [],
    "itinerary": [],
    "activities": [],
    "budget_breakdown": {},
    "current_agent": "",
}

while True:
    user_input = input("You: ")
    if user_input.lower() in ("quit", "exit"):
        break
    state["messages"].append(HumanMessage(content=user_input))
    state = app.invoke(state)
    # The last AI message is the orchestrator's response to the user
    print(f"Agent: {state['messages'][-1].content}")
```

---

## 9. Implementation Steps

Follow these in order. Each step is self-contained and testable.

### Step 1 — State & Config
- Define `TravelPlannerState`.
- Instantiate the LLM with `Config().get_llm()`.
- Verify the LLM responds to a simple test message.

### Step 2 — Orchestrator Agent (single-agent baseline)
- Create the orchestrator node with its system prompt.
- Build a minimal `StateGraph` with just the orchestrator and `END`.
- Test: have a conversation where the orchestrator gathers destination, dates, budget, and interests.

### Step 3 — Tools (mock implementations)
- Implement all six tools with hardcoded mock data.
- Test each tool individually to confirm inputs/outputs.

### Step 4 — Specialist Agents
- Create the three specialist nodes, each bound to its tools.
- Test each in isolation: call the node function directly with a crafted state.

### Step 5 — Full Graph Wiring
- Add all nodes and edges (including `route_from_orchestrator`).
- Compile the graph and run an end-to-end conversation.
- Verify the orchestrator delegates correctly and synthesizes a final plan.

### Step 6 — Human-in-the-Loop (optional extension)
- Add a confirmation step after the Budget Agent: pause and ask the user to approve the plan before finalizing.
- Use LangGraph's `interrupt` or a conditional edge back to the user.

### Step 7 — Structured Output (optional extension)
- Make the Itinerary Agent return a Pydantic model instead of free text.
- Use `llm.with_structured_output(ItineraryResponse)` to enforce the schema.

---

## 10. Notebook Structure

Map each implementation step to notebook cells for a guided walkthrough:

| Cell(s) | Content |
|---|---|
| 1 | Imports & config setup |
| 2 | Markdown: architecture overview |
| 3 | `TravelPlannerState` definition |
| 4 | Mock tool implementations |
| 5 | Orchestrator agent node |
| 6 | Itinerary agent node |
| 7 | Activities agent node |
| 8 | Budget agent node |
| 9 | Routing function |
| 10 | Graph construction & compilation |
| 11 | Conversation loop |
| 12+ | Optional extensions (human-in-the-loop, structured output) |

---

## 11. Key Concepts Cheat Sheet

Use these explanations in notebook markdown cells to teach each concept as it appears.

**Agent**: An LLM + system prompt + tools. The system prompt defines the agent's role and constraints. Tools give it access to capabilities beyond text generation.

**Orchestrator Pattern**: A central agent that doesn't do domain work itself — instead it understands the user's intent and routes to the right specialist. This keeps each agent focused and testable.

**State Graph**: A directed graph where nodes are agent functions and edges define control flow. State flows through the graph, getting enriched at each node. This makes the workflow explicit and debuggable.

**Conditional Edges**: Edges whose target is determined at runtime by a routing function. This is how the orchestrator "decides" which specialist to call.

**Tool Calling**: The LLM generates a structured tool-call request; the framework executes the function and feeds the result back to the LLM. The LLM never runs code directly.

**Shared State**: A single typed dictionary that all agents read from and write to. This is how agents communicate without directly calling each other.

**Human-in-the-Loop**: Pausing automated execution to get user confirmation. Critical for high-stakes decisions (e.g., booking confirmation).

**Structured Output**: Constraining the LLM to return data in a specific schema (via Pydantic models). Ensures downstream code can reliably parse agent outputs.

# CommuteGenie Singapore

CommuteGenie Singapore is a multi-agent AI system for intelligent public transportation assistance in Singapore.

It uses real-time transportation signals from **LTA DataMall**, contextual signals such as **Singapore time, rush hour, and public holidays**, and **Gemini** for reasoning and response generation.

The system follows a **manager-worker-reflection architecture** implemented using **LangGraph**, with a **FastAPI backend** and a **Streamlit frontend**.

---

## Project Overview

Commuters often need to check multiple sources before making a transportation decision, such as:
- bus arrival timings
- MRT / train disruptions
- traffic incidents
- taxi availability
- commute context such as rush hour or public holidays

Instead of switching between different apps, CommuteGenie provides a single conversational interface where the user can ask transportation-related questions in natural language.

Example questions:
- When is the next bus arriving at stop 83139?
- Are there any MRT disruptions right now?
- Is traffic bad at the moment?
- Are taxis available right now?
- Will rush hour affect my commute today?

The system retrieves relevant transportation and contextual data, coordinates multiple agents, and generates a grounded natural-language answer.

---

## Architecture

### Architecture Style

This project uses a **multi-agent architecture** with the following agents:
- **Manager / Orchestrator Agent**
- **Transport Agent**
- **Context Agent**
- **Critic / Reflection Agent**

The workflow is implemented using **LangGraph**.

### High-Level Flow

```text
User
  ↓
Streamlit Frontend
  ↓
FastAPI Backend
  ↓
LangGraph Workflow
  ↓
Manager Agent
  ↓
Transport Agent + Context Agent
  ↓
Manager Agent (response drafting)
  ↓
Critic Agent
  ↓
Final Answer
```

### Why this architecture?

This architecture is used because:
- transport and contextual information come from different sources
- specialized agents make the system modular
- the manager agent coordinates the workflow
- the critic agent improves reliability
- LangGraph provides explicit control over agent interaction and routing

---

## Core Design Pattern

### Manager–Worker Pattern

The **Manager Agent** is the central coordinator. It reads the user’s question and decides which worker agents are needed.

The worker agents are:
- **Transport Agent** → handles Singapore transport tools
- **Context Agent** → handles time, rush hour, holidays, and other contextual signals

The manager then combines their outputs and prepares a draft response.

### Reflection / Critic Pattern

Before the final answer is returned, the **Critic Agent** reviews the manager’s draft answer and checks:
- whether the answer is supported by retrieved data
- whether the answer contains contradictions
- whether the answer is complete enough
- whether the manager invented unsupported information

This adds a reflection layer and improves answer reliability.

### ReAct-Style Routing

The **Manager Router** uses lightweight ReAct-style planning:
- analyze the user question
- decide which worker agents are needed
- route execution through the graph

---

## Technology Stack

### Backend
- FastAPI
- LangGraph
- LangChain
- Gemini (Google Generative AI)

### Frontend
- Streamlit

### Data Sources
- LTA DataMall
- Singapore time and holiday context
- optional future weather integration

### Utilities
- requests for HTTP API calls
- pytz for Singapore timezone handling
- holidays for Singapore public holiday detection
- in-memory TTL caching for transport tool results

---

## Project Structure

```text
commutegenie_sg/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── schemas.py
│   ├── prompts.py
│   ├── state.py
│   ├── graph.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   └── llm_service.py
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── manager_agent.py
│   │   ├── transport_agent.py
│   │   ├── context_agent.py
│   │   └── critic_agent.py
│   │
│   └── tools/
│       ├── __init__.py
│       ├── lta_client.py
│       ├── transit_tools.py
│       └── context_tools.py
│
├── frontend/
│   └── streamlit_app.py
│
├── .env
├── requirements.txt
└── README.md
```

---

## Module-by-Module Explanation

### `app/main.py`
This is the FastAPI entry point.

Responsibilities:
- creates the FastAPI app
- enables CORS
- exposes API endpoints
- receives user questions
- invokes the LangGraph workflow
- returns the final response to the frontend

Main endpoints:
- `GET /` → root endpoint
- `GET /health` → health check
- `POST /ask` → main question-answering endpoint

---

### `app/config.py`
This module loads and stores application configuration from `.env`.

Responsibilities:
- loads environment variables
- stores API keys and model settings
- centralizes configuration

Main config values:
- `GOOGLE_API_KEY`
- `MODEL_NAME`
- `LTA_ACCOUNT_KEY`
- `DEFAULT_COUNTRY`

---

### `app/schemas.py`
This module defines request and response schemas using Pydantic.

Responsibilities:
- validates incoming API requests
- defines outgoing API responses
- keeps API contracts clear and consistent

Main models:
- `AskRequest`
- `AskResponse`

---

### `app/prompts.py`
This module stores the system prompts used by Gemini.

Responsibilities:
- defines the Manager Agent prompt
- defines the Critic Agent prompt
- separates prompts from business logic
- makes prompt updates easier

Main prompts:
- `MANAGER_SYSTEM_PROMPT`
- `CRITIC_SYSTEM_PROMPT`

---

### `app/state.py`
This module defines the shared LangGraph state.

Responsibilities:
- stores intermediate outputs across graph nodes
- allows agents to communicate through structured state
- tracks tool outputs, trace, used agents, draft answer, critic result, and final answer

Main state fields:
- `question`
- `manager_plan`
- `transport_result`
- `context_result`
- `draft_answer`
- `critic_result`
- `final_answer`
- `used_agents`
- `trace`

---

### `app/graph.py`
This module defines the full LangGraph workflow.

Responsibilities:
- creates the graph
- adds all agent nodes
- defines conditional routing logic
- controls how the manager, workers, and critic interact

Workflow logic:
1. start at `manager_router`
2. decide whether transport and/or context agents are needed
3. execute selected worker nodes
4. generate a draft through `manager_writer`
5. send the draft to `critic_agent`
6. return the final output

This is the core orchestration layer of the application.

---

## Services Layer

### `app/services/llm_service.py`
This module initializes the Gemini chat model.

Responsibilities:
- creates and returns the Gemini LLM object
- centralizes LLM configuration
- keeps model initialization separate from agent logic

Why this separation is useful:
- if the LLM changes later, only this module needs to be updated

---

## Agents Layer

### `app/agents/manager_agent.py`

This module contains two manager-related nodes.

#### `manager_router_node`
Responsibilities:
- reads the user question
- determines whether transport data is needed
- determines whether context data is needed
- stores the routing plan in graph state

Purpose:
- acts as the decision-making node for agent selection

#### `manager_writer_node`
Responsibilities:
- reads outputs from worker agents
- sends them to Gemini
- generates a grounded transport answer
- stores the draft answer in state

Purpose:
- this is the main answer construction step

---

### `app/agents/transport_agent.py`

This module handles Singapore transportation tool execution.

Responsibilities:
- examines the question
- identifies transport-related intent
- calls the relevant transport tool functions
- writes structured transport results into state

Supported tool types:
- bus stop lookup
- bus arrival lookup
- traffic incident lookup
- train service alert lookup
- taxi availability lookup

Example use cases:
- When is the next bus at stop 83139?
- Any MRT disruption now?
- How many taxis are available?

---

### `app/agents/context_agent.py`

This module gathers contextual signals that affect commuting.

Responsibilities:
- gets current Singapore time context
- determines rush hour
- checks public holiday information
- returns weather placeholder context

Context signals included:
- Singapore timestamp
- current hour
- weekday / weekend
- rush hour status
- public holiday status

Why it matters:
- transportation decisions are not only about raw transport data
- time-of-day and holiday conditions can affect commute behavior

---

### `app/agents/critic_agent.py`

This module performs the reflection step.

Responsibilities:
- reviews the manager’s draft answer
- compares it against transport and context outputs
- checks for unsupported claims or contradictions
- returns approval or feedback

Expected output format:
```json
{
  "approved": true,
  "feedback": "Answer is grounded and complete."
}
```

Why it matters:
- improves answer reliability
- demonstrates reflection in the multi-agent architecture

---

## Tools Layer

### `app/tools/lta_client.py`

This module provides the low-level LTA DataMall client.

Responsibilities:
- sends authenticated requests to LTA DataMall
- manages HTTP session reuse
- handles retries for transient network failures
- supports paginated retrieval

Core functionality:
- uses `requests.Session`
- configures retry behavior with `HTTPAdapter` and `Retry`
- adds the LTA `AccountKey` in request headers
- exposes:
  - `get(...)`
  - `get_paged(...)`

Why this matters:
- this module isolates all raw LTA API communication from the rest of the application

---

### `app/tools/transit_tools.py`

This module contains the actual Singapore transport tool functions.

Responsibilities:
- wraps raw LTA data into structured outputs
- provides transport-specific tool functions for the Transport Agent
- adds caching for repeated lookups

Main tool functions:

#### `tool_bus_arrival(bus_stop_code, service_no=None)`
Returns bus arrival information for a Singapore bus stop.

#### `tool_bus_stops_search(query, max_results=5)`
Searches bus stops by description or road name.

#### `tool_traffic_incidents()`
Fetches traffic incident data from LTA.

#### `tool_train_alerts()`
Fetches MRT / train service alert information.

#### `tool_taxi_availability()`
Fetches taxi availability information.

### Caching
This module includes a simple **TTL cache**.

Why caching is used:
- reduces duplicate API calls
- reduces latency
- reduces risk of hitting API limits

Cached items include:
- bus stops master dataset
- traffic incidents
- train alerts
- taxi availability

Current cache design:
- lightweight in-memory TTL cache
- suitable for coursework and single-instance demo use
- not distributed across multiple servers

Possible future improvement:
- replace with Redis or another shared caching solution

---

### `app/tools/context_tools.py`

This module provides Singapore-specific context functions.

Responsibilities:
- generates Singapore timezone-aware timestamps
- determines rush hour
- detects weekends
- checks public holidays
- provides placeholder weather context

Main functions:
- `get_sg_time_context()`
- `get_sg_holiday_context()`
- `get_mock_weather_context()`

Why this module is separate:
- it keeps context logic modular
- it avoids mixing transport API logic with calendar/time logic

---

## Frontend

### `frontend/streamlit_app.py`

This is the user-facing application.

Responsibilities:
- accepts natural-language transport questions
- sends requests to the FastAPI backend
- displays the final answer
- displays critic approval
- displays agent trace

Why Streamlit:
- simple to build
- fast for demos
- good for academic projects
- easy to connect with API backends

---

## Core Functionalities

The current system supports the following:

### 1. Bus Arrival Lookup
The user can ask for next bus arrival times using a 5-digit Singapore bus stop code.

Example:
- `When is the next bus arriving at stop 83139?`

### 2. Bus Stop Search
The user can search for a bus stop code using a bus stop description or road name.

Example:
- `Find bus stop code for Lucky Plaza`

### 3. Train / MRT Alert Lookup
The system can retrieve train service alerts.

Example:
- `Any MRT disruption right now?`

### 4. Traffic Incident Lookup
The system can retrieve traffic incident information.

Example:
- `Any traffic incidents now?`

### 5. Taxi Availability
The system can check overall taxi availability.

Example:
- `Are taxis available right now?`

### 6. Singapore Commute Context
The system can include:
- current Singapore time
- rush hour signal
- weekend signal
- public holiday signal

---

## Networking and External Communication

### LTA DataMall Network Calls
The application uses authenticated HTTP GET requests to access Singapore transport data.

Network reliability mechanisms:
- session reuse
- retry policy
- timeout handling
- safe fallback behavior when no live LTA key is configured

### Gemini API Calls
Gemini is used for:
- manager response generation
- critic reflection and validation

---

## Caching Strategy

The application uses a lightweight **TTL cache** inside `transit_tools.py`.

Why caching is necessary:
- without caching, repeated user requests would trigger repeated LTA API calls
- latency would increase
- API usage would be inefficient

Current cache characteristics:
- in-memory
- lightweight
- suitable for single-instance demo usage
- not shared across multiple backend instances

Cached items:
- bus stops dataset
- traffic incidents
- train alerts
- taxi availability

---

## Error Handling and Fallback Behavior

The project includes safe fallback behavior where possible.

Examples:
- if the LTA AccountKey is missing, some transport functions return mock/demo responses
- if a bus stop code is missing, the transport agent returns a clear error message
- if Gemini returns malformed JSON for the critic output, the parser falls back safely

This keeps the system usable during development and demos.

---

## Full Workflow

Step-by-step flow:
1. the user enters a question in the Streamlit UI
2. Streamlit sends the question to FastAPI `/ask`
3. FastAPI initializes graph state
4. LangGraph starts at `manager_router`
5. the manager decides which worker agents are needed
6. the transport agent retrieves transport data if required
7. the context agent retrieves contextual signals
8. the manager writes a grounded draft answer using Gemini
9. the critic agent reviews the draft using Gemini
10. the final answer is returned to FastAPI
11. the frontend displays the answer, approval status, and trace

---

## Setup Instructions

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

Create a `.env` file and add:

```env
GOOGLE_API_KEY=your_gemini_api_key_here
MODEL_NAME=gemini-1.5-flash
LTA_ACCOUNT_KEY=your_lta_datamall_account_key_here
DEFAULT_COUNTRY=Singapore
```

### 3. Run the backend

```bash
uvicorn app.main:app --reload
```

### 4. Run the frontend

```bash
streamlit run frontend/streamlit_app.py
```

---

## Example Queries

Try these example queries in the Streamlit app:

- `When is the next bus arriving at stop 83139?`
- `Find bus stop code for Lucky Plaza`
- `Any MRT disruption right now?`
- `Any traffic incidents now?`
- `Are taxis available right now?`
- `Will rush hour affect travel now?`

---

## Current Limitations

- weather is currently a placeholder context signal
- bus route planning is not yet implemented end-to-end
- no long-term conversation memory is included
- no RAG module is included yet
- current cache is in-memory only
- some responses may depend on question phrasing for correct tool triggering

---

## Future Improvements

Possible next improvements:
- integrate a real weather API
- add route planning support
- add RAG for static transport knowledge
- improve intent parsing with structured extraction
- add user preferences and personalization
- replace in-memory cache with Redis
- add monitoring and structured logs

---

## Summary

CommuteGenie Singapore is a modular multi-agent transportation assistant built with:
- FastAPI
- Streamlit
- LangGraph
- Gemini
- LTA DataMall

It uses a manager-worker-critic architecture to combine:
- real-time Singapore transport data
- contextual commute signals
- LLM-based grounded reasoning
- reflection-based answer validation

This structure makes the system:
- modular
- explainable
- extensible
- suitable for coursework and future enhancement

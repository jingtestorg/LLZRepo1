# Product Requirements Document (PRD)

**Title:** Finance Controller Cost Center Agent  
**Date:** 2026-08-28  
**Owner:** Finance Controlling Team  
**Solution Category:** AI Agent

---

## Product Purpose & Value Proposition

**Elevator Pitch:**  
Finance Controllers spend hours running manual SAP transactions just to answer basic department questions about cost centers. This agent lets them ask in plain language and get instant answers — no SAP access, no training required.

**Business Need:**  
Today, retrieving cost center information (total count, top cost centers) requires controllers to log into SAP, navigate to transaction KS13 or similar, and manually interpret results. This is slow, error-prone, and creates a dependency on SAP expertise. Controllers need a faster, self-service path to answer recurring department questions.

**Expected Value:**  
- Cost center query time reduced from hours to seconds
- No SAP transaction access required for basic controlling queries
- Controllers can independently answer department questions in real time

**Product Objectives (Prioritized):**
1. Enable natural language querying of SAP S/4HANA cost center data without any SAP system access
2. Deliver accurate, instant answers on total cost center count and top 5 cost centers
3. Be simple enough for non-technical Finance Controllers to use without training

---

## Business Metrics

| Metric | Baseline | Target | Timeline | Process / Capability | Source |
|--------|----------|--------|----------|----------------------|--------|
| Time to answer cost center questions | Hours (manual SAP transactions) | Seconds (instant NL query) | — | Financial Analytics / Controlling | user |
| SAP transaction access needed for queries | Required | Eliminated for basic queries | — | Cost Center Master Data Management | user |

---

## User Profiles & Personas

### Primary Persona: Clara — Finance Controller

Clara is a 38-year-old Finance Controller at a mid-sized manufacturing company. She oversees cost center reporting for multiple departments and regularly fields ad hoc questions from department heads: "How many cost centers do we have active?" or "Which are our biggest cost centers?" She has strong Excel and finance skills but limited SAP Fiori experience. She often has to ask a colleague with SAP access or wait until her next login session to get an answer. Clara needs a fast, reliable way to look up cost center facts without navigating SAP menus or writing queries.

**Goals:**
- Answer department questions about cost centers quickly and confidently
- Avoid depending on IT or SAP-trained colleagues for basic data lookups
- Stay on top of controlling data without interrupting her workflow

**Key Tasks:**
- Ask "How many cost centers are there?" and get an immediate answer
- Ask "What are the top 5 cost centers?" and receive a clear, ranked list
- Trust that the data is live and sourced directly from SAP S/4HANA

### Secondary Persona: Marcus — Head of Department

Marcus is a department head who regularly asks Clara cost center questions during planning meetings. He is not an SAP user and expects instant, confident answers from his Finance Controller. He doesn't care about the tool — he just needs reliable numbers fast.

---

## Goals and Non-Goals

### Goals (In Scope)

- Accept natural language questions about cost centers from Finance Controllers
- Return the total count of cost centers from SAP S/4HANA via the CE_COSTCENTER_0001 MCP server
- Return the top 5 cost centers from SAP S/4HANA, ranked by a relevant attribute (e.g., name/ID)
- Operate without requiring the user to have SAP system access
- Handle follow-up or rephrased queries gracefully

### Non-Goals (Out of Scope)

- Creating, updating, or deleting cost centers in SAP
- Querying financial postings, actuals, or budget data
- Reporting across multiple controlling areas simultaneously
- Supporting personas outside Finance Controlling (e.g., AP, HR)
- Building a UI — the agent is conversational/API-based

---

## Requirements

### Must-Have Requirements

**R1: Natural Language Cost Center Count**

- **Problem to Solve**: Controllers cannot quickly find out how many cost centers exist without running a SAP transaction.
- **User Story**: As a Finance Controller, I need to ask "How many cost centers do we have?" in plain language so that I can answer department questions instantly.
- **Acceptance Criteria**:
  - Given a natural language query about the total number of cost centers, when the agent processes the request, then it returns the accurate total count sourced from SAP S/4HANA via the CE_COSTCENTER_0001 MCP server.
- **Maps to Objective**: Objective 1, 2
- **Priority Rank**: 1

**R2: Natural Language Top 5 Cost Centers**

- **Problem to Solve**: Controllers need a quick view of the leading cost centers but must currently run and interpret SAP reports manually.
- **User Story**: As a Finance Controller, I need to ask "What are the top 5 cost centers?" so that I can share a clear, ranked list with department heads in seconds.
- **Acceptance Criteria**:
  - Given a natural language query about top cost centers, when the agent processes the request, then it returns a ranked list of the top 5 cost centers with relevant identifiers (name/ID).
- **Maps to Objective**: Objective 1, 2
- **Priority Rank**: 2

**R3: SAP-Free Query Experience**

- **Problem to Solve**: Controllers without active SAP sessions or transaction knowledge cannot access controlling data independently.
- **User Story**: As a Finance Controller, I need to query cost center data without logging into SAP so that I can answer questions at any time, from any context.
- **Acceptance Criteria**:
  - Given the agent is running, when a controller submits a cost center query, then the agent retrieves and returns results without the user needing to authenticate to or navigate SAP.
- **Maps to Objective**: Objective 1, 3
- **Priority Rank**: 3

**R4: Graceful Handling of Unrecognized Queries**

- **Problem to Solve**: Controllers may phrase questions in unexpected ways or ask things outside the agent's scope.
- **User Story**: As a Finance Controller, I need the agent to clearly tell me when it cannot answer my question so that I know when to seek information elsewhere.
- **Acceptance Criteria**:
  - Given a query outside the agent's supported scope, when the agent processes it, then it returns a clear, helpful message explaining what it can and cannot do.
- **Maps to Objective**: Objective 3
- **Priority Rank**: 4

---

## Solution Architecture

**Architecture Overview:**  
A Python-based AI agent (A2A protocol) deployed on SAP BTP. The agent accepts natural language input, routes the query to the appropriate tool, calls the CE_COSTCENTER_0001 MCP server to retrieve live data from SAP S/4HANA Controlling, and returns a formatted response to the user.

**Key Components:**

- **AI Agent (Python, A2A protocol)**: Core reasoning engine — interprets queries, selects the right tool, and formats responses
- **CE_COSTCENTER_0001 MCP Server**: Existing MCP integration layer providing access to SAP S/4HANA cost center master data
- **SAP S/4HANA Controlling**: Source of truth for all cost center data

**Integration Points:**

- CE_COSTCENTER_0001 MCP Server → SAP S/4HANA: read-only, on-demand, per user query

---

### Agent Extensibility & Instrumentation

**Agent Extensibility:**
- The agent is designed to be extended with additional cost center query types (e.g., filter by controlling area, cost center category) without changing the core architecture
- New MCP tools can be registered as additional data sources for future use cases (e.g., budget data, actuals)
- Skills can be added to cover additional Finance controlling domains (profit centers, internal orders)

**Business Step Instrumentation:**
- All key business steps (milestones) must emit structured log statements on achievement and on miss
- Log pattern: `[MILESTONE_ID].[achieved|missed]: [description]`
- Enables production monitoring, debugging, and future analytics on agent usage patterns

---

### Automation & Agent Behaviour

**Automation Level:** Autonomous agent

**Actions the system performs without human approval:**
- Interpreting the natural language query
- Calling the CE_COSTCENTER_0001 MCP server to retrieve cost center data
- Ranking and formatting the top 5 cost centers
- Returning the response to the user

**Actions that require human review or approval:**
- None — the agent is read-only; no write operations are performed

**Model or engine used:** Large language model via SAP Generative AI Hub

**Knowledge & data sources accessed:**
- CE_COSTCENTER_0001 MCP Server: SAP S/4HANA cost center master data (read-only)

**Tools or connectors invoked:**
- `CE_COSTCENTER_0001` MCP tools: retrieve cost center list and count (read-only, no side effects)

**Guardrails & fail-safes:**
- The agent never modifies, creates, or deletes SAP data — strictly read-only
- If the MCP server is unavailable, the agent returns a clear error message rather than a partial or incorrect result
- Queries outside the cost center domain are declined with a helpful out-of-scope message
- No financial postings, actuals, or sensitive HR data are accessed

---

## Milestones

### M1: Query Received

- **Description**: The Finance Controller submits a natural language question about cost centers
- **Achieved when**: The agent receives and acknowledges a non-empty input message
- **Log on achievement**: `M1.achieved: user query received and passed to intent classification`
- **Log on miss**: `M1.missed: no input received or input was empty`

### M2: Intent Understood

- **Description**: The agent correctly classifies the query as a cost center count or top-5 request
- **Achieved when**: The agent selects the appropriate tool (count or list) based on the query
- **Log on achievement**: `M2.achieved: intent classified as [count|top5], routing to MCP tool`
- **Log on miss**: `M2.missed: intent could not be classified — returning out-of-scope message`

### M3: Data Retrieved

- **Description**: The agent successfully retrieves cost center data from SAP S/4HANA via the CE_COSTCENTER_0001 MCP server
- **Achieved when**: The MCP tool call returns a valid, non-empty response
- **Log on achievement**: `M3.achieved: cost center data retrieved from CE_COSTCENTER_0001`
- **Log on miss**: `M3.missed: MCP server call failed or returned empty result`

### M4: Answer Delivered

- **Description**: The agent returns a clear, formatted answer to the controller
- **Achieved when**: The response is sent back to the user with the requested information
- **Log on achievement**: `M4.achieved: response delivered to user`
- **Log on miss**: `M4.missed: response could not be formatted or delivered`

### M5: Session Complete

- **Description**: The controller has the information needed without requiring SAP access
- **Achieved when**: The interaction completes without any SAP transaction being required from the user
- **Log on achievement**: `M5.achieved: session completed — controller query resolved via agent`
- **Log on miss**: `M5.missed: session ended without resolving the controller's query`

---

## Risks, Assumptions, and Dependencies

### Risks

- MCP server CE_COSTCENTER_0001 availability: if the server is down, the agent cannot retrieve data; a clear fallback message is required
- Data freshness: cost center data reflects the current SAP state at query time; near-real-time, not historical

### Assumptions (Validate These)

- The CE_COSTCENTER_0001 MCP server is deployed, accessible, and returns cost center master data
- The agent deployment environment has connectivity to the MCP server
- Finance Controllers will interact with the agent via a conversational interface (chat or API)

### Dependencies

- CE_COSTCENTER_0001 MCP server (existing, user-confirmed)
- SAP S/4HANA Controlling module with cost center master data populated
- SAP Generative AI Hub access for the LLM runtime

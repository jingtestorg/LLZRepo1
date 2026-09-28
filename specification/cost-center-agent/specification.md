# Specification: cost-center-agent

> **Guidelines**: Read all applicable guidelines before executing ANY tasks below:
> - [guidelines.md](../guidelines.md) — Universal execution rules
> - [guidelines-agent.md](../guidelines-agent.md) — Universal agent patterns
> - [guidelines-agent-python.md](../guidelines-agent-python.md) — Python implementation details
> - [guidelines-agent-skills.md](../guidelines-agent-skills.md) — Runtime skills patterns
> - [guidelines-agent-mcp.md](../guidelines-agent-mcp.md) — MCP integration patterns

---

## Basic Setup

- [ ] Read the project input: `product-requirements-document.md` and `intent.md`
- [ ] Bootstrap agent code in `assets/cost-center-agent/` using instructions from the `sap-agent-bootstrap` section of the agent skill. Run from inside `assets/cost-center-agent/`, use copy commands — do NOT create files manually.
- [ ] Install dependencies: `pip install -r requirements.txt` from `assets/cost-center-agent/`
- [ ] Validate the agent starts and responds at `/.well-known/agent.json`

---

## Runtime Skills

No runtime skills required — all queries map to simple direct MCP tool calls. The system prompt is sufficient.

---

## MCP Integration (Path A — API Spec File)

The CE_COSTCENTER_0001 API spec has been downloaded to `specification/cost-center-agent/api-specs/CE_COSTCENTER_0001.json`.
The user has specified CE_COSTCENTER_0001 as the MCP server to use.

- [ ] Invoke the `mcp-translation-file` skill with:
  - Input spec: `specification/cost-center-agent/api-specs/CE_COSTCENTER_0001.json`
  - API ORD ID: `sap.s4:apiResource:CE_COSTCENTER_0001:v1`
  - API type: `openapi-v3`
  - Focus translation on GET operations only (list cost centers, count): `GET /A_CostCenter_2` with `$count=true`, `$top`, `$orderby`, `$select`, `$filter` support
- [ ] Invoke the `setup-solution` skill to create the MCP server asset for the generated translation file
- [ ] Read the generated `asset.yaml` and copy the exact `ordId` value for use in the agent's `asset.yaml` `requires` entry
- [ ] Wire MCP tool loading in `app/agent.py` using `get_mcp_tools()` from the `mcp_tools` module

---

## Agent System Prompt

- [ ] Write the system prompt in `app/agent.py` `@prompt_section` (or equivalent) with the following requirements:
  - Role: "You are a Finance Controller assistant. You answer questions about SAP S/4HANA cost center data."
  - Supported queries: total count of cost centers, top 5 cost centers by name/ID
  - MUST NOT fabricate or invent data — always use MCP tools to retrieve live data
  - When calling tools that support pagination, set `$top` to a maximum of 100
  - If a tool returns an error, report it verbatim without suggestions
  - If the query is outside supported scope (cost center count or top 5 list), respond with a clear out-of-scope message listing what IS supported
  - Read-only only: never create, update, or delete cost centers

---

## Feature: Cost Center Count (R1)

- [ ] Ensure the agent can handle queries such as:
  - "How many cost centers do we have?"
  - "What is the total number of cost centers?"
  - "Count all cost centers"
- [ ] Agent must call the cost center MCP tool with `$count=true` and `$top=1` (or equivalent) to retrieve the total count
- [ ] Response must include the exact numeric count sourced from SAP S/4HANA
- [ ] Log milestone M3 on successful data retrieval: `M3.achieved: cost center data retrieved from CE_COSTCENTER_0001`

---

## Feature: Top 5 Cost Centers (R2)

- [ ] Ensure the agent can handle queries such as:
  - "What are the top 5 cost centers?"
  - "Show me the top cost centers"
  - "List the leading cost centers"
- [ ] Agent must call the cost center MCP tool with `$top=5` and `$orderby=CostCenter` (ascending by ID as default ranking)
- [ ] Response must include cost center ID (`CostCenter`), name (`CostCenterName`), and controlling area (`ControllingArea`) for each of the top 5
- [ ] Response must be formatted as a clear ranked list
- [ ] Log milestone M3 on successful data retrieval: `M3.achieved: cost center data retrieved from CE_COSTCENTER_0001`

---

## Feature: Out-of-Scope Handling (R4)

- [ ] Ensure the agent responds gracefully to queries outside the cost center count/top-5 scope
- [ ] Out-of-scope response must be clear and list what the agent CAN answer
- [ ] Log milestone M2 miss: `M2.missed: intent could not be classified — returning out-of-scope message`

---

## Business Instrumentation

- [ ] Implement all 5 milestones from the PRD with structured log statements and OpenTelemetry spans:
  - `M1.achieved: user query received and passed to intent classification`
  - `M1.missed: no input received or input was empty`
  - `M2.achieved: intent classified as [count|top5], routing to MCP tool`
  - `M2.missed: intent could not be classified — returning out-of-scope message`
  - `M3.achieved: cost center data retrieved from CE_COSTCENTER_0001`
  - `M3.missed: MCP server call failed or returned empty result`
  - `M4.achieved: response delivered to user`
  - `M4.missed: response could not be formatted or delivered`
  - `M5.achieved: session completed — controller query resolved via agent`
  - `M5.missed: session ended without resolving the controller's query`
- [ ] Extract business logic from `stream()` into a plain async helper `_run_agent()` to avoid `GeneratorExit` context errors with OTel spans
- [ ] Verify `auto_instrument()` is called at the top of `main.py` before any AI framework imports

---

## MCP Dependencies

- [ ] Add the CE_COSTCENTER_0001 MCP server dependency to `assets/cost-center-agent/asset.yaml` under `requires`:
  ```yaml
  requires:
    - name: ce-costcenter-0001
      kind: mcp-server
      ordId: <exact ordId from generated MCP asset.yaml>
  ```
  **Use the exact ORD ID from the generated asset — never invent it.**

---

## Mock Configuration

- [ ] After `mcp-translation-file` and `setup-solution` complete, invoke `mcp-mock-config` skill to generate `mcp-mock.json` for tests
- [ ] `mcp-mock.json` must include realistic mock responses for:
  - Cost center list (for count query): a collection with `@odata.count` = 47 (example total)
  - Top 5 cost centers: 5 entries with `CostCenter`, `CostCenterName`, `ControllingArea` populated

---

## Testing

- [ ] `conftest.py` sets only `IBD_TESTING=true` — no other patching in this file
- [ ] Write unit tests in `assets/cost-center-agent/tests/`:
  - `test_count_query.py` — test agent handles count queries correctly, MCP tool is called with `$count=true`
  - `test_top5_query.py` — test agent handles top-5 queries, MCP tool returns 5 items formatted as a list
  - `test_out_of_scope.py` — test agent returns an out-of-scope message for unsupported queries
- [ ] Write one integration test in `assets/cost-center-agent/tests/test_integration.py` — end-to-end agent flow with mocked LLM and mocked MCP tool results
- [ ] All LLM calls must be mocked — no real AI Core calls during tests
- [ ] Run `pytest` from `assets/cost-center-agent/` (no args) — coverage must be ≥ 70%
- [ ] Verify `assets/cost-center-agent/app/agent.py` has exactly 5 decorated functions:
  ```bash
  grep -c "^@agent_model\|^@agent_config\|^@prompt_section" assets/cost-center-agent/app/agent.py
  # must return 5
  ```
- [ ] Run final `pytest` from `assets/cost-center-agent/` (no args) to generate `test_report.json`
- [ ] Verify `test_report.json` exists in `assets/cost-center-agent/`

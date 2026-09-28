# Finance Controller Cost Center Agent

Natural language querying of cost center data in SAP S/4HANA Controlling for Finance Controllers.

## Business challenge

Finance Controllers need instant answers on cost center data — total count and top 5 cost centers — but today this requires manually running SAP transactions (e.g. KS13), which is time-consuming and requires system access. Controllers cannot quickly answer department questions without IT or SAP expertise.

## Business Goals & Success Criteria

| Metric | Baseline | Target | Timeline | Process / Capability | Source |
|--------|----------|--------|----------|----------------------|--------|
| Time to answer cost center questions | Hours (manual SAP transactions) | Seconds (instant NL query) | — | Financial Analytics / Controlling | user |
| SAP transaction access needed for queries | Required | Eliminated for basic queries | — | Cost Center Master Data Management | user |

## Key Milestones

1. **Query Received** — Controller submits a natural language question about cost centers (e.g. "How many cost centers do we have?" or "What are the top 5 cost centers?")
2. **Intent Understood** — Agent interprets the query and selects the appropriate tool (count or list top cost centers)
3. **Data Retrieved** — Agent calls the CE_COSTCENTER_0001 MCP server to fetch cost center data from SAP S/4HANA
4. **Answer Delivered** — Agent returns a clear, formatted response to the controller
5. **Session Complete** — Controller has the information needed to answer department questions without SAP access

## Business Architecture (RBA)

### End-to-End Process

Finance (generic)

### Process Hierarchy

```
Finance (E2E)
└── Plan to Optimize Financials (generic)
    └── Plan and analyze financials (generic) [BPS-412]
        └── Perform financial analysis
└── Record to Report (generic)
    └── Perform accounting and financial close (generic) [BPS-413]
        └── Perform financial reporting
```

### Summary

Cost center querying maps to the Finance E2E — specifically financial analysis (BPS-412) and financial reporting (BPS-413). The agent enables controllers to perform these activities through natural language without needing direct SAP transaction access.

## Fit Gap Analysis

| Requirement (business) | Standard asset(s) found | API ORD ID | MCP Server ORD ID | MCP Server Version | Gap? | Notes / assumptions |
| ---------------------- | ----------------------- | ---------- | ----------------- | ------------------ | ---- | ------------------- |
| Query total count of cost centers | SAP S/4HANA Controlling — Cost Center API | `sap.s4:apiResource:CE_COSTCENTER_0001:v1` | CE_COSTCENTER_0001 MCP (existing, user-specified) | — | No | User has confirmed existing MCP server CE_COSTCENTER_0001 is available |
| Query top 5 cost centers | SAP S/4HANA Controlling — Cost Center API | `sap.s4:apiResource:CE_COSTCENTER_0001:v1` | CE_COSTCENTER_0001 MCP (existing, user-specified) | — | No | Sort/filter to be handled by agent logic |
| Natural language understanding and intent routing | No standard SAP product covers NL query agent | — | — | — | Yes | Custom AI agent required |
| No SAP transaction access required for query | SAP S/4HANA Financial Analytics (SC1763 / SC5664) covers reporting | — | — | — | Partial | Agent abstracts SAP access; standard analytics tools require login |

### Key findings

- The user has explicitly specified the MCP server CE_COSTCENTER_0001 as the integration point — no additional API discovery needed.
- SAP S/4HANA Cloud (Public and Private) provides Financial Analytics and Financial Master Data Management capabilities that cover this domain (BPS-412, BPS-413).
- No standard SAP product provides natural language querying over cost center data out of the box — a custom AI agent is required.
- The agent will use the CE_COSTCENTER_0001 MCP server to retrieve data, and apply its own reasoning for count and ranking (top 5).
- The solution eliminates the need for controllers to have direct SAP GUI or Fiori access for basic cost center queries.
- A Python A2A agent is the right fit: it reasons dynamically over queries, calls MCP tools, and returns structured answers.

## Recommendations

### Finance Controller Cost Center AI Agent

#### Executive Summary

Python A2A agent using CE_COSTCENTER_0001 MCP for NL cost center queries.

#### Recommended Solution

A Python-based AI agent (A2A protocol) that accepts natural language questions from Finance Controllers about cost center data. The agent calls the existing CE_COSTCENTER_0001 MCP server to retrieve live cost center data from SAP S/4HANA Controlling, then computes and returns answers for:
- Total count of cost centers
- Top 5 cost centers (by name/ID or relevant ranking criteria)

The agent requires no SAP GUI or Fiori access for the controller.

#### Recommended solution category

AI Agent

#### Intent fit
95%

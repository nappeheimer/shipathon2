# Onboarding Agent — Nasiko AI Agent Buildthon

**Problem Statement 3: Adaptive Workflow Orchestration Agent**
**Domain: Employee Onboarding Automation**

---

## What It Does

This agent onboards a new employee from a single natural language instruction. It plans a strict sequence of steps, executes each one using a defined toolset, retries intelligently on failure, escalates gracefully when retries are exhausted, and produces a full structured audit log at the end.

**Architecture: Plan-then-Execute**

1. A Groq LLM (LLaMA 3.3 70b) reads the instruction and generates a validated DAG of steps
2. The executor runs each step sequentially using only the 5 permitted tools
3. On failure: up to 2 retries with modified parameters (or exponential backoff for rate limits)
4. On exhaustion: a structured escalation payload is generated for human review
5. A JSON audit log captures every decision, parameter, retry, and outcome

---

## Tools

| Tool | Purpose |
|---|---|
| `account_provisioner` | Provisions system access with RBAC |
| `welcome_email_composer` | Sends personalised welcome email |
| `calendar_scheduler` | Books orientation and kickoff meetings |
| `document_generator` | Generates contracts and NDAs |
| `onboarding_tracker` | Updates the central onboarding record |

---

## Running Locally

### Prerequisites
- Docker Desktop
- Groq API key (free at https://console.groq.com)

### Setup

```bash
# Clone the repo
git clone https://github.com/nappenheimer/shipathon2.git
cd shipathon2

# Add your Groq API key
echo "ALT_API_KEY=your_key_here" > .env

# Build and run
docker build -t shipathon2 .
docker run --env-file .env -p 5000:5000 shipathon2
```

### Verify it's running

```bash
curl http://localhost:5000/.well-known/agent.json
```

### Visual Audit Dashboard

Open your browser at:
```
http://localhost:5000/ui
```

Type any onboarding request in the input box and hit Run. The dashboard shows the full execution trace with live status badges, retry details, timing, and escalation payloads.

---

## Test Scenarios

### Scenario 1 — Standard onboarding (happy path)

```bash
curl -X POST http://localhost:5000/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-1",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "messageId": "msg-001",
        "parts": [{"kind": "text", "text": "Onboard Sarah Connor to the Cybersecurity team starting next Monday as a Security Analyst."}]
      }
    }
  }'
```

**Expected:** All 5 tools execute successfully. Final status: `complete`.

---

### Scenario 2 — Ambiguous instruction (missing details)

```bash
curl -X POST http://localhost:5000/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-2",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "messageId": "msg-002",
        "parts": [{"kind": "text", "text": "Onboard John Smith to Engineering tomorrow."}]
      }
    }
  }'
```

**Expected:** Agent infers missing fields (role, salary band, systems) using department context. All 5 steps complete. Final status: `complete`.

---

### Scenario 3 — Different department and role

```bash
curl -X POST http://localhost:5000/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-3",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "messageId": "msg-003",
        "parts": [{"kind": "text", "text": "Complete full onboarding for Maria Garcia joining the Product team on 2026-05-15 as a Senior Product Manager."}]
      }
    }
  }'
```

**Expected:** Agent generates a plan tailored to Product team context. All 5 steps complete. Final status: `complete`.

---

## Audit Log

Every workflow produces a structured JSON execution log returned in the response artifact. It contains:

- `workflow_metadata` — workflow ID, timestamps, final status, step counts, retry counts, escalation count
- `planned_steps` — the full DAG generated before any execution began
- `execution_trace` — one record per step with tool name, parameters used, result, errors, retry attempts, and escalation payload if triggered

---

## Project Structure

```
my-awesome-agent/
├── 
├── __init__.py
├── __main__.py              # A2A server entry point
├── webhook_agent.py         # Planner + Executor orchestrator
├── webhook_agent_executor.py # A2A AgentExecutor implementation
├── onboarding_tools.py      # 5 mock tools with Pydantic schemas
├── audit_store.py           # In-memory audit log store
└── ui_routes.py             # Visual dashboard routes
├── Dockerfile
├── docker-compose.yml
├── AgentCard.json
└── README.md
```

---

## Evaluation Criteria Coverage

| Criterion | How it's addressed |
|---|---|
| Decomposition quality | LLM generates a strict ordered DAG before any execution |
| Tool adherence | Pydantic schema validation blocks any tool not in the permitted set |
| Failure handling | Per-step try/catch with modified-parameter LLM retry on validation errors, backoff on transient errors |
| Escalation appropriateness | After 2 failed retries, full context payload generated and workflow halts |
| Execution log quality | Structured JSON with every step, attempt, error, corrected params, and final status |
| End-to-end completion | 3 distinct scenarios tested and documented above |

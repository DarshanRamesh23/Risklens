# RiskLens — AI-Powered Third-Party Risk & Compliance Copilot

RiskLens ingests vendor documents (SOC 2 reports, security questionnaires, contracts)
and your internal risk policies, then produces a **scored, cited risk assessment**
for each vendor — combining a classic ML risk model with an LLM agent that grounds
every finding in the exact policy clause it matched against.

## Why this project exists

Third-party risk assessment today is manual: a GRC analyst reads a 40-page SOC 2
report, cross-references it against internal policy by memory, and writes up
findings by hand. RiskLens automates the *reading and cross-referencing* step while
keeping a human in the loop for the decision — every finding shows its receipts.

## Architecture

```
                       ┌─────────────────────┐
                       │   React Dashboard    │
                       │ (vendor list, score  │
                       │  cards, drill-down)  │
                       └──────────┬───────────┘
                                  │ REST (JSON)
                       ┌──────────▼───────────┐
                       │     FastAPI API      │
                       │  /vendors /ingest    │
                       │  /score   /findings  │
                       └──────┬───────┬────────┘
                              │       │
              ┌───────────────┘       └───────────────┐
              ▼                                        ▼
   ┌─────────────────────┐                  ┌──────────────────────┐
   │  Ingestion Service   │                  │  Risk-Scoring Service │
   │  - chunk documents    │                  │  - ML gate (sklearn) │
   │  - embed (MiniLM)      │                  │  - RAG retrieval     │
   │  - store vectors       │                  │  - LLM agent + cite  │
   └──────────┬────────────┘                  │    verification pass │
              │                                └──────────┬───────────┘
              ▼                                           ▼
   ┌─────────────────────┐                     ┌──────────────────────┐
   │      MongoDB          │                     │   Postgres + pgvector │
   │  raw doc bytes +       │◄────────────────────┤  chunks, embeddings, │
   │  upload metadata       │      chunk refs      │  vendors, findings   │
   └─────────────────────┘                     └──────────────────────┘
```

## The two-layer scoring design (the part interviewers will ask about)

Blending a logistic-regression model with an LLM's qualitative read is easy to
describe badly ("we combined ML and AI!"). RiskLens uses a specific, defensible
pattern — **ML as a gate + feature injection**, not a weighted average of two
incomparable scores:

1. `ml/train_model.py` trains a logistic regression on structured vendor
   attributes (industry risk tier, geography, number of past incidents, contract
   value) → outputs a **prior probability of material risk**.
2. That prior is injected into the LLM agent's prompt as a *fact*, not blended
   numerically: *"The structured risk model estimates a 72% prior probability of
   material risk for this vendor, driven mainly by [past incidents]. Read the
   attached documents and confirm, revise, or override this prior — citing the
   specific clauses that support your conclusion."*
3. The agent must ground every finding in a retrieved policy chunk. A
   **second LLM call re-checks the finding against the retrieved chunk** before
   it's allowed to be emitted — if the chunk doesn't actually support the claim,
   the finding is dropped and re-attempted or flagged as "ungrounded."

This means the ML model's job is narrow and honest (a prior from structured data),
and the LLM's job is narrow and honest (read text, cite text, get checked).

## Tech stack → JD mapping

| Area | Implementation |
|---|---|
| Vector DB / RAG | Postgres + `pgvector`, chunking + `sentence-transformers` embeddings |
| LLM / Agentic AI | Claude (Anthropic API) agent with a retrieval → draft → verify loop |
| Python ML + MLOps | scikit-learn logistic regression, versioned via `ml/train_model.py`, loaded by the scoring service |
| Backend | FastAPI, split into ingestion router + scoring router (two logical services, one deployable app — see `infra/azure`) |
| SQL + NoSQL | Postgres (structured + vector) and MongoDB (raw docs/metadata) |
| Frontend | React (Vite) dashboard: vendor list → risk scorecard → "why was this flagged" drill-down |
| Cloud + DevOps | Azure Container Apps / App Service target, GitHub Actions CI (`.github/workflows/ci.yml`) |

## Repo layout

```
risklens/
├── backend/           FastAPI app, services, ML training script, tests
├── frontend/           React dashboard (Vite)
├── infra/               docker-compose for local dev + Azure deployment notes
└── .github/workflows/  CI pipeline
```

## Running it locally

```bash
# 1. Start Postgres (pgvector) + Mongo
docker compose -f infra/docker-compose.yml up -d

# 2. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-...        # required for the agent step
export DATABASE_URL=postgresql://risklens:risklens@localhost:5432/risklens
export MONGO_URL=mongodb://localhost:27017
alembic upgrade head 2>/dev/null || python -m app.db.postgres  # create tables
python ml/train_model.py                # trains + saves ml/model.pkl on synthetic data
uvicorn app.main:app --reload --port 8000

# 3. Frontend
cd ../frontend
npm install
npm run dev   # http://localhost:5173, proxies /api to :8000
```

## Deployment (Azure)

See `infra/azure/README.md` for the Container Apps deployment path and how the
GitHub Actions pipeline in `.github/workflows/ci.yml` builds, tests, and deploys
on merge to `main`.

## What's genuinely v1 vs. documented direction

Being upfront about this is more credible in an interview than pretending it's
all production-grade:
- **v1 (built, runs):** ingestion → chunk → embed → pgvector store; RAG retrieval;
  LLM agent with citation-verification pass; logistic regression gate; FastAPI
  endpoints; React dashboard; docker-compose local stack; CI test workflow.
- **Documented direction (not fully productionized here):** multi-tenant auth,
  autoscaling Container Apps config, model retraining pipeline / drift monitoring,
  virus-scanning on upload, SOC 2 for RiskLens itself.

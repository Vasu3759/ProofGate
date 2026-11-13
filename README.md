# ProofGate

Brand governance with proof. This repository now contains the first text review workflow: approved synthetic brand facts → submission revision → deterministic evidence checks → correction → human decision.

## Current implementation

- Next.js workspace with the ProofGate editorial visual system: sharp corners, dark left navigation, bright lime action color, editorial headings, and visible data dividers.
- FastAPI API with PostgreSQL support, SQLAlchemy models, Alembic migrations, and organization-scoped queries.
- Versioned evidence sources and approved facts, policy versions pinned to review runs, immutable content revisions, findings, citations, correction suggestions, human decisions, and audit events.
- Synthetic Meridian Labs records for the demonstration flow. Demo identity switching is explicitly local-only and is not production authentication.
- Review checks are deterministic scenario rules. No LLM, document upload, image review, automatic publishing, or production identity provider is connected yet. A lack of evidence is reported as unverified.

## Run locally

The API defaults to a local SQLite database for a quick demo. PostgreSQL is available through the included compose file for Docker-capable environments.

### API

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
export DEMO_MODE=true
export DATABASE_URL=sqlite:///./proofgate.db
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --port 8000
```

The API schema is available at [http://localhost:8000/docs](http://localhost:8000/docs).

### Web app

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Use the demo identity selector in the workspace utility bar to switch between creator Alex Rivera, reviewer Dana Kim, and brand manager Morgan Lee. Start at Review Studio, create and run the sample claim, apply corrections, submit the current revision, then switch to Dana Kim in Approvals to decide it.

### PostgreSQL with Docker Compose

```bash
docker compose up --build
```

The API container applies migrations and seeds synthetic records on startup. The frontend remains a local `npm run dev` process unless separately containerized.

## Configuration and security boundary

`DEMO_MODE=true` enables a header-based local identity selector against seeded organization memberships. Do not enable it for a deployed or shared environment: anyone able to call the API can select a demo user. With demo mode disabled, authenticated routes fail closed until a real OIDC/JWT identity adapter is configured. Tenant membership is checked server-side on every request.

The reviewer decision is bound to the exact submission revision and review run. Approved facts and policies are versioned. The current API creates manager-entered fact records as approved, records an audit event, and does not yet implement a second-person fact-approval workflow; use only synthetic/demo data until that control is added for production.

## Verification

Focused backend tests cover evidence citations and version pinning, organization and role boundaries, missing-evidence classification, and review decision transitions. Run them from `backend` with `pytest`.

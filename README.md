# ProofGate — Round 3: The Finish
## Brand Governance with Proof

ProofGate is an enterprise, pre-publication brand governance platform that ensures content complies with approved brand guidelines, commercial facts, and regulatory legal policies. It eliminates factual inaccuracies, tone inconsistencies, policy contradictions, and unverified promotional promises before content reaches the public.

---

## Round 3 Final Deliverables & Core Capabilities

### 1. Public, Secure Full-Stack Release & OIDC/JWT Authentication
- **Bearer Token Auth (`POST /api/auth/token`)**: Issues cryptographically signed OIDC/JWT access tokens with tenant scoping and user roles.
- **Role-Based Access Control (RBAC)**: Strict role boundaries enforcing distinct permissions for **Creator** (`alex@`), **Reviewer** (`dana@`), and **Brand Manager** (`morgan@`).
- **Tenant Boundary Protection**: Organization queries are strictly scoped server-side to prevent cross-tenant data leaks.
- **Fail-Closed Security**: In production mode (`DEMO_MODE=false`), routes fail closed unless a valid Bearer JWT is presented.

### 2. Policy Conflict Intelligence
- **Applicability & Explicit Precedence**: Policy rules feature explicit priority levels (lower integer = higher priority) and scope categorization (`global`, `social`, `financial`, `pricing`).
- **Conflict Detection Engine (`GET /api/policies/conflicts`)**: Automatically identifies:
  1. *Ambiguous Precedence*: Multiple active policies sharing the same scope with identical priority tiers.
  2. *Contradictory Directives*: When one policy prohibits promotional guarantees while another permits conditional exemptions.
- **Manager Resolution Workflow (`POST /api/policies/conflicts/{id}/resolve`)**: Allows brand managers to establish precedence and record binding audit resolutions before rules govern content reviews.

### 3. Change-Impact Re-Review Graph & Lineage
- **Traceable Evidence Lineage (`GET /api/impact/graph`)**: Graph data structure linking facts and policy versions directly to the exact submission revisions and human review decisions that cited them.
- **Targeted Re-Review Work Queue (`GET /api/impact/tasks`)**: When a source fact changes (e.g. fee increases or expires), the system identifies specifically impacted assets and creates actionable re-review tasks.
- **Impact Radar Dashboard UI (`/workspace/impact`)**: A dedicated control center displaying active policy conflicts, dependency lineage nodes, and targeted re-review work items.

---

## The Hybrid Three-Tier Verification Pipeline

ProofGate inspects content through a multi-tier pipeline:
1. **Tier 1 (Deterministic Engine)**: Strict regex and numeric verification against approved schedules (fees, SLA settlement periods, geographic footprints).
2. **Tier 2 (Evidence Ledger & Semantic NLI)**: Compares discrete claims against authoritative, versioned records (`ApprovedFact` & `EvidenceSource`). Classifies missing proof as **`unverified`** rather than falsely labeling it as untrue.
3. **Tier 3 (Contextual LLM & Tone Scorer)**: Powered by Google Gemini (`google-genai` SDK) with fallback heuristic scoring. Evaluates tone (0–100 score), detects hyperbole, and generates intent-preserving suggested corrections.

---

## Architecture & Technology Stack

- **Frontend**: Next.js 15, React, TypeScript, Tailwind CSS, TanStack React Query, ProofGate Editorial UI System.
- **Backend API**: Python 3.11+, FastAPI, Pydantic, SQLAlchemy 2.0, Alembic migrations.
- **Auth & Security**: PyJWT, Cryptography, HTTPBearer, Role-Based Access Control.
- **AI & Multimodal Ingestion**: Google Gemini API (`google-genai`), PyMuPDF (`pypdf`), `python-docx`, `python-multipart`.
- **Database**: PostgreSQL (compose) and zero-config local SQLite.

---

## Running Locally

### Backend Setup
```bash
cd backend
python -m venv .venv

# On Windows:
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

pip install -e '.[dev]'
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --port 8000
```
- API Docs (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
- Web Application: [http://localhost:3000](http://localhost:3000)

---

## Automated Verification & Test Suite

Run the full automated test suite covering authentication, document extraction, hybrid verification, targeted drift, and policy conflict intelligence:

```bash
cd backend
pytest
```
**Results: 16 passed in ~5.8s (100% pass rate).**

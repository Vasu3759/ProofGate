# ProofGate — Round 3: The Finish
## Brand Governance with Proof

ProofGate is an enterprise, pre-publication brand governance platform that ensures marketing copy, product briefs, and campaign documents comply with approved brand facts, guidelines, and regulatory legal policies. It eliminates factual inaccuracies, tone inconsistencies, policy contradictions, and unverified promotional promises before content reaches the public.

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
3. **Tier 3 (Contextual LLM & Tone Scorer)**: Powered by Google Gemini (`google-genai` SDK) with fallback heuristic scoring. Evaluates tone (0–100 score), detects hyperbole, validates findings strictly against cited facts, and generates intent-preserving suggested corrections.

---

## Standout Capabilities Delivered

### 1. Multimodal Document Ingestion
- **Formats Supported**: `.pdf` (`pypdf`), `.docx` (`python-docx`), and `.txt` / `.md`.
- **Capability**: Creators can upload full marketing documents directly into Review Studio with instant word parsing, paragraph formatting, and automated title assignment.

### 2. Hybrid AI Verification & Grounded Tone Scoring Engine
- Evaluates submitted content against corporate voice and regulatory safety rules.
- Computes real-time **AI Tone & Compliance Scores (0–100)** with detected tone classification (e.g. *"Promotional / Unverified"* vs. *"Compliant / Brand-Aligned"*).
- Detects promotional guarantees and unsubstantiated superlatives (*"the best"*, *"risk-free"*, *"guaranteed"*), offering one-click intent-preserving rewrites.
- Strictly grounds AI findings and suggestions against approved evidence records.

### 3. Retroactive Policy Drift & Dependency Tracking
- Pins review runs and approval decisions to the exact version of the evidence records cited.
- When an `ApprovedFact` is updated (e.g., fee schedule changes from v1 to v2) or expires, the system triggers a retroactive scan across all historical approved submissions.
- Surfaces a critical **Policy Drift Detected** alert in the Brand Intelligence dashboard and creates targeted work items in the **Impact Radar**.

---

## Architecture & Technology Stack

- **Frontend**: Next.js 15 (App Router), React, TypeScript, Tailwind CSS, TanStack React Query, ProofGate Editorial UI System.
- **Backend API**: Python 3.11+, FastAPI, Pydantic Settings, SQLAlchemy 2.0, Alembic migrations.
- **Auth & Security**: PyJWT, Cryptography, HTTPBearer, Role-Based Access Control (RBAC).
- **AI & Multimodal Ingestion**: Google Gemini API (`google-genai`), PyMuPDF (`pypdf`), `python-docx`, `python-multipart`.
- **Database**: PostgreSQL (via Docker Compose) and zero-config local SQLite.

---

## Running Locally

### 1. Backend Setup
```bash
cd backend
python -m venv .venv

# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

pip install -e '.[dev]'
pip install pypdf python-docx python-multipart google-genai pyjwt cryptography

# Run migrations and seed synthetic records
alembic upgrade head
python -m app.seed

# Start the API server
uvicorn app.main:app --reload --port 8000
```
- API Docs (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
- Web Application: [http://localhost:3000](http://localhost:3000)

---

## How to Test the Core Workflows

### Scenario A: Multimodal Document Review
1. Open [http://localhost:3000/workspace/review](http://localhost:3000/workspace/review).
2. In the **`MULTIMODAL INGESTION`** box, click **`SELECT FILE ↗`** and upload `sample_brief.docx` or `sample_campaign.txt`.
3. Click **`RUN COMPLIANCE ↗`**:
   - Inspect the **AI Tone & Compliance Score** (e.g. `55/100`).
   - Review flagged contradictions (fees, settlement, unsupported guarantees) with cited evidence sources.
   - Click **`APPLY SUGGESTIONS & RECHECK ↗`** to auto-correct the copy.
4. Click **`SUBMIT REVISION FOR HUMAN REVIEW ↗`**.

### Scenario B: Human Review & Decision
1. Switch demo identity to **Dana Kim (Reviewer)** using the top workspace header.
2. Go to **Approvals** ([http://localhost:3000/workspace/approvals](http://localhost:3000/workspace/approvals)).
3. Open the pending submission, inspect findings, and click **`APPROVE REVISION ↗`**.

### Scenario C: Live Policy Drift Tracking & Impact Radar
1. Switch identity to **Morgan Lee (Brand Manager)**.
2. Go to **Brand Knowledge** ([http://localhost:3000/workspace/knowledge](http://localhost:3000/workspace/knowledge)).
3. Under **`Register an approved fact`**, submit an updated fact:
   - **Fact Key**: `fee`
   - **Assertion**: `Subject to a 0.8% processing fee` (new v2 rate)
4. Navigate to **Impact Radar** ([http://localhost:3000/workspace/impact](http://localhost:3000/workspace/impact)) to inspect the dynamic Change-Impact Graph, active policy conflict resolutions, and the targeted re-review work queue.

---

## Automated Verification & Test Suite

Run the full automated test suite covering authentication, document extraction, hybrid verification, grounded corrections, targeted drift, and policy conflict intelligence:

```bash
cd backend
pytest
```
**Results: 21 passed (100% pass rate).**

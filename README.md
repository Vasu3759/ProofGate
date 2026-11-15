# ProofGate — Brand Governance with Proof

ProofGate is an AI-powered, pre-publication brand governance platform that ensures marketing copy, product briefs, and campaign documents follow approved brand facts and legal policies. It eliminates factual inaccuracies, tone inconsistencies, and unsupported promotional promises before content reaches the public.

---

## Round 2 Build: Key Capabilities & Architecture

ProofGate operates on a **hybrid, three-tier verification pipeline**:

1. **Tier 1 — Deterministic Verification Engine**: Strict pattern and numeric matching against approved fact schedules (fees, SLA settlement periods, geographic footprints, and mandatory legal disclaimers).
2. **Tier 2 — Version-Controlled Evidence Ledger & Semantic Inference**: Compares discrete claims against authoritative, versioned records (`ApprovedFact` & `EvidenceSource`). Flags contradicted claims, pins exact version citations, and classifies missing proof as **`unverified`** (preventing false-negative bias).
3. **Tier 3 — Contextual LLM Engine & Tone Evaluator**: Integrated with Google Gemini (`google-genai` SDK) and an air-gapped Semantic NLI fallback. Dynamically extracts claims, computes an **AI Tone & Compliance Score (0–100)**, identifies hyperbole/unsupported guarantees, and generates intent-preserving suggested corrections.

---

## The Three Standout Improvements Delivered

### 1. Multimodal Document Ingestion
- **Formats Supported**: `.pdf` (PyMuPDF / pypdf), `.docx` (python-docx), and `.txt` / `.md`.
- **Capability**: Creators can upload full marketing documents directly into Review Studio with instant word parsing, paragraph formatting, and automated title assignment.

### 2. Hybrid AI Verification & Tone Scoring Engine
- Evaluates submitted content against corporate voice and regulatory safety rules.
- Computes real-time **AI Tone & Compliance Scores (0–100)** with detected tone classification (e.g. *"Promotional / Unverified"* vs. *"Compliant / Brand-Aligned"*).
- Detects promotional guarantees and unsubstantiated superlatives (*"the best"*, *"risk-free"*, *"guaranteed"*), offering one-click intent-preserving rewrites.

### 3. Retroactive Policy Drift & Dependency Tracking
- Pinning review runs and approval decisions to the exact version of the evidence records cited.
- When an `ApprovedFact` is updated (e.g., fee schedule changes from v1 to v2) or expires, the system triggers a retroactive scan across all historical approved submissions.
- Surfaces a critical **Policy Drift Detected** alert in the Brand Intelligence dashboard, notifying managers that previously approved campaigns require re-certification.

---

## Tech Stack

- **Frontend**: Next.js 15 (App Router), React, TypeScript, Tailwind CSS, TanStack React Query, ProofGate Editorial UI System.
- **Backend API**: Python 3.11+, FastAPI, Pydantic Settings, SQLAlchemy 2.0, Alembic migrations.
- **AI & Processing**: Google Gemini API (`google-genai` SDK), Semantic NLI heuristics engine, `pypdf`, `python-docx`, `python-multipart`.
- **Database**: SQLite (default zero-config local demo) and PostgreSQL (via Docker Compose).

---

## Quick Start & Local Development

### 1. Backend Setup (FastAPI)

```bash
cd backend
python -m venv .venv

# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

pip install -e '.[dev]'
pip install pypdf python-docx python-multipart google-genai

# Run migrations and seed synthetic records
alembic upgrade head
python -m app.seed

# Start the API server
uvicorn app.main:app --reload --port 8000
```
- API Docs (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)

### 2. Frontend Setup (Next.js)

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

### Scenario C: Live Policy Drift Tracking
1. Switch identity to **Morgan Lee (Brand Manager)**.
2. Go to **Brand Knowledge** ([http://localhost:3000/workspace/knowledge](http://localhost:3000/workspace/knowledge)).
3. Under **`Register an approved fact`**, submit an updated fact:
   - **Fact Key**: `fee`
   - **Assertion**: `Subject to a 0.8% processing fee` (new v2 rate)
4. Watch the top metric card immediately update to **`POLICY DRIFT DETECTED: 01`** with an alert banner identifying the affected past approved campaign.

---

## Automated Verification

Run the full automated test suite covering document ingestion, workflow state transitions, evidence citations, and role boundaries:

```bash
cd backend
pytest
```
*(All 9 tests pass cleanly).*

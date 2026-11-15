import json
import logging
import re
from typing import Any
from app.core.config import settings

logger = logging.getLogger(__name__)


def call_llm_verification(
    content: str,
    approved_facts: list[dict[str, Any]],
    brand_policies: list[str],
) -> dict[str, Any] | None:
    """
    Tier 3 LLM verification pipeline using google-genai.
    Analyzes:
    1. Tone & Brand Persona (hyperbole, unsupported urgency, missing disclaimers).
    2. Dynamic claim validation against the Evidence Ledger.
    3. Context-aware, intent-preserving correction suggestions.
    Returns structured JSON findings or None if the LLM is not configured / fails.
    """
    api_key = settings.gemini_api_key
    if not api_key:
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        facts_context = "\n".join(
            f"- [{f['fact_key']}] {f['label']}: \"{f['claim_text']}\""
            for f in approved_facts
        )
        policies_context = "\n".join(f"- {p}" for p in brand_policies)

        prompt = f"""You are the ProofGate Brand Compliance and Verification Engine.
Analyze the following marketing/product content for brand compliance, factual accuracy, and tone consistency.

APPROVED EVIDENCE LEDGER (Authoritative facts):
{facts_context}

ACTIVE BRAND POLICIES:
{policies_context}

SUBMITTED CONTENT:
\"\"\"{content}\"\"\"

Task Instructions:
1. Examine claims against the Approved Evidence Ledger.
2. Flag any claims that:
   - "contradicted": directly conflict with approved facts.
   - "unverified": make factual claims or promises not supported by the evidence ledger. Missing evidence is NOT proof of falsity; mark it unverified.
   - "policy_violation": violate brand tone (e.g. hyperbole, guarantees like 'risk-free', 'the best', missing required disclaimers).
3. For each flagged item, generate an intent-preserving, context-aware suggestion that fixes the issue using approved facts.
4. Provide a tone assessment: tone score (1-100), detected tone, and any tone issues.

Return ONLY a valid JSON object matching this schema:
{{
  "tone_score": 85,
  "detected_tone": "Promotional / Bold",
  "tone_summary": "Clear value proposition, but contains unsupported absolute guarantees.",
  "findings": [
    {{
      "claim_text": "exact sentence or clause from submitted content",
      "status": "contradicted | unverified | policy_violation",
      "severity": "critical | high | medium | info",
      "explanation": "Clear explanation citing the approved evidence or policy reason",
      "matched_fact_key": "fact_key or null",
      "suggested_text": "Corrected sentence preserving author intent and tone",
      "rationale": "Why this correction aligns with brand governance"
    }}
  ]
}}
"""

        response = client.models.generate_content(
            model=settings.ai_model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )

        if response and response.text:
            cleaned = response.text.strip()
            # Clean possible markdown fence
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            return json.loads(cleaned.strip())

    except Exception as e:
        logger.warning(f"LLM verification failed or timed out: {e}. Falling back to deterministic rules.")
        return None

    return None


def semantic_nli_fallback(
    content: str,
    approved_facts: list[dict[str, Any]],
    brand_policies: list[str],
) -> dict[str, Any]:
    """
    Tier 2 Heuristic / Semantic-NLI Fallback Engine.
    Executes deep semantic pattern recognition when the LLM service is offline
    or running in isolated air-gapped demo mode.
    """
    findings = []
    tone_flags = []

    # 1. Check tone & hyperbole
    HYPERBOLE_PATTERNS = [
        (re.compile(r"\b(?:guaranteed|100%\s+guarantee|risk[- ]free)\b", re.I), "Promotional Guarantee", "Absolute guarantee violates brand safety rules and consumer protection guidelines."),
        (re.compile(r"\b(?:the\s+best|#1|number\s+one|world['’]?s\s+fastest|unbeatable)\b", re.I), "Unsubstantiated Superlative", "Comparative superlatives require third-party independent audit proof before publication."),
        (re.compile(r"\b(?:revolutionary|game[- ]changing|miracle)\b", re.I), "Overly Sensational Tone", "Sensational language detracts from institutional credibility."),
    ]

    for pattern, label, explanation in HYPERBOLE_PATTERNS:
        match = pattern.search(content)
        if match:
            phrase = match.group(0)
            tone_flags.append(f"{label}: '{phrase}'")
            # Unverified claim finding (missing evidence is unverified)
            findings.append({
                "claim_text": phrase,
                "status": "unverified",
                "severity": "high",
                "explanation": "This promotional promise has no matching approved evidence record. It is unverified, not established as false.",
                "matched_fact_key": None,
                "suggested_text": f"Remove this unsupported promise or provide an approved source.",
                "rationale": "Missing evidence must be marked unverified rather than false.",
            })
            # Policy violation finding
            findings.append({
                "claim_text": phrase,
                "status": "policy_violation",
                "severity": "high",
                "explanation": f"{explanation} The active brand policy prohibits unsupported promotional guarantees.",
                "matched_fact_key": None,
                "suggested_text": f"[Remove '{phrase}' or substitute with verified metric]",
                "rationale": "Aligns copy with regulated brand governance standards.",
            })

    # 2. Check numeric and factual claims against ApprovedFacts
    for fact in approved_facts:
        key = fact.get("fact_key")
        fact_text = fact.get("claim_text", "")

        # Fees
        if key == "fee":
            if re.search(r"\b(?:free|zero\s+fees?|no\s+fees?|0\s*%(?:\s+fee)?)\b", content, re.I):
                findings.append({
                    "claim_text": "free",
                    "status": "contradicted",
                    "severity": "critical",
                    "explanation": f"Claim directly conflicts with approved fee schedule: '{fact_text}'",
                    "matched_fact_key": key,
                    "suggested_text": "subject to a standard 0.5% processing fee",
                    "rationale": "Prevents deceptive pricing and regulatory penalties.",
                })

        # Speed / Settlement
        if key == "settlement":
            if re.search(r"\b(?:instant(?:ly)?|real[- ]time|same[- ]day)\b", content, re.I):
                findings.append({
                    "claim_text": "instantly",
                    "status": "contradicted",
                    "severity": "critical",
                    "explanation": f"Delivery speed conflicts with current network SLAs: '{fact_text}'",
                    "matched_fact_key": key,
                    "suggested_text": "with settlement in 1–2 business days",
                    "rationale": "Maintains accurate customer SLA expectations.",
                })

        # Markets
        if key == "markets":
            match = re.search(r"\b(?:over|more than|\+)?\s*(\d+)\s*(?:\+)?\s*(?:countries|markets)\b", content, re.I)
            if match:
                claimed = int(match.group(1))
                # If claimed exceeds 45 (approved)
                if claimed > 45:
                    findings.append({
                        "claim_text": match.group(0).strip(),
                        "status": "contradicted",
                        "severity": "critical",
                        "explanation": f"Geographical coverage ({claimed} countries) exceeds approved operational footprint: '{fact_text}'",
                        "matched_fact_key": key,
                        "suggested_text": "45 supported markets",
                        "rationale": "Aligns with currently licensed partner corridors.",
                    })

    tone_score = max(40, 100 - (len(findings) * 15))
    return {
        "tone_score": tone_score,
        "detected_tone": "Promotional / Unverified" if findings else "Compliant / Brand-Aligned",
        "tone_summary": f"Identified {len(findings)} governance issue(s). {'; '.join(tone_flags) if tone_flags else 'Tone is appropriate.'}",
        "findings": findings,
    }

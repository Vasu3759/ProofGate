import json
import logging
import re
from typing import Any, Literal
from pydantic import BaseModel, Field, ValidationError

from app.core.config import settings

logger = logging.getLogger(__name__)


class FindingItem(BaseModel):
    claim_text: str = Field(..., min_length=1)
    status: Literal["supported", "contradicted", "unverified", "policy_violation"]
    severity: Literal["critical", "high", "medium", "info"]
    explanation: str = Field(..., min_length=1)
    matched_fact_key: str | None = None
    suggested_text: str | None = None
    rationale: str | None = None


class LLMReviewOutput(BaseModel):
    tone_score: int = Field(..., ge=0, le=100)
    detected_tone: str = Field(..., min_length=1)
    tone_summary: str = Field(default="")
    findings: list[FindingItem] = Field(default_factory=list)


def parse_numeric_fact(fact_text: str) -> dict[str, Any]:
    """
    Extract key numeric parameters from approved fact claim text.
    For fee: percentage (e.g. 1.5, 0.8)
    For settlement: range string (e.g. '1–2 business days')
    For markets: integer count (e.g. 85)
    """
    params = {}
    fee_match = re.search(r"(\d+(?:\.\d+)?)%", fact_text)
    if fee_match:
        params["fee"] = fee_match.group(1)

    settle_match = re.search(r"(\d+\s*[–-]\s*\d+\s+business\s+days)", fact_text, re.I)
    if settle_match:
        params["settlement"] = settle_match.group(1).replace("-", "–")

    market_match = re.search(r"(\d+)\s+supported\s+markets", fact_text, re.I)
    if market_match:
        params["markets"] = int(market_match.group(1))

    return params


def derive_suggestion(fact_key: str, fact_text: str) -> str | None:
    """Derive correction suggestion text dynamically from the approved record."""
    params = parse_numeric_fact(fact_text)
    if fact_key == "fee" and "fee" in params:
        return f"international transfers, subject to a {params['fee']}% processing fee"
    if fact_key == "settlement" and "settlement" in params:
        return f"available with settlement in {params['settlement']}"
    if fact_key == "markets" and "markets" in params:
        return f"{params['markets']} supported markets"
    return None


def finding_claim_is_grounded(claim_text: str, content: str) -> bool:
    """Require an LLM finding to quote a contiguous span of the reviewed revision."""
    normalize = lambda value: " ".join(value.split()).casefold()
    claim = normalize(claim_text)
    return bool(claim) and claim in normalize(content)


def suggestion_matches_fact(suggestion: str, fact_key: str, fact_text: str) -> bool:
    """Reject numeric corrections that conflict with the matched approved fact."""
    params = parse_numeric_fact(fact_text)
    if fact_key == "fee" and "fee" in params:
        suggested_values = re.findall(r"\b(\d+(?:\.\d+)?)\s*%", suggestion)
        return all(value == str(params["fee"]) for value in suggested_values)

    if fact_key == "settlement" and "settlement" in params:
        normalize = lambda value: re.sub(r"\s+", "", value).replace("-", "–").casefold()
        suggested_values = re.findall(r"\b\d+\s*[–-]\s*\d+\s+business\s+days\b", suggestion, re.I)
        return all(normalize(value) == normalize(params["settlement"]) for value in suggested_values)

    if fact_key == "markets" and "markets" in params:
        suggested_values = re.findall(
            r"\b(?:(?:over|more than)\s*)?(\d+)\+?\s+(?:supported\s+)?(?:markets|countries)\b",
            suggestion,
            re.I,
        )
        return all(int(value) == params["markets"] for value in suggested_values)

    return True


def call_llm_verification(
    content: str,
    approved_facts: list[dict[str, Any]],
    brand_policies: list[str],
) -> dict[str, Any] | None:
    """
    Tier 3 LLM verification pipeline using google-genai.
    Strictly validated against LLMReviewOutput Pydantic schema.
    """
    api_key = settings.gemini_api_key
    if not api_key:
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        facts_context = "\n".join(
            f"- [{f['fact_key']}] {f.get('label', f['fact_key'])}: \"{f['claim_text']}\""
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
3. If an approved fact is cited in `matched_fact_key`, you MUST verify that the fact actually supports the claim or contradicts it as explained.
4. For each flagged item, generate an intent-preserving, context-aware suggestion that fixes the issue using approved facts.
5. Provide a tone assessment: tone score (0-100), detected tone, and any tone issues.

Return ONLY a valid JSON object matching this schema:
{{
  "tone_score": 85,
  "detected_tone": "Promotional / Bold",
  "tone_summary": "Clear value proposition, but contains unsupported absolute guarantees.",
  "findings": [
    {{
      "claim_text": "exact sentence or clause from submitted content",
      "status": "contradicted",
      "severity": "critical",
      "explanation": "Clear explanation citing the approved evidence or policy reason",
      "matched_fact_key": "fee",
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
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            parsed_raw = json.loads(cleaned.strip())
            validated = LLMReviewOutput.model_validate(parsed_raw)
            return validated.model_dump()

    except ValidationError as ve:
        logger.warning(f"LLM output failed Pydantic schema validation: {ve}. Falling back to fallback engine.")
        return None
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
    Tier 2 Semantic-NLI Fallback Engine.
    Derives ALL numeric comparisons and suggestions directly from approved_facts.
    Zero hardcoded values for market count, fees, or settlement times.
    """
    findings = []
    tone_flags = []

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
            findings.append({
                "claim_text": phrase,
                "status": "unverified",
                "severity": "high",
                "explanation": "This promotional promise has no matching approved evidence record. It is unverified, not established as false.",
                "matched_fact_key": None,
                "suggested_text": "Remove this unsupported promise or provide an approved source.",
                "rationale": "Missing evidence must be marked unverified rather than false.",
            })
            findings.append({
                "claim_text": phrase,
                "status": "policy_violation",
                "severity": "high",
                "explanation": f"{explanation} The active brand policy prohibits unsupported promotional guarantees.",
                "matched_fact_key": None,
                "suggested_text": f"[Remove '{phrase}' or substitute with verified metric]",
                "rationale": "Aligns copy with regulated brand governance standards.",
            })

    for fact in approved_facts:
        key = fact.get("fact_key")
        fact_text = fact.get("claim_text", "")
        params = parse_numeric_fact(fact_text)
        suggestion = derive_suggestion(key, fact_text)

        if key == "fee":
            fee_free_match = re.search(
                r"\b(?:completely\s+)?free(?:\s+of\s+(?:fees?|charge))?(?:\s+(?:international\s+)?transfers?)?\b|\btransfers?\s+(?:are\s+)?free\b|\bzero\s+fees?\b|\bno\s+fees?\b",
                content,
                re.I,
            )
            if fee_free_match and any(w in content.lower() for w in ["transfer", "fee", "transfers"]):
                findings.append({
                    "claim_text": fee_free_match.group(0),
                    "status": "contradicted",
                    "severity": "critical",
                    "explanation": f"Claim directly conflicts with approved fee schedule: '{fact_text}'",
                    "matched_fact_key": key,
                    "suggested_text": suggestion or f"subject to an approved processing fee",
                    "rationale": "Prevents deceptive pricing and regulatory penalties.",
                })

        if key == "settlement":
            settle_match = re.search(r"\bavailable\s+instantly\b|\binstant(?:ly)?\b|\bsame[- ]day\b|\breal[- ]time\b", content, re.I)
            if settle_match:
                findings.append({
                    "claim_text": settle_match.group(0),
                    "status": "contradicted",
                    "severity": "critical",
                    "explanation": f"Delivery speed conflicts with current network SLAs: '{fact_text}'",
                    "matched_fact_key": key,
                    "suggested_text": suggestion or "with standard settlement",
                    "rationale": "Maintains accurate customer SLA expectations.",
                })

        if key == "markets" and "markets" in params:
            approved_count = params["markets"]
            for m in re.finditer(r"\b(?:over|more than)\s+(\d+)\s+(?:countries|markets)\b|\b(\d+)\+\s*(?:countries|markets)\b|\b(\d+)\s+supported\s+markets\b", content, re.I):
                claimed_str = next((g for g in m.groups() if g), None)
                if claimed_str:
                    claimed_count = int(claimed_str)
                    if claimed_count > approved_count:
                        findings.append({
                            "claim_text": m.group(0),
                            "status": "contradicted",
                            "severity": "critical",
                            "explanation": f"Geographical coverage ({claimed_count} markets) exceeds approved operational footprint: '{fact_text}'",
                            "matched_fact_key": key,
                            "suggested_text": suggestion or f"{approved_count} supported markets",
                            "rationale": "Aligns with currently licensed partner corridors.",
                        })

    tone_score = max(40, 100 - (len(findings) * 15))
    return {
        "tone_score": tone_score,
        "detected_tone": "Promotional / Unverified" if findings else "Compliant / Brand-Aligned",
        "tone_summary": f"Identified {len(findings)} governance issue(s). {'; '.join(tone_flags) if tone_flags else 'Tone is appropriate.'}",
        "findings": findings,
    }

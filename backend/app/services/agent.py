"""
The agentic core of RiskLens.

For each vendor document chunk:
  1. Retrieve the most relevant internal policy chunks (RAG).
  2. Ask the LLM to draft a risk finding grounded in those chunks, seeded
     with the ML model's prior risk probability as a fact to confirm/revise.
  3. VERIFY: ask the LLM a second, narrower question -- "does this exact
     policy excerpt support this exact claim?" -- before the finding is
     allowed to be stored as `grounded=True`. Findings that fail verification
     are either dropped or surfaced as "ungrounded / needs human review"
     rather than silently kept, so the dashboard never shows a citation that
     doesn't actually back the claim.

This two-call pattern (draft, then verify) is deliberately more expensive
and slower than a single call -- that's the trade-off being made explicitly
to reduce hallucinated citations, which is the single biggest credibility
risk in a "reads your compliance documents for you" product.
"""
import json
from dataclasses import dataclass

import google.generativeai as genai

from app.config import settings
from app.db.postgres import Finding, PolicyChunk, VendorChunk, get_session
from app.services.retrieval import get_vendor_chunks, retrieve_relevant_policy_chunks

genai.configure(api_key=settings.gemini_api_key)


@dataclass
class DraftFinding:
    severity: str
    summary: str
    vendor_quote: str
    policy_quote: str
    policy_chunk_id: int


DRAFT_SYSTEM_PROMPT = """You are a third-party risk analyst assistant. You will be given:
- A structured ML model's prior probability that this vendor carries material risk, and its main driver.
- One excerpt from a vendor's document (SOC 2 report, questionnaire, or contract).
- Several excerpts from the company's internal risk policy that were retrieved as potentially relevant.

Decide whether the vendor excerpt reveals anything that confirms, contradicts, or is irrelevant to the
policy excerpts. Only produce a finding if a specific policy excerpt is actually relevant -- do not force
a match. If nothing relevant is found, return an empty findings list.

Respond ONLY with JSON matching this schema, no other text:
{
  "findings": [
    {
      "severity": "low" | "medium" | "high",
      "summary": "one or two sentence explanation of the risk, referencing the ML prior if relevant",
      "vendor_quote": "short exact excerpt (<=25 words) copied verbatim from the vendor excerpt",
      "policy_quote": "short exact excerpt (<=25 words) copied verbatim from the matched policy excerpt",
      "policy_chunk_index": <integer index into the provided policy excerpts, 0-based>
    }
  ]
}
"""

VERIFY_SYSTEM_PROMPT = """You are a strict fact-checker. You will be given a claimed finding, a policy
excerpt, and a vendor excerpt. Answer ONLY "GROUNDED" if the policy_quote text is truly present in the
policy excerpt AND the vendor_quote text is truly present in the vendor excerpt AND the summary is a fair
characterization of the relationship between them. Otherwise answer ONLY "NOT_GROUNDED". No other text.
"""


def _call_llm(system: str, user_content: str) -> str:
    model = genai.GenerativeModel(model_name=settings.llm_model, system_instruction=system)
    response = model.generate_content(
        user_content,
        generation_config=genai.types.GenerationConfig(max_output_tokens=1000, temperature=0),
    )
    return response.text


def _draft_findings(vendor_chunk: VendorChunk, policy_chunks: list[PolicyChunk], ml_prior: dict) -> list[DraftFinding]:
    policy_excerpts = "\n".join(
        f"[{i}] ({pc.policy_name} / {pc.section_label}): {pc.text}" for i, pc in enumerate(policy_chunks)
    )
    user_content = (
        f"ML prior risk probability: {ml_prior['prior_risk_probability']} "
        f"(main driver: {ml_prior['main_driver']})\n\n"
        f"VENDOR EXCERPT ({vendor_chunk.doc_name}):\n{vendor_chunk.text}\n\n"
        f"POLICY EXCERPTS:\n{policy_excerpts}"
    )
    raw = _call_llm(DRAFT_SYSTEM_PROMPT, user_content)
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        # Gemini sometimes wraps JSON in a markdown fence even when told not to.
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return []

    drafts = []
    for f in data.get("findings", []):
        idx = f.get("policy_chunk_index")
        if idx is None or not (0 <= idx < len(policy_chunks)):
            continue
        drafts.append(DraftFinding(
            severity=f.get("severity", "low"),
            summary=f.get("summary", ""),
            vendor_quote=f.get("vendor_quote", ""),
            policy_quote=f.get("policy_quote", ""),
            policy_chunk_id=policy_chunks[idx].id,
        ))
    return drafts


def _verify_finding(draft: DraftFinding, vendor_chunk: VendorChunk, policy_chunk: PolicyChunk) -> bool:
    user_content = (
        f"CLAIMED FINDING:\nsummary: {draft.summary}\n"
        f"vendor_quote: {draft.vendor_quote}\npolicy_quote: {draft.policy_quote}\n\n"
        f"POLICY EXCERPT:\n{policy_chunk.text}\n\n"
        f"VENDOR EXCERPT:\n{vendor_chunk.text}"
    )
    verdict = _call_llm(VERIFY_SYSTEM_PROMPT, user_content).strip()
    return verdict.startswith("GROUNDED")


def run_agent_for_vendor(vendor_id: int, ml_prior: dict) -> list[Finding]:
    """Full pipeline for one vendor: retrieve -> draft -> verify -> store."""
    vendor_chunks = get_vendor_chunks(vendor_id)
    session = get_session()
    stored: list[Finding] = []
    try:
        for vchunk in vendor_chunks:
            policy_chunks = retrieve_relevant_policy_chunks(vchunk.text)
            if not policy_chunks:
                continue

            drafts = _draft_findings(vchunk, policy_chunks, ml_prior)
            policy_by_id = {pc.id: pc for pc in policy_chunks}

            for draft in drafts:
                policy_chunk = policy_by_id[draft.policy_chunk_id]
                grounded = _verify_finding(draft, vchunk, policy_chunk)

                finding = Finding(
                    vendor_id=vendor_id,
                    vendor_chunk_id=vchunk.id,
                    policy_chunk_id=policy_chunk.id,
                    severity=draft.severity,
                    summary=draft.summary,
                    vendor_quote=draft.vendor_quote,
                    policy_quote=draft.policy_quote,
                    grounded=grounded,
                )
                session.add(finding)
                stored.append(finding)

        session.commit()
        return stored
    finally:
        session.close()
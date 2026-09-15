"""LLM reasoning constrained to the retrieved chunks - the model is only
shown these chunks and instructed to cite by exact doc_id + section, so
validate_citations can mechanically check every claim against what it
was actually given.
"""

from __future__ import annotations

import json

from app.config import settings
from app.graph.state import Citation, GraphState
from app.llm.generate import generate_json

_PROMPT_TEMPLATE = """You are IP-SAKTI Sahayak, an assistant answering \
Ayurveda intellectual-property and regulatory questions. You are NOT a \
lawyer and must state this is information, not legal advice, when \
relevant.

JURISDICTION FOR THIS ANSWER: {jurisdiction}
Use ONLY the numbered source chunks below. Do not cite or invent \
authority from any other jurisdiction. If the chunks are insufficient, \
abstain plainly instead of guessing.

If any chunk is from the WIPO GRATK treaty (doc_id containing \
"gratk"), you MUST state it is signed but NOT YET IN FORCE / not \
binding law.

A chunk's header shows its doc_type. Only doc_type=statute, rules, or \
treaty is primary binding law. doc_type=case_law is a court record, not \
legislation. doc_type=secondary_analysis, guideline, or manual is \
commentary/procedural guidance, NOT primary law - present it as such, \
never as if it were a statute or binding rule.

SOURCE CHUNKS:
{chunks_block}

QUESTION: {question}

Respond with a JSON object with exactly these fields:
- "answer": your answer as plain text, citing chunks inline like [1], [2]
- "citations": a list of objects, one per chunk you actually relied on, \
each with "doc_id" and "section_or_article" copied EXACTLY from that \
chunk's header above - never invent a doc_id or section that isn't in \
the list above.

Return ONLY the JSON object, nothing else.
"""


def _format_chunks(chunks: list[dict]) -> str:
    lines = []
    for i, chunk in enumerate(chunks, start=1):
        section = chunk["section_or_article"] or "(no section)"
        lines.append(
            f"[{i}] doc_id={chunk['doc_id']} doc_type={chunk['doc_type']} "
            f"section={section} title={chunk['title']!r}\n{chunk['source_text']}"
        )
    return "\n\n".join(lines)


def reason_and_cite(state: GraphState) -> dict:
    chunks = state.get("reranked_chunks", [])
    question = state["question"]
    jurisdiction = state.get("jurisdiction") or "unspecified"

    if not chunks:
        return {
            "answer": "No relevant sources were found for this question. "
            "Please rephrase or consult a human IP facilitator.",
            "raw_citations": [],
        }

    prompt = _PROMPT_TEMPLATE.format(
        chunks_block=_format_chunks(chunks),
        question=question,
        jurisdiction=jurisdiction,
    )

    provider = settings.llm_reasoning_provider
    try:
        if provider:
            result = generate_json(prompt, provider=provider)
        else:
            result = generate_json(prompt)
    except (json.JSONDecodeError, KeyError, RuntimeError, ValueError):
        return {
            "answer": "The assistant could not produce a well-formed answer "
            "for this question. Please try rephrasing, or escalate to a "
            "human IP facilitator.",
            "raw_citations": [],
        }

    answer = result.get("answer", "")
    raw_citations: list[Citation] = [
        Citation(doc_id=c.get("doc_id", ""), section_or_article=c.get("section_or_article"))
        for c in result.get("citations", [])
        if isinstance(c, dict) and c.get("doc_id")
    ]

    return {"answer": answer, "raw_citations": raw_citations}

"""LLM reasoning constrained to the retrieved chunks - the model is only
shown these chunks and instructed to cite by exact doc_id + section, so
validate_citations can mechanically check every claim against what it
was actually given.
"""

from __future__ import annotations

import json

from app.graph.state import Citation, GraphState
from app.llm.ollama_client import generate_json

_PROMPT_TEMPLATE = """You are IP-SAKTI Sahayak, an assistant answering \
Ayurveda intellectual-property and regulatory questions. You are NOT a \
lawyer and must state this is information, not legal advice, when \
relevant. Answer ONLY using the numbered source chunks below - if they \
don't contain enough information to answer, say so plainly instead of \
guessing.

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
            f"[{i}] doc_id={chunk['doc_id']} section={section} "
            f"title={chunk['title']!r}\n{chunk['source_text']}"
        )
    return "\n\n".join(lines)


def reason_and_cite(state: GraphState) -> dict:
    chunks = state.get("reranked_chunks", [])
    question = state["question"]

    if not chunks:
        return {
            "answer": "No relevant sources were found for this question. "
            "Please rephrase or consult a human IP facilitator.",
            "raw_citations": [],
        }

    prompt = _PROMPT_TEMPLATE.format(chunks_block=_format_chunks(chunks), question=question)

    try:
        result = generate_json(prompt)
    except (json.JSONDecodeError, KeyError):
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

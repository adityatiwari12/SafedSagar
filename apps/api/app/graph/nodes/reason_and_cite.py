"""LLM reasoning constrained to the retrieved chunks - the model is only
shown these chunks and instructed to cite by exact doc_id + section, so
validate_citations can mechanically check every claim against what it
was actually given.
"""

from __future__ import annotations

import json
import re

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
{history_section}

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
- "answer": your answer as plain text. Every substantive claim MUST end \
with the bracket number(s) of the chunk(s) it came from, e.g. "...must \
register under Section 3 [1]." Use ONLY the bracket numbers shown before \
each chunk above ([1], [2], ...) - never a doc_id or section string \
inline, just the number.
- "next_steps": a short list (2-5 items) of concrete, actionable next \
steps for the user, grounded only in what the cited chunks actually say \
(e.g. "File Form I with the National Biodiversity Authority before \
commercial use" - not generic advice like "consult a lawyer" unless the \
chunks give nothing more specific).

Return ONLY the JSON object, nothing else.
"""


# Matches [1], [1,2], [1, 5] - the model sometimes groups multiple
# indices in one bracket rather than writing [1][5] separately.
_BRACKET_CITATION_RE = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")


def _extract_bracket_citations(texts: list[str], chunks: list[dict]) -> list[Citation]:
    """Map every [N] (or [N, M, ...]) marker across all given texts back
    to the Nth numbered chunk (1-indexed, matching _format_chunks).
    Citations built this way are valid by construction - N either indexes
    into `chunks` or it doesn't, there's no doc_id/section transcription
    for the model to get subtly wrong. This replaced asking the model for
    a separate citations JSON field, which the local model frequently
    filled with a doc_id/section that didn't exactly match its own
    numbered list, causing validate_citations to reject everything even
    when the answer's inline references were perfectly sound.

    Scans `answer` AND `next_steps` (not just `answer`): the model often
    puts its citation for a recommendation inside the next_steps item
    itself (e.g. "File Form I [4]") rather than repeating it in the
    prose answer - those are just as real and checkable.
    """
    seen: set[int] = set()
    citations: list[Citation] = []
    for text in texts:
        for match in _BRACKET_CITATION_RE.finditer(text):
            for index_str in match.group(1).split(","):
                index = int(index_str.strip())
                if index in seen or not (1 <= index <= len(chunks)):
                    continue
                seen.add(index)
                chunk = chunks[index - 1]
                citations.append(Citation(doc_id=chunk["doc_id"], section_or_article=chunk["section_or_article"]))
    return citations


def _format_chunks(chunks: list[dict]) -> str:
    lines = []
    for i, chunk in enumerate(chunks, start=1):
        section = chunk["section_or_article"] or "(no section)"
        lines.append(
            f"[{i}] doc_id={chunk['doc_id']} doc_type={chunk['doc_type']} "
            f"section={section} title={chunk['title']!r}\n{chunk['source_text']}"
        )
    return "\n\n".join(lines)


def _format_history_section(history_text: str | None) -> str:
    if not history_text:
        return ""
    return (
        f"\nCONVERSATION SO FAR:\n{history_text}\n\n"
        f"The user's latest message (QUESTION below) may refer back to "
        f"something already described above (e.g. \"it\"/\"this\") - "
        f"resolve it using that context. Do not ask the user to repeat "
        f"information they already gave.\n"
    )


def reason_and_cite(state: GraphState) -> dict:
    chunks = state.get("reranked_chunks", [])
    question = state["question"]
    jurisdiction = state.get("jurisdiction") or "unspecified"

    if not chunks:
        return {
            "answer": "No relevant sources were found for this question. "
            "Please rephrase or consult a human IP facilitator.",
            "raw_citations": [],
            "next_steps": ["Rephrase the question with more product/context detail",
                            "Escalate to a human IP facilitator"],
        }

    prompt = _PROMPT_TEMPLATE.format(
        chunks_block=_format_chunks(chunks),
        question=question,
        jurisdiction=jurisdiction,
        history_section=_format_history_section(state.get("history_text")),
    )

    provider = settings.llm_reasoning_provider
    reasoning_model = settings.ollama_reasoning_model
    # A local thinking model (e.g. gpt-oss:20b) can take tens of seconds per
    # call on CPU-only hardware even for a short prompt - verified live
    # (2026-09-15): ~44s for a trivial JSON reply with thinking enabled, and
    # thinking cannot be disabled without breaking JSON validity. The full
    # reason_and_cite prompt (chunks + conversation history) is much longer,
    # so give it real headroom instead of racing the default 120s budget.
    timeout = 240.0 if reasoning_model else 120.0
    # Reasoning-effort tuning for a thinking model, verified live
    # (2026-09-15): "low" cut a trivial warm call from ~44s to ~3.5s (still
    # valid JSON - unlike `think: false`, which breaks JSON validity
    # entirely). On the full multi-chunk prompt it still costs ~55s since
    # CPU token decode itself dominates once the answer is long, but it's
    # consistently faster than the unset default. keep_alive avoids paying
    # gpt-oss:20b's ~20-40s disk reload on every turn of a conversation
    # with gaps between messages.
    think = "low" if reasoning_model else None
    keep_alive = "30m" if reasoning_model else None

    def _generate() -> dict:
        return generate_json(prompt, timeout, provider=provider, model=reasoning_model, think=think, keep_alive=keep_alive)

    # Small local models occasionally emit malformed JSON, especially on
    # longer prompts (e.g. once conversation history is folded into the
    # question - verified live 2026-09-15: ~1 in 3 calls failed on a
    # contextualized follow-up, and the identical retry succeeded with a
    # real, on-topic answer). One retry before falling back to the
    # "could not produce a well-formed answer" abstention - cheap, and it
    # turns a chunk of genuine model hiccups into a real answer instead
    # of a dead end that looks like the system didn't understand.
    result = None
    for _attempt in range(2):
        try:
            result = _generate()
            break
        except (json.JSONDecodeError, KeyError, RuntimeError, ValueError):
            continue

    if result is None:
        return {
            "answer": "The assistant could not produce a well-formed answer "
            "for this question. Please try rephrasing, or escalate to a "
            "human IP facilitator.",
            "raw_citations": [],
            "next_steps": ["Rephrase the question", "Escalate to a human IP facilitator"],
        }

    answer = result.get("answer", "")
    next_steps = [s for s in result.get("next_steps", []) if isinstance(s, str) and s.strip()]
    raw_citations = _extract_bracket_citations([answer, *next_steps], chunks)

    return {"answer": answer, "raw_citations": raw_citations, "next_steps": next_steps}

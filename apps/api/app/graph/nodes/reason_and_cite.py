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
authority from any other jurisdiction.
{history_section}

If, and ONLY if, the question is phrased as a yes/no question ("can I \
patent X", "is X allowed", "do I need to register", "must I..."), your \
FIRST sentence MUST be a direct verdict before any procedure or next \
steps - pick the ONE opener that actually fits: "Yes,", "No,", "Likely \
not,", "Uncertain," or, when the real answer is conditional, "Yes, but \
only if...," / "Generally yes, subject to...,". Never write a verdict \
that contradicts itself (e.g. "Yes, ... No, ..." in the same answer) - \
if the honest answer is conditional, say so as ONE conditional sentence, \
don't tack on a second, opposite verdict afterward. A user who asks "can \
I patent this" wants to know if they can, not just how filing works. A \
question asking WHAT rules/obligations apply, or HOW something works, is \
NOT a yes/no question - do not force a Yes/No/Likely-not opener onto it.

Regardless of question shape, "answer" must always be a real, substantive \
explanation, never just a bare verdict word or a one-sentence stub. State \
the applicable rule(s) and how they apply to the facts given, with \
citations - a verdict opener (when one applies) is the first sentence of \
that explanation, not the whole answer.

Apply the retrieved rules to the SPECIFIC facts in the question, even if \
the chunks don't name the exact product. E.g. if a chunk excludes \
"traditional knowledge" or something "known to the public" from \
patentability, and the question describes a well-known traditional \
remedy, that exclusion applies - say so plainly, don't just describe the \
filing process as if the exclusion weren't relevant. This is applying a \
retrieved rule to given facts, not inventing law - still cite the chunk \
providing the exclusion.

Genuine uncertainty is a valid, honest answer - if the chunks don't let \
you form a real verdict either way, say "Uncertain," and explain exactly \
what's missing (e.g. "depends on whether your formulation differs from \
the known traditional use") rather than defaulting to generic procedure \
to avoid committing to an answer.

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
- "clarifying_question": a single specific question, or null. Set this \
ONLY when the question is genuinely too under-specified to give a \
precise answer - it names a broad category instead of a specific thing \
(e.g. "Indian medicinal plants" instead of naming one; "my formulation" \
with no ingredients given) AND the missing detail would actually change \
which rule/obligation applies. This includes patentability questions \
that turn on whether there is a genuine inventive step: Section 3(p) \
(or an equivalent exclusion chunk) bars traditional knowledge "as such", \
NOT a real inventive advance built on top of it - if the user says they \
"developed"/"invented" a formulation using a known herb/classical \
ingredient but names no actual novelty (no specific new ratio, \
combination, extraction/delivery method, dosage form, or measured \
effect not already in the classical/traditional record), that missing \
detail is exactly what decides patentable-vs-excluded - ask what's \
novel about it rather than assuming either way. Do NOT set it just \
because the topic is complex, or to avoid committing to a verdict - if \
you can give a correct general answer that covers the reasonable cases, \
do that instead and leave this null. Still fill "answer" with your best \
general answer even when you also set this - it's shown only if the \
graph decides to ask instead of answer.

Return ONLY the JSON object, nothing else.
"""


# Matches [1], [1,2], [1, 5] - the model sometimes groups multiple
# indices in one bracket rather than writing [1][5] separately.
_BRACKET_CITATION_RE = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")

# Deterministic backstop for the "claims novelty, names none" pattern the
# prompt's clarifying_question guidance above asks the model to catch -
# verified live (2026-09-17): llama3.2 (3B, CPU) missed it on 3/3 identical
# runs of "I developed a new Ayurvedic formulation using Ashwagandha. Can I
# patent it?", giving a confident "No, it's traditional knowledge" without
# ever asking what's actually novel about the formulation. Prompt wording
# alone isn't reliable for this multi-condition judgment on a small local
# model, so this is checked in code instead: a keyword heuristic, not a
# real understanding of the question - it can miss phrasings or, more
# rarely, fire when the user already gave enough detail. Only overrides a
# null clarifying_question (never replaces one the model already asked),
# and only when the model's own answer already leans on a TK exclusion -
# i.e. exactly the case where "what's novel about it" would change the
# verdict, not every patent question about a known herb.
_NOVELTY_CLAIM_RE = re.compile(r"\b(developed|invented|created|formulated)\b", re.IGNORECASE)
_NOVELTY_DETAIL_RE = re.compile(
    r"\b(\d+(\.\d+)?\s*%|\d+\s*mg|extract|combination of|ratio|dosage|capsule|tablet|synerg\w*)\b",
    re.IGNORECASE,
)
_TK_EXCLUSION_ANSWER_RE = re.compile(
    r"traditional knowledge|\bas such\b|3\(p\)|not patentable|excluded", re.IGNORECASE
)


def _needs_novelty_clarification(question: str, answer: str) -> bool:
    return bool(
        _NOVELTY_CLAIM_RE.search(question)
        and not _NOVELTY_DETAIL_RE.search(question)
        and _TK_EXCLUSION_ANSWER_RE.search(answer)
    )


_NOVELTY_CLARIFYING_QUESTION = (
    "What specifically is novel about your formulation compared to the known/classical "
    "use - a new ingredient combination or ratio, extraction/processing method, dosage "
    "form, or a documented effect not found in classical texts? This determines whether "
    "it's excluded as traditional knowledge \"as such\" or may qualify as a genuine "
    "inventive step."
)


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
            "clarifying_question": None,
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
    # A blank "answer" in otherwise-valid JSON is the same failure mode as
    # malformed JSON - the model produced nothing usable - and was
    # previously invisible: it returned confidence 0.0 and zero citations
    # but the caller had no signal to distinguish it from a real (if thin)
    # answer, so the user just saw an empty response. Retried the same as
    # a parse failure instead of accepted as-is.
    #
    # A non-blank but bare-verdict answer (e.g. "No, [7]") is the same
    # failure mode again, just non-empty - verified live (2026-09-17): the
    # prompt instructs the model to always explain, not just verdict, but
    # llama3.2 (3B, CPU) doesn't reliably follow that on every sample; the
    # identical question re-asked a minute later produced a full, correctly
    # cited paragraph. Word-count is a crude substantiveness check but a
    # real explanation with citations clears it easily, while a bare
    # verdict doesn't - so treat "too short" the same as "blank": worth one
    # retry. Keeps a non-substantive candidate as a fallback (never worse
    # than before this change) rather than discarding it outright, in case
    # both attempts come back short.
    # 3 attempts, not 2 - verified live (2026-09-17): a bare-verdict answer
    # can recur on back-to-back samples of the same question, so 2 tries
    # isn't always enough headroom to land a substantive one.
    MIN_SUBSTANTIVE_WORDS = 8
    result = None
    fallback = None
    for _attempt in range(3):
        try:
            candidate = _generate()
            answer_text = candidate.get("answer", "").strip()
            if not answer_text:
                continue
            if len(answer_text.split()) >= MIN_SUBSTANTIVE_WORDS:
                result = candidate
                break
            fallback = fallback or candidate
        except (json.JSONDecodeError, KeyError, RuntimeError, ValueError):
            continue

    if result is None:
        result = fallback

    if result is None:
        return {
            "answer": "The assistant could not produce a well-formed answer "
            "for this question. Please try rephrasing, or escalate to a "
            "human IP facilitator.",
            "raw_citations": [],
            "next_steps": ["Rephrase the question", "Escalate to a human IP facilitator"],
            "clarifying_question": None,
        }

    answer = result.get("answer", "")
    next_steps = [s for s in result.get("next_steps", []) if isinstance(s, str) and s.strip()]
    raw_citations = _extract_bracket_citations([answer, *next_steps], chunks)
    clarifying_question = result.get("clarifying_question")
    if not isinstance(clarifying_question, str) or not clarifying_question.strip():
        clarifying_question = None

    if clarifying_question is None and _needs_novelty_clarification(question, answer):
        clarifying_question = _NOVELTY_CLARIFYING_QUESTION

    return {
        "answer": answer,
        "raw_citations": raw_citations,
        "next_steps": next_steps,
        "clarifying_question": clarifying_question,
    }

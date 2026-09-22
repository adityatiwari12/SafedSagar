"""Decide whether the conversation so far carries enough information to
give a specific, well-grounded answer - or whether one more targeted
follow-up question is worth asking first.

This is the multi-round conversational intake gate (FR-01, CLAUDE.md:
"Conversational intake + minimum clarifying questions"). It replaces the
old one-shot behaviour where a single fixed list of three static
questions was asked once and the pipeline then always ploughed on to a
full answer, however little it actually understood. Runs inside
run_classification() - the cheap condense_query + classify_product pass
chat/router.py already makes before committing to retrieval - so the
intake decision costs one small LLM call and never pays for retrieval or
the slow reason_and_cite call on a turn whose answer would be discarded.

The round cap itself lives in chat/router.py (it needs the conversation's
message history, which the graph has no access to); this node only judges
sufficiency for the current turn.
"""

from __future__ import annotations

import json

from app.graph.state import GraphState
from app.llm.generate import generate_json

_PROMPT_TEMPLATE = """You are deciding whether you have enough information to \
give a specific, well-grounded answer about an Ayurveda product's IP, \
regulatory, or ABS/biodiversity status - not whether the topic is \
interesting, but whether you could classify the product and answer \
precisely right now.
{history_section}
LATEST MESSAGE: {question}
PRODUCT CATEGORY SO FAR: {product_classification}

You have enough information when you know, at minimum:
1. What the product/formulation actually is (named ingredients, source, or \
form - not just "an Ayurvedic product")
2. What specifically the user wants to know (e.g. patentability, trademark, \
a specific regulatory approval, ABS/biodiversity compliance, or general \
guidance - not just "help with IP")

You do NOT need every possible detail - only enough to give a real, \
specific answer rather than a generic one. If the category above is \
already a real, non-"unclear" category and the user has named what they \
want to know, that is usually enough - do not ask more questions just \
because more detail is theoretically available.

Respond with a JSON object:
{{"sufficient": true or false, "question": "<one specific, natural \
follow-up question>" or null}}

If insufficient, the question must target the single biggest gap - not a \
checklist, one focused question, phrased naturally as you would ask a \
person in conversation, not a form field label.

Return ONLY the JSON object.
"""


def _format_history_section(history_text: str | None) -> str:
    """Prior turns as a labelled block for the prompt above.

    Deliberately a local ~5-line helper rather than importing
    reason_and_cite._format_history_section: that one's trailing
    instruction refers to "QUESTION below", which this prompt doesn't
    have (it says LATEST MESSAGE), and its guidance is about resolving
    pronouns in an answer rather than about not re-asking for detail the
    user already supplied - which is the failure mode that actually
    matters here.
    """
    if not history_text:
        return ""
    return (
        f"\nCONVERSATION SO FAR:\n{history_text}\n\n"
        f"Everything the user has already told you above counts as "
        f"information you have - never ask again for a detail they have "
        f"already given.\n"
    )


def assess_intake(state: GraphState) -> dict:
    question = state.get("question") or state.get("retrieval_query", "")
    prompt = _PROMPT_TEMPLATE.format(
        history_section=_format_history_section(state.get("history_text")),
        question=question,
        product_classification=state.get("product_classification", "unclear"),
    )

    # Fail OPEN on any malformed reply, exactly as classify_product falls
    # back to "unclear" on its own parse failures. The asymmetry is
    # deliberate: a bad parse that defaulted to "insufficient" would keep
    # asking questions the user can't escape by answering them, turning a
    # transient LLM hiccup into a conversation that never reaches an
    # answer. Defaulting to "sufficient" costs at most one slightly
    # under-informed answer.
    try:
        result = generate_json(prompt)
        sufficient = result.get("sufficient", True)
        follow_up = result.get("question")
    except (json.JSONDecodeError, KeyError, RuntimeError, ValueError, TypeError):
        return {"intake_sufficient": True, "intake_question": None}

    if not isinstance(sufficient, bool):
        sufficient = True
    if not isinstance(follow_up, str) or not follow_up.strip():
        follow_up = None

    return {"intake_sufficient": sufficient, "intake_question": follow_up}

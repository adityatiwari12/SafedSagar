"""Classify the user's question into one of the PRD's six formulation
categories (or "unclear") before any IP/regulatory guidance is given -
each category has a very different IP/ABS posture (CLAUDE.md, Core
architecture principle)."""

from __future__ import annotations

import json

from app.graph.state import PRODUCT_CATEGORIES, GraphState
from app.llm.generate import generate_json

_PROMPT_TEMPLATE = """Classify the Ayurvedic product or innovation described \
in the question below into exactly one of these categories:

- classical_or_generic_medicine: formulation and method drawn from a \
First-Schedule authoritative classical text
- patent_or_proprietary_medicine: a proprietary Ayurvedic medicine
- new_or_non_classical_drug: a new drug requiring proof of safety and \
effectiveness
- phytopharmaceutical: a phytopharmaceutical drug
- ayurveda_aahara_or_nutraceutical: a food, Ayurveda-Aahar, or nutraceutical
- cosmetic: a cosmetic product
- unclear: not enough information in the question to classify
- out_of_scope: the question is NOT about an Ayurvedic product/formulation \
or its IP, biodiversity/ABS, or regulatory status at all (e.g. general \
chit-chat, coding help, weather, unrelated law/medicine). Use this, not \
"unclear", when the topic itself is wrong rather than merely under-specified. \
A question that names actual ingredients, a product form, or an IP/ \
regulatory ask (patent, trademark, GI, ABS, food/cosmetic approval) is \
NEVER out_of_scope, even if you'd classify it as "unclear" on category \
specifics - out_of_scope means the topic itself is wrong, not that a \
category is hard to pick.

QUESTION: {question}

Respond with a JSON object: {{"category": "<one of the categories above>"}}
Return ONLY the JSON object.
"""


def _classify_once(question: str) -> str:
    prompt = _PROMPT_TEMPLATE.format(question=question)
    try:
        result = generate_json(prompt)
        category = result.get("category", "unclear")
    except (json.JSONDecodeError, KeyError):
        category = "unclear"
    return category if category in PRODUCT_CATEGORIES else "unclear"


# out_of_scope is a hard refusal (chat/router.py short-circuits the entire
# turn on it - no retrieval, no answer) - the single most costly
# misclassification this node can make. Verified live (2026-09-23) to be a
# real, non-deterministic failure mode on this model, and worse than a
# single retry: the exact same well-specified, clearly in-scope question
# ("topical oil, Brahmi/Bhringraj, trademark in India") hit out_of_scope on
# BOTH attempts of a 2-attempt retry in one live run, out of 3 - a single
# retry only catches an isolated miss, not a run where the model misfires
# twice in a row on the same input. 3 attempts, first non-out_of_scope
# result wins (same "give the model more chances before trusting the worst
# outcome" shape as reason_and_cite's substantiveness retry elsewhere in
# this graph) - a genuine false-positive rate would need all 3 samples to
# agree, which is a much stronger signal than 1-of-1 or 1-of-2.
_OUT_OF_SCOPE_MAX_ATTEMPTS = 3


def classify_product(state: GraphState) -> dict:
    question = state["retrieval_query"]
    category = _classify_once(question)

    # Only retry when there's conversation history to sanity-check
    # against: a conversation already this far in has, by construction,
    # already been through a real exchange about an Ayurvedic product, so
    # a sudden out_of_scope reading is exactly the risky case. A cold-open
    # message has no such prior signal - if it's genuinely off-topic,
    # refusing immediately on the first read is correct, not retried.
    if category == "out_of_scope" and state.get("history_text"):
        for _attempt in range(_OUT_OF_SCOPE_MAX_ATTEMPTS - 1):
            category = _classify_once(question)
            if category != "out_of_scope":
                break

    return {"product_classification": category}

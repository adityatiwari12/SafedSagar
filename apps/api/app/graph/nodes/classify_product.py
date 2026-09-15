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

QUESTION: {question}

Respond with a JSON object: {{"category": "<one of the categories above>"}}
Return ONLY the JSON object.
"""


def classify_product(state: GraphState) -> dict:
    question = state["retrieval_query"]
    prompt = _PROMPT_TEMPLATE.format(question=question)

    try:
        result = generate_json(prompt)
        category = result.get("category", "unclear")
    except (json.JSONDecodeError, KeyError):
        category = "unclear"

    if category not in PRODUCT_CATEGORIES:
        category = "unclear"

    return {"product_classification": category}

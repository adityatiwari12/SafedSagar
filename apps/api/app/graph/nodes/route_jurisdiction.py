"""Jurisdiction routing. FR-04 requires an explicit India/international
switch so answers are never conflated - if the caller already provided
one (the frontend's jurisdiction toggle), that's honored as-is and never
overridden. Only when nothing was provided does this node infer a
best-guess default from the question text, clearly flagged as inferred
so a future UI can prompt the user to confirm rather than silently
trusting a guess."""

from __future__ import annotations

import json

from app.graph.state import GraphState
from app.llm.ollama_client import generate_json

_VALID_JURISDICTIONS = {"india", "international"}

_PROMPT_TEMPLATE = """Read the question below and decide whether it is \
primarily about INDIAN law/regulation/registries, or INTERNATIONAL \
(treaties, foreign markets, PCT/Madrid/WIPO, export). If genuinely \
ambiguous or both, default to "india" (this assistant's corpus is \
India-first).

QUESTION: {question}

Respond with a JSON object: {{"jurisdiction": "india" or "international"}}
Return ONLY the JSON object.
"""


def route_jurisdiction(state: GraphState) -> dict:
    if state.get("jurisdiction") in _VALID_JURISDICTIONS:
        return {"jurisdiction_source": "explicit"}

    prompt = _PROMPT_TEMPLATE.format(question=state["question"])
    try:
        result = generate_json(prompt)
        jurisdiction = result.get("jurisdiction", "india")
    except (json.JSONDecodeError, KeyError):
        jurisdiction = "india"

    if jurisdiction not in _VALID_JURISDICTIONS:
        jurisdiction = "india"

    return {"jurisdiction": jurisdiction, "jurisdiction_source": "inferred"}

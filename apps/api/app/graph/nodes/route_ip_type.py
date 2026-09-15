"""Multi-label IP-type routing (FR-03) - an Ayurvedic product question can
touch several IP regimes at once (e.g. patent + ABS), so this returns a
list, not a single category."""

from __future__ import annotations

import json

from app.graph.state import IP_TYPES, GraphState
from app.llm.ollama_client import generate_json

_PROMPT_TEMPLATE = """Which of these IP/regulatory regimes are relevant to \
the question below? Select ALL that apply (a question can touch several \
at once):

{ip_types_list}

QUESTION: {question}

Respond with a JSON object: {{"ip_types": ["<one or more of the values above>"]}}
Return ONLY the JSON object.
"""


def route_ip_type(state: GraphState) -> dict:
    ip_types_list = "\n".join(f"- {t}" for t in IP_TYPES)
    prompt = _PROMPT_TEMPLATE.format(ip_types_list=ip_types_list, question=state["question"])

    try:
        result = generate_json(prompt)
        raw_types = result.get("ip_types", [])
    except (json.JSONDecodeError, KeyError):
        raw_types = []

    ip_types = [t for t in raw_types if t in IP_TYPES]
    return {"ip_types": ip_types}

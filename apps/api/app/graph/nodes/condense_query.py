"""Condense a follow-up turn into a standalone query for retrieval/routing.

Multi-turn conversations fold prior history into the graph so pronouns
like "it"/"this" resolve to the right product (chat/router.py). But
feeding that same raw transcript into classify_product/route_jurisdiction/
route_ip_type/retrieve pollutes them: BM25 tokenizes the whole
conversation's vocabulary instead of just the current info need, vector
embed centers on a multi-paragraph blob instead of a focused question,
and the small local classifier model has to parse conversational filler
just to pick one category label.

This node produces a short, self-contained rewrite of the latest turn -
`retrieval_query` - used by everything except the final answer.
reason_and_cite keeps `history_text` directly for real pronoun/context
resolution in the prose answer, which needs the full transcript, not a
condensed query.
"""

from __future__ import annotations

import json

import httpx

from app.graph.state import GraphState
from app.llm.generate import generate_json

_PROMPT_TEMPLATE = """Conversation so far:
{history_text}

User's latest message: {question}

Rewrite the user's latest message as ONE standalone question that makes \
sense without the conversation above - resolve any "it"/"this"/pronoun by \
naming the actual product or topic already discussed. Keep it short and \
on-topic; do not add information that wasn't in the conversation.

Respond with a JSON object: {{"standalone_question": "<rewritten question>"}}
Return ONLY the JSON object.
"""


def condense_query(state: GraphState) -> dict:
    history_text = state.get("history_text")
    question = state["question"]
    if not history_text:
        return {"retrieval_query": question}

    prompt = _PROMPT_TEMPLATE.format(history_text=history_text, question=question)
    try:
        result = generate_json(prompt)
        standalone = result.get("standalone_question", "")
        standalone = standalone.strip() if isinstance(standalone, str) else ""
    except (json.JSONDecodeError, KeyError, RuntimeError, ValueError, httpx.HTTPError):
        # This node adds a network round-trip that didn't exist before -
        # a malformed reply, timeout, or connection hiccup here must fall
        # back to the raw question, never block the turn. Broad on purpose:
        # this is a best-effort rewrite, not a step the turn depends on.
        standalone = ""

    return {"retrieval_query": standalone or question}

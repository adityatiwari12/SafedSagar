"""Prompt contract for reason_and_cite (no LLM call)."""

from app.graph.nodes import reason_and_cite as rac


def test_prompt_template_locks_jurisdiction_and_gratk():
    text = rac._PROMPT_TEMPLATE
    assert "JURISDICTION FOR THIS ANSWER" in text
    assert "not legal advice" in text.lower()
    assert "NOT YET IN FORCE" in text
    assert "gratk" in text.lower()

"""classify_product's out_of_scope retry - verified live (2026-09-23) as a
real non-deterministic failure mode: the identical well-specified,
in-scope question returned out_of_scope on one sample and a real category
on the next two. A hard refusal deserves a retry when there's conversation
history to sanity-check against; a cold-open message doesn't get one."""

from unittest.mock import patch

from app.graph.nodes.classify_product import classify_product


def test_out_of_scope_with_history_recovers_on_second_attempt():
    calls = iter([{"category": "out_of_scope"}, {"category": "cosmetic"}])
    with patch(
        "app.graph.nodes.classify_product.generate_json",
        side_effect=lambda *a, **k: next(calls),
    ) as mock_generate:
        result = classify_product(
            {"retrieval_query": "trademark my hair oil", "history_text": "User: ...\nAssistant: ..."}
        )
    assert result["product_classification"] == "cosmetic"
    assert mock_generate.call_count == 2


def test_out_of_scope_with_history_recovers_on_third_attempt():
    calls = iter([{"category": "out_of_scope"}, {"category": "out_of_scope"}, {"category": "cosmetic"}])
    with patch(
        "app.graph.nodes.classify_product.generate_json",
        side_effect=lambda *a, **k: next(calls),
    ) as mock_generate:
        result = classify_product(
            {"retrieval_query": "trademark my hair oil", "history_text": "User: ...\nAssistant: ..."}
        )
    assert result["product_classification"] == "cosmetic"
    assert mock_generate.call_count == 3


def test_out_of_scope_without_history_is_not_retried():
    with patch(
        "app.graph.nodes.classify_product.generate_json",
        return_value={"category": "out_of_scope"},
    ) as mock_generate:
        result = classify_product({"retrieval_query": "what's the weather", "history_text": None})
    assert result["product_classification"] == "out_of_scope"
    assert mock_generate.call_count == 1


def test_out_of_scope_confirmed_three_times_is_accepted():
    with patch(
        "app.graph.nodes.classify_product.generate_json",
        return_value={"category": "out_of_scope"},
    ) as mock_generate:
        result = classify_product(
            {"retrieval_query": "write me a poem", "history_text": "User: ...\nAssistant: ..."}
        )
    assert result["product_classification"] == "out_of_scope"
    assert mock_generate.call_count == 3


def test_non_out_of_scope_category_is_not_retried():
    with patch(
        "app.graph.nodes.classify_product.generate_json",
        return_value={"category": "cosmetic"},
    ) as mock_generate:
        result = classify_product(
            {"retrieval_query": "trademark my hair oil", "history_text": "User: ...\nAssistant: ..."}
        )
    assert result["product_classification"] == "cosmetic"
    assert mock_generate.call_count == 1

"""BM25 cache behaviour — pure unit tests with stubs (no Postgres/Chroma)."""

from __future__ import annotations

from app.graph.nodes import retrieve as retrieve_mod


def test_invalidate_bm25_cache_clears_module_cache():
    retrieve_mod._bm25_cache["india|None"] = object()  # type: ignore[assignment]
    retrieve_mod.invalidate_bm25_cache()
    assert retrieve_mod._bm25_cache == {}


def test_cache_key_includes_jurisdiction_and_doc_type():
    assert retrieve_mod._bm25_cache_key("india", "statute") == "india|statute"
    assert retrieve_mod._bm25_cache_key(None, None) == "None|None"

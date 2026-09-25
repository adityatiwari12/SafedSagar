"""Tests for the researcher-persona prior-art search endpoint (GET
/research/prior-art). Follows tests/test_abs.py's style: httpx `client` +
`make_user` fixtures, real corpus data (no mocking retrieve/rerank) since
the whole point is that results are real, sourced corpus rows."""


async def _auth_headers(make_user, role: str = "user"):
    _email, _password, token = await make_user(role=role)
    return {"Authorization": f"Bearer {token}"}


async def test_search_returns_real_sourced_results(client, make_user):
    headers = await _auth_headers(make_user)
    resp = await client.get("/research/prior-art", params={"q": "biological diversity act"}, headers=headers)
    assert resp.status_code == 200, resp.text
    results = resp.json()
    assert isinstance(results, list)
    assert len(results) > 0
    for r in results:
        assert r["doc_id"]
        assert r["title"]
        assert r["authority"]
        assert r["jurisdiction"] in ("india", "international")
        assert r["snippet"]


async def test_query_too_short_is_422(client, make_user):
    headers = await _auth_headers(make_user)
    resp = await client.get("/research/prior-art", params={"q": "ab"}, headers=headers)
    assert resp.status_code == 422


async def test_facilitator_role_cannot_search(client, make_user):
    headers = await _auth_headers(make_user, role="facilitator")
    resp = await client.get("/research/prior-art", params={"q": "biological diversity act"}, headers=headers)
    assert resp.status_code == 403


async def test_jurisdiction_filter_only_returns_that_jurisdiction(client, make_user):
    headers = await _auth_headers(make_user)
    resp = await client.get(
        "/research/prior-art",
        params={"q": "patent traditional knowledge", "jurisdiction": "india"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    for r in resp.json():
        assert r["jurisdiction"] == "india"

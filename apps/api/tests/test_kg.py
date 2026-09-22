"""Legal knowledge graph (app/kg): builder guarantees + answer-time
expansion rules. Runs against the live dev DB like the rest of the suite;
every test that needs a graph (re)builds it, which is idempotent."""

import re
import uuid
from datetime import date

import pytest
from sqlalchemy import delete, func, select, text

from app.chat.router import NODE_TO_STEP
from app.db.base import AsyncSessionLocal, engine
from app.db.models import (
    Jurisdiction,
    KgEdge,
    KgEdgeOrigin,
    KgNode,
    KgNodeType,
    KgRelation,
    SourceDocument,
)
from app.graph.graph import REMAINING_NODES
from app.kg.build import (
    GRATK_DOC_ID,
    build_graph,
    load_corpus,
    load_curated_spec,
    resolve_curated_entry,
)
from app.kg.expand import expand

PATENTS_ACT = "ipindia-patents-act-1970"


async def _build():
    async with AsyncSessionLocal() as session:
        return await build_graph(session)


async def _counts(session) -> tuple:
    nodes = (await session.execute(select(KgNode.node_type, func.count()).group_by(KgNode.node_type))).all()
    edges = (await session.execute(
        select(KgEdge.relation, KgEdge.origin, func.count()).group_by(KgEdge.relation, KgEdge.origin)
    )).all()
    return sorted((str(a), b) for a, b in nodes), sorted((str(a), str(b), c) for a, b, c in edges)


async def _chunk(session, doc_id: str, section: str | None) -> dict:
    stmt = select(SourceDocument).where(SourceDocument.doc_id == doc_id)
    stmt = stmt.where(SourceDocument.section_or_article.is_(None) if section is None
                      else SourceDocument.section_or_article == section)
    row = (await session.execute(stmt.order_by(SourceDocument.id).limit(1))).scalar_one()
    return {"id": row.id, "doc_id": row.doc_id, "doc_type": row.doc_type, "section_or_article": row.section_or_article,
            "source_text": row.source_text, "title": row.title, "source_url": row.source_url or ""}


async def _jurisdiction_of_docs(session, doc_ids: set[str]) -> set[str]:
    rows = (await session.execute(
        select(SourceDocument.jurisdiction).where(SourceDocument.doc_id.in_(doc_ids)).distinct()
    )).scalars().all()
    return {getattr(j, "value", j) for j in rows}


@pytest.mark.asyncio
async def test_builder_is_idempotent():
    await _build()
    async with AsyncSessionLocal() as session:
        first = await _counts(session)
    await _build()
    async with AsyncSessionLocal() as session:
        second = await _counts(session)
    assert first == second
    assert first[0] and first[1]


@pytest.mark.asyncio
async def test_every_curated_edge_provenance_resolves():
    """The no-fabrication guarantee: every curated entry names a real
    source_documents row AND its evidence text is actually in that row."""
    spec = load_curated_spec()
    async with AsyncSessionLocal() as session:
        corpus = await load_corpus(session)
    doc_node_key = {d: f"doc:{d}" for d in corpus.doc_ids}
    failures = []
    for entry in spec["edges"]:
        edge, reason = resolve_curated_entry(entry, corpus, doc_node_key)
        if edge is None:
            failures.append(f"{entry.get('src')} -> {entry.get('dst')}: {reason}")
    assert not failures, failures

    # ...and every curated edge that made it into the DB resolves too.
    await _build()
    async with AsyncSessionLocal() as session:
        curated = (await session.execute(select(KgEdge).where(KgEdge.origin == KgEdgeOrigin.curated))).scalars().all()
        assert len(curated) == len(spec["edges"])
        for e in curated:
            stmt = select(func.count()).select_from(SourceDocument).where(SourceDocument.doc_id == e.source_doc_id)
            if e.source_section is not None:
                stmt = stmt.where(SourceDocument.section_or_article == e.source_section)
            assert await session.scalar(stmt) > 0, (e.source_doc_id, e.source_section)
            assert e.source_chunk_id and await session.get(SourceDocument, e.source_chunk_id) is not None


@pytest.mark.asyncio
async def test_all_edges_have_resolvable_provenance():
    await _build()
    async with AsyncSessionLocal() as session:
        bad = await session.scalar(text("""
            SELECT count(*) FROM kg_edges e
            WHERE NOT EXISTS (
                SELECT 1 FROM source_documents s
                WHERE s.doc_id = e.source_doc_id
                  AND (e.source_section IS NULL OR s.section_or_article = e.source_section))
        """))
    assert bad == 0


@pytest.mark.asyncio
async def test_no_node_for_doc_absent_from_corpus():
    await _build()
    async with AsyncSessionLocal() as session:
        orphan_docs = await session.scalar(text("""
            SELECT count(*) FROM kg_nodes n WHERE n.doc_id IS NOT NULL
              AND NOT EXISTS (SELECT 1 FROM source_documents s WHERE s.doc_id = n.doc_id)
        """))
        orphan_provisions = await session.scalar(text("""
            SELECT count(*) FROM kg_nodes n WHERE n.node_type = 'provision'
              AND NOT EXISTS (SELECT 1 FROM source_documents s
                              WHERE s.doc_id = n.doc_id AND s.section_or_article = n.section_or_article)
        """))
        # Laws known to be missing from the corpus must not get nodes.
        # Drugs and Magic Remedies Act, PPV&FR Act, and the Hague Geneva
        # Act were ingested (ingestion/source_registry.yaml,
        # 2026-09-22) - removed from this list because they now
        # legitimately have nodes, not because this check was relaxed.
        # Pharmacopoeia is still genuinely absent (no accessible official
        # source found yet) and stays covered.
        for missing in ("pharmacopoeia",):
            n = await session.scalar(
                select(func.count()).select_from(KgNode)
                .where(KgNode.node_type.in_([KgNodeType.statute, KgNodeType.rules, KgNodeType.treaty]))
                .where(func.lower(KgNode.label).contains(missing))
            )
            assert n == 0, missing
    assert orphan_docs == 0
    assert orphan_provisions == 0


@pytest.mark.asyncio
async def test_patents_act_fragments_canonicalize_to_one_statute_node():
    fragment_id = f"{PATENTS_ACT}-{uuid.uuid4().hex[:8]}"
    async with AsyncSessionLocal() as session:
        session.add(SourceDocument(
            id=f"{fragment_id}#kgtest", doc_id=fragment_id, title="The Patents Act, 1970 - Section 3(p)",
            authority="Office of the Controller General of Patents, Designs & Trade Marks",
            jurisdiction=Jurisdiction.india, doc_type="statute", effective_date=date(1972, 4, 20),
            section_or_article="Section 3(p)", source_url="https://ipindia.gov.in/patents-act.htm",
            source_text="kg canonicalization test fragment",
        ))
        await session.commit()
    try:
        report = await _build()
        assert report.fragments_canonicalized >= 1
        async with AsyncSessionLocal() as session:
            statutes = (await session.execute(
                select(KgNode).where(KgNode.node_type == KgNodeType.statute)
                .where(KgNode.doc_id.like(f"{PATENTS_ACT}%"))
            )).scalars().all()
            assert [n.key for n in statutes] == [f"statute:{PATENTS_ACT}"]
            fragment_nodes = (await session.execute(select(KgNode.doc_id).where(KgNode.doc_id.isnot(None)))).scalars().all()
            assert not [d for d in fragment_nodes if re.search(r"-[0-9a-f]{8}$", d)]
    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(SourceDocument).where(SourceDocument.doc_id == fragment_id))
            await session.commit()


@pytest.mark.asyncio
async def test_refers_to_edges_only_point_at_existing_provisions():
    await _build()
    async with AsyncSessionLocal() as session:
        dst_types = (await session.execute(text("""
            SELECT DISTINCT d.node_type FROM kg_edges e JOIN kg_nodes d ON d.id = e.dst_id
            WHERE e.relation = 'REFERS_TO'
        """))).scalars().all()
        dangling = await session.scalar(text("""
            SELECT count(*) FROM kg_edges e JOIN kg_nodes d ON d.id = e.dst_id
            WHERE e.relation = 'REFERS_TO' AND NOT EXISTS (
                SELECT 1 FROM source_documents s
                WHERE s.doc_id = d.doc_id AND s.section_or_article = d.section_or_article)
        """))
        max_conf = await session.scalar(
            select(func.max(KgEdge.confidence)).where(KgEdge.relation == KgRelation.REFERS_TO)
        )
    assert set(dst_types) <= {"provision"}
    assert dangling == 0
    assert max_conf is None or max_conf < 1.0


@pytest.mark.asyncio
async def test_gratk_marked_not_in_force():
    await _build()
    async with AsyncSessionLocal() as session:
        node = (await session.execute(select(KgNode).where(KgNode.key == f"treaty:{GRATK_DOC_ID}"))).scalar_one()
    assert "not yet in force" in node.label.lower()


async def _cross_jurisdiction_state(session, jurisdiction):
    # Seeds chosen to touch BOTH sides: BD Act preamble IMPLEMENTS CBD
    # (india -> international); ip_type/concept seeds have curated edges
    # into both jurisdictions.
    chunks = [
        await _chunk(session, "india-biological-diversity-act-2002", None),
        await _chunk(session, "india-biological-diversity-act-2002", "3"),
        await _chunk(session, "wipo-nagoya-protocol-2010", "3"),
    ]
    if jurisdiction:
        chunks = [c for c in chunks if (await _jurisdiction_of_docs(session, {c["doc_id"]})) == {jurisdiction}]
    return {
        "question": "Can I patent a traditional knowledge formulation using genetic resources? benefit sharing",
        "retrieval_query": "patent traditional knowledge genetic resources benefit sharing",
        "jurisdiction": jurisdiction,
        "product_classification": "classical_or_generic_medicine",
        "ip_types": ["patent", "access_and_benefit_sharing"],
        "reranked_chunks": chunks,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("jurisdiction", ["india", "international"])
async def test_expansion_never_crosses_selected_jurisdiction(jurisdiction):
    await _build()
    async with AsyncSessionLocal() as session:
        state = await _cross_jurisdiction_state(session, jurisdiction)
        out = await expand(session, state)
        appended = [c for c in out.get("reranked_chunks", []) if c.get("via_graph")]
        assert appended, "expected the graph to contribute at least one chunk"
        docs = {c["doc_id"] for c in appended} | {r["doc_id"] for r in out["related_provisions"]}
        assert await _jurisdiction_of_docs(session, docs) == {jurisdiction}
        assert {r["jurisdiction"] for r in out["related_provisions"]} == {jurisdiction}


@pytest.mark.asyncio
async def test_expansion_follows_cross_edges_only_when_jurisdiction_unset():
    await _build()
    async with AsyncSessionLocal() as session:
        state = await _cross_jurisdiction_state(session, None)
        out = await expand(session, state)
    related = out["related_provisions"]
    assert {r["jurisdiction"] for r in related} == {"india", "international"}


@pytest.mark.asyncio
async def test_graph_chunks_are_real_rows_and_marked():
    await _build()
    async with AsyncSessionLocal() as session:
        state = await _cross_jurisdiction_state(session, "india")
        out = await expand(session, state)
        appended = [c for c in out["reranked_chunks"] if c.get("via_graph")]
        for c in appended:
            row = await session.get(SourceDocument, c["id"])
            assert row is not None and row.doc_id == c["doc_id"] and row.section_or_article == c["section_or_article"]
            assert c["graph_via"]
        assert len(appended) == len(out["graph_chunks"]) <= 3
        original_ids = [c["id"] for c in state["reranked_chunks"]]
        assert [c["id"] for c in out["reranked_chunks"][: len(original_ids)]] == original_ids


@pytest.mark.asyncio
async def test_expansion_is_noop_on_empty_graph():
    async with engine.connect() as conn:
        trans = await conn.begin()
        try:
            from sqlalchemy.ext.asyncio import AsyncSession

            session = AsyncSession(bind=conn)
            await session.execute(delete(KgEdge))
            await session.execute(delete(KgNode))
            state = await _cross_jurisdiction_state(session, "india")
            out = await expand(session, state)
            await session.close()
        finally:
            await trans.rollback()
    assert out == {"related_provisions": [], "graph_chunks": []}
    assert "reranked_chunks" not in out


def test_expand_node_is_wired_between_rerank_and_reason():
    names = [n.__name__ for n in REMAINING_NODES]
    assert names.index("rerank") < names.index("expand_with_graph") < names.index("reason_and_cite")
    assert NODE_TO_STEP["expand_with_graph"] == "need"

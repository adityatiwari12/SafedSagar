"""Answer-time graph expansion: pull the law connected to what retrieval
found into the answer context.

Cheap by design - no LLM calls, three small indexed queries:
  1. seed nodes (provisions of the top reranked chunks + the product
     category / IP-type / concept nodes for this question),
  2. their 1-hop edges (outgoing REFERS_TO / IMPLEMENTS / APPLIES_TO /
     GOVERNED_BY / RELATES_TO, incoming INTERPRETS),
  3. the source_documents rows for the chosen neighbour provisions.

Appended chunks are real source_documents rows, so validate_citations
keeps working unchanged. Jurisdiction rule: when the query has a
jurisdiction, a neighbour from any other jurisdiction is never followed
(cross-jurisdiction edges like BD Act -> CBD are only used when the
jurisdiction is unset). An empty graph is a no-op.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import and_, func, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.db.models import KgEdge, KgEdgeOrigin, KgNode, KgNodeType, KgRelation, SourceDocument
from app.graph.state import GraphState, RetrievedChunk

# --- tunables (module-level on purpose: app/config.py is not ours) ---------
MAX_GRAPH_CHUNKS = 3  # chunks appended to reranked_chunks
SEED_CHUNKS = 5  # how many top reranked chunks seed the expansion
MAX_RELATED = 8  # related_provisions returned to the UI
# Total source_text chars (retrieved + graph) we let reach reason_and_cite.
# The local model runs at Ollama's default 4096-token context, and the
# retrieved set alone is often ~11k chars already; a graph chunk that would
# push the total past this is skipped (the next, smaller one may still fit)
# rather than silently truncating the prompt's instructions.
GRAPH_CONTEXT_CHAR_BUDGET = 15000

FOLLOW_OUT = (
    KgRelation.REFERS_TO,
    KgRelation.IMPLEMENTS,
    KgRelation.APPLIES_TO,
    KgRelation.GOVERNED_BY,
    KgRelation.RELATES_TO,
)
FOLLOW_IN = (KgRelation.INTERPRETS,)

_DOCUMENT_NODE_TYPES = {
    KgNodeType.statute, KgNodeType.rules, KgNodeType.treaty, KgNodeType.case,
    KgNodeType.guidance, KgNodeType.provision,
}
_ORIGIN_RANK = {KgEdgeOrigin.curated: 0, KgEdgeOrigin.structural: 1, KgEdgeOrigin.extracted: 2}
_FRAGMENT_RE = re.compile(r"-[0-9a-f]{8}$")

# Keyword seeds for concept nodes. These only decide which concept nodes
# to START expansion from - the legal claims live on the curated edges,
# each of which carries its own provenance.
_CONCEPT_SEEDS = {
    "concept:traditional_knowledge": re.compile(
        r"traditional|classical|\btkdl\b|prior art|indigenous|folk", re.I
    ),
    "concept:access_and_benefit_sharing": re.compile(
        r"benefit.?sharing|\babs\b|\bnba\b|biodiversity|biological resource|nagoya", re.I
    ),
    "concept:genetic_resources": re.compile(r"genetic resource|biological (resource|material)", re.I),
}

_IP_TYPE_KEYWORD_SEEDS = {
    "ip_type:patent": re.compile(r"\bpatent", re.I),
    "ip_type:trademark": re.compile(r"\btrade ?marks?\b", re.I),
    "ip_type:geographical_indication": re.compile(r"geographical indication", re.I),
    "ip_type:copyright": re.compile(r"\bcopyright", re.I),
}


@dataclass
class _Candidate:
    node: KgNode
    relation: KgRelation
    origin: KgEdgeOrigin
    confidence: float
    via: str
    seed_rank: int
    pinned_chunk_id: str | None
    seed_type: KgNodeType
    in_focus_doc: bool = False
    seed_hits: int = 1  # how many distinct seeds reach this node


def _empty() -> dict:
    return {"related_provisions": [], "graph_chunks": []}


def _seed_keys(state: GraphState) -> list[str]:
    """Taxonomy seeds, strongest first: product category, keyword concepts,
    IP types named literally in the question, then route_ip_type's list
    (primary first). The literal-keyword pass is a cheap backstop for the
    LLM router occasionally omitting the obvious type (verified live: a
    "can I patent..." question routed without `patent`)."""
    keys: list[str] = []
    category = state.get("product_classification")
    if category and category not in ("unclear", "out_of_scope"):
        keys.append(f"category:{category}")
    text = " ".join(filter(None, [state.get("retrieval_query"), state.get("question")]))
    # Concepts are triggered by specific terms ("traditional", "classical")
    # so they outrank the broader IP-type seeds.
    keys.extend(k for k, rx in _CONCEPT_SEEDS.items() if rx.search(text))
    keys.extend(k for k, rx in _IP_TYPE_KEYWORD_SEEDS.items() if rx.search(text))
    keys.extend(f"ip_type:{t}" for t in state.get("ip_types") or [])
    return list(dict.fromkeys(keys))


def _chunk_key(c: dict) -> tuple[str, str | None]:
    return (c["doc_id"], c.get("section_or_article"))


def _node_label(node: KgNode) -> str:
    return node.label


async def expand(session: AsyncSession, state: GraphState) -> dict:
    reranked: list[RetrievedChunk] = list(state.get("reranked_chunks") or [])
    jurisdiction = state.get("jurisdiction")

    # ---- 1. seed nodes -------------------------------------------------------
    taxonomy_keys = _seed_keys(state)
    seed_pairs: list[tuple[str, str | None]] = []
    for c in reranked[:SEED_CHUNKS]:
        doc_id = _FRAGMENT_RE.sub("", c["doc_id"])
        seed_pairs.append((doc_id, c.get("section_or_article")))
        seed_pairs.append((doc_id, None))  # its document node too
    seed_docs = {d for d, _ in seed_pairs}

    conditions = []
    if taxonomy_keys:
        conditions.append(KgNode.key.in_(taxonomy_keys))
    if seed_docs:
        conditions.append(KgNode.doc_id.in_(seed_docs))
    if not conditions:
        return _empty()
    result = await session.execute(select(KgNode).where(or_(*conditions)))
    wanted_pairs = set(seed_pairs)
    seeds: dict = {}
    seed_rank: dict = {}
    for node in result.scalars():
        if node.key in taxonomy_keys:
            seeds[node.id] = node
            # route_ip_type lists the primary IP type first
            seed_rank[node.id] = taxonomy_keys.index(node.key)
        elif (node.doc_id, node.section_or_article) in wanted_pairs:
            seeds[node.id] = node
            seed_rank[node.id] = len(taxonomy_keys) + next(
                i for i, p in enumerate(seed_pairs) if p == (node.doc_id, node.section_or_article)
            )
    if not seeds:
        return _empty()  # includes: graph not built yet

    # ---- 2. one-hop edges ---------------------------------------------------
    src_n, dst_n = aliased(KgNode), aliased(KgNode)
    seed_ids = list(seeds)
    edge_rows = await session.execute(
        select(KgEdge, src_n, dst_n)
        .join(src_n, KgEdge.src_id == src_n.id)
        .join(dst_n, KgEdge.dst_id == dst_n.id)
        .where(
            or_(
                and_(KgEdge.src_id.in_(seed_ids), KgEdge.relation.in_(FOLLOW_OUT)),
                and_(KgEdge.dst_id.in_(seed_ids), KgEdge.relation.in_(FOLLOW_IN)),
            )
        )
    )

    candidates: dict = {}
    seeds_reaching: dict = {}
    for edge, src, dst in edge_rows.all():
        outgoing = edge.src_id in seeds and edge.relation in FOLLOW_OUT
        neighbour, seed = (dst, src) if outgoing else (src, dst)
        if neighbour.id in seeds or neighbour.node_type not in _DOCUMENT_NODE_TYPES:
            continue
        # Rule #4: never cross jurisdictions once one is chosen.
        if jurisdiction and neighbour.jurisdiction not in (None, jurisdiction):
            continue
        via = (
            f"{_node_label(seed)} --{edge.relation.value}--> {_node_label(neighbour)}"
            if outgoing
            else f"{_node_label(neighbour)} --{edge.relation.value}--> {_node_label(seed)}"
        )
        via += f" [{edge.origin.value}; source: {edge.source_doc_id}" + (
            f" {edge.source_section}]" if edge.source_section else "]"
        )
        pinned = (
            edge.source_chunk_id
            if edge.source_doc_id == neighbour.doc_id and edge.source_section == neighbour.section_or_article
            else None
        )
        cand = _Candidate(neighbour, edge.relation, edge.origin, edge.confidence, via,
                          seed_rank[seed.id], pinned, seed.node_type)
        seeds_reaching.setdefault(neighbour.id, set()).add(seed.id)
        # Keyed by (node, pinned chunk): two curated edges into the same
        # provision can pin different chunks of it (e.g. Patents Act s.3's
        # opening chunk vs. the chunk carrying clause (p)) - keep both.
        ckey = (neighbour.id, pinned)
        best = candidates.get(ckey)
        if best is None or _sort_key(cand) < _sort_key(best):
            candidates[ckey] = cand

    if not candidates:
        return _empty()
    # Documents the question's own product category / IP type lead to
    # (e.g. the Patents Act for a patent question) are the answer's focus;
    # other neighbours of the same origin rank after them.
    focus_docs = {
        c.node.doc_id for c in candidates.values()
        if c.seed_type in (KgNodeType.product_category, KgNodeType.ip_type)
    }
    for c in candidates.values():
        c.in_focus_doc = c.node.doc_id in focus_docs
        c.seed_hits = len(seeds_reaching[c.node.id])
    ranked = sorted(candidates.values(), key=_sort_key)

    # ---- 3. fetch rows for the chosen neighbours -----------------------------
    present_keys = {_chunk_key(c) for c in reranked}
    present_ids = {c["id"] for c in reranked}
    related: list[_Candidate] = []
    seen_nodes: set = set()
    for c in ranked:
        if c.node.id not in seen_nodes and len(related) < MAX_RELATED:
            seen_nodes.add(c.node.id)
            related.append(c)
    # Fetch a few more than we can append: the context budget below may
    # skip a long chunk in favour of the next one.
    to_append = [
        c for c in ranked
        if (c.node.doc_id, c.node.section_or_article) not in present_keys
        and (c.node.section_or_article is not None or c.pinned_chunk_id)
    ][: MAX_GRAPH_CHUNKS * 2]

    pinned_ids = [c.pinned_chunk_id for c in to_append if c.pinned_chunk_id]
    pairs = [
        (c.node.doc_id, c.node.section_or_article) for c in to_append
        if not c.pinned_chunk_id and c.node.section_or_article is not None
    ]
    docs = {c.node.doc_id for c in related}
    url_by_doc = dict((await session.execute(
        select(SourceDocument.doc_id, func.min(SourceDocument.source_url))
        .where(SourceDocument.doc_id.in_(docs))
        .group_by(SourceDocument.doc_id)
    )).all()) if docs else {}
    row_conditions = []
    if pinned_ids:
        row_conditions.append(SourceDocument.id.in_(pinned_ids))
    if pairs:
        row_conditions.append(tuple_(SourceDocument.doc_id, SourceDocument.section_or_article).in_(pairs))
    rows = (await session.execute(
        select(SourceDocument.id, SourceDocument.doc_id, SourceDocument.title, SourceDocument.doc_type,
               SourceDocument.section_or_article, SourceDocument.source_url, SourceDocument.source_text,
               SourceDocument.jurisdiction)
        .where(or_(*row_conditions))
        .order_by(SourceDocument.id)
    )).all() if row_conditions else []
    by_id = {r.id: r for r in rows}
    by_pair: dict = {}
    for r in rows:
        by_pair.setdefault((r.doc_id, r.section_or_article), []).append(r)

    graph_chunks: list[dict] = []
    appended: list[RetrievedChunk] = []
    context_chars = sum(len(c.get("source_text") or "") for c in reranked)
    for cand in to_append:
        if len(appended) >= MAX_GRAPH_CHUNKS:
            break
        row = by_id.get(cand.pinned_chunk_id) if cand.pinned_chunk_id else _pick_row(
            by_pair.get((cand.node.doc_id, cand.node.section_or_article), []), cand.node.section_or_article
        )
        if row is None or row.id in present_ids:
            continue
        if context_chars + len(row.source_text) > GRAPH_CONTEXT_CHAR_BUDGET:
            continue
        context_chars += len(row.source_text)
        present_ids.add(row.id)
        chunk = RetrievedChunk(
            id=row.id, doc_id=row.doc_id, doc_type=row.doc_type, section_or_article=row.section_or_article,
            source_text=row.source_text, title=row.title, source_url=row.source_url or "",
        )
        chunk["via_graph"] = True  # type: ignore[typeddict-unknown-key]
        chunk["graph_via"] = cand.via  # type: ignore[typeddict-unknown-key]
        appended.append(chunk)
        graph_chunks.append({
            "chunk_id": row.id, "doc_id": row.doc_id, "section_or_article": row.section_or_article,
            "relation": cand.relation.value, "via": cand.via,
        })

    related_out = []
    for cand in related:
        related_out.append({
            "doc_id": cand.node.doc_id,
            "title": cand.node.label,
            "section_or_article": cand.node.section_or_article,
            "jurisdiction": cand.node.jurisdiction,
            "relation": cand.relation.value,
            "via": cand.via,
            "source_url": url_by_doc.get(cand.node.doc_id) or None,
        })

    out: dict = {"related_provisions": related_out, "graph_chunks": graph_chunks}
    if appended:
        out["reranked_chunks"] = reranked + appended
    return out


def _sort_key(c: _Candidate) -> tuple:
    # curated before structural before extracted; provisions (citable,
    # specific) before whole documents; focus documents first; then nodes
    # reached from more seeds; then the stronger seed; then confidence.
    is_doc_level = c.node.section_or_article is None and not c.pinned_chunk_id
    return (_ORIGIN_RANK[c.origin], is_doc_level, not c.in_focus_doc, -c.seed_hits, c.seed_rank,
            -c.confidence, c.node.key, c.pinned_chunk_id or "")


def _pick_row(rows: list, section: str | None):
    """Prefer the chunk that opens the provision ("3. What are not
    inventions...") over a footnote/continuation chunk with the same label."""
    if not rows:
        return None
    if section:
        for r in rows:
            if r.source_text.lstrip().startswith(f"{section}."):
                return r
    return rows[0]

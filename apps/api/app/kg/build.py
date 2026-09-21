"""Build the legal knowledge graph from source_documents.

    python -m app.kg.build

Rebuilds kg_nodes / kg_edges from scratch in ONE transaction (idempotent:
same corpus in, same graph out) and prints counts by node_type, relation
and origin.

No-fabricated-law rules enforced here (see CLAUDE.md / app/kg/curated_edges.yaml):

1. Document / provision / authority nodes are created ONLY from rows that
   exist in source_documents. A law that isn't ingested gets no node.
2. Every edge carries provenance (source_doc_id + optional source_section)
   and `_add_edge` REJECTS - logs and skips, never silently inserts - any
   edge whose provenance doesn't resolve to a source_documents row
   (doc_id, and (doc_id, section_or_article) when a section is given).
3. Curated edges additionally need an `evidence` regex that matches the
   actual text of the cited chunk; no match -> rejected.
4. Duplicate-ingestion fragments (`<doc_id>-<8 hex>`) canonicalize onto
   their base document's node.

Three layers:
- structural (confidence 1.0): doc nodes, provision nodes, CONTAINS,
  ADMINISTERED_BY, IMPLEMENTS/AMENDS between known rule/amendment docs
  and their parent (only when the child's own text names the parent).
- extracted (confidence < 1.0): REFERS_TO between provisions, by regex
  over source_text; only to provision nodes that exist; capped.
- curated (confidence 1.0): app/kg/curated_edges.yaml.
"""

from __future__ import annotations

import asyncio
import logging
import re
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import AsyncSessionLocal
from app.db.models import KgEdge, KgEdgeOrigin, KgNode, KgNodeType, KgRelation, SourceDocument
from app.graph.state import IP_TYPES, PRODUCT_CATEGORIES

logger = logging.getLogger("app.kg.build")

CURATED_PATH = Path(__file__).with_name("curated_edges.yaml")

# --- tunables (module-level on purpose: app/config.py is not ours) ---------
REFS_PER_CHUNK_CAP = 8
REFS_PER_PROVISION_CAP = 12
CONF_REF_SAME_DOC = 0.8
CONF_REF_RULES_TO_ACT = 0.75
CONF_REF_NAMED_STATUTE = 0.7

_FRAGMENT_RE = re.compile(r"^(?P<base>.+)-[0-9a-f]{8}$")
_WS_RE = re.compile(r"\s+")

# WIPO GRATK (adopted 24 May 2024) needs 15 ratifications - CLAUDE.md
# caveat 2: present it as signed, not binding. Carried in the node label
# so every surface that shows the node (related_provisions) says so.
GRATK_DOC_ID = "wipo-gratk-2024"
GRATK_LABEL_SUFFIX = " [signed 24 May 2024 - NOT yet in force]"

_DOC_TYPE_TO_NODE_TYPE = {
    "statute": KgNodeType.statute,
    "rules": KgNodeType.rules,
    "regulation": KgNodeType.rules,
    "treaty": KgNodeType.treaty,
    "case_law": KgNodeType.case,
}

_PROVISION_PREFIX = {
    KgNodeType.statute: "Section",
    KgNodeType.rules: "Rule",
    KgNodeType.treaty: "Article",
    KgNodeType.case: "Para",
    KgNodeType.guidance: "Part",
}

# Docs whose `section_or_article` labels are known NOT to be real section/
# article numbers, so regex references into them would resolve to the
# wrong provision: the CDSCO Drugs & Cosmetics compilation mixes Act
# sections and Rules numbering under one doc_id; CBD / Nagoya chunks are
# labelled with paragraph numbers, not article numbers.
UNRELIABLE_SECTION_LABELS = {
    "india-drugs-and-cosmetics-act-1940",
    "cbd-1992",
    "wipo-nagoya-protocol-2010",
}

# Parent-document names, used both to validate IMPLEMENTS/AMENDS links
# (the child's own text must name its parent) and to resolve explicit
# cross-statute references ("section 3 of the Patents Act, 1970").
STATUTE_NAMES: dict[str, str] = {
    "ipindia-patents-act-1970": r"Patents Act,? 1970",
    "india-patents-rules-2003": r"Patents Rules,? 2003",
    "india-biological-diversity-act-2002": r"Biological Diversity Act,? 2002",
    "india-copyright-act-1957": r"Copyright Act,? 1957",
    "india-gi-act-1999": r"Geographical Indications of Goods \(Registration and Protection\) Act,? 1999",
    "india-gi-rules-2002": r"Geographical Indications of Goods \(Registration and Protection\) Rules,? 2002",
    "india-trade-marks-act-1999": r"Trade Marks Act,? 1999",
    "india-designs-act-2000": r"Designs? Act,? 2000",
    "india-drugs-and-cosmetics-act-1940": r"Drugs and Cosmetics Act,? 1940",
}

# (child, relation, parent). Validated at build time: both docs must exist
# and the child's text must name the parent (STATUTE_NAMES[parent]).
# Deliberately NOT linked (corpus-content issues, verified by reading):
# - india-patents-2nd-amendment-rules-2024: despite doc_type=rules, the
#   ingested text is a stakeholder COMMENT SUBMISSION on the draft rules,
#   not the rules themselves - an IMPLEMENTS/AMENDS edge would be false.
# - india-gi-2025-amendment: the ingested text is GI name/logo usage
#   guidance and never names the GI Rules, 2002.
PARENT_LINKS: list[tuple[str, KgRelation, str]] = [
    ("india-patents-rules-2003", KgRelation.IMPLEMENTS, "ipindia-patents-act-1970"),
    ("india-patents-amendment-rules-2024", KgRelation.IMPLEMENTS, "ipindia-patents-act-1970"),
    ("india-patents-amendment-rules-2024", KgRelation.AMENDS, "india-patents-rules-2003"),
    ("india-biological-diversity-rules-2024", KgRelation.IMPLEMENTS, "india-biological-diversity-act-2002"),
    ("india-abs-regulations-2025", KgRelation.IMPLEMENTS, "india-biological-diversity-act-2002"),
    ("india-biological-diversity-amendment-act-2023", KgRelation.AMENDS, "india-biological-diversity-act-2002"),
    ("india-copyright-rules-1957", KgRelation.IMPLEMENTS, "india-copyright-act-1957"),
    ("india-copyright-rules-2013", KgRelation.IMPLEMENTS, "india-copyright-act-1957"),
    ("india-copyright-amendment-act-2012", KgRelation.AMENDS, "india-copyright-act-1957"),
    ("india-gi-rules-2002", KgRelation.IMPLEMENTS, "india-gi-act-1999"),
    ("india-gi-2020-amendment", KgRelation.AMENDS, "india-gi-rules-2002"),
    ("india-trademark-rules-2017", KgRelation.IMPLEMENTS, "india-trade-marks-act-1999"),
    ("india-drug-cosmetics-rules-1945", KgRelation.IMPLEMENTS, "india-drugs-and-cosmetics-act-1940"),
]

_NUM = r"\d{1,3}[A-Z]{0,3}"
_NUM_LIST = rf"({_NUM})((?:\s*,\s*{_NUM})*(?:\s*,?\s*(?:and|or)\s+{_NUM})?)"
_SECTION_REF_RE = re.compile(rf"\b(?i:sections?)\s+{_NUM_LIST}")
_RULE_REF_RE = re.compile(rf"\b(?i:rules?|regulations?)\s+{_NUM_LIST}")
_ARTICLE_REF_RE = re.compile(rf"\b(?i:articles?)\s+{_NUM_LIST}")
_NUM_RE = re.compile(_NUM)
_OF_CLAUSE_RE = re.compile(r"\s*(?:\([^)]{0,12}\)\s*)*of\s+(?:the\s+)?(.{0,90})", re.IGNORECASE)
_SAME_DOC_OF_RE = re.compile(r"(this|said)\s+(Act|Rules?|Regulations?|Protocol|Convention|Agreement|Treaty)\b", re.I)
_THE_ACT_RE = re.compile(r"Act\b", re.I)
_PRINCIPAL_RE = re.compile(r"principal\s+(Act|Rules|Regulations)\b", re.I)


def normalize_ws(text: str) -> str:
    return _WS_RE.sub(" ", text or "").strip()


# --------------------------------------------------------------------------
# Corpus snapshot
# --------------------------------------------------------------------------


@dataclass
class Row:
    id: str
    doc_id: str
    title: str
    authority: str
    jurisdiction: str
    doc_type: str
    section: str | None
    text: str


@dataclass
class Corpus:
    rows: list[Row]
    doc_ids: set[str] = field(default_factory=set)
    pairs: set[tuple[str, str]] = field(default_factory=set)
    canonical: dict[str, str] = field(default_factory=dict)  # raw doc_id -> canonical doc_id
    rows_by_pair: dict[tuple[str, str | None], list[Row]] = field(default_factory=lambda: defaultdict(list))
    rows_by_doc: dict[str, list[Row]] = field(default_factory=lambda: defaultdict(list))

    def __post_init__(self) -> None:
        self.rows.sort(key=lambda r: r.id)
        for r in self.rows:
            self.doc_ids.add(r.doc_id)
            if r.section is not None:
                self.pairs.add((r.doc_id, r.section))
            self.rows_by_pair[(r.doc_id, r.section)].append(r)
            self.rows_by_doc[r.doc_id].append(r)
        for doc_id in self.doc_ids:
            self.canonical[doc_id] = canonical_doc_id(doc_id, self.doc_ids)

    def resolves(self, doc_id: str | None, section: str | None) -> bool:
        """The provenance check: does (doc_id[, section]) name a real row?"""
        if not doc_id or doc_id not in self.doc_ids:
            return False
        return section is None or (doc_id, section) in self.pairs

    def find_evidence(self, doc_id: str, section: str | None, pattern: str) -> Row | None:
        """First chunk of exactly (doc_id, section) whose whitespace-
        collapsed text matches `pattern` (case-insensitive)."""
        rx = re.compile(pattern, re.IGNORECASE)
        for row in self.rows_by_pair.get((doc_id, section), []):
            if rx.search(normalize_ws(row.text)):
                return row
        return None


def canonical_doc_id(doc_id: str, known_doc_ids: set[str]) -> str:
    """Strip a trailing `-<8 hex>` duplicate-ingestion suffix - but only
    when the base doc actually exists, so a legitimately hex-ending id is
    never collapsed onto a doc that isn't there."""
    m = _FRAGMENT_RE.match(doc_id)
    if m and m.group("base") in known_doc_ids:
        return m.group("base")
    return doc_id


async def load_corpus(session: AsyncSession) -> Corpus:
    result = await session.execute(
        select(
            SourceDocument.id,
            SourceDocument.doc_id,
            SourceDocument.title,
            SourceDocument.authority,
            SourceDocument.jurisdiction,
            SourceDocument.doc_type,
            SourceDocument.section_or_article,
            SourceDocument.source_text,
        )
    )
    rows = [
        Row(
            id=r.id,
            doc_id=r.doc_id,
            title=r.title,
            authority=r.authority,
            jurisdiction=getattr(r.jurisdiction, "value", r.jurisdiction),
            doc_type=r.doc_type,
            section=r.section_or_article,
            text=r.source_text,
        )
        for r in result.all()
    ]
    return Corpus(rows=rows)


# --------------------------------------------------------------------------
# Graph under construction
# --------------------------------------------------------------------------


_ORIGIN_PRIORITY = {KgEdgeOrigin.curated: 3, KgEdgeOrigin.structural: 2, KgEdgeOrigin.extracted: 1}


@dataclass
class _Node:
    key: str
    node_type: KgNodeType
    label: str
    jurisdiction: str | None = None
    doc_id: str | None = None
    section_or_article: str | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass
class _Edge:
    src: str
    dst: str
    relation: KgRelation
    source_doc_id: str
    source_section: str | None
    origin: KgEdgeOrigin
    confidence: float
    source_chunk_id: str | None = None
    note: str | None = None


@dataclass
class BuildReport:
    nodes_by_type: Counter = field(default_factory=Counter)
    edges_by_relation: Counter = field(default_factory=Counter)
    edges_by_origin: Counter = field(default_factory=Counter)
    fragments_canonicalized: int = 0
    fragment_rows: int = 0
    rejected: list[str] = field(default_factory=list)
    curated_accepted: list[str] = field(default_factory=list)

    def format(self) -> str:
        lines = ["Knowledge graph built."]
        lines.append("Nodes by type: " + ", ".join(f"{k}={v}" for k, v in sorted(self.nodes_by_type.items())))
        lines.append("Edges by relation: " + ", ".join(f"{k}={v}" for k, v in sorted(self.edges_by_relation.items())))
        lines.append("Edges by origin: " + ", ".join(f"{k}={v}" for k, v in sorted(self.edges_by_origin.items())))
        lines.append(
            f"Fragments canonicalized: {self.fragments_canonicalized} doc_ids ({self.fragment_rows} rows)"
        )
        lines.append(f"Curated edges accepted: {len(self.curated_accepted)}")
        lines.append(f"Rejected edges: {len(self.rejected)}")
        lines.extend(f"  REJECTED {r}" for r in self.rejected)
        return "\n".join(lines)


class GraphBuilder:
    def __init__(self, corpus: Corpus) -> None:
        self.corpus = corpus
        self.nodes: dict[str, _Node] = {}
        self.edges: dict[tuple[str, str, KgRelation], _Edge] = {}
        self.report = BuildReport()
        self.doc_node_key: dict[str, str] = {}  # canonical doc_id -> node key

    # -- primitives -----------------------------------------------------

    def _add_node(self, node: _Node) -> str:
        self.nodes.setdefault(node.key, node)
        return node.key

    def _add_edge(self, edge: _Edge) -> bool:
        """The single gate every edge passes through - provenance must
        resolve and both endpoints must exist, else reject (log + skip)."""
        desc = f"{edge.origin.value} {edge.src} -{edge.relation.value}-> {edge.dst} (prov {edge.source_doc_id}#{edge.source_section})"
        if not self.corpus.resolves(edge.source_doc_id, edge.source_section):
            self._reject(f"{desc}: provenance does not resolve to a source_documents row")
            return False
        if edge.src not in self.nodes or edge.dst not in self.nodes:
            self._reject(f"{desc}: endpoint node missing")
            return False
        if edge.src == edge.dst:
            return False
        k = (edge.src, edge.dst, edge.relation)
        existing = self.edges.get(k)
        if existing is None or _ORIGIN_PRIORITY[edge.origin] > _ORIGIN_PRIORITY[existing.origin]:
            self.edges[k] = edge
        return True

    def _reject(self, message: str) -> None:
        logger.warning("kg: rejected edge %s", message)
        self.report.rejected.append(message)

    @staticmethod
    def provision_key(doc_id: str, section: str) -> str:
        return f"provision:{doc_id}#{section}"

    # -- structural -------------------------------------------------------

    def build_structural(self) -> None:
        corpus = self.corpus
        fragments = {d for d, c in corpus.canonical.items() if d != c}
        self.report.fragments_canonicalized = len(fragments)
        self.report.fragment_rows = sum(len(corpus.rows_by_doc[d]) for d in fragments)

        canonical_docs = sorted({c for c in corpus.canonical.values()})
        for doc_id in canonical_docs:
            rows = corpus.rows_by_doc[doc_id]
            if not rows:  # canonical id with only fragments - cannot happen by construction
                continue
            first = rows[0]
            node_type = _DOC_TYPE_TO_NODE_TYPE.get(first.doc_type, KgNodeType.guidance)
            label = min(r.title for r in rows)
            if doc_id == GRATK_DOC_ID:
                label += GRATK_LABEL_SUFFIX
            key = self._add_node(
                _Node(key=f"{node_type.value}:{doc_id}", node_type=node_type, label=label,
                      jurisdiction=first.jurisdiction, doc_id=doc_id)
            )
            self.doc_node_key[doc_id] = key

            # Provision nodes: only from the canonical doc's own rows.
            # Fragment rows attach to the statute (counted above) but add
            # no provisions of their own - their section labels don't
            # follow the canonical numbering.
            prefix = _PROVISION_PREFIX[node_type]
            for section in sorted({r.section for r in rows if r.section}):
                pkey = self._add_node(
                    _Node(key=self.provision_key(doc_id, section), node_type=KgNodeType.provision,
                          label=f"{label} - {prefix} {section}", jurisdiction=first.jurisdiction,
                          doc_id=doc_id, section_or_article=section)
                )
                self._add_edge(_Edge(key, pkey, KgRelation.CONTAINS, doc_id, section,
                                     KgEdgeOrigin.structural, 1.0))

            for authority in sorted({r.authority for r in rows if r.authority}):
                akey = self._add_node(
                    _Node(key=f"authority:{first.jurisdiction}:{_slug(authority)}", node_type=KgNodeType.authority,
                          label=authority, jurisdiction=first.jurisdiction)
                )
                self._add_edge(_Edge(key, akey, KgRelation.ADMINISTERED_BY, doc_id, None,
                                     KgEdgeOrigin.structural, 1.0))

        for child, relation, parent in PARENT_LINKS:
            if child not in self.doc_node_key or parent not in self.doc_node_key:
                self._reject(f"structural {child} -{relation.value}-> {parent}: document not in corpus")
                continue
            pattern = STATUTE_NAMES[parent]
            evidence = self._find_naming_chunk(child, pattern)
            if evidence is None:
                self._reject(f"structural {child} -{relation.value}-> {parent}: child text never names the parent")
                continue
            self._add_edge(_Edge(self.doc_node_key[child], self.doc_node_key[parent], relation, child,
                                 evidence.section, KgEdgeOrigin.structural, 1.0, source_chunk_id=evidence.id))

    def _find_naming_chunk(self, doc_id: str, pattern: str) -> Row | None:
        rx = re.compile(pattern, re.IGNORECASE)
        fallback = None
        for row in self.corpus.rows_by_doc[doc_id]:
            text = normalize_ws(row.text)
            if rx.search(text):
                if re.search(r"exercise of the powers|amend", text, re.IGNORECASE):
                    return row
                fallback = fallback or row
        return fallback

    # -- extracted ----------------------------------------------------------

    def build_extracted(self) -> None:
        corpus = self.corpus
        parent_act = {c: p for c, r, p in PARENT_LINKS if r == KgRelation.IMPLEMENTS}
        # Amending instruments ("In section 7 of the principal Act, ...")
        # talk about the AMENDED document's numbering, never their own -
        # so a bare "section 7" there must not resolve to their own s.7.
        amended = {c: p for c, r, p in PARENT_LINKS if r == KgRelation.AMENDS}
        named = [(doc_id, re.compile(rf"^{pat}", re.IGNORECASE)) for doc_id, pat in STATUTE_NAMES.items()]

        # (src provision key) -> Counter(dst key) + first evidence per dst
        counts: dict[str, Counter] = defaultdict(Counter)
        evidence: dict[tuple[str, str], tuple[Row, float]] = {}

        for doc_id in sorted(self.doc_node_key):
            if doc_id in UNRELIABLE_SECTION_LABELS:
                continue
            node_type = self.nodes[self.doc_node_key[doc_id]].node_type
            if node_type not in (KgNodeType.statute, KgNodeType.rules, KgNodeType.treaty):
                continue
            for row in corpus.rows_by_doc[doc_id]:
                if not row.section:
                    continue
                src = self.provision_key(doc_id, row.section)
                targets = self._refs_in_chunk(row, doc_id, node_type, parent_act.get(doc_id),
                                              amended.get(doc_id), named)
                for dst, conf in targets[:REFS_PER_CHUNK_CAP]:
                    if dst == src or dst not in self.nodes:
                        continue
                    counts[src][dst] += 1
                    evidence.setdefault((src, dst), (row, conf))

        for src, counter in counts.items():
            for dst, _n in counter.most_common(REFS_PER_PROVISION_CAP):
                row, conf = evidence[(src, dst)]
                self._add_edge(_Edge(src, dst, KgRelation.REFERS_TO, row.doc_id, row.section,
                                     KgEdgeOrigin.extracted, conf, source_chunk_id=row.id))

    def _refs_in_chunk(self, row: Row, doc_id: str, node_type: KgNodeType, parent: str | None,
                       amended: str | None, named) -> list[tuple[str, float]]:
        text = normalize_ws(row.text)
        found: list[tuple[str, float]] = []
        seen: set[str] = set()

        def emit(target: tuple[str, float] | None, m: re.Match) -> None:
            if not target:
                return
            target_doc, conf = target
            for n in _numbers(m):
                key = self.provision_key(target_doc, n)
                if key in self.nodes and key not in seen:
                    seen.add(key)
                    found.append((key, conf))

        if node_type == KgNodeType.treaty:
            for m in _ARTICLE_REF_RE.finditer(text):
                emit(self._resolve_of_clause(text, m.end(), doc_id, None, None, named,
                                             same_doc_default=True, allow_named=False), m)
            return found

        # Bare "section N" resolves to the same doc only in a plain statute;
        # in rules it's ambiguous (usually the parent Act) and in an
        # amending instrument it's the amended doc - both need an explicit
        # "of the Act" / "of the principal Act" / named-statute clause.
        bare_ok = node_type == KgNodeType.statute and amended is None
        for m in _SECTION_REF_RE.finditer(text):
            emit(self._resolve_of_clause(text, m.end(), doc_id, parent, amended, named,
                                         same_doc_default=bare_ok), m)

        if node_type == KgNodeType.rules:
            for m in _RULE_REF_RE.finditer(text):
                emit(self._resolve_of_clause(text, m.end(), doc_id, None, amended, named,
                                             same_doc_default=amended is None, allow_named=False), m)
        return found

    def _resolve_of_clause(self, text: str, pos: int, doc_id: str, parent: str | None, amended: str | None,
                           named, same_doc_default: bool, allow_named: bool = True) -> tuple[str, float] | None:
        m = _OF_CLAUSE_RE.match(text, pos)
        if not m:
            return (doc_id, CONF_REF_SAME_DOC) if same_doc_default else None
        phrase = m.group(1)
        if amended and _PRINCIPAL_RE.match(phrase) and amended in self.doc_node_key:
            return (amended, CONF_REF_RULES_TO_ACT)
        if _SAME_DOC_OF_RE.match(phrase):
            return (doc_id, CONF_REF_SAME_DOC)
        if allow_named:
            for target_doc, rx in named:
                if rx.match(phrase):
                    if target_doc == doc_id:
                        return (doc_id, CONF_REF_SAME_DOC)
                    if target_doc in self.doc_node_key:
                        return (target_doc, CONF_REF_NAMED_STATUTE)
                    return None
            # "of the Act" in rules/regulations means the parent Act
            if parent and _THE_ACT_RE.match(phrase) and parent in self.doc_node_key:
                return (parent, CONF_REF_RULES_TO_ACT)
            if (not amended and _THE_ACT_RE.match(phrase)
                    and self.nodes[self.doc_node_key[doc_id]].node_type == KgNodeType.statute):
                return (doc_id, CONF_REF_SAME_DOC)
        # Anything else ("of the Income-tax Act", "of the Convention", ...)
        # names a document we can't resolve safely -> skip.
        return None

    # -- curated ----------------------------------------------------------

    def build_curated(self, spec: dict) -> None:
        for name, label in (spec.get("concepts") or {}).items():
            self._add_node(_Node(key=f"concept:{name}", node_type=KgNodeType.concept, label=label))
        for cat in PRODUCT_CATEGORIES:
            if cat in ("unclear", "out_of_scope"):
                continue
            self._add_node(_Node(key=f"category:{cat}", node_type=KgNodeType.product_category,
                                 label=cat.replace("_", " ")))
        for ip in IP_TYPES:
            self._add_node(_Node(key=f"ip_type:{ip}", node_type=KgNodeType.ip_type, label=ip.replace("_", " ")))

        for entry in spec.get("edges") or []:
            resolved, reason = resolve_curated_entry(entry, self.corpus, self.doc_node_key)
            desc = f"curated {entry.get('src')} -{entry.get('relation')}-> {entry.get('dst')}"
            if resolved is None:
                self._reject(f"{desc}: {reason}")
                continue
            if self._add_edge(resolved):
                self.report.curated_accepted.append(desc)

    # -- output -------------------------------------------------------------

    def finalize_report(self) -> BuildReport:
        for node in self.nodes.values():
            self.report.nodes_by_type[node.node_type.value] += 1
        for edge in self.edges.values():
            self.report.edges_by_relation[edge.relation.value] += 1
            self.report.edges_by_origin[edge.origin.value] += 1
        return self.report


def _numbers(m: re.Match) -> list[str]:
    return [m.group(1)] + _NUM_RE.findall(m.group(2) or "")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:120]


def load_curated_spec(path: Path = CURATED_PATH) -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _ref_to_key(ref: str, doc_node_key: dict[str, str]) -> tuple[str | None, str | None, str | None]:
    """Resolve a curated node ref -> (node key, doc_id, section). Returns
    (None, ...) when the ref names something not in the graph/corpus."""
    kind, _, value = (ref or "").partition(":")
    if kind in ("category", "ip_type", "concept"):
        return f"{kind}:{value}", None, None
    if kind == "doc":
        doc_id, _, section = value.partition("#")
        if doc_id not in doc_node_key:
            return None, doc_id, section or None
        if section:
            return GraphBuilder.provision_key(doc_id, section), doc_id, section
        return doc_node_key[doc_id], doc_id, None
    return None, None, None


def resolve_curated_entry(entry: dict, corpus: Corpus, doc_node_key: dict[str, str]) -> tuple[_Edge | None, str]:
    """Turn one curated YAML entry into an edge, or explain why not.
    Provenance defaults to the dst doc/section; the evidence regex must
    match real chunk text at exactly that (doc_id, section)."""
    try:
        relation = KgRelation(entry["relation"])
    except (KeyError, ValueError):
        return None, f"unknown relation {entry.get('relation')!r}"
    src_key, _, _ = _ref_to_key(entry.get("src", ""), doc_node_key)
    dst_key, dst_doc, dst_section = _ref_to_key(entry.get("dst", ""), doc_node_key)
    if src_key is None:
        return None, "src not in corpus/graph"
    if dst_key is None:
        return None, f"dst document {dst_doc!r} not in corpus"
    source_doc = entry.get("source_doc", dst_doc)
    source_section = entry["source_section"] if "source_section" in entry else dst_section
    if source_section is not None:
        source_section = str(source_section)
    if not source_doc:
        return None, "no provenance document"
    if not corpus.resolves(source_doc, source_section):
        return None, f"provenance {source_doc}#{source_section} does not resolve to a source_documents row"
    evidence = entry.get("evidence")
    if not evidence:
        return None, "no evidence regex"
    row = corpus.find_evidence(source_doc, source_section, evidence)
    if row is None:
        return None, f"evidence not found in {source_doc}#{source_section}"
    return _Edge(src_key, dst_key, relation, source_doc, source_section, KgEdgeOrigin.curated, 1.0,
                 source_chunk_id=row.id, note=entry.get("note")), "ok"


# --------------------------------------------------------------------------
# Entry points
# --------------------------------------------------------------------------


async def build_graph(session: AsyncSession, curated_spec: dict | None = None) -> BuildReport:
    """Rebuild kg_nodes/kg_edges from source_documents inside the caller's
    session and commit once. Safe to re-run."""
    corpus = await load_corpus(session)
    builder = GraphBuilder(corpus)
    builder.build_structural()
    builder.build_curated(curated_spec if curated_spec is not None else load_curated_spec())
    builder.build_extracted()
    report = builder.finalize_report()

    await session.execute(delete(KgEdge))
    await session.execute(delete(KgNode))
    node_rows = [
        {"id": n.id, "key": n.key, "node_type": n.node_type, "label": n.label, "jurisdiction": n.jurisdiction,
         "doc_id": n.doc_id, "section_or_article": n.section_or_article}
        for n in builder.nodes.values()
    ]
    edge_rows = [
        {"id": uuid.uuid4(), "src_id": builder.nodes[e.src].id, "dst_id": builder.nodes[e.dst].id,
         "relation": e.relation, "source_doc_id": e.source_doc_id, "source_section": e.source_section,
         "source_chunk_id": e.source_chunk_id, "origin": e.origin, "confidence": e.confidence, "note": e.note}
        for e in builder.edges.values()
    ]
    for i in range(0, len(node_rows), 2000):
        await session.execute(insert(KgNode), node_rows[i : i + 2000])
    for i in range(0, len(edge_rows), 2000):
        await session.execute(insert(KgEdge), edge_rows[i : i + 2000])
    await session.commit()
    return report


async def _main() -> None:
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    async with AsyncSessionLocal() as session:
        report = await build_graph(session)
    print(report.format())


if __name__ == "__main__":
    asyncio.run(_main())

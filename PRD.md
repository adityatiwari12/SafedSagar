**IP-SAKTI Sahayak**

**Product Requirements Document**

*SIH Problem Statement 26045 \| Ministry of Ayush \| All India Institute
of Ayurveda*

# Document Purpose

This document combines the complete Smart India Hackathon (SIH) problem
statement supplied for Problem Statement 26045 with the product
requirements derived from it. The SIH source section is preserved in
full so that the PRD can be used as a single reference document.

# Part I --- Complete SIH Problem Statement

## Problem Statement ID

26045

## Problem Statement Title

IP-SAKTI Sahayak a multilingual, RAG-based (source-cited) AI assistant
for Intellectual Property and regulatory guidance in Ayurveda, across
national and international regimes.

## Description --- Background

Ayurveda rests on a vast corpus of codified and community-held
traditional knowledge (TK) and on therapeutics derived from plant,
microbial and animal sources. Protecting and commercialising an
Ayurvedic product means navigating several overlapping regimes at once:
patents, geographical indications (GI), trademarks, copyright, designs,
trade secrets and plant-variety rights; the Access-and-Benefit-Sharing
duties that flow from India's sovereignty over its biological resources;
and the drug-regulatory framework that decides whether a formulation is
a classical medicine, a proprietary medicine, a new drug, a
phytopharmaceutical, a food or a cosmetic. Practitioners, researchers,
AYUSH startups and MSMEs and cultivators routinely struggle with this.
The result is twofold: legitimate Ayurvedic innovation is
under-protected and under-commercialised, while India's traditional
knowledge remains exposed to misappropriation abroad. Recent shifts ---
the 2024 patent and biodiversity rules, the WIPO Treaty on Genetic
Resources and Associated Traditional Knowledge (2024) and a fast-moving
advertising and regulatory landscape --- make authoritative,
plain-language guidance more necessary than ever, yet no such tool
exists for the AYUSH community.

## Description --- Detailed Description

The assistant answers IPR questions specific to Ayurveda with accuracy,
source citation and jurisdictional clarity, keeping the national and the
international layers distinct through an explicit jurisdiction switch so
that answers are never conflated.

Because intellectual property for an Ayurvedic product is inseparable
from how the product is regulated, the assistant first helps classify
the formulation. It asks the minimum clarifying questions to determine
whether the product is a classical/generic medicine (formulation and
method drawn from a First-Schedule authoritative text), a
patent-or-proprietary medicine, a new or non-classical drug requiring
proof of safety and effectiveness, a phytopharmaceutical, an
Ayurveda-Aahar / nutraceutical, or a cosmetic --- and then states what
each category requires and its very different IP and ABS posture. For
example, a classical formulation is largely traditional knowledge that
faces the Section 3(p) patenting bar and is defended through the
Traditional Knowledge Digital Library, whereas a new drug gains genuine
patent potential but must generate clinical evidence.

National coverage spans the Patents Act (and the 2024 Rules), the GI,
Trade Marks, Designs, Copyright and Plant-Variety regimes, the
Biological Diversity Act (as amended in 2023, with the 2024 Rules) and
the allied drug, advertising, labelling and food/cosmetic regimes ---
the Drugs and Cosmetics Act, the Drugs and Magic Remedies (Objectionable
Advertisements) Act and the FSSAI Ayurveda-Aahar regulations.
International coverage separately spans TRIPS, the Convention on
Biological Diversity and the Nagoya Protocol, the WIPO GRATK Treaty, the
PCT, the Madrid and Hague systems, the Budapest Treaty (for
micro-organism deposits) and the herbal-product market-access regimes of
key export markets.

The assistant also facilitates access to authoritative sources --- free
official databases directly and the user's own paid subscriptions only
with explicit, logged permission --- so that a user can move from a
question to the right registry, record or form. It must cite the
specific statute, rule, treaty article or record it relies on; clearly
state that it provides information and not legal advice; keep its corpus
current as the law changes; and never fabricate authority.

## Description --- Expected Solution

A deployable, multilingual assistant built on retrieval-augmented
generation grounded in a curated, version-tracked corpus of statutes,
rules, treaties, pharmacopoeial standards, registry records and case
law, so that every answer is traceable to a source and hallucination is
minimised. The solution should provide: a jurisdiction toggle (India vs
international) with the two answer-sets kept visibly separate; routing
across IP types together with the formulation-classification flow; an
ABS-compliance helper and a TKDL / prior-art pointer; mandatory source
citations with a confidence indicator and a path to escalate to a human
IP facilitator; multilingual delivery (leveraging national language
infrastructure such as Bhashini); and guardrails, a standing
\'information, not legal advice\' disclaimer and privacy, audit and
security aligned to the Digital Personal Data Protection regime and to
recognised AI-application standards. A relational knowledge graph and
agentic, multi-source orchestration deepen multi-step reasoning and the
build can be staged --- a citation-grounded retrieval MVP first, then
the graph and agentic layers, then paid-source connectors and the full
multilingual and voice experience. The output should be evaluable on
answer accuracy, citation correctness, safe abstention on out-of-scope
or uncertain queries and multilingual quality.

## Organization

Ministry of Ayush

## Department

All India Institute of Ayurveda

## Category

Software

## Theme

MedTech / BioTech / HealthTech

# Part II --- Product Requirements

The following requirements translate the complete SIH statement above
into a buildable product definition. They are intended for product
planning, engineering, architecture and hackathon execution.

Purpose: Define a hackathon-ready, citation-grounded AI assistant for
Ayurveda-specific intellectual property and regulatory guidance, based
on the official problem statement.

# 1. Executive Summary

IP-SAKTI Sahayak is a multilingual AI assistant designed to help
Ayurveda practitioners, researchers, AYUSH startups, MSMEs and
cultivators navigate overlapping intellectual-property, biodiversity,
regulatory and international requirements. The product uses
retrieval-augmented generation (RAG) over a curated, version-tracked
corpus so that answers are traceable to authoritative sources. It
separates India and international jurisdictions, classifies the
Ayurvedic product before giving guidance, provides confidence
indicators, supports safe abstention, and offers escalation to a human
IP facilitator.

# 2. Problem Statement

Ayurvedic products can involve patents, geographical indications,
trademarks, copyright, designs, trade secrets, plant-variety rights,
Access-and-Benefit-Sharing obligations, drug regulation, food/cosmetic
rules and international regimes. Users struggle to determine which rules
apply, how traditional knowledge affects protection, and which
authoritative sources or registries they should consult.

# 3. Product Vision

Provide a trusted AI copilot that takes an Ayurveda-related product or
innovation from an initial natural-language question to an
understandable IP, regulatory, biodiversity and commercialisation
roadmap, while making the evidence behind each substantive answer
visible.

# 4. Goals

-   Understand an Ayurvedic product or innovation from conversational
    input.

-   Classify the formulation into the relevant regulatory category.

-   Identify potentially relevant IP regimes and ABS/TK considerations.

-   Retrieve authoritative Indian or international sources.

-   Generate source-cited answers with confidence indicators.

-   Keep Indian and international jurisdictional guidance visibly
    separate.

-   Support multilingual interaction and a future voice interface.

-   Abstain safely when authoritative evidence is insufficient.

-   Provide a path to human IP-facilitator escalation.

# 5. Non-Goals

-   Providing legally binding advice or replacing a lawyer/IP
    professional.

-   Guaranteeing patentability or regulatory approval.

-   Automatically filing IP or regulatory applications in the MVP.

-   Claiming unrestricted access to restricted databases.

-   Generating unsupported legal citations.

# 6. Target Users

# 7. Core User Journey

User question → product identification → minimum clarifying questions →
formulation classification → India/International jurisdiction → IP and
regulatory routing → evidence retrieval → reasoning → citation
validation → answer, confidence and next steps → human escalation where
required.

# 8. Functional Requirements

# 9. Knowledge Base Requirements

The initial corpus should prioritize authoritative primary sources:

-   Indian IP Acts and Rules: patents, GI, trademarks, copyright,
    designs and plant varieties.

-   AYUSH drug regulations, standards, notifications and related
    regulatory material.

-   Biological Diversity Act, Rules, ABS material and National
    Biodiversity Authority guidance.

-   FSSAI and Ayurveda-Aahar/nutraceutical regulations where applicable.

-   WIPO treaties and international frameworks including TRIPS, PCT,
    Madrid, Hague, Budapest, CBD, Nagoya and the WIPO GRATK Treaty.

-   Relevant patent, GI and registry records.

-   Relevant Indian and international case law.

-   Publicly available TKDL information and documented
    traditional-knowledge/prior-art material.

# 10. Metadata Model

Each document/chunk should retain document ID, title, authority,
jurisdiction, document type, effective date, version, section/article,
source URL, last-verified date and source text. This enables
version-aware retrieval and precise citations.

# 11. Proposed Architecture

User → Web/mobile/voice channel → language layer → conversation engine →
intent/entity extraction → product classifier + IP router + jurisdiction
router → query planner → vector retrieval + knowledge graph → reranker →
LLM reasoning → evidence validator → answer + citations + confidence →
escalation.

# 12. MVP Scope

-   Web-based conversational interface.

-   India-first citation-grounded RAG corpus.

-   Ayurvedic formulation/product classifier.

-   Patent/IP question routing.

-   Basic ABS and traditional-knowledge checks.

-   Relevant prior-art retrieval.

-   Exact source citations and confidence score.

-   Safe abstention and human-escalation UI.

-   A small multilingual demonstration using Bhashini or an equivalent
    national language layer.

# 13. Example MVP Interaction

User: \"I developed a new Ayurvedic formulation using Ashwagandha. Can I
patent it?\"

System: identify the product, ask minimum clarifying questions, classify
it, determine jurisdiction, retrieve relevant patent and
traditional-knowledge provisions, search prior art, explain the
applicable requirements, cite the exact sources, provide a confidence
level, and present next steps.

# 14. Success Metrics

-   Answer accuracy: target ≥90% on a curated benchmark.

-   Citation correctness: target ≥95%.

-   Hallucination rate: target \<5%.

-   Safe abstention: uncertain/out-of-scope cases should be qualified or
    escalated rather than fabricated.

-   Multilingual quality: evaluate intent preservation, terminology and
    answer quality.

-   Retrieval quality: track Recall@K, Precision@K and MRR.

# 15. Evaluation Dataset

Create a benchmark of approximately 200 questions spanning patents,
trademarks, GI, copyright, biodiversity/ABS, AYUSH regulation,
international regimes and prior-art/traditional-knowledge questions.
Each item should include the expected classification, jurisdiction,
authoritative source, relevant section/article, expected answer and
whether abstention is required.

# 16. Roadmap

Phase 1 --- Citation-grounded RAG: Collect and normalize official
documents; implement chunking, metadata, retrieval and citation.

Phase 2 --- Decision Intelligence: Add product classification, IP
routing, jurisdiction routing, confidence and regulatory roadmaps.

Phase 3 --- Knowledge Graph: Connect products, ingredients, laws,
sections, patents, regulations and jurisdictions.

Phase 4 --- Agentic Research: Add specialized IP, regulatory, ABS,
prior-art and international research agents under an orchestrator.

Phase 5 --- Multilingual + Voice: Expand language coverage and
voice/WhatsApp-style interaction.

# 17. Key Product Differentiator

IP-SAKTI Sahayak should not be positioned as a generic AI chatbot for
Ayurveda. Its differentiator is a citation-grounded decision engine that
converts an Ayurvedic innovation into an IP, regulatory, biodiversity
and commercialization roadmap. The conversational interface is the
access layer; classification, evidence retrieval, legal/regulatory
reasoning, citation validation and safe escalation are the core product.

# 18. Governance and Safety

-   Persistent \'information, not legal advice\' disclaimer.

-   No unsupported legal authority or fabricated citations.

-   Source/version tracking and audit logs.

-   Privacy, security and Digital Personal Data Protection alignment.

-   Explicit handling of uncertainty and safe abstention.

-   Restricted-source access only with authorized, logged permission.

-   Maintain a clear distinction between informational guidance and
    actions requiring a qualified legal or regulatory professional.

# 19. Requirements Traceability to SIH

  -----------------------------------------------------------------------
  SIH Requirement                     PRD Implementation
  ----------------------------------- -----------------------------------
  Jurisdiction toggle                 FR-04 / India vs International

  Formulation classification          FR-02 / Product Classification

  IP routing                          FR-03 / IP Type Detection

  ABS helper                          FR-08 / ABS Assistant

  TKDL / prior-art pointer            FR-09 / TKDL and Prior-Art

  Mandatory citations                 FR-06 / Citation Engine

  Confidence indicator                FR-07 / Confidence & Abstention

  Human facilitator escalation        FR-11 / Human Escalation

  Bhashini / multilingual             FR-12 / Multilingual and Voice

  Version-tracked corpus              FR-05 / RAG Knowledge Engine

  Knowledge graph                     Phase 3

  Agentic orchestration               Phase 4

  Paid-source connectors              Phase 4

  Privacy, audit, security            Governance and Safety

  Evaluation on accuracy, citations,  Success Metrics
  abstention and multilingual quality 
  -----------------------------------------------------------------------

# 20. Final MVP Definition

The MVP should demonstrate the complete core loop: a user describes an
Ayurvedic product or innovation; the assistant asks only necessary
clarifying questions; classifies the product; determines India or
international jurisdiction; retrieves authoritative IP, regulatory,
biodiversity and traditional-knowledge evidence; produces a reasoned
recommendation; cites the supporting sources; displays confidence; and
escalates when the evidence is insufficient.

# 21. Source Reference

Primary source: SIH Problem Statement 26045 supplied by the user. The
complete problem statement and description are reproduced in Part I of
this document.

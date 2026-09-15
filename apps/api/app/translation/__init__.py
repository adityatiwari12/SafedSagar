"""Multilingual language layer: detection, translation-provider abstraction,
legal-terminology glossary protection, and post-translation validation.

See docs/multilingual-architecture.md for the full design. Phase 1 scope:
this package plus DB columns and /chat wiring. The IndicTrans2 sidecar
process itself (services/indictrans2-sidecar/) is scaffolded but not yet
running a model - IndicTrans2Provider degrades to translation_status
"unavailable" until it is.
"""

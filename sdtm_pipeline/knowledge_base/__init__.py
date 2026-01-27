"""
SDTM Knowledge Base
===================
Pinecone vector store setup and management for SDTM knowledge.

Includes:
- Domain specifications (SDTM-IG 3.4)
- Controlled terminology
- Validation rules (Pinnacle 21/FDA)
- Business rules
- Derivation rules with cross-domain dependencies and many-to-one mappings
"""

from .setup_pinecone import PineconeKnowledgeBase, KnowledgeDocument
from .derivation_rules import (
    DERIVATION_RULES,
    CROSS_DOMAIN_DEPENDENCIES,
    SOURCE_COLUMN_PATTERNS,
    get_derivation_rule,
    get_cross_domain_dependencies,
    find_source_pattern,
    get_all_derivation_rules,
)

__all__ = [
    # Pinecone setup
    "PineconeKnowledgeBase",
    "KnowledgeDocument",
    # Derivation rules
    "DERIVATION_RULES",
    "CROSS_DOMAIN_DEPENDENCIES",
    "SOURCE_COLUMN_PATTERNS",
    "get_derivation_rule",
    "get_cross_domain_dependencies",
    "find_source_pattern",
    "get_all_derivation_rules",
]

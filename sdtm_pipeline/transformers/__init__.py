"""SDTM Transformers Module

Includes intelligent mapping capabilities for dynamic EDC-to-SDTM conversion.
"""

from .mapping_generator import MappingSpecificationGenerator
from .domain_transformers import (
    BaseDomainTransformer,
    DMTransformer,
    AETransformer,
    VSTransformer,
    LBTransformer,
    CMTransformer,
    get_transformer,
    get_available_domains
)

# Intelligent mapping for dynamic column discovery
try:
    from .intelligent_mapper import (
        IntelligentMapper,
        create_intelligent_mapping,
        ColumnMapping,
        DomainMappingSpec
    )
    INTELLIGENT_MAPPING_AVAILABLE = True
except ImportError:
    INTELLIGENT_MAPPING_AVAILABLE = False
    IntelligentMapper = None
    create_intelligent_mapping = None
    ColumnMapping = None
    DomainMappingSpec = None

__all__ = [
    "MappingSpecificationGenerator",
    "BaseDomainTransformer",
    "DMTransformer",
    "AETransformer",
    "VSTransformer",
    "LBTransformer",
    "CMTransformer",
    "get_transformer",
    "get_available_domains",
    # Intelligent mapping
    "IntelligentMapper",
    "create_intelligent_mapping",
    "ColumnMapping",
    "DomainMappingSpec",
    "INTELLIGENT_MAPPING_AVAILABLE"
]

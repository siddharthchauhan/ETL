"""
SDTM Pipeline - Clinical Data Transformation System
====================================================
A comprehensive pipeline for transforming raw clinical trial data
to CDISC SDTM format with validation and code generation.
"""

from .models.sdtm_models import (
    SDTMDomain,
    MappingSpecification,
    ValidationResult,
    TransformationResult
)

__version__ = "1.0.0"
__all__ = [
    "SDTMDomain",
    "MappingSpecification",
    "ValidationResult",
    "TransformationResult"
]

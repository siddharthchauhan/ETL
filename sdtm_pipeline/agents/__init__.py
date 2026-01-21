"""
SDTM Multi-Agent System
=======================
Specialized agents for SDTM transformation pipeline.

Agent Types:
1. Source Data Analyst - Schema analysis and data profiling
2. SDTM Expert - SDTM-IG specification and mapping expertise
3. Code Generator - SAS and R code generation
4. Validator Agent - Multi-layer validation
5. Anomaly Detector - Statistical and physiological anomaly detection
6. Protocol Compliance - Protocol adherence checking
"""

from .source_data_analyst import (
    SourceDataAnalystAgent,
    analyze_source_schema,
    detect_data_relationships,
    profile_source_data,
    assess_data_quality,
    SOURCE_ANALYST_TOOLS
)

from .sdtm_expert import (
    SDTMExpertAgent,
    lookup_sdtm_ig,
    validate_ct_value,
    get_historical_mappings,
    hybrid_sdtm_search,
    SDTM_EXPERT_TOOLS
)

from .code_generator import (
    CodeGeneratorAgent,
    generate_sas_transformation,
    generate_r_transformation,
    validate_code_syntax,
    test_code_snippet,
    CODE_GENERATOR_TOOLS
)

from .validator_agent import (
    ValidatorAgent,
    validate_structural,
    validate_cdisc_conformance,
    validate_cross_domain,
    validate_semantic,
    VALIDATOR_TOOLS
)

from .anomaly_detector import (
    AnomalyDetectorAgent,
    detect_statistical_anomalies,
    check_physiological_ranges,
    analyze_temporal_patterns,
    ANOMALY_DETECTOR_TOOLS
)

from .protocol_compliance import (
    ProtocolComplianceAgent,
    validate_visit_windows,
    check_inclusion_exclusion,
    validate_dosing_compliance,
    PROTOCOL_COMPLIANCE_TOOLS
)

__all__ = [
    # Source Data Analyst
    "SourceDataAnalystAgent",
    "analyze_source_schema",
    "detect_data_relationships",
    "profile_source_data",
    "assess_data_quality",
    "SOURCE_ANALYST_TOOLS",
    # SDTM Expert
    "SDTMExpertAgent",
    "lookup_sdtm_ig",
    "validate_ct_value",
    "get_historical_mappings",
    "hybrid_sdtm_search",
    "SDTM_EXPERT_TOOLS",
    # Code Generator
    "CodeGeneratorAgent",
    "generate_sas_transformation",
    "generate_r_transformation",
    "validate_code_syntax",
    "test_code_snippet",
    "CODE_GENERATOR_TOOLS",
    # Validator
    "ValidatorAgent",
    "validate_structural",
    "validate_cdisc_conformance",
    "validate_cross_domain",
    "validate_semantic",
    "VALIDATOR_TOOLS",
    # Anomaly Detector
    "AnomalyDetectorAgent",
    "detect_statistical_anomalies",
    "check_physiological_ranges",
    "analyze_temporal_patterns",
    "ANOMALY_DETECTOR_TOOLS",
    # Protocol Compliance
    "ProtocolComplianceAgent",
    "validate_visit_windows",
    "check_inclusion_exclusion",
    "validate_dosing_compliance",
    "PROTOCOL_COMPLIANCE_TOOLS",
]

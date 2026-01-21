"""
SDTM Expert Agent
=================
Specialized agent for SDTM-IG specification lookup,
controlled terminology validation, and mapping expertise.
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from functools import lru_cache

from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent


# SDTM-IG 3.4 Domain Reference (embedded knowledge)
SDTM_DOMAINS = {
    "DM": {
        "label": "Demographics",
        "class": "Special-Purpose",
        "required": ["STUDYID", "DOMAIN", "USUBJID", "SUBJID", "RFSTDTC", "RFENDTC", "SITEID", "BRTHDTC", "AGE", "AGEU", "SEX", "RACE", "ETHNIC", "ARMCD", "ARM", "COUNTRY"],
        "expected": ["INVID", "INVNAM", "RFXSTDTC", "RFXENDTC", "RFICDTC", "RFPENDTC", "DTHDTC", "DTHFL", "ACTARMCD", "ACTARM"],
    },
    "AE": {
        "label": "Adverse Events",
        "class": "Events",
        "required": ["STUDYID", "DOMAIN", "USUBJID", "AESEQ", "AETERM", "AEDECOD", "AESTDTC"],
        "expected": ["AEBODSYS", "AESEV", "AESER", "AEACN", "AEREL", "AEOUT", "AESCONG", "AESDISAB", "AESDTH", "AESHOSP", "AESLIFE", "AESMIE", "AEENDTC"],
    },
    "VS": {
        "label": "Vital Signs",
        "class": "Findings",
        "required": ["STUDYID", "DOMAIN", "USUBJID", "VSSEQ", "VSTESTCD", "VSTEST", "VSORRES", "VSORRESU"],
        "expected": ["VSCAT", "VSPOS", "VSLOC", "VSMETHOD", "VSBLFL", "VSDRVFL", "VSSTRESC", "VSSTRESN", "VSSTRESU", "VSDTC", "VISITNUM", "VISIT"],
    },
    "LB": {
        "label": "Laboratory Test Results",
        "class": "Findings",
        "required": ["STUDYID", "DOMAIN", "USUBJID", "LBSEQ", "LBTESTCD", "LBTEST", "LBORRES", "LBORRESU"],
        "expected": ["LBCAT", "LBSCAT", "LBSPEC", "LBMETHOD", "LBBLFL", "LBDRVFL", "LBSTRESC", "LBSTRESN", "LBSTRESU", "LBSTNRLO", "LBSTNRHI", "LBNRIND", "LBDTC", "VISITNUM", "VISIT"],
    },
    "CM": {
        "label": "Concomitant Medications",
        "class": "Interventions",
        "required": ["STUDYID", "DOMAIN", "USUBJID", "CMSEQ", "CMTRT"],
        "expected": ["CMCAT", "CMSCAT", "CMDECOD", "CMDOSE", "CMDOSU", "CMDOSFRM", "CMROUTE", "CMSTDTC", "CMENDTC", "CMONGO", "CMINDC"],
    },
    "EX": {
        "label": "Exposure",
        "class": "Interventions",
        "required": ["STUDYID", "DOMAIN", "USUBJID", "EXSEQ", "EXTRT", "EXDOSE", "EXDOSU", "EXSTDTC", "EXENDTC"],
        "expected": ["EXCAT", "EXDOSFRM", "EXDOSFRQ", "EXROUTE", "EXLOT", "EXLOC", "EXFAST", "EXADJ", "EPOCH", "VISITNUM", "VISIT"],
    },
    "MH": {
        "label": "Medical History",
        "class": "Events",
        "required": ["STUDYID", "DOMAIN", "USUBJID", "MHSEQ", "MHTERM"],
        "expected": ["MHCAT", "MHSCAT", "MHDECOD", "MHBODSYS", "MHSTDTC", "MHENDTC", "MHENRF", "MHONGO"],
    },
    "DS": {
        "label": "Disposition",
        "class": "Events",
        "required": ["STUDYID", "DOMAIN", "USUBJID", "DSSEQ", "DSTERM", "DSDECOD", "DSCAT", "DSSTDTC"],
        "expected": ["DSSCAT", "DSEPOCH"],
    },
}

# Controlled Terminology
CONTROLLED_TERMINOLOGY = {
    "SEX": ["M", "F", "U", "UNDIFFERENTIATED"],
    "RACE": ["AMERICAN INDIAN OR ALASKA NATIVE", "ASIAN", "BLACK OR AFRICAN AMERICAN", "NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER", "WHITE", "MULTIPLE", "NOT REPORTED", "UNKNOWN"],
    "ETHNIC": ["HISPANIC OR LATINO", "NOT HISPANIC OR LATINO", "NOT REPORTED", "UNKNOWN"],
    "AGEU": ["YEARS", "MONTHS", "WEEKS", "DAYS", "HOURS"],
    "AESER": ["Y", "N"],
    "AESEV": ["MILD", "MODERATE", "SEVERE"],
    "AEOUT": ["RECOVERED/RESOLVED", "RECOVERING/RESOLVING", "NOT RECOVERED/NOT RESOLVED", "RECOVERED/RESOLVED WITH SEQUELAE", "FATAL", "UNKNOWN"],
    "NY": ["Y", "N"],
    "LBNRIND": ["NORMAL", "LOW", "HIGH", "ABNORMAL", "LOW LOW", "HIGH HIGH"],
    "VSPOS": ["SITTING", "STANDING", "SUPINE", "PRONE"],
    "EPOCH": ["SCREENING", "RUN-IN", "TREATMENT", "FOLLOW-UP"],
}


@tool
def lookup_sdtm_ig(
    domain: str,
    variable: Optional[str] = None
) -> Dict[str, Any]:
    """
    Look up SDTM Implementation Guide specifications.

    Retrieves domain structure, required/expected variables, and variable definitions.
    Uses hybrid search (BM25 + semantic) for comprehensive lookup.

    Args:
        domain: SDTM domain code (e.g., DM, AE, VS)
        variable: Optional specific variable to look up

    Returns:
        SDTM-IG specification details
    """
    domain = domain.upper()

    # First check embedded knowledge
    if domain in SDTM_DOMAINS:
        result = {
            "domain": domain,
            "label": SDTM_DOMAINS[domain]["label"],
            "class": SDTM_DOMAINS[domain]["class"],
            "required_variables": SDTM_DOMAINS[domain]["required"],
            "expected_variables": SDTM_DOMAINS[domain]["expected"],
            "source": "embedded"
        }

        # If specific variable requested
        if variable:
            variable = variable.upper()
            all_vars = result["required_variables"] + result["expected_variables"]
            if variable in all_vars:
                result["variable"] = {
                    "name": variable,
                    "core": "Required" if variable in result["required_variables"] else "Expected",
                    "domain": domain
                }
    else:
        result = {"domain": domain, "error": f"Domain {domain} not in embedded knowledge"}

    # Try hybrid search for additional context
    try:
        from ..langgraph_agent.hybrid_search import get_hybrid_retriever
        retriever = get_hybrid_retriever()

        query = f"SDTM {domain} domain specification"
        if variable:
            query += f" {variable} variable"

        search_results = retriever.search(query, "sdtmig", top_k=3)
        if search_results:
            result["additional_context"] = [
                {"score": r.score, "content": r.metadata}
                for r in search_results
            ]
            result["source"] = "hybrid"
    except Exception:
        pass

    return result


@tool
def validate_ct_value(
    codelist: str,
    value: str
) -> Dict[str, Any]:
    """
    Validate a value against CDISC Controlled Terminology.

    Args:
        codelist: Controlled terminology codelist name (e.g., SEX, RACE)
        value: Value to validate

    Returns:
        Validation result with valid values if invalid
    """
    codelist = codelist.upper()
    value = value.upper() if value else ""

    if codelist not in CONTROLLED_TERMINOLOGY:
        # Try hybrid search for unknown codelists
        try:
            from ..langgraph_agent.hybrid_search import get_hybrid_retriever
            retriever = get_hybrid_retriever()
            results = retriever.search(
                f"CDISC controlled terminology {codelist} codelist values",
                "sdtmct",
                top_k=3
            )
            if results:
                return {
                    "codelist": codelist,
                    "value": value,
                    "found_in_kb": True,
                    "results": [r.metadata for r in results]
                }
        except Exception:
            pass

        return {
            "codelist": codelist,
            "error": f"Unknown codelist: {codelist}",
            "available_codelists": list(CONTROLLED_TERMINOLOGY.keys())
        }

    valid_values = CONTROLLED_TERMINOLOGY[codelist]
    is_valid = value in valid_values

    return {
        "codelist": codelist,
        "value": value,
        "is_valid": is_valid,
        "valid_values": valid_values if not is_valid else None,
        "message": "Value is valid" if is_valid else f"Invalid value. Expected one of: {valid_values}"
    }


@tool
def get_historical_mappings(
    source_columns: List[str],
    target_domain: str
) -> Dict[str, Any]:
    """
    Retrieve historical mapping patterns for similar source data.

    Finds previously successful mappings that can guide new mapping generation.

    Args:
        source_columns: List of source column names
        target_domain: Target SDTM domain

    Returns:
        Similar historical mappings with recommendations
    """
    try:
        from ..langgraph_agent.hybrid_search import get_historical_mapping_retriever
        retriever = get_historical_mapping_retriever()

        similar = retriever.search_similar_mappings(source_columns, target_domain, top_k=5)

        return {
            "target_domain": target_domain,
            "source_columns": source_columns,
            "similar_mappings": similar,
            "recommendations": _generate_mapping_recommendations(source_columns, target_domain, similar)
        }
    except Exception as e:
        # Fallback to rule-based recommendations
        return {
            "target_domain": target_domain,
            "source_columns": source_columns,
            "similar_mappings": [],
            "recommendations": _generate_rule_based_recommendations(source_columns, target_domain),
            "note": "Using rule-based recommendations (historical search unavailable)"
        }


def _generate_mapping_recommendations(
    source_columns: List[str],
    target_domain: str,
    historical: List[Dict]
) -> List[Dict[str, str]]:
    """Generate recommendations from historical patterns."""
    recommendations = []

    # Build pattern map from historical
    patterns = {}
    for mapping in historical:
        for col_map in mapping.get("column_mappings", []):
            src = col_map.get("source_column", "").lower()
            tgt = col_map.get("target_variable", "")
            if src and tgt:
                patterns[src] = tgt

    # Match source columns to patterns
    for col in source_columns:
        col_lower = col.lower()
        if col_lower in patterns:
            recommendations.append({
                "source": col,
                "target": patterns[col_lower],
                "confidence": "high",
                "basis": "historical"
            })
        else:
            # Try partial matching
            for pattern, target in patterns.items():
                if pattern in col_lower or col_lower in pattern:
                    recommendations.append({
                        "source": col,
                        "target": target,
                        "confidence": "medium",
                        "basis": "partial_match"
                    })
                    break

    return recommendations


def _generate_rule_based_recommendations(
    source_columns: List[str],
    target_domain: str
) -> List[Dict[str, str]]:
    """Generate rule-based mapping recommendations."""
    recommendations = []
    domain = target_domain.upper()

    # Common patterns
    patterns = {
        "subjid": "USUBJID",
        "subject": "USUBJID",
        "patient": "USUBJID",
        "age": "AGE",
        "sex": "SEX",
        "gender": "SEX",
        "race": "RACE",
        "ethnic": "ETHNIC",
        "country": "COUNTRY",
        "site": "SITEID",
        "birth": "BRTHDTC",
        "death": "DTHDTC",
        "start": f"{domain}STDTC" if domain not in ["DM"] else "RFSTDTC",
        "end": f"{domain}ENDTC" if domain not in ["DM"] else "RFENDTC",
        "date": f"{domain}DTC" if domain in ["VS", "LB", "EG"] else None,
        "term": f"{domain}TERM" if domain in ["AE", "MH", "CM", "DS"] else None,
        "dose": "EXDOSE" if domain == "EX" else "CMDOSE" if domain == "CM" else None,
        "unit": f"{domain}ORRESU" if domain in ["VS", "LB"] else None,
        "result": f"{domain}ORRES" if domain in ["VS", "LB"] else None,
        "test": f"{domain}TESTCD" if domain in ["VS", "LB", "EG"] else None,
        "visit": "VISITNUM",
    }

    for col in source_columns:
        col_lower = col.lower()
        for pattern, target in patterns.items():
            if target and pattern in col_lower:
                recommendations.append({
                    "source": col,
                    "target": target,
                    "confidence": "medium",
                    "basis": "rule"
                })
                break

    return recommendations


@tool
def hybrid_sdtm_search(
    query: str,
    index_names: Optional[List[str]] = None,
    top_k: int = 10
) -> Dict[str, Any]:
    """
    Perform hybrid search across SDTM knowledge bases.

    Combines BM25 keyword search with semantic vector search
    for improved retrieval accuracy.

    Args:
        query: Search query
        index_names: List of indexes to search (default: all SDTM indexes)
        top_k: Number of results to return

    Returns:
        Search results from hybrid retrieval
    """
    if not index_names:
        index_names = ["sdtmig", "sdtmct", "businessrules", "validationrules"]

    try:
        from ..langgraph_agent.hybrid_search import get_hybrid_retriever
        retriever = get_hybrid_retriever()

        results = retriever.search_multiple_indexes(
            query,
            index_names,
            top_k_per_index=5,
            total_top_k=top_k
        )

        return {
            "query": query,
            "result_count": len(results),
            "results": [
                {
                    "id": r.id,
                    "score": r.score,
                    "source": r.source,
                    "metadata": r.metadata
                }
                for r in results
            ]
        }
    except Exception as e:
        return {
            "query": query,
            "error": str(e),
            "results": []
        }


# List of all tools for this agent
SDTM_EXPERT_TOOLS = [
    lookup_sdtm_ig,
    validate_ct_value,
    get_historical_mappings,
    hybrid_sdtm_search
]


class SDTMExpertAgent:
    """
    SDTM Expert Agent for specification lookup and mapping expertise.

    Responsibilities:
    - Look up SDTM-IG specifications using hybrid RAG
    - Validate controlled terminology values
    - Retrieve similar historical mappings
    - Provide mapping recommendations
    """

    SYSTEM_PROMPT = """You are an SDTM Expert Agent specialized in CDISC SDTM standards.

Your responsibilities:
1. Provide accurate SDTM Implementation Guide (SDTM-IG 3.4) specifications
2. Validate values against CDISC Controlled Terminology
3. Find similar historical mappings to guide new transformations
4. Recommend variable mappings based on source data analysis

Key knowledge areas:
- SDTM domain structures (DM, AE, VS, LB, CM, EX, MH, DS, etc.)
- Required vs Expected vs Permissible variables
- Controlled Terminology codelists
- Variable naming conventions (--SEQ, --TESTCD, --ORRES, etc.)
- Derivation rules for standard variables (USUBJID, --DY, etc.)

When providing mapping recommendations:
- Always check controlled terminology for categorical variables
- Ensure date variables follow ISO 8601 format
- Verify required variables are mapped
- Consider timing variables (--DTC, --DY, --STDY, --ENDY)

Use hybrid search to find relevant guidelines when uncertain."""

    def __init__(self, api_key: Optional[str] = None):
        model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
        self.llm = ChatAnthropic(
            model=model,
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY"),
            max_tokens=4096
        )
        self.agent = create_react_agent(
            self.llm,
            SDTM_EXPERT_TOOLS,
            state_modifier=self.SYSTEM_PROMPT
        )

    async def get_mapping_guidance(
        self,
        source_columns: List[str],
        target_domain: str
    ) -> Dict[str, Any]:
        """Get mapping guidance for source data."""
        input_message = f"""Provide SDTM mapping guidance for the following:

Target Domain: {target_domain}
Source Columns: {', '.join(source_columns)}

Please:
1. Look up the {target_domain} domain specification
2. Find historical mappings for similar source data
3. Recommend variable mappings for each source column
4. Identify any controlled terminology requirements"""

        result = await self.agent.ainvoke({
            "messages": [{"role": "user", "content": input_message}]
        })

        return {
            "agent": "sdtm_expert",
            "target_domain": target_domain,
            "result": result.get("messages", [])[-1].content if result.get("messages") else "",
            "timestamp": datetime.now().isoformat()
        }

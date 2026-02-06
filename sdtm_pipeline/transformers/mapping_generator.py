"""
SDTM Mapping Specification Generator
====================================
Uses LLM to analyze source data and generate SDTM mapping specifications.
Enhanced with SDTMIG reference module, Tavily (web search) and Pinecone (vector database) for
referencing SDTM IG, business rules, and controlled terminology.
"""

import os
import pandas as pd
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import anthropic
from dotenv import load_dotenv
load_dotenv()

from ..models.sdtm_models import (
    MappingSpecification,
    ColumnMapping,
    SDTM_DOMAINS,
    CONTROLLED_TERMINOLOGY
)

# Import knowledge retriever for SDTM guidelines
try:
    from ..langgraph_agent.knowledge_tools import get_knowledge_retriever, SDTMKnowledgeRetriever
    KNOWLEDGE_TOOLS_AVAILABLE = True
except ImportError:
    KNOWLEDGE_TOOLS_AVAILABLE = False
    SDTMKnowledgeRetriever = None

# Import SDTMIG reference module
try:
    from ..langgraph_agent.sdtmig_reference import get_sdtmig_reference, SDTMIGReference
    SDTMIG_AVAILABLE = True
except ImportError:
    SDTMIG_AVAILABLE = False
    SDTMIGReference = None


class MappingSpecificationGenerator:
    """
    Generates SDTM mapping specifications using Claude AI.

    Analyzes source data structure and semantics to create
    appropriate mappings to SDTM domains and variables.
    """

    def __init__(self, api_key: str, study_id: str = "UNKNOWN", use_knowledge_tools: bool = True):
        self.api_key = api_key
        self.study_id = study_id
        self.client = anthropic.Anthropic(api_key=api_key)

        # Initialize SDTMIG reference
        self.sdtmig_reference: Optional[SDTMIGReference] = None
        if SDTMIG_AVAILABLE:
            try:
                self.sdtmig_reference = get_sdtmig_reference()
                print("  SDTMIG reference module enabled")
            except Exception as e:
                print(f"  WARNING: SDTMIG reference initialization failed: {e}")
                self.sdtmig_reference = None

        # Initialize knowledge retriever for SDTM guidelines
        self.knowledge_retriever: Optional[SDTMKnowledgeRetriever] = None
        if use_knowledge_tools and KNOWLEDGE_TOOLS_AVAILABLE:
            try:
                self.knowledge_retriever = get_knowledge_retriever()
                print("  Knowledge tools (Tavily/Pinecone) enabled for mapping generation")
            except Exception as e:
                print(f"  WARNING: Knowledge tools initialization failed: {e}")
                self.knowledge_retriever = None

    def analyze_source_data(self, df: pd.DataFrame, source_name: str) -> Dict[str, Any]:
        """
        Analyze source data structure and content.

        Args:
            df: Source DataFrame
            source_name: Name of the source dataset

        Returns:
            Dictionary with data analysis results
        """
        analysis = {
            "source_name": source_name,
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": []
        }

        for col in df.columns:
            col_info = {
                "name": col,
                "dtype": str(df[col].dtype),
                "non_null_count": int(df[col].notna().sum()),
                "null_count": int(df[col].isna().sum()),
                "unique_count": int(df[col].nunique()),
                "sample_values": df[col].dropna().head(5).tolist()
            }

            # Add numeric stats if applicable
            if pd.api.types.is_numeric_dtype(df[col]):
                col_info["min"] = float(df[col].min()) if df[col].notna().any() else None
                col_info["max"] = float(df[col].max()) if df[col].notna().any() else None
                col_info["mean"] = float(df[col].mean()) if df[col].notna().any() else None

            analysis["columns"].append(col_info)

        return analysis

    def determine_target_domain(self, source_name: str, df: pd.DataFrame) -> str:
        """
        Determine the target SDTM domain based on source data.

        Args:
            source_name: Name of source file/table
            df: Source DataFrame

        Returns:
            SDTM domain code (e.g., DM, AE, VS)
        """
        source_upper = source_name.upper().replace(".CSV", "")

        # Direct mapping based on common EDC domain names
        domain_mapping = {
            "DEMO": "DM",
            "DEMOGRAPHY": "DM",
            "DEMOGRAPHICS": "DM",
            "AEVENT": "AE",
            "AE": "AE",
            "ADVERSE": "AE",
            "VITALS": "VS",
            "VS": "VS",
            "VITAL": "VS",
            "CHEMLAB": "LB",
            "HEMLAB": "LB",
            "LAB": "LB",
            "LABORATORY": "LB",
            "CONMEDS": "CM",
            "CM": "CM",
            "MEDICATIONS": "CM",
            "DOSE": "EX",
            "EXPOSURE": "EX",
            "EX": "EX",
        }

        for key, domain in domain_mapping.items():
            if key in source_upper:
                return domain

        # If no direct match, use LLM to determine
        return self._llm_determine_domain(source_name, df)

    def _llm_determine_domain(self, source_name: str, df: pd.DataFrame) -> str:
        """Use LLM to determine target domain."""
        columns = list(df.columns)
        sample_data = df.head(3).to_dict(orient='records')

        prompt = f"""Analyze this clinical trial data and determine the appropriate SDTM domain.

Source: {source_name}
Columns: {columns}
Sample Data: {json.dumps(sample_data, default=str)[:1000]}

Available SDTM domains:
- DM: Demographics (subject-level information)
- AE: Adverse Events
- VS: Vital Signs
- LB: Laboratory Test Results
- CM: Concomitant Medications
- EX: Exposure (study treatment)
- MH: Medical History
- DS: Disposition

Return ONLY the 2-letter domain code (e.g., DM, AE, VS, LB, CM, EX)."""

        try:
            model = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-6")
            # Use streaming even for short calls to avoid timeout issues
            response_text = ""
            with self.client.messages.stream(
                model=model,
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}]
            ) as stream:
                for text in stream.text_stream:
                    response_text += text

            domain = response_text.strip().upper()[:2]
            if domain in SDTM_DOMAINS:
                return domain
        except Exception:
            pass

        return "DM"  # Default to Demographics

    def generate_mapping(
        self,
        df: pd.DataFrame,
        source_name: str,
        target_domain: Optional[str] = None
    ) -> MappingSpecification:
        """
        Generate SDTM mapping specification for source data.

        Args:
            df: Source DataFrame
            source_name: Name of source dataset
            target_domain: Target SDTM domain (auto-detected if not provided)

        Returns:
            MappingSpecification object
        """
        # Determine target domain
        if not target_domain:
            target_domain = self.determine_target_domain(source_name, df)

        # Get domain specification
        domain_spec = SDTM_DOMAINS.get(target_domain)

        # Analyze source data
        analysis = self.analyze_source_data(df, source_name)

        # Generate mappings using LLM
        column_mappings = self._generate_column_mappings(
            analysis, target_domain, domain_spec
        )

        # Generate derivation rules
        derivation_rules = self._generate_derivation_rules(
            analysis, target_domain, column_mappings
        )

        # Get applicable controlled terminology
        controlled_terms = self._get_applicable_ct(target_domain, column_mappings)

        return MappingSpecification(
            study_id=self.study_id,
            source_domain=source_name,
            target_domain=target_domain,
            column_mappings=column_mappings,
            derivation_rules=derivation_rules,
            controlled_terminologies=controlled_terms,
            comments=f"Auto-generated mapping for {source_name} to SDTM {target_domain}"
        )

    def _generate_column_mappings(
        self,
        analysis: Dict[str, Any],
        target_domain: str,
        domain_spec
    ) -> List[ColumnMapping]:
        """Generate column mappings using LLM enhanced with SDTMIG reference and knowledge retrieval."""
        source_columns = [col["name"] for col in analysis["columns"]]

        # Get SDTMIG reference context (comprehensive domain specification)
        sdtmig_context = ""
        if self.sdtmig_reference:
            sdtmig_context = self.sdtmig_reference.generate_mapping_prompt_context(target_domain)

        # Get expected SDTM variables from SDTMIG
        expected_vars = []
        if self.sdtmig_reference:
            expected_vars = (
                self.sdtmig_reference.get_required_variables(target_domain) +
                self.sdtmig_reference.get_expected_variables(target_domain)
            )
        elif domain_spec:
            expected_vars = (
                domain_spec.required_variables +
                domain_spec.expected_variables
            )

        # Retrieve additional SDTM knowledge from Pinecone/Tavily
        domain_knowledge = self._retrieve_domain_knowledge(target_domain, expected_vars)
        business_rules = self._retrieve_business_rules(target_domain)

        # Build enhanced prompt with SDTMIG reference
        knowledge_context = ""
        if domain_knowledge:
            knowledge_context = f"""

Additional SDTM Knowledge (from Pinecone):
{json.dumps(domain_knowledge, default=str)[:1500]}
"""

        rules_context = ""
        if business_rules:
            rules_context = f"""

Business Rules and Validation Requirements:
{json.dumps(business_rules, default=str)[:1000]}
"""

        # Build comprehensive prompt for LLM
        prompt = f"""You are an expert in CDISC SDTM standards (SDTMIG 3.4). Generate comprehensive column mappings from source EDC data to SDTM {target_domain} domain.

{sdtmig_context}
{knowledge_context}
{rules_context}

SOURCE DATA ANALYSIS:
=====================
Source columns: {source_columns}
Source sample data: {json.dumps(analysis['columns'][:15], default=str)}

MAPPING REQUIREMENTS:
=====================
1. Map ALL source columns to appropriate SDTM variables
2. Include ALL Required (Req) and Expected (Exp) SDTM variables
3. Create derivations for variables not directly in source
4. Convert dates to ISO 8601 format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
5. Apply controlled terminology mappings where applicable
6. Generate sequence numbers ({target_domain}SEQ)
7. Derive USUBJID from study/site/subject identifiers

For each mapping, provide in this JSON format:
{{
  "mappings": [
    {{
      "source_column": "SOURCE_COL or null if derived",
      "target_variable": "SDTM_VAR",
      "transformation": "transformation rule (e.g., 'Convert to ISO 8601', 'Map M/F to SEX codelist') or null",
      "derivation_rule": "derivation logic for derived variables or null",
      "controlled_terminology": "codelist name if applicable or null",
      "comments": "explanation of mapping logic"
    }}
  ]
}}

IMPORTANT: Include mappings for:
- All source columns that have SDTM equivalents
- All Required SDTM variables (derive if not in source)
- All Expected SDTM variables that can be derived
- Standard derived variables: DOMAIN, USUBJID, {target_domain}SEQ
- Date conversions to ISO 8601 format

Return ONLY valid JSON with comprehensive mappings."""

        try:
            model = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-6")
            max_tokens = int(os.getenv("ANTHROPIC_MAX_TOKENS", "16000"))

            # Use streaming to avoid timeout for long-running operations
            response_text = ""
            with self.client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            ) as stream:
                for text in stream.text_stream:
                    response_text += text

            # Extract JSON from response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                mapping_data = json.loads(response_text[json_start:json_end])

                mappings = []
                for m in mapping_data.get("mappings", []):
                    mappings.append(ColumnMapping(
                        source_column=m.get("source_column") or "",
                        target_variable=m.get("target_variable", ""),
                        transformation=m.get("transformation"),
                        derivation_rule=m.get("derivation_rule"),
                        controlled_terminology=m.get("controlled_terminology"),
                        comments=m.get("comments", "")
                    ))

                # Ensure all required SDTM variables are included
                mappings = self._ensure_required_variables(mappings, target_domain)
                return mappings

        except Exception as e:
            print(f"LLM mapping generation error: {e}")

        # Fallback: Generate basic mappings
        return self._generate_fallback_mappings(source_columns, target_domain)

    def _ensure_required_variables(
        self,
        mappings: List[ColumnMapping],
        target_domain: str
    ) -> List[ColumnMapping]:
        """
        Ensure all required SDTM variables are included in the mapping.

        Args:
            mappings: Current list of mappings
            target_domain: Target SDTM domain

        Returns:
            Updated mappings with all required variables
        """
        if not self.sdtmig_reference:
            return mappings

        # Get mapped variables
        mapped_vars = {m.target_variable.upper() for m in mappings if m.target_variable}

        # Get required and expected variables from SDTMIG
        required_vars = self.sdtmig_reference.get_required_variables(target_domain)
        expected_vars = self.sdtmig_reference.get_expected_variables(target_domain)
        derivation_rules = self.sdtmig_reference.get_derivation_rules(target_domain)
        ct_vars = self.sdtmig_reference.get_controlled_terminology_variables(target_domain)

        # Add missing required variables
        for var in required_vars:
            if var.upper() not in mapped_vars:
                var_def = self.sdtmig_reference.get_variable_definition(target_domain, var)
                derivation = derivation_rules.get(var, f"Derived - {var_def.get('label', '') if var_def else ''}")

                mappings.append(ColumnMapping(
                    source_column="",
                    target_variable=var,
                    derivation_rule=derivation,
                    controlled_terminology=ct_vars.get(var),
                    comments=f"Required variable (SDTMIG) - {var_def.get('label', '') if var_def else 'auto-added'}"
                ))
                mapped_vars.add(var.upper())

        # Add key expected variables if not present
        key_expected = ['USUBJID', f'{target_domain}SEQ', 'DOMAIN', 'STUDYID']
        for var in key_expected:
            if var.upper() not in mapped_vars:
                derivation = derivation_rules.get(var, "")
                mappings.append(ColumnMapping(
                    source_column="",
                    target_variable=var,
                    derivation_rule=derivation,
                    comments="Standard derived variable (SDTMIG)"
                ))
                mapped_vars.add(var.upper())

        return mappings

    def _retrieve_domain_knowledge(
        self,
        target_domain: str,
        expected_vars: List[str]
    ) -> Dict[str, Any]:
        """
        Retrieve SDTM domain knowledge from Pinecone and Tavily.

        Queries the vector database for:
        - Domain specification from SDTM IG
        - Variable definitions and data types
        - Derivation rules and guidance
        """
        knowledge = {}

        if not self.knowledge_retriever:
            return knowledge

        try:
            # Get domain specification
            domain_spec = self.knowledge_retriever.get_domain_specification(target_domain)
            if domain_spec:
                knowledge["domain_specification"] = domain_spec

            # Get variable definitions for key variables
            var_definitions = {}
            for var in expected_vars[:10]:  # Limit to avoid too many queries
                var_def = self.knowledge_retriever.get_sdtm_variable_definition(
                    target_domain, var
                )
                if var_def:
                    var_definitions[var] = var_def

            if var_definitions:
                knowledge["variable_definitions"] = var_definitions

            # Get mapping guidance
            guidance = self.knowledge_retriever.get_mapping_guidance(
                source_column="",  # General guidance
                target_domain=target_domain,
                target_variable=""
            )
            if guidance:
                knowledge["mapping_guidance"] = guidance

        except Exception as e:
            print(f"  Knowledge retrieval warning: {e}")

        return knowledge

    def _retrieve_business_rules(self, target_domain: str) -> List[Dict[str, Any]]:
        """
        Retrieve business rules for the domain from Pinecone.

        Queries for:
        - FDA validation rules
        - Pinnacle 21 checks
        - CDISC conformance rules
        """
        if not self.knowledge_retriever:
            return []

        try:
            rules = self.knowledge_retriever.get_business_rules(target_domain, rule_type="all")
            return rules[:10]  # Limit to top 10 rules
        except Exception as e:
            print(f"  Business rules retrieval warning: {e}")
            return []

    def _retrieve_controlled_terminology(self, codelist: str) -> Optional[List[str]]:
        """
        Retrieve controlled terminology from Pinecone.

        Args:
            codelist: CDISC codelist name (e.g., "SEX", "RACE")

        Returns:
            List of valid controlled terminology values
        """
        if not self.knowledge_retriever:
            return None

        try:
            return self.knowledge_retriever.get_controlled_terminology(codelist)
        except Exception as e:
            print(f"  CT retrieval warning for {codelist}: {e}")
            return None

    def _generate_fallback_mappings(
        self, source_columns: List[str], target_domain: str
    ) -> List[ColumnMapping]:
        """Generate basic fallback mappings."""
        mappings = []

        # Common mappings
        common_mappings = {
            "STUDY": ("STUDYID", None),
            "PT": ("SUBJID", None),
            "INVSITE": ("SITEID", None),
            "VISIT": (f"{target_domain}VISIT" if target_domain != "DM" else None, None),
        }

        # Domain-specific mappings
        domain_mappings = {
            "DM": {
                "DOB": ("BRTHDTC", "Convert YYYYMMDD to ISO 8601"),
                "GENDER": ("SEX", "Map M/F to controlled terminology"),
                "GENDRL": ("SEX", "Map MALE/FEMALE to M/F"),
                "RCE": ("RACE", "Map to CDISC controlled terminology"),
            },
            "AE": {
                "AETERM": ("AETERM", None),
                "AESTDT": ("AESTDTC", "Convert to ISO 8601"),
                "AEENDT": ("AEENDTC", "Convert to ISO 8601"),
                "AESEV": ("AESEV", None),
                "AEREL": ("AEREL", None),
            },
            "VS": {
                "VSTESTCD": ("VSTESTCD", None),
                "VSTEST": ("VSTEST", None),
                "VSORRES": ("VSORRES", None),
                "VSORRESU": ("VSORRESU", None),
                "VSDT": ("VSDTC", "Convert to ISO 8601"),
            },
            "LB": {
                "LBTESTCD": ("LBTESTCD", None),
                "LBTEST": ("LBTEST", None),
                "LBORRES": ("LBORRES", None),
                "LBORRESU": ("LBORRESU", None),
                "LBDT": ("LBDTC", "Convert to ISO 8601"),
            },
            "CM": {
                "CMTRT": ("CMTRT", None),
                "CMDOSE": ("CMDOSE", None),
                "CMSTDT": ("CMSTDTC", "Convert to ISO 8601"),
                "CMENDT": ("CMENDTC", "Convert to ISO 8601"),
            },
        }

        # Apply common mappings
        for source_col in source_columns:
            source_upper = source_col.upper()

            if source_upper in common_mappings:
                target, transform = common_mappings[source_upper]
                if target:
                    mappings.append(ColumnMapping(
                        source_column=source_col,
                        target_variable=target,
                        transformation=transform,
                        comments="Common mapping"
                    ))

            # Apply domain-specific mappings
            if target_domain in domain_mappings:
                if source_upper in domain_mappings[target_domain]:
                    target, transform = domain_mappings[target_domain][source_upper]
                    if target:
                        mappings.append(ColumnMapping(
                            source_column=source_col,
                            target_variable=target,
                            transformation=transform,
                            comments=f"Domain-specific mapping for {target_domain}"
                        ))

        # Add derived variables
        mappings.append(ColumnMapping(
            source_column="",
            target_variable="DOMAIN",
            derivation_rule=f"'{target_domain}'",
            comments="Constant value"
        ))

        mappings.append(ColumnMapping(
            source_column="",
            target_variable="USUBJID",
            derivation_rule="STUDYID || '-' || SITEID || '-' || SUBJID",
            comments="Derived unique subject identifier"
        ))

        if target_domain != "DM":
            mappings.append(ColumnMapping(
                source_column="",
                target_variable=f"{target_domain}SEQ",
                derivation_rule=f"Row number within USUBJID",
                comments="Derived sequence number"
            ))

        return mappings

    def _generate_derivation_rules(
        self,
        analysis: Dict[str, Any],
        target_domain: str,
        mappings: List[ColumnMapping]
    ) -> Dict[str, str]:
        """Generate derivation rules for computed variables using SDTMIG reference."""
        rules = {}

        # Get derivation rules from SDTMIG reference
        if self.sdtmig_reference:
            rules = self.sdtmig_reference.get_derivation_rules(target_domain).copy()

        # Standard derivations (fallback if not in SDTMIG)
        if "USUBJID" not in rules:
            rules["USUBJID"] = "STUDYID || '-' || SITEID || '-' || SUBJID"

        if "DOMAIN" not in rules:
            rules["DOMAIN"] = f"'{target_domain}'"

        # Sequence number
        seq_var = f"{target_domain}SEQ"
        if seq_var not in rules and target_domain != "DM":
            rules[seq_var] = f"ROW_NUMBER() OVER (PARTITION BY USUBJID ORDER BY {target_domain}DTC)"

        # Domain-specific derivations (enhanced)
        if target_domain == "DM":
            if "AGE" not in rules:
                rules["AGE"] = "floor((RFSTDTC - BRTHDTC) / 365.25) -- Calculate age in years"
            if "AGEU" not in rules:
                rules["AGEU"] = "'YEARS'"

        elif target_domain == "VS":
            if "VSSTRESC" not in rules:
                rules["VSSTRESC"] = "VSORRES converted to standard format"
            if "VSSTRESN" not in rules:
                rules["VSSTRESN"] = "Numeric conversion of VSSTRESC where applicable"
            if "VSBLFL" not in rules:
                rules["VSBLFL"] = "'Y' for baseline records, null otherwise"

        elif target_domain == "LB":
            if "LBSTRESC" not in rules:
                rules["LBSTRESC"] = "LBORRES converted to standard format"
            if "LBSTRESN" not in rules:
                rules["LBSTRESN"] = "Numeric conversion of LBSTRESC where applicable"
            if "LBNRIND" not in rules:
                rules["LBNRIND"] = "Derived: 'NORMAL' if LBSTNRLO <= LBSTRESN <= LBSTNRHI, 'LOW' if < LBSTNRLO, 'HIGH' if > LBSTNRHI"
            if "LBBLFL" not in rules:
                rules["LBBLFL"] = "'Y' for baseline records, null otherwise"

        elif target_domain == "AE":
            if "AESEQ" not in rules:
                rules["AESEQ"] = "ROW_NUMBER() OVER (PARTITION BY USUBJID ORDER BY AESTDTC, AETERM)"
            if "AESTDY" not in rules:
                rules["AESTDY"] = "AESTDTC - RFSTDTC + 1 (if AESTDTC >= RFSTDTC) else AESTDTC - RFSTDTC"
            if "AEENDY" not in rules:
                rules["AEENDY"] = "AEENDTC - RFSTDTC + 1 (if AEENDTC >= RFSTDTC) else AEENDTC - RFSTDTC"

        elif target_domain == "CM":
            if "CMSEQ" not in rules:
                rules["CMSEQ"] = "ROW_NUMBER() OVER (PARTITION BY USUBJID ORDER BY CMSTDTC, CMTRT)"
            if "CMSTDY" not in rules:
                rules["CMSTDY"] = "CMSTDTC - RFSTDTC + 1 (if CMSTDTC >= RFSTDTC) else CMSTDTC - RFSTDTC"
            if "CMENDY" not in rules:
                rules["CMENDY"] = "CMENDTC - RFSTDTC + 1 (if CMENDTC >= RFSTDTC) else CMENDTC - RFSTDTC"

        elif target_domain == "EX":
            if "EXSEQ" not in rules:
                rules["EXSEQ"] = "ROW_NUMBER() OVER (PARTITION BY USUBJID ORDER BY EXSTDTC)"
            if "EXSTDY" not in rules:
                rules["EXSTDY"] = "EXSTDTC - RFSTDTC + 1 (if EXSTDTC >= RFSTDTC) else EXSTDTC - RFSTDTC"

        elif target_domain == "MH":
            if "MHSEQ" not in rules:
                rules["MHSEQ"] = "ROW_NUMBER() OVER (PARTITION BY USUBJID ORDER BY MHTERM)"

        # Add derivations from mappings
        for mapping in mappings:
            if mapping.derivation_rule and mapping.target_variable:
                if mapping.target_variable not in rules:
                    rules[mapping.target_variable] = mapping.derivation_rule

        return rules

    def _get_applicable_ct(
        self, target_domain: str, mappings: List[ColumnMapping]
    ) -> Dict[str, List[str]]:
        """
        Get applicable controlled terminology from local definitions and Pinecone.

        Enhances local CT with values from the knowledge base when available.
        """
        ct = {}

        # Get mapped variables (filter out None values)
        mapped_vars = {m.target_variable for m in mappings if m.target_variable}

        # Common CT codelists by variable name patterns
        ct_codelists = {
            "SEX": "SEX",
            "RACE": "RACE",
            "ETHNIC": "ETHNIC",
            "NY": "NY",  # Yes/No
            "NRIND": "NRIND",  # Normal Range Indicator
            "POSITION": "POSITION",
            "LOC": "LOC",  # Location
            "LAT": "LAT",  # Laterality
            "DIR": "DIR",  # Directionality
            "METHOD": "METHOD",
            "AESSION": "AESSION",  # AE Serious
            "AEOUT": "AEOUT",  # AE Outcome
            "AEACN": "AEACN",  # AE Action Taken
            "AEREL": "AEREL",  # AE Relationship
            "AETOXGR": "AETOXGR",  # AE Toxicity Grade
        }

        # Check local CT definitions first
        for var, values in CONTROLLED_TERMINOLOGY.items():
            # Check if var is in mapped_vars OR if var is a substring of any target_variable
            # (e.g., "SEX" in "AESEX" for AE domain)
            if var in mapped_vars or any(
                m.target_variable and var in m.target_variable for m in mappings
            ):
                ct[var] = values

        # Enhance with Pinecone knowledge base if available
        if self.knowledge_retriever:
            for var in mapped_vars:
                # Determine if variable needs CT
                var_upper = var.upper()
                for pattern, codelist in ct_codelists.items():
                    if pattern in var_upper and var not in ct:
                        # Query knowledge base for CT
                        kb_ct = self._retrieve_controlled_terminology(codelist)
                        if kb_ct:
                            ct[var] = kb_ct
                            print(f"    Retrieved CT for {var} from knowledge base")
                        break

        return ct

    def generate_mapping_excel(
        self, spec: MappingSpecification, output_path: str
    ) -> str:
        """
        Export mapping specification to Excel format.

        Args:
            spec: MappingSpecification object
            output_path: Path for output Excel file

        Returns:
            Path to created file
        """
        # Create DataFrames for each sheet
        # Main mapping sheet
        mapping_data = []
        for m in spec.column_mappings:
            mapping_data.append({
                "Source Column": m.source_column,
                "Target Variable": m.target_variable,
                "Transformation": m.transformation or "",
                "Derivation Rule": m.derivation_rule or "",
                "Controlled Terminology": m.controlled_terminology or "",
                "Comments": m.comments
            })

        mapping_df = pd.DataFrame(mapping_data)

        # Metadata sheet
        metadata_df = pd.DataFrame([{
            "Study ID": spec.study_id,
            "Source Domain": spec.source_domain,
            "Target Domain": spec.target_domain,
            "Created At": spec.created_at,
            "Created By": spec.created_by,
            "Version": spec.version
        }])

        # Derivation rules sheet
        derivation_df = pd.DataFrame([
            {"Variable": k, "Rule": v}
            for k, v in spec.derivation_rules.items()
        ])

        # Controlled terminology sheet
        ct_data = []
        for var, values in spec.controlled_terminologies.items():
            for val in values:
                ct_data.append({"Variable": var, "Value": val})
        ct_df = pd.DataFrame(ct_data) if ct_data else pd.DataFrame()

        # Write to Excel
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            mapping_df.to_excel(writer, sheet_name='Mappings', index=False)
            metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
            derivation_df.to_excel(writer, sheet_name='Derivations', index=False)
            if not ct_df.empty:
                ct_df.to_excel(writer, sheet_name='Controlled Terminology', index=False)

        return output_path

    def generate_mapping_json(self, spec: MappingSpecification, output_path: str) -> str:
        """Export mapping specification to JSON format."""
        with open(output_path, 'w') as f:
            json.dump(spec.to_dict(), f, indent=2)
        return output_path

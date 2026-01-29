"""
SDTM Knowledge Retrieval Tools
==============================
Tools for searching SDTM guidelines, business rules, and validation rules
using Tavily (web search) and Pinecone (vector database).
"""

import os
from typing import Dict, Any, List, Optional
from functools import lru_cache
from dotenv import load_dotenv
load_dotenv()

# Pinecone client
try:
    from pinecone import Pinecone
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False

# Tavily client
try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False

# Firecrawl client (backup for Tavily)
try:
    from firecrawl import FirecrawlApp
    FIRECRAWL_AVAILABLE = True
except ImportError:
    FIRECRAWL_AVAILABLE = False

# OpenAI client for embeddings
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from .config import get_tavily_config, get_pinecone_config


class SDTMKnowledgeRetriever:
    """
    Retrieves SDTM knowledge from Pinecone indexes and web search.

    Used during:
    - Mapping generation: Get SDTM variable definitions and rules
    - Validation: Get business rules and CDISC standards
    - Transformation: Get controlled terminology and derivation rules
    """

    def __init__(self):
        self.pinecone_client = None
        self.tavily_client = None
        self.firecrawl_client = None  # Backup for Tavily
        self.openai_client = None
        self.indexes = {}
        self._tavily_disabled = False  # Flag to disable Tavily after rate limit
        self._use_firecrawl = False    # Flag to switch to Firecrawl
        self._firecrawl_disabled = False  # Flag to disable Firecrawl after rate limit
        self._web_search_disabled = False  # Flag when both services are rate limited
        self._initialize_clients()

    def _initialize_clients(self):
        """Initialize Pinecone, OpenAI, and Tavily clients."""
        # Initialize OpenAI for embeddings
        if OPENAI_AVAILABLE:
            try:
                openai_key = os.getenv("OPENAI_API_KEY")
                if openai_key and openai_key != "your_openai_api_key_here":
                    self.openai_client = OpenAI(api_key=openai_key)
                    print("  OpenAI embeddings initialized")
                else:
                    print("  WARNING: OPENAI_API_KEY not set, Pinecone queries will be limited")
            except Exception as e:
                print(f"  WARNING: OpenAI initialization failed: {e}")
                self.openai_client = None

        # Initialize Pinecone
        if PINECONE_AVAILABLE:
            try:
                config = get_pinecone_config()
                self.pinecone_client = Pinecone(api_key=config["api_key"])
                # List available indexes
                indexes = self.pinecone_client.list_indexes()
                for idx in indexes:
                    self.indexes[idx.name] = idx
                print(f"  Pinecone initialized with {len(self.indexes)} indexes")
            except Exception as e:
                print(f"  WARNING: Pinecone initialization failed: {e}")
                self.pinecone_client = None

        # Initialize Tavily
        if TAVILY_AVAILABLE:
            try:
                config = get_tavily_config()
                self.tavily_client = TavilyClient(api_key=config["api_key"])
                print("  Tavily web search initialized")
            except Exception as e:
                print(f"  WARNING: Tavily initialization failed: {e}")
                self.tavily_client = None

        # Initialize Firecrawl (backup for Tavily)
        if FIRECRAWL_AVAILABLE:
            try:
                firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY", "fc-4a39356cf081453f96726af430e24ae1")
                self.firecrawl_client = FirecrawlApp(api_key=firecrawl_api_key)
                print("  Firecrawl initialized (backup for Tavily)")
            except Exception as e:
                print(f"  WARNING: Firecrawl initialization failed: {e}")
                self.firecrawl_client = None

    def _get_embedding(self, text: str, model: str = None) -> List[float]:
        """Generate embedding using OpenAI."""
        if not self.openai_client:
            return []
        try:
            embedding_model = model or os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
            response = self.openai_client.embeddings.create(
                input=text,
                model=embedding_model
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"  Embedding error: {e}")
            return []

    def list_pinecone_indexes(self) -> List[str]:
        """List available Pinecone indexes."""
        return list(self.indexes.keys())

    def search_pinecone(
        self,
        query: str,
        index_name: str,
        namespace: str = "",
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search Pinecone index for relevant documents using OpenAI embeddings.

        Args:
            query: Search query
            index_name: Name of the Pinecone index
            namespace: Optional namespace within the index
            top_k: Number of results to return

        Returns:
            List of matching documents with scores
        """
        if not self.pinecone_client:
            return []

        try:
            index = self.pinecone_client.Index(index_name)

            # Generate embedding using OpenAI
            query_vector = self._get_embedding(query)

            if not query_vector:
                print(f"  WARNING: Could not generate embedding for query")
                return []

            results = index.query(
                vector=query_vector,
                top_k=top_k,
                namespace=namespace if namespace else None,
                include_metadata=True
            )

            return [
                {
                    "id": match.id,
                    "score": match.score,
                    "metadata": match.metadata if hasattr(match, 'metadata') else {}
                }
                for match in results.matches
            ]
        except Exception as e:
            print(f"  Pinecone search error for {index_name}: {e}")
            return []

    def search_web(
        self,
        query: str,
        search_depth: str = "basic",
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search the web for SDTM-related information.

        Uses Tavily by default, switches to Firecrawl after first Tavily failure.

        Args:
            query: Search query
            search_depth: "basic" or "advanced"
            max_results: Maximum number of results

        Returns:
            List of search results
        """
        # Skip if both services are rate limited
        if self._web_search_disabled:
            return []

        # Use Firecrawl if switched after Tavily failure
        if self._use_firecrawl and not self._firecrawl_disabled:
            return self._search_firecrawl(query, max_results)

        # Try Tavily first
        if self.tavily_client and not self._tavily_disabled:
            try:
                response = self.tavily_client.search(
                    query=query,
                    search_depth=search_depth,
                    max_results=max_results,
                    include_domains=["cdisc.org", "fda.gov", "ich.org"],
                    include_answer=True
                )
                return response.get("results", [])
            except Exception as e:
                error_msg = str(e).lower()

                # On any Tavily error, switch to Firecrawl
                if "usage limit" in error_msg or "rate limit" in error_msg or "quota" in error_msg:
                    print(f"  Tavily rate limit exceeded, switching to Firecrawl")
                else:
                    print(f"  Tavily error: {e}, switching to Firecrawl")

                self._tavily_disabled = True
                self._use_firecrawl = True

                # Try Firecrawl as fallback
                return self._search_firecrawl(query, max_results)

        # Fall back to Firecrawl if Tavily not available
        return self._search_firecrawl(query, max_results)

    def _search_firecrawl(
        self,
        query: str,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search using Firecrawl API.

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of search results formatted like Tavily results
        """
        if not self.firecrawl_client or self._firecrawl_disabled:
            return []

        try:
            # Firecrawl search with SDTM-related domains
            search_query = f"{query} site:cdisc.org OR site:fda.gov OR site:ich.org"

            # Use Firecrawl's search endpoint
            response = self.firecrawl_client.search(
                query=search_query,
                limit=max_results
            )

            # Format results to match Tavily structure
            results = []

            # Handle Firecrawl v2 SearchData response (has .web attribute)
            if hasattr(response, 'web') and response.web:
                for item in response.web[:max_results]:
                    results.append({
                        "title": getattr(item, 'title', '') or '',
                        "url": getattr(item, 'url', '') or '',
                        "content": (getattr(item, 'description', '') or '')[:500],
                        "source": "firecrawl"
                    })
            # Handle list response format
            elif response and isinstance(response, list):
                for item in response[:max_results]:
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "content": item.get("description", item.get("content", ""))[:500],
                        "source": "firecrawl"
                    })
            # Handle dict response format
            elif response and isinstance(response, dict):
                data = response.get("data", response.get("results", []))
                for item in data[:max_results]:
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "content": item.get("description", item.get("content", ""))[:500],
                        "source": "firecrawl"
                    })

            return results
        except Exception as e:
            error_msg = str(e).lower()

            # Check for rate limit errors
            if "rate limit" in error_msg or "429" in error_msg:
                self._firecrawl_disabled = True
                self._web_search_disabled = True  # Both services now rate limited
                print(f"  Firecrawl rate limit exceeded, web search disabled for this session")
            else:
                print(f"  Firecrawl search error: {e}")

            return []

    @lru_cache(maxsize=100)
    def get_sdtm_variable_definition(
        self,
        domain: str,
        variable: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get SDTM variable definition from knowledge base.

        Args:
            domain: SDTM domain code (e.g., "DM", "AE")
            variable: Variable name (e.g., "USUBJID", "AETERM")

        Returns:
            Variable definition including type, controlled terminology, rules
        """
        # First try Pinecone with actual index names
        if self.pinecone_client:
            # Try sdtmig index first (SDTM Implementation Guide)
            for index_name in ["sdtmig", "sdtmmetadata"]:
                if index_name in self.indexes:
                    results = self.search_pinecone(
                        query=f"SDTM {domain} domain {variable} variable definition",
                        index_name=index_name,
                        top_k=3
                    )
                    if results:
                        return results[0].get("metadata", {})

        # Fall back to web search
        if self.tavily_client:
            results = self.search_web(
                query=f"CDISC SDTM {domain} {variable} variable definition specification",
                max_results=3
            )
            if results:
                return {
                    "source": "web",
                    "content": results[0].get("content", ""),
                    "url": results[0].get("url", "")
                }

        return None

    @lru_cache(maxsize=50)
    def get_domain_specification(self, domain: str) -> Optional[Dict[str, Any]]:
        """
        Get full domain specification from SDTM IG.

        Args:
            domain: SDTM domain code

        Returns:
            Domain specification including required/expected variables
        """
        # Try Pinecone first with actual index names
        if self.pinecone_client:
            for index_name in ["sdtmig", "sdtmmetadata"]:
                if index_name in self.indexes:
                    results = self.search_pinecone(
                        query=f"SDTM {domain} domain specification required variables expected variables",
                        index_name=index_name,
                        top_k=5
                    )
                    if results:
                        return {
                            "domain": domain,
                            "results": results
                        }

        # Fall back to web search
        if self.tavily_client:
            results = self.search_web(
                query=f"CDISC SDTM Implementation Guide {domain} domain specification",
                search_depth="advanced",
                max_results=5
            )
            if results:
                return {
                    "domain": domain,
                    "source": "web",
                    "results": results
                }

        return None

    @lru_cache(maxsize=100)
    def get_controlled_terminology(
        self,
        codelist: str
    ) -> Optional[List[str]]:
        """
        Get CDISC controlled terminology values for a codelist.

        Args:
            codelist: Codelist name (e.g., "SEX", "RACE", "ETHNIC")

        Returns:
            List of valid controlled terminology values
        """
        # Try Pinecone with actual index names
        if self.pinecone_client:
            # sdtmct is the controlled terminology index
            if "sdtmct" in self.indexes:
                results = self.search_pinecone(
                    query=f"CDISC controlled terminology {codelist} codelist values",
                    index_name="sdtmct",
                    top_k=3
                )
                if results:
                    # Extract values from metadata
                    for r in results:
                        if "values" in r.get("metadata", {}):
                            return r["metadata"]["values"]
                        # Try alternate field names
                        if "terms" in r.get("metadata", {}):
                            return r["metadata"]["terms"]
                        if "codelist_values" in r.get("metadata", {}):
                            return r["metadata"]["codelist_values"]

        # Fall back to web search
        if self.tavily_client:
            results = self.search_web(
                query=f"CDISC controlled terminology {codelist} codelist valid values list",
                max_results=3
            )
            # Would need to parse results

        return None

    @lru_cache(maxsize=50)
    def get_business_rules(
        self,
        domain: str,
        rule_type: str = "all"
    ) -> List[Dict[str, Any]]:
        """
        Get FDA/Pinnacle 21 business rules for a domain.

        Args:
            domain: SDTM domain code
            rule_type: "FDA", "P21", "CDISC", or "all"

        Returns:
            List of applicable business rules
        """
        rules = []

        # Try Pinecone with actual index names
        if self.pinecone_client:
            # businessrules and validationrules are the actual indexes
            for index_name in ["businessrules", "validationrules"]:
                if index_name in self.indexes:
                    query = f"SDTM {domain} domain validation business rules"
                    if rule_type != "all":
                        query = f"{rule_type} {query}"

                    results = self.search_pinecone(
                        query=query,
                        index_name=index_name,
                        top_k=10
                    )
                    rules.extend([r.get("metadata", {}) for r in results])

        # Supplement with web search
        if self.tavily_client and len(rules) < 5:
            web_results = self.search_web(
                query=f"Pinnacle 21 SDTM {domain} validation rules FDA business rules",
                search_depth="advanced",
                max_results=5
            )
            for r in web_results:
                rules.append({
                    "source": "web",
                    "content": r.get("content", ""),
                    "url": r.get("url", "")
                })

        return rules

    def get_mapping_guidance(
        self,
        source_column: str,
        target_domain: str,
        target_variable: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get guidance for mapping a source column to SDTM variable.

        Args:
            source_column: Source EDC column name
            target_domain: Target SDTM domain
            target_variable: Target SDTM variable

        Returns:
            Mapping guidance including transformation rules
        """
        # Try Pinecone with actual index names
        if self.pinecone_client:
            # sdtmig and sdtmmetadata contain mapping guidance
            for index_name in ["sdtmig", "sdtmmetadata"]:
                if index_name in self.indexes:
                    query = f"SDTM {target_domain} {target_variable} derivation rule transformation"
                    if source_column:
                        query = f"map source {source_column} to {query}"

                    results = self.search_pinecone(
                        query=query,
                        index_name=index_name,
                        top_k=3
                    )
                    if results:
                        return results[0].get("metadata", {})

        # Fall back to web search for standard mappings
        if self.tavily_client:
            results = self.search_web(
                query=f"SDTM {target_domain} {target_variable} derivation rule transformation",
                max_results=3
            )
            if results:
                return {
                    "source": "web",
                    "guidance": results[0].get("content", "")
                }

        return None

    def get_mapping_specification(
        self,
        domain: str,
        source_columns: List[str]
    ) -> Dict[str, Any]:
        """
        Get complete mapping specification for a domain from knowledge base.

        Args:
            domain: Target SDTM domain code
            source_columns: List of source column names

        Returns:
            Mapping specification with variable mappings and derivation rules
        """
        spec = {
            "domain": domain,
            "variable_mappings": [],
            "derivation_rules": [],
            "controlled_terminology": {},
            "source": "pinecone"
        }

        if not self.pinecone_client or not self.openai_client:
            spec["source"] = "default"
            return spec

        # Get domain specification from SDTM IG
        if "sdtmig" in self.indexes:
            results = self.search_pinecone(
                query=f"SDTM {domain} domain variables required expected permissible specification",
                index_name="sdtmig",
                top_k=10
            )
            for r in results:
                meta = r.get("metadata", {})
                if meta:
                    spec["variable_mappings"].append({
                        "variable": meta.get("variable", meta.get("name", "")),
                        "label": meta.get("label", ""),
                        "type": meta.get("type", ""),
                        "core": meta.get("core", ""),
                        "description": meta.get("description", meta.get("text", "")),
                        "score": r.get("score", 0)
                    })

        # Get derivation rules from business rules
        if "businessrules" in self.indexes:
            results = self.search_pinecone(
                query=f"SDTM {domain} domain derivation transformation calculation rule",
                index_name="businessrules",
                top_k=10
            )
            for r in results:
                meta = r.get("metadata", {})
                if meta:
                    spec["derivation_rules"].append({
                        "rule_id": meta.get("rule_id", meta.get("id", "")),
                        "variable": meta.get("variable", ""),
                        "rule": meta.get("rule", meta.get("description", meta.get("text", ""))),
                        "score": r.get("score", 0)
                    })

        # Get controlled terminology
        if "sdtmct" in self.indexes:
            results = self.search_pinecone(
                query=f"SDTM {domain} controlled terminology codelist",
                index_name="sdtmct",
                top_k=10
            )
            for r in results:
                meta = r.get("metadata", {})
                codelist = meta.get("codelist", meta.get("name", ""))
                if codelist and meta:
                    spec["controlled_terminology"][codelist] = {
                        "values": meta.get("values", meta.get("terms", [])),
                        "description": meta.get("description", meta.get("text", ""))
                    }

        return spec

    def get_validation_rules_for_domain(
        self,
        domain: str,
        include_fda: bool = True,
        include_p21: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get comprehensive validation rules for a domain.

        Args:
            domain: SDTM domain code
            include_fda: Include FDA validation rules
            include_p21: Include Pinnacle 21 rules

        Returns:
            List of validation rules with details
        """
        rules = []

        if not self.pinecone_client or not self.openai_client:
            return rules

        # Get from validationrules index
        if "validationrules" in self.indexes:
            query = f"SDTM {domain} domain validation rule check conformance"
            results = self.search_pinecone(
                query=query,
                index_name="validationrules",
                top_k=20
            )
            for r in results:
                meta = r.get("metadata", {})
                if meta:
                    rules.append({
                        "rule_id": meta.get("rule_id", meta.get("id", f"VR-{len(rules)+1}")),
                        "category": meta.get("category", "validation"),
                        "severity": meta.get("severity", "error"),
                        "message": meta.get("message", meta.get("description", meta.get("text", ""))),
                        "check": meta.get("check", ""),
                        "source": "validationrules",
                        "score": r.get("score", 0)
                    })

        # Get from businessrules index
        if "businessrules" in self.indexes:
            query = f"SDTM {domain} domain FDA Pinnacle 21 conformance rule"
            results = self.search_pinecone(
                query=query,
                index_name="businessrules",
                top_k=20
            )
            for r in results:
                meta = r.get("metadata", {})
                if meta:
                    rules.append({
                        "rule_id": meta.get("rule_id", meta.get("id", f"BR-{len(rules)+1}")),
                        "category": meta.get("category", "business"),
                        "severity": meta.get("severity", "warning"),
                        "message": meta.get("message", meta.get("description", meta.get("text", ""))),
                        "check": meta.get("check", meta.get("rule", "")),
                        "source": "businessrules",
                        "score": r.get("score", 0)
                    })

        # Sort by score and deduplicate
        rules.sort(key=lambda x: x.get("score", 0), reverse=True)
        return rules[:30]

    def get_sdtm_generation_guidance(
        self,
        domain: str,
        source_data_description: str
    ) -> Dict[str, Any]:
        """
        Get guidance for generating SDTM dataset from source data.

        Args:
            domain: Target SDTM domain
            source_data_description: Description of source data structure

        Returns:
            Guidance including transformation steps, required variables, and examples
        """
        guidance = {
            "domain": domain,
            "required_variables": [],
            "expected_variables": [],
            "transformation_steps": [],
            "examples": [],
            "source": "pinecone"
        }

        if not self.pinecone_client or not self.openai_client:
            guidance["source"] = "default"
            return guidance

        # Get required/expected variables from SDTM IG
        if "sdtmig" in self.indexes:
            results = self.search_pinecone(
                query=f"SDTM {domain} domain required expected permissible variables",
                index_name="sdtmig",
                top_k=15
            )
            for r in results:
                meta = r.get("metadata", {})
                core = meta.get("core", "").upper()
                var_info = {
                    "variable": meta.get("variable", meta.get("name", "")),
                    "label": meta.get("label", ""),
                    "type": meta.get("type", ""),
                    "description": meta.get("description", meta.get("text", ""))
                }
                if core == "REQ" or "required" in str(meta).lower():
                    guidance["required_variables"].append(var_info)
                else:
                    guidance["expected_variables"].append(var_info)

        # Get transformation guidance from business rules
        if "businessrules" in self.indexes:
            query = f"SDTM {domain} transformation derivation algorithm from {source_data_description}"
            results = self.search_pinecone(
                query=query,
                index_name="businessrules",
                top_k=10
            )
            for r in results:
                meta = r.get("metadata", {})
                if meta:
                    guidance["transformation_steps"].append({
                        "step": meta.get("rule", meta.get("description", meta.get("text", ""))),
                        "variable": meta.get("variable", ""),
                        "source": meta.get("source_variable", "")
                    })

        return guidance

    # ── DTA (Data Transfer Agreement) Methods ──────────────────────

    def search_dta(
        self,
        query: str,
        domain: Optional[str] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search the DTA Pinecone index for relevant agreement clauses.

        Args:
            query: Free-text search query (e.g. "adverse event reporting requirements")
            domain: Optional SDTM domain code to focus the search (e.g. "AE")
            top_k: Number of results to return

        Returns:
            List of matching DTA clauses with metadata
        """
        search_query = f"Data Transfer Agreement {query}"
        if domain:
            search_query = f"Data Transfer Agreement {domain} domain {query}"

        results = self.search_pinecone(
            query=search_query,
            index_name="dta",
            top_k=top_k,
        )

        # Enrich results with metadata extraction
        enriched = []
        for r in results:
            meta = r.get("metadata", {})
            enriched.append({
                "clause_id": meta.get("clause_id", r.get("id", "")),
                "section_title": meta.get("section_title", ""),
                "applicable_domains": meta.get("applicable_domains", "ALL"),
                "requirement_type": meta.get("requirement_type", "general"),
                "dta_id": meta.get("dta_id", ""),
                "score": r.get("score", 0),
                "content": meta.get("text", meta.get("content", "")),
            })
        return enriched

    def get_dta_requirements_for_domain(
        self,
        domain: str
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all DTA requirements applicable to a specific SDTM domain.

        Args:
            domain: SDTM domain code (e.g. "AE", "DM", "LB")

        Returns:
            List of DTA requirement dicts with clause_id, section_title,
            requirement_type, and content.
        """
        # Two-pronged search: domain-specific + general requirements
        domain_results = self.search_pinecone(
            query=f"Data Transfer Agreement {domain} domain requirements specifications quality",
            index_name="dta",
            top_k=15,
        )
        general_results = self.search_pinecone(
            query=f"Data Transfer Agreement general data quality completeness format requirements",
            index_name="dta",
            top_k=10,
        )

        # Merge and deduplicate by ID
        seen_ids: set = set()
        merged: List[Dict[str, Any]] = []
        for r in domain_results + general_results:
            rid = r.get("id", "")
            if rid in seen_ids:
                continue
            seen_ids.add(rid)

            meta = r.get("metadata", {})
            applicable = meta.get("applicable_domains", "ALL")

            # Keep if applicable to this domain or to ALL
            if applicable == "ALL" or domain.upper() in applicable.upper():
                merged.append({
                    "clause_id": meta.get("clause_id", rid),
                    "section_title": meta.get("section_title", ""),
                    "applicable_domains": applicable,
                    "requirement_type": meta.get("requirement_type", "general"),
                    "dta_id": meta.get("dta_id", ""),
                    "score": r.get("score", 0),
                    "content": meta.get("text", meta.get("content", "")),
                })

        # Sort by relevance
        merged.sort(key=lambda x: x["score"], reverse=True)
        return merged

    def search_all_indexes(
        self,
        query: str,
        top_k_per_index: int = 5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search all available Pinecone indexes for a query.

        Args:
            query: Search query
            top_k_per_index: Results per index

        Returns:
            Dictionary with results from each index
        """
        all_results = {}

        if not self.pinecone_client or not self.openai_client:
            return all_results

        for index_name in self.indexes:
            results = self.search_pinecone(
                query=query,
                index_name=index_name,
                top_k=top_k_per_index
            )
            if results:
                all_results[index_name] = results

        return all_results


# Import hybrid search components
try:
    from .hybrid_search import (
        HybridRetriever,
        HistoricalMappingRetriever,
        get_hybrid_retriever,
        get_historical_mapping_retriever,
        SearchResult
    )
    HYBRID_SEARCH_AVAILABLE = True
except ImportError:
    HYBRID_SEARCH_AVAILABLE = False


class SDTMKnowledgeRetrieverExtended(SDTMKnowledgeRetriever):
    """
    Extended knowledge retriever with hybrid search capabilities.

    Adds BM25 + Semantic hybrid search for improved retrieval accuracy.
    """

    def __init__(self):
        super().__init__()
        self.hybrid_retriever = None
        self.historical_retriever = None
        self._init_hybrid_search()

    def _init_hybrid_search(self):
        """Initialize hybrid search components."""
        if HYBRID_SEARCH_AVAILABLE:
            try:
                self.hybrid_retriever = get_hybrid_retriever()
                self.historical_retriever = get_historical_mapping_retriever()
                print("  Hybrid search (BM25 + Semantic) enabled")
            except Exception as e:
                print(f"  WARNING: Hybrid search initialization failed: {e}")

    def hybrid_search(
        self,
        query: str,
        index_name: str = "sdtmig",
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining BM25 and semantic retrieval.

        Args:
            query: Search query
            index_name: Name of the index to search
            top_k: Number of results to return

        Returns:
            List of search results with combined scores
        """
        if not self.hybrid_retriever:
            # Fall back to semantic-only search
            return self.search_pinecone(query, index_name, top_k=top_k)

        try:
            results = self.hybrid_retriever.search(query, index_name, top_k)
            return [
                {
                    "id": r.id,
                    "score": r.score,
                    "source": r.source,
                    "metadata": r.metadata
                }
                for r in results
            ]
        except Exception as e:
            print(f"  Hybrid search error: {e}")
            return self.search_pinecone(query, index_name, top_k=top_k)

    def search_historical_mappings(
        self,
        source_columns: List[str],
        target_domain: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for historical mapping patterns.

        Args:
            source_columns: Source column names
            target_domain: Target SDTM domain
            top_k: Number of results

        Returns:
            List of similar historical mappings
        """
        if not self.historical_retriever:
            return []

        try:
            return self.historical_retriever.search_similar_mappings(
                source_columns, target_domain, top_k
            )
        except Exception as e:
            print(f"  Historical mapping search error: {e}")
            return []

    def get_sdtm_variable_definition_hybrid(
        self,
        domain: str,
        variable: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get SDTM variable definition using hybrid search.

        Args:
            domain: SDTM domain code
            variable: Variable name

        Returns:
            Variable definition with enhanced retrieval
        """
        query = f"SDTM {domain} domain {variable} variable definition type core"

        # Try hybrid search first
        results = self.hybrid_search(query, "sdtmig", top_k=5)
        if results:
            # Return best match
            return results[0].get("metadata", {})

        # Fall back to original method
        return self.get_sdtm_variable_definition(domain, variable)

    def get_validation_rules_hybrid(
        self,
        domain: str,
        rule_type: str = "all"
    ) -> List[Dict[str, Any]]:
        """
        Get validation rules using hybrid search.

        Args:
            domain: SDTM domain code
            rule_type: Type of rules ("FDA", "P21", "CDISC", "all")

        Returns:
            List of validation rules
        """
        query = f"SDTM {domain} domain validation rule"
        if rule_type != "all":
            query = f"{rule_type} {query}"

        # Search multiple indexes with hybrid retrieval
        all_results = []

        for index_name in ["validationrules", "businessrules"]:
            results = self.hybrid_search(query, index_name, top_k=15)
            for r in results:
                all_results.append({
                    "rule_id": r.get("metadata", {}).get("rule_id", r.get("id")),
                    "category": r.get("metadata", {}).get("category", "validation"),
                    "severity": r.get("metadata", {}).get("severity", "warning"),
                    "message": r.get("metadata", {}).get("message",
                              r.get("metadata", {}).get("description", "")),
                    "score": r.get("score", 0),
                    "source": index_name
                })

        # Deduplicate and sort by score
        seen_ids = set()
        unique_results = []
        for r in sorted(all_results, key=lambda x: x.get("score", 0), reverse=True):
            rule_id = r.get("rule_id")
            if rule_id and rule_id not in seen_ids:
                seen_ids.add(rule_id)
                unique_results.append(r)

        return unique_results[:30]


# Singleton instances
_knowledge_retriever = None
_extended_retriever = None


def get_knowledge_retriever() -> SDTMKnowledgeRetriever:
    """Get or create the knowledge retriever singleton."""
    global _knowledge_retriever
    if _knowledge_retriever is None:
        print("\nInitializing SDTM Knowledge Retriever...")
        _knowledge_retriever = SDTMKnowledgeRetriever()
    return _knowledge_retriever


def get_extended_knowledge_retriever() -> SDTMKnowledgeRetrieverExtended:
    """Get or create the extended knowledge retriever with hybrid search."""
    global _extended_retriever
    if _extended_retriever is None:
        print("\nInitializing Extended SDTM Knowledge Retriever...")
        _extended_retriever = SDTMKnowledgeRetrieverExtended()
    return _extended_retriever

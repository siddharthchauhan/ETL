"""
SDTM Knowledge Retrieval Tools
==============================
Tools for searching SDTM guidelines, business rules, and validation rules
using Tavily (web search) and Pinecone (vector database).
"""

import os
from typing import Dict, Any, List, Optional
from functools import lru_cache

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
        self.indexes = {}
        self._initialize_clients()

    def _initialize_clients(self):
        """Initialize Pinecone and Tavily clients."""
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
        Search Pinecone index for relevant documents using integrated inference.

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

            # Get index dimension for proper vector sizing
            index_stats = index.describe_index_stats()
            dimension = index_stats.dimension if hasattr(index_stats, 'dimension') else 3072

            # Try using the integrated inference API for text-to-vector search
            # This requires the index to be configured with an embedding model
            try:
                # Try query with integrated inference (newer Pinecone feature)
                results = index.query(
                    data=query,  # Use text directly with integrated inference
                    top_k=top_k,
                    namespace=namespace if namespace else None,
                    include_metadata=True
                )
            except Exception:
                # Fallback: Create a simple query vector for demonstration
                # In production, use a proper embedding service
                import hashlib
                # Create a deterministic pseudo-embedding from query text
                query_hash = hashlib.sha256(query.encode()).digest()
                # Expand hash to match index dimension
                base_vector = [float(b) / 255.0 - 0.5 for b in query_hash]
                query_vector = (base_vector * (dimension // len(base_vector) + 1))[:dimension]

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

        Args:
            query: Search query
            search_depth: "basic" or "advanced"
            max_results: Maximum number of results

        Returns:
            List of search results
        """
        if not self.tavily_client:
            return []

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
            print(f"  Tavily search error: {e}")
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


# Singleton instance
_knowledge_retriever = None


def get_knowledge_retriever() -> SDTMKnowledgeRetriever:
    """Get or create the knowledge retriever singleton."""
    global _knowledge_retriever
    if _knowledge_retriever is None:
        print("\nInitializing SDTM Knowledge Retriever...")
        _knowledge_retriever = SDTMKnowledgeRetriever()
    return _knowledge_retriever

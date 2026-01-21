"""
Hybrid Search System (BM25 + Semantic)
======================================
Combines BM25 keyword search with semantic vector search for improved
retrieval accuracy in SDTM knowledge bases.
"""

import os
import re
from typing import Dict, Any, List, Optional, Tuple
from functools import lru_cache
from dataclasses import dataclass

# BM25 imports
try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False

# NLTK for tokenization
try:
    import nltk
    from nltk.tokenize import word_tokenize
    from nltk.corpus import stopwords
    from nltk.stem import PorterStemmer
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False


@dataclass
class SearchResult:
    """A single search result."""
    id: str
    score: float
    metadata: Dict[str, Any]
    source: str  # 'bm25', 'semantic', or 'hybrid'


class BM25Index:
    """
    Local BM25 index for keyword-based search.

    Provides fast, exact keyword matching complementary to
    semantic vector search.
    """

    def __init__(self, documents: Optional[List[Dict[str, Any]]] = None):
        """
        Initialize BM25 index with optional documents.

        Args:
            documents: List of documents with 'id', 'text', and 'metadata' fields
        """
        self.documents: List[Dict[str, Any]] = []
        self.tokenized_corpus: List[List[str]] = []
        self.bm25: Optional[BM25Okapi] = None
        self.stemmer = PorterStemmer() if NLTK_AVAILABLE else None
        self.stop_words = set()

        # Initialize NLTK resources
        if NLTK_AVAILABLE:
            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                try:
                    nltk.download('punkt', quiet=True)
                    nltk.download('punkt_tab', quiet=True)
                except Exception:
                    pass
            try:
                self.stop_words = set(stopwords.words('english'))
            except LookupError:
                try:
                    nltk.download('stopwords', quiet=True)
                    self.stop_words = set(stopwords.words('english'))
                except Exception:
                    pass

        if documents:
            self.index(documents)

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize and preprocess text."""
        if not text:
            return []

        # Convert to lowercase
        text = text.lower()

        # Tokenize
        if NLTK_AVAILABLE:
            try:
                tokens = word_tokenize(text)
            except Exception:
                # Fallback to simple tokenization
                tokens = re.findall(r'\b\w+\b', text)
        else:
            tokens = re.findall(r'\b\w+\b', text)

        # Remove stopwords and stem
        processed = []
        for token in tokens:
            if token not in self.stop_words and len(token) > 1:
                if self.stemmer:
                    processed.append(self.stemmer.stem(token))
                else:
                    processed.append(token)

        return processed

    def index(self, documents: List[Dict[str, Any]]) -> None:
        """
        Index a list of documents.

        Args:
            documents: List of documents with 'id', 'text', and optional 'metadata'
        """
        if not BM25_AVAILABLE:
            print("WARNING: rank-bm25 not installed. BM25 search disabled.")
            return

        self.documents = documents
        self.tokenized_corpus = []

        for doc in documents:
            text = doc.get('text', doc.get('content', ''))
            tokens = self._tokenize(text)
            self.tokenized_corpus.append(tokens)

        if self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)

    def add_document(self, document: Dict[str, Any]) -> None:
        """Add a single document to the index."""
        self.documents.append(document)
        text = document.get('text', document.get('content', ''))
        tokens = self._tokenize(text)
        self.tokenized_corpus.append(tokens)

        # Rebuild BM25 index
        if BM25_AVAILABLE and self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)

    def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """
        Search the index using BM25 scoring.

        Args:
            query: Search query string
            top_k: Number of results to return

        Returns:
            List of SearchResult objects sorted by score
        """
        if not self.bm25 or not self.documents:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scores = self.bm25.get_scores(query_tokens)

        # Get top-k indices
        scored_indices = [(i, score) for i, score in enumerate(scores)]
        scored_indices.sort(key=lambda x: x[1], reverse=True)
        top_indices = scored_indices[:top_k]

        results = []
        for idx, score in top_indices:
            if score > 0:  # Only include non-zero scores
                doc = self.documents[idx]
                results.append(SearchResult(
                    id=doc.get('id', str(idx)),
                    score=float(score),
                    metadata=doc.get('metadata', {}),
                    source='bm25'
                ))

        return results


class HybridRetriever:
    """
    Combines BM25 (keyword) and Semantic (vector) search.

    Uses Reciprocal Rank Fusion (RRF) to merge results from both
    search methods for improved retrieval accuracy.

    Default weights:
    - BM25: 40% (good for exact terminology matches)
    - Semantic: 60% (good for conceptual similarity)
    """

    def __init__(
        self,
        bm25_weight: float = 0.4,
        semantic_weight: float = 0.6,
        rrf_k: int = 60
    ):
        """
        Initialize hybrid retriever.

        Args:
            bm25_weight: Weight for BM25 results (0-1)
            semantic_weight: Weight for semantic results (0-1)
            rrf_k: RRF constant (default 60)
        """
        self.bm25_weight = bm25_weight
        self.semantic_weight = semantic_weight
        self.rrf_k = rrf_k

        # BM25 indexes by domain/index name
        self.bm25_indexes: Dict[str, BM25Index] = {}

        # Pinecone client for semantic search
        self.pinecone_client = None
        self.openai_client = None

        self._initialize_clients()

    def _initialize_clients(self) -> None:
        """Initialize Pinecone and OpenAI clients."""
        # Initialize OpenAI for embeddings
        try:
            from openai import OpenAI
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key and openai_key != "your_openai_api_key_here":
                self.openai_client = OpenAI(api_key=openai_key)
        except ImportError:
            pass
        except Exception as e:
            print(f"  WARNING: OpenAI initialization failed: {e}")

        # Initialize Pinecone
        try:
            from pinecone import Pinecone
            api_key = os.getenv("PINECONE_API_KEY")
            if api_key:
                self.pinecone_client = Pinecone(api_key=api_key)
        except ImportError:
            pass
        except Exception as e:
            print(f"  WARNING: Pinecone initialization failed: {e}")

    def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI."""
        if not self.openai_client:
            return []
        try:
            model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
            response = self.openai_client.embeddings.create(
                input=text,
                model=model
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"  Embedding error: {e}")
            return []

    def create_bm25_index(
        self,
        index_name: str,
        documents: List[Dict[str, Any]]
    ) -> None:
        """
        Create a BM25 index for a specific domain.

        Args:
            index_name: Name of the index
            documents: Documents to index
        """
        self.bm25_indexes[index_name] = BM25Index(documents)

    def _semantic_search(
        self,
        query: str,
        index_name: str,
        top_k: int = 10,
        namespace: str = ""
    ) -> List[SearchResult]:
        """Perform semantic search using Pinecone."""
        if not self.pinecone_client:
            return []

        try:
            index = self.pinecone_client.Index(index_name)
            query_vector = self._get_embedding(query)

            if not query_vector:
                return []

            results = index.query(
                vector=query_vector,
                top_k=top_k,
                namespace=namespace if namespace else None,
                include_metadata=True
            )

            search_results = []
            for match in results.matches:
                search_results.append(SearchResult(
                    id=match.id,
                    score=float(match.score),
                    metadata=match.metadata if hasattr(match, 'metadata') else {},
                    source='semantic'
                ))

            return search_results

        except Exception as e:
            print(f"  Semantic search error for {index_name}: {e}")
            return []

    def _bm25_search(
        self,
        query: str,
        index_name: str,
        top_k: int = 10
    ) -> List[SearchResult]:
        """Perform BM25 keyword search."""
        if index_name not in self.bm25_indexes:
            return []

        return self.bm25_indexes[index_name].search(query, top_k)

    def _reciprocal_rank_fusion(
        self,
        bm25_results: List[SearchResult],
        semantic_results: List[SearchResult],
        top_k: int = 10
    ) -> List[SearchResult]:
        """
        Merge results using Reciprocal Rank Fusion.

        RRF score = sum(1 / (k + rank)) for each result list
        where k is a constant (default 60).
        """
        rrf_scores: Dict[str, float] = {}
        result_map: Dict[str, SearchResult] = {}

        # Score BM25 results
        for rank, result in enumerate(bm25_results):
            rrf_score = self.bm25_weight / (self.rrf_k + rank + 1)
            rrf_scores[result.id] = rrf_scores.get(result.id, 0) + rrf_score
            if result.id not in result_map:
                result_map[result.id] = result

        # Score semantic results
        for rank, result in enumerate(semantic_results):
            rrf_score = self.semantic_weight / (self.rrf_k + rank + 1)
            rrf_scores[result.id] = rrf_scores.get(result.id, 0) + rrf_score
            if result.id not in result_map:
                result_map[result.id] = result

        # Sort by RRF score
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        results = []
        for doc_id in sorted_ids[:top_k]:
            result = result_map[doc_id]
            # Update score with RRF score
            results.append(SearchResult(
                id=result.id,
                score=rrf_scores[doc_id],
                metadata=result.metadata,
                source='hybrid'
            ))

        return results

    def search(
        self,
        query: str,
        index_name: str,
        top_k: int = 10,
        namespace: str = "",
        bm25_only: bool = False,
        semantic_only: bool = False
    ) -> List[SearchResult]:
        """
        Perform hybrid search combining BM25 and semantic results.

        Args:
            query: Search query
            index_name: Name of the index to search
            top_k: Number of results to return
            namespace: Optional namespace for Pinecone
            bm25_only: Only use BM25 search
            semantic_only: Only use semantic search

        Returns:
            List of SearchResult objects
        """
        if bm25_only:
            return self._bm25_search(query, index_name, top_k)

        if semantic_only:
            return self._semantic_search(query, index_name, top_k, namespace)

        # Get results from both methods
        bm25_results = self._bm25_search(query, index_name, top_k * 2)
        semantic_results = self._semantic_search(query, index_name, top_k * 2, namespace)

        # If only one method has results, return those
        if not bm25_results and not semantic_results:
            return []
        if not bm25_results:
            return semantic_results[:top_k]
        if not semantic_results:
            return bm25_results[:top_k]

        # Merge using RRF
        return self._reciprocal_rank_fusion(bm25_results, semantic_results, top_k)

    def search_multiple_indexes(
        self,
        query: str,
        index_names: List[str],
        top_k_per_index: int = 5,
        total_top_k: int = 10
    ) -> List[SearchResult]:
        """
        Search across multiple indexes and merge results.

        Args:
            query: Search query
            index_names: List of index names to search
            top_k_per_index: Results per index
            total_top_k: Total results to return

        Returns:
            Merged and sorted results
        """
        all_results: List[SearchResult] = []

        for index_name in index_names:
            results = self.search(query, index_name, top_k_per_index)
            all_results.extend(results)

        # Sort by score and deduplicate
        seen_ids = set()
        unique_results = []
        for result in sorted(all_results, key=lambda x: x.score, reverse=True):
            if result.id not in seen_ids:
                seen_ids.add(result.id)
                unique_results.append(result)

        return unique_results[:total_top_k]


class HistoricalMappingRetriever:
    """
    Retrieves historical mapping patterns for similar source data.

    Uses hybrid search to find previously successful mappings
    that can guide new mapping generation.
    """

    def __init__(self, hybrid_retriever: Optional[HybridRetriever] = None):
        self.retriever = hybrid_retriever or HybridRetriever()
        self.mapping_index = BM25Index()
        self.historical_mappings: List[Dict[str, Any]] = []

    def index_historical_mappings(
        self,
        mappings: List[Dict[str, Any]]
    ) -> None:
        """
        Index historical mapping specifications.

        Args:
            mappings: List of mapping specs with source_columns, target_domain, etc.
        """
        self.historical_mappings = mappings

        # Create searchable documents
        documents = []
        for i, mapping in enumerate(mappings):
            # Build searchable text from mapping
            text_parts = [
                f"Domain: {mapping.get('target_domain', '')}",
                f"Source columns: {', '.join(mapping.get('source_columns', []))}",
            ]

            # Add column mappings
            for col_map in mapping.get('column_mappings', []):
                text_parts.append(
                    f"{col_map.get('source_column', '')} -> {col_map.get('target_variable', '')}"
                )

            documents.append({
                'id': f"mapping_{i}",
                'text': ' '.join(text_parts),
                'metadata': mapping
            })

        self.mapping_index.index(documents)

    def search_similar_mappings(
        self,
        source_columns: List[str],
        target_domain: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find historical mappings similar to the current source data.

        Args:
            source_columns: List of source column names
            target_domain: Target SDTM domain
            top_k: Number of results to return

        Returns:
            List of similar historical mappings
        """
        query = f"Domain: {target_domain} Source columns: {', '.join(source_columns)}"

        results = self.mapping_index.search(query, top_k)

        return [
            result.metadata
            for result in results
            if result.metadata
        ]


# Singleton instances
_hybrid_retriever: Optional[HybridRetriever] = None
_historical_retriever: Optional[HistoricalMappingRetriever] = None


def get_hybrid_retriever() -> HybridRetriever:
    """Get or create the hybrid retriever singleton."""
    global _hybrid_retriever
    if _hybrid_retriever is None:
        _hybrid_retriever = HybridRetriever()
    return _hybrid_retriever


def get_historical_mapping_retriever() -> HistoricalMappingRetriever:
    """Get or create the historical mapping retriever singleton."""
    global _historical_retriever
    if _historical_retriever is None:
        _historical_retriever = HistoricalMappingRetriever(get_hybrid_retriever())
    return _historical_retriever

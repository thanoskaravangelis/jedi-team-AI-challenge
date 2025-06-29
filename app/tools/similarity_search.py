"""Similarity search tool using ChromaDB for semantic search of market research data."""

import os
from typing import List, Optional
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

# Optional imports with fallbacks
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    logger.warning("ChromaDB not available. Similarity search will be disabled.")
    CHROMADB_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    logger.warning("sentence-transformers not available. Similarity search will be disabled.")
    SENTENCE_TRANSFORMERS_AVAILABLE = False


class SimilaritySearchInput(BaseModel):
    """Input schema for similarity search."""
    query: str = Field(description="Query to find semantically similar market research insights")
    limit: int = Field(default=5, description="Maximum number of similar results to return")
    similarity_threshold: float = Field(default=0.5, description="Minimum similarity score (0.0-1.0)")


class SimilaritySearchTool(BaseTool):
    """Tool for semantic similarity search of market research data."""
    
    name: str = "similarity_search"
    description: str = """Find semantically similar market research insights using vector embeddings.
    This tool is useful when exact keyword matches don't work but you need conceptually related information.
    It can find insights about similar topics, demographics, or market trends even if the exact words don't match."""
    
    args_schema: type[BaseModel] = SimilaritySearchInput
    
    def __init__(self):
        super().__init__()
        # Use object.__setattr__ to bypass Pydantic validation
        object.__setattr__(self, 'chroma_client', None)
        object.__setattr__(self, 'collection', None)
        object.__setattr__(self, 'encoder', None)
        try:
            self._initialize_client()
        except Exception as e:
            logger.warning(f"SimilaritySearchTool initialization failed: {e}")
            object.__setattr__(self, 'chroma_client', None)
            object.__setattr__(self, 'collection', None)
            object.__setattr__(self, 'encoder', None)
    
    def _initialize_client(self):
        """Initialize ChromaDB client and collection."""
        if not CHROMADB_AVAILABLE or not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.warning("ChromaDB or sentence-transformers not available. Similarity search disabled.")
            return
            
        try:
            # Initialize the sentence transformer for embeddings
            encoder = SentenceTransformer('all-MiniLM-L6-v2')
            object.__setattr__(self, 'encoder', encoder)
            
            # Initialize ChromaDB
            vector_db_path = os.getenv("VECTOR_DB_PATH", "./vector_db")
            chroma_client = chromadb.PersistentClient(
                path=vector_db_path,
                settings=Settings(anonymized_telemetry=False)
            )
            object.__setattr__(self, 'chroma_client', chroma_client)
            
            # Get or create collection
            try:
                collection = self.chroma_client.get_collection("market_research")
                object.__setattr__(self, 'collection', collection)
                logger.info("Connected to existing ChromaDB collection")
            except:
                collection = self.chroma_client.create_collection(
                    name="market_research",
                    metadata={"description": "Market research insights"}
                )
                object.__setattr__(self, 'collection', collection)
                logger.info("Created new ChromaDB collection")
                self._populate_collection()
            
        except Exception as e:
            logger.error(f"Error initializing ChromaDB: {e}")
            object.__setattr__(self, 'chroma_client', None)
            object.__setattr__(self, 'collection', None)
            object.__setattr__(self, 'encoder', None)
    
    def _populate_collection(self):
        """Populate the collection with market research data."""
        try:
            from app.tools.internal_search import get_all_market_research_data
            
            logger.info("Populating ChromaDB with market research data...")
            
            # Get all market research statements
            statements = get_all_market_research_data()
            
            if not statements:
                logger.warning("No market research data found to populate vector database")
                return
            
            # Generate embeddings
            embeddings = self.encoder.encode(statements).tolist()
            
            # Prepare data for ChromaDB
            ids = [f"statement_{i}" for i in range(len(statements))]
            
            # Add to collection in batches to avoid memory issues
            batch_size = 100
            for i in range(0, len(statements), batch_size):
                batch_statements = statements[i:i + batch_size]
                batch_embeddings = embeddings[i:i + batch_size]
                batch_ids = ids[i:i + batch_size]
                
                self.collection.add(
                    embeddings=batch_embeddings,
                    documents=batch_statements,
                    ids=batch_ids
                )
            
            logger.info(f"Successfully populated ChromaDB with {len(statements)} statements")
            
        except Exception as e:
            logger.error(f"Error populating ChromaDB collection: {e}")
    
    def _run(self, query: str, limit: int = 5, similarity_threshold: float = 0.3) -> str:
        """Execute the similarity search."""
        if not CHROMADB_AVAILABLE or not SENTENCE_TRANSFORMERS_AVAILABLE:
            return "Similarity search is not available. ChromaDB or sentence-transformers dependencies not installed."
            
        if not self.collection or not self.encoder:
            return "Similarity search is not available. ChromaDB not properly initialized."
        
        try:
            logger.info(f"Performing similarity search for: {query}")
            
            # Try multiple query variations for better matching
            query_variations = [
                query,  # Original query
                query.lower(),  # Lowercase
                query.replace("trens", "trends").replace("trends", "trend"),  # Fix common typos and variations
            ]
            
            # Also try expanding location-based queries
            if any(location in query.lower() for location in ["nashville", "tennessee", "tn"]):
                query_variations.extend([
                    f"Nashville {query}",
                    f"Tennessee {query}",
                    f"Gen Z {query}",
                    f"Millennials {query}"
                ])
            
            best_results = []
            best_similarity = 0
            
            for variant in query_variations:
                if len(variant.strip()) == 0:
                    continue
                    
                # Generate embedding for the query variant
                query_embedding = self.encoder.encode([variant]).tolist()[0]
                
                # Search the collection with more results to increase chances
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=limit * 3,  # Get more results to filter by threshold
                    include=['documents', 'distances']
                )
                
                if results['documents'] and results['documents'][0]:
                    # Filter by similarity threshold
                    documents = results['documents'][0]
                    distances = results['distances'][0]
                    
                    variant_results = []
                    for doc, distance in zip(documents, distances):
                        # Convert distance to similarity (ChromaDB uses cosine distance)
                        similarity = 1 - distance
                        
                        if similarity >= similarity_threshold:
                            variant_results.append({
                                "content": doc,
                                "similarity": similarity,
                                "query_variant": variant
                            })
                    
                    # Keep the best results from this variant
                    if variant_results and (not best_results or variant_results[0]["similarity"] > best_similarity):
                        best_results = variant_results
                        best_similarity = variant_results[0]["similarity"]
            
            # If results with the original threshold less than 3, try with a much lower threshold
            if len(best_results) < 3:
                logger.info(f"No results found with threshold {similarity_threshold}, trying with 0.1")
                # Try again with lower threshold on the original query
                query_embedding = self.encoder.encode([query]).tolist()[0]
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=limit * 2,
                    include=['documents', 'distances']
                )
                
                if results['documents'] and results['documents'][0]:
                    documents = results['documents'][0]
                    distances = results['distances'][0]
                    
                    for doc, distance in zip(documents, distances):
                        similarity = 1 - distance
                        if similarity >= 0.1:  # Much lower threshold
                            best_results.append({
                                "content": doc,
                                "similarity": similarity,
                                "query_variant": query
                            })
            
            if not best_results:
                return f"No sufficiently similar insights found (threshold: {similarity_threshold}). Try lowering the similarity threshold or rephrasing your query."
            
            # Sort by similarity and take top results
            best_results.sort(key=lambda x: x["similarity"], reverse=True)
            final_results = best_results[:limit]
            
            # Format response with structured citations
            response_parts = []
            response_parts.append(f"Found {len(final_results)} relevant market research insights:")
            response_parts.append("")
            
            for i, result in enumerate(final_results, 1):
                response_parts.append(f"[Citation {i}] (Similarity: {result['similarity']:.2f}): {result['content']}")
                response_parts.append("")
            
            # Add structured citations metadata for API extraction
            response_parts.append("---CITATIONS_START---")
            for i, result in enumerate(final_results, 1):
                response_parts.append(f"CITATION|{i}|{result['similarity']:.3f}|{result['content']}")
            response_parts.append("---CITATIONS_END---")
            
            response = "\n".join(response_parts)
            
            logger.info(f"Found {len(final_results)} similar results for query: {query}")
            return response
            
        except Exception as e:
            logger.error(f"Error during similarity search: {e}")
            return f"Error performing similarity search: {str(e)}"
    
    async def _arun(self, query: str, limit: int = 5, similarity_threshold: float = 0.5) -> str:
        """Async version of the similarity search."""
        return self._run(query, limit, similarity_threshold)

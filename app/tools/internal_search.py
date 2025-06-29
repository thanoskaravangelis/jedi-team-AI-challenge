"""Internal data search tool for querying market research statements."""

from typing import List, Optional
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.db.database import SessionLocal
from app.db.models import MarketResearchData
import logging

logger = logging.getLogger(__name__)


class InternalDataSearchInput(BaseModel):
    """Input schema for internal data search."""
    query: str = Field(description="Search query to find relevant market research data")
    limit: int = Field(default=5, description="Maximum number of results to return")


class InternalDataSearchTool(BaseTool):
    """Tool for searching internal market research data."""
    
    name: str = "internal_data_search"
    description: str = """Search the internal market research database for relevant information.
    Use this tool to find specific data points, statistics, or insights from our proprietary market research.
    The tool performs both exact matches and partial text searches.
    Always cite the exact text you found when using this tool."""
    
    args_schema: type[BaseModel] = InternalDataSearchInput
    
    def _run(self, query: str, limit: int = 5) -> str:
        """Execute the internal data search with multiple strategies."""
        db = SessionLocal()
        try:
            logger.info(f"Searching internal data for: {query}")
            
            # Perform search with multiple strategies
            results = []
            
            # Strategy 1: Exact phrase match (case insensitive)
            exact_matches = db.query(MarketResearchData).filter(
                func.lower(MarketResearchData.text).contains(func.lower(query))
            ).limit(limit).all()
            
            if exact_matches:
                results.extend(exact_matches)
            
            # Strategy 2: Word-based search if exact matches are insufficient
            if len(results) < limit:
                words = query.lower().split()
                if len(words) > 1:
                    word_conditions = [
                        func.lower(MarketResearchData.text).contains(word)
                        for word in words
                    ]
                    word_matches = db.query(MarketResearchData).filter(
                        or_(*word_conditions)
                    ).filter(
                        ~MarketResearchData.id.in_([r.id for r in results])
                    ).limit(limit - len(results)).all()
                    
                    results.extend(word_matches)
            
            # Strategy 3: Try broader search terms if still no results
            if not results and len(query.split()) > 1:
                # Try searching for each word individually
                for word in query.split():
                    if len(word) > 3:  # Only search meaningful words
                        broader_matches = db.query(MarketResearchData).filter(
                            func.lower(MarketResearchData.text).contains(func.lower(word))
                        ).limit(2).all()
                        
                        for match in broader_matches:
                            if match not in results:
                                results.append(match)
                                if len(results) >= limit:
                                    break
                        if len(results) >= limit:
                            break
            
            if not results:
                return f"No relevant market research data found for query: '{query}'. Try rephrasing your search or using broader terms."
            
            # Format results with citations
            formatted_results = []
            for i, result in enumerate(results[:limit], 1):
                formatted_results.append(
                    f"[Citation {i}]: {result.text}"
                )
            
            response = f"Found {len(formatted_results)} relevant market research insights:\n\n"
            response += "\n\n".join(formatted_results)
            
            logger.info(f"Found {len(formatted_results)} results for query: {query}")
            return response
            
        except Exception as e:
            logger.error(f"Error searching internal data: {e}")
            return f"Error searching internal database: {str(e)}"
        finally:
            db.close()
    
    async def _arun(self, query: str, limit: int = 5) -> str:
        """Async version of the search."""
        return self._run(query, limit)


def get_all_market_research_data() -> List[str]:
    """Get all market research statements for vector database initialization."""
    db = SessionLocal()
    try:
        results = db.query(MarketResearchData).all()
        return [result.text for result in results]
    finally:
        db.close()

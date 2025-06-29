"""Web search tool using Tavily API."""

import os
from typing import Optional
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from tavily import TavilyClient
import logging

logger = logging.getLogger(__name__)


class WebSearchInput(BaseModel):
    """Input schema for web search."""
    query: str = Field(description="Search query to find information on the web")
    max_results: int = Field(default=3, description="Maximum number of search results to return")


class WebSearchTool(BaseTool):
    """Tool for searching the web using Tavily API."""
    
    name: str = "web_search"
    description: str = """Search the web for current information that might not be available in internal data.
    Use this tool when the internal database doesn't have sufficient information to answer a question.
    This is particularly useful for recent trends, current events, or external market data."""
    
    args_schema: type[BaseModel] = WebSearchInput
    
    def __init__(self):
        super().__init__()
        # Use object.__setattr__ to bypass Pydantic validation
        object.__setattr__(self, 'tavily_client', None)
        try:
            self._initialize_client()
        except Exception as e:
            logger.warning(f"WebSearchTool initialization failed: {e}")
            object.__setattr__(self, 'tavily_client', None)
    
    def _initialize_client(self):
        """Initialize the Tavily client."""
        api_key = os.getenv("TAVILY_API_KEY")
        logger.debug(f"TAVILY_API_KEY found: {'Yes' if api_key else 'No'}")
        if not api_key:
            logger.warning("TAVILY_API_KEY not found. Web search will be disabled.")
            return
        
        try:
            tavily_client = TavilyClient(api_key=api_key)
            object.__setattr__(self, 'tavily_client', tavily_client)
            logger.info("Tavily client initialized successfully")
            logger.debug(f"tavily_client attribute set: {hasattr(self, 'tavily_client')}")
        except Exception as e:
            logger.error(f"Error initializing Tavily client: {e}")
    
    def _run(self, query: str, max_results: int = 3) -> str:
        """Execute the web search."""
        if not self.tavily_client:
            return "Web search is not available. TAVILY_API_KEY not configured."
        
        try:
            logger.info(f"Searching web for: {query}")
            
            # Perform the search
            response = self.tavily_client.search(
                query=query,
                search_depth="basic",
                max_results=max_results,
                include_answer=True,
                include_raw_content=False
            )
            
            if not response or 'results' not in response:
                return f"No web search results found for query: '{query}'"
            
            # Prepare citations and formatted results
            citations = []
            formatted_results = []
            
            # Include Tavily's AI-generated answer if available
            if response.get('answer'):
                formatted_results.append(f"AI Summary: {response['answer']}")
            
            # Add individual search results with citation metadata
            for i, result in enumerate(response['results'][:max_results], 1):
                title = result.get('title', 'No title')
                url = result.get('url', 'No URL')
                content = result.get('content', 'No content available')
                score = result.get('score', 0)  # Relevance score from Tavily
                
                # Create citation entry
                citations.append({
                    "title": title,
                    "url": url,
                    "content": content,
                    "score": score,
                    "rank": i
                })
                
                # Format for display
                formatted_results.append(
                    f"[Web Result {i}]\n"
                    f"Title: {title}\n"
                    f"URL: {url}\n"
                    f"Content: {content[:300]}{'...' if len(content) > 300 else ''}"
                )
            
            if not formatted_results:
                return f"No meaningful web search results found for query: '{query}'"
            
            # Build response with structured citations
            response_parts = []
            response_parts.append(f"Web search results for '{query}':")
            response_parts.append("")
            response_parts.extend(formatted_results)
            response_parts.append("")
            
            # Add structured citations metadata for API extraction
            response_parts.append("---CITATIONS_START---")
            for citation in citations:
                response_parts.append(f"WEB_CITATION|{citation['rank']}|{citation['score']:.3f}|{citation['title']}|{citation['url']}|{citation['content']}")
            response_parts.append("---CITATIONS_END---")
            
            response_text = "\n".join(response_parts)
            
            logger.info(f"Found {len(response['results'])} web results for query: {query}")
            return response_text
            
        except Exception as e:
            logger.error(f"Error during web search: {e}")
            return f"Error performing web search: {str(e)}"
    
    async def _arun(self, query: str, max_results: int = 3) -> str:
        """Async version of the web search."""
        return self._run(query, max_results)

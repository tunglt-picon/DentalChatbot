"""DuckDuckGo Search tool."""
import logging
from duckduckgo_search import DDGS
from .base import BaseSearchTool

logger = logging.getLogger(__name__)


class DuckDuckGoSearchTool(BaseSearchTool):
    """Search tool using DuckDuckGo."""
    
    async def search(self, query: str) -> str:
        """
        Perform search using DuckDuckGo.
        
        Args:
            query: Search query
            
        Returns:
            Search results as text
        """
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
            
            if not results:
                return f"No results found for query: {query}"
            
            # Format results
            formatted_results = []
            for result in results:
                title = result.get("title", "")
                body = result.get("body", "")
                href = result.get("href", "")
                formatted_results.append(
                    f"Title: {title}\nContent: {body}\nLink: {href}\n"
                )
            
            return "\n---\n".join(formatted_results)
            
        except Exception as e:
            logger.error(f"Error searching with DuckDuckGo: {e}")
            raise Exception(f"Error searching with DuckDuckGo: {str(e)}")

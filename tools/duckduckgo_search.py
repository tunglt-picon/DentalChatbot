"""DuckDuckGo Search tool."""
import logging
import warnings
from duckduckgo_search import DDGS
from .base import BaseSearchTool

# Suppress deprecation warning
warnings.filterwarnings("ignore", message=".*duckduckgo_search.*has been renamed.*")

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
        logger.info(f"[DUCKDUCKGO] Starting search for query: {query[:100]}...")
        try:
            with DDGS() as ddgs:
                logger.debug(f"[DUCKDUCKGO] DDGS instance created, searching...")
                results = list(ddgs.text(query, max_results=5))
                logger.info(f"[DUCKDUCKGO] Found {len(results)} results")
            
            if not results:
                logger.warning(f"[DUCKDUCKGO] No results found for query: {query}")
                return f"No results found for query: {query}"
            
            # Format results
            formatted_results = []
            for idx, result in enumerate(results, 1):
                title = result.get("title", "")
                body = result.get("body", "")
                href = result.get("href", "")
                formatted_results.append(
                    f"Title: {title}\nContent: {body}\nLink: {href}\n"
                )
                logger.debug(f"[DUCKDUCKGO] Result {idx}: {title[:50]}...")
            
            formatted_text = "\n---\n".join(formatted_results)
            logger.info(f"[DUCKDUCKGO] Search completed. Total formatted length: {len(formatted_text)} characters")
            return formatted_text
            
        except Exception as e:
            logger.error(f"[DUCKDUCKGO] Error searching: {e}", exc_info=True)
            raise Exception(f"Error searching with DuckDuckGo: {str(e)}")

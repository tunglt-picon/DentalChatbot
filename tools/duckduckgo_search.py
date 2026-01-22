"""DuckDuckGo Search tool."""
import logging
import warnings
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
        logger.debug(f"[DUCKDUCKGO] Full query: {query}")
        
        try:
            # Try new package name first (ddgs)
            try:
                from ddgs import DDGS
                logger.debug(f"[DUCKDUCKGO] Using 'ddgs' package")
            except ImportError:
                # Fallback to old package name
                try:
                    from duckduckgo_search import DDGS
                    logger.debug(f"[DUCKDUCKGO] Using 'duckduckgo_search' package (deprecated)")
                except ImportError:
                    logger.error("[DUCKDUCKGO] Neither 'ddgs' nor 'duckduckgo_search' package found")
                    raise ImportError(
                        "DuckDuckGo search package not found. "
                        "Please install: pip install ddgs"
                    )
            
            with DDGS() as ddgs:
                logger.debug(f"[DUCKDUCKGO] DDGS instance created, searching with max_results=5...")
                results = list(ddgs.text(query, max_results=5))
                logger.info(f"[DUCKDUCKGO] Found {len(results)} results")
                logger.debug(f"[DUCKDUCKGO] Raw results: {results}")
            
            if not results:
                logger.warning(f"[DUCKDUCKGO] No results found for query: {query}")
                return f"No results found for query: {query}"
            
            # Format results
            formatted_results = []
            for idx, result in enumerate(results, 1):
                title = result.get("title", "")
                body = result.get("body", "")
                href = result.get("href", "")
                logger.debug(f"[DUCKDUCKGO] Result {idx}: Title='{title[:50]}...', Link='{href}'")
                formatted_results.append(
                    f"Title: {title}\nContent: {body}\nLink: {href}\n"
                )
            
            formatted_text = "\n---\n".join(formatted_results)
            logger.info(f"[DUCKDUCKGO] Search completed. Total formatted length: {len(formatted_text)} characters")
            logger.debug(f"[DUCKDUCKGO] Formatted results:\n{formatted_text[:500]}...")
            return formatted_text
            
        except ImportError as e:
            logger.error(f"[DUCKDUCKGO] Import error: {e}", exc_info=True)
            raise Exception(f"DuckDuckGo package not installed. Please run: pip install ddgs")
        except Exception as e:
            logger.error(f"[DUCKDUCKGO] Error searching: {e}", exc_info=True)
            raise Exception(f"Error searching with DuckDuckGo: {str(e)}")

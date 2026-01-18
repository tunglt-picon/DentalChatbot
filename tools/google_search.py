"""Google Custom Search API tool."""
import httpx
import logging
from typing import Optional
from .base import BaseSearchTool
import config

logger = logging.getLogger(__name__)


class GoogleSearchTool(BaseSearchTool):
    """Search tool using Google Custom Search API."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        cse_id: Optional[str] = None
    ):
        """
        Initialize Google Search Tool.
        
        Args:
            api_key: Google Custom Search API key
            cse_id: Google Custom Search Engine ID
        """
        self.api_key = api_key or config.settings.google_search_api_key
        self.cse_id = cse_id or config.settings.google_cse_id
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        
    def is_configured(self) -> bool:
        """Check if Google Search is fully configured."""
        return bool(self.api_key and self.cse_id)
    
    async def search(self, query: str) -> str:
        """
        Perform search using Google Custom Search API.
        
        Args:
            query: Search query
            
        Returns:
            Search results as text
        """
        if not self.is_configured():
            raise ValueError(
                "Google Search API is not configured. "
                "GOOGLE_SEARCH_API_KEY and GOOGLE_CSE_ID are required."
            )
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                params = {
                    "key": self.api_key,
                    "cx": self.cse_id,
                    "q": query,
                    "num": 5  # Get top 5 results
                }
                
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                # Extract information from results
                results = []
                if "items" in data:
                    for item in data["items"]:
                        title = item.get("title", "")
                        snippet = item.get("snippet", "")
                        link = item.get("link", "")
                        results.append(f"Title: {title}\nContent: {snippet}\nLink: {link}\n")
                
                if not results:
                    return f"No results found for query: {query}"
                
                return "\n---\n".join(results)
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from Google Search API: {e}")
            raise Exception(f"Error calling Google Search API: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Unexpected error from Google Search: {e}")
            raise

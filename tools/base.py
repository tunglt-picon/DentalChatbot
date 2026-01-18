"""Base class for search tools."""
from abc import ABC, abstractmethod


class BaseSearchTool(ABC):
    """Common interface for search tools."""
    
    @abstractmethod
    async def search(self, query: str) -> str:
        """
        Perform search and return results as text.
        
        Args:
            query: Search query
            
        Returns:
            Search results as text
            
        Raises:
            Exception: If there's an error during search
        """
        pass

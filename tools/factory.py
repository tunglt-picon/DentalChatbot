"""Factory pattern to create search tools."""
import logging
from typing import Optional
from .base import BaseSearchTool
from .duckduckgo_search import DuckDuckGoSearchTool

logger = logging.getLogger(__name__)


class SearchToolFactory:
    """Factory to create search tools."""
    
    @staticmethod
    def create_search_tool() -> BaseSearchTool:
        """
        Create DuckDuckGo search tool.
            
        Returns:
            Instance of DuckDuckGoSearchTool
        """
        return DuckDuckGoSearchTool()

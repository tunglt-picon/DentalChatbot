"""Factory pattern to create search tools."""
import logging
from typing import Optional
from .base import BaseSearchTool
from .google_search import GoogleSearchTool
from .duckduckgo_search import DuckDuckGoSearchTool

logger = logging.getLogger(__name__)


class SearchToolFactory:
    """Factory to create search tools based on model name."""
    
    @staticmethod
    def create_search_tool(model: str) -> BaseSearchTool:
        """
        Create search tool based on model name.
        
        Args:
            model: Model name ("dental-google" or "dental-duckduckgo")
            
        Returns:
            Instance of corresponding BaseSearchTool
        """
        if model == "dental-google":
            tool = GoogleSearchTool()
            return tool
        elif model == "dental-duckduckgo":
            return DuckDuckGoSearchTool()
        else:
            raise ValueError(f"Invalid model: {model}")

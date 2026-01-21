"""Google Search tool using Google ADK (Agent Development Kit)."""
import google.generativeai as genai
import logging
from .base import BaseSearchTool
import config

logger = logging.getLogger(__name__)

# Configure Gemini (required for ADK tools)
genai.configure(api_key=config.settings.google_api_key)


class GoogleSearchTool(BaseSearchTool):
    """Search tool using Google ADK google_search tool."""
    
    def __init__(self):
        """
        Initialize Google Search Tool using ADK.
        
        Note: ADK google_search tool requires Gemini 2.0+ models.
        This tool uses Gemini API with Google Search grounding.
        """
        # Use Gemini 2.0+ model for Google Search tool
        self.model_name = config.settings.google_base_model
        # Ensure using Gemini 2.0+ model for Google Search compatibility
        if "gemini-2.0" not in self.model_name and "gemini-2.5" not in self.model_name:
            logger.warning(
                f"Model {self.model_name} may not support Google Search tool. "
                "Google Search tool requires Gemini 2.0+ models. "
                "Using 'gemini-2.5-flash' for Google Search."
            )
            # Auto-upgrade to Gemini 2.5 Flash if not 2.0+
            self.model_name = "gemini-2.5-flash"
        
        try:
            # Import ADK google_search tool
            from google.adk.tools import google_search as adk_google_search
            self.google_search_tool = adk_google_search
            logger.info("ADK google_search tool imported successfully")
        except ImportError as e:
            logger.error(f"Failed to import ADK google_search tool: {e}")
            raise ImportError(
                "Google ADK is required for Google Search tool. "
                "Please install: pip install google-adk"
            )
    
    def is_configured(self) -> bool:
        """Check if Google Search tool is configured (always True for ADK tool)."""
        return True
    
    async def search(self, query: str) -> str:
        """
        Perform search using Google ADK google_search tool.
        
        Args:
            query: Search query
            
        Returns:
            Search results as text with sources
        """
        logger.info(f"[GOOGLE_SEARCH] Starting search for query: {query[:100]}...")
        logger.info(f"[GOOGLE_SEARCH] Using model: {self.model_name}")
        
        try:
            # Use Gemini API with Google Search tool from ADK
            # Create model with google_search tool
            logger.debug(f"[GOOGLE_SEARCH] Creating Gemini model with google_search tool")
            model = genai.GenerativeModel(
                model_name=self.model_name,
                tools=[self.google_search_tool]
            )
            
            # Create prompt that triggers Google Search tool
            prompt = f"Please search for information about: {query}. Provide detailed results with sources."
            logger.debug(f"[GOOGLE_SEARCH] Prompt created, length: {len(prompt)}")
            
            # Generate content with Google Search tool
            # The tool will automatically be invoked when the model determines it needs to search
            logger.info(f"[GOOGLE_SEARCH] Calling Gemini API with search tool...")
            response = model.generate_content(prompt)
            logger.debug(f"[GOOGLE_SEARCH] Gemini API response received")
            
            # Extract the response text
            result_text = response.text if hasattr(response, 'text') and response.text else ""
            logger.debug(f"[GOOGLE_SEARCH] Response text length: {len(result_text)}")
            
            # Extract grounding metadata (search results with sources)
            results_with_sources = []
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                
                # Check for grounding metadata (contains search sources)
                if hasattr(candidate, 'grounding_metadata'):
                    grounding = candidate.grounding_metadata
                    
                    # Extract grounding chunks (search results)
                    if hasattr(grounding, 'grounding_chunks'):
                        logger.debug(f"[GOOGLE_SEARCH] Extracting grounding chunks...")
                        for chunk in grounding.grounding_chunks:
                            if hasattr(chunk, 'web'):
                                web = chunk.web
                                uri = getattr(web, 'uri', '')
                                title = getattr(web, 'title', '')
                                # Get text snippet from chunk if available
                                chunk_text = getattr(chunk, 'text', '')
                                
                                if uri:
                                    results_with_sources.append(
                                        f"Title: {title}\n"
                                        f"Content: {chunk_text}\n"
                                        f"Link: {uri}\n"
                                    )
                        logger.info(f"[GOOGLE_SEARCH] Extracted {len(results_with_sources)} search sources")
            
            # Combine response text with formatted sources
            if results_with_sources:
                formatted_results = "\n---\n".join(results_with_sources)
                # Return both the model's response and the formatted sources
                final_result = f"{result_text}\n\nSearch Sources:\n{formatted_results}"
                logger.info(f"[GOOGLE_SEARCH] Search completed. Total result length: {len(final_result)} characters")
                return final_result
            
            # If no grounding chunks, return the response text
            if result_text:
                logger.info(f"[GOOGLE_SEARCH] Search completed. Using response text only. Length: {len(result_text)}")
                return result_text
            
            logger.warning(f"[GOOGLE_SEARCH] No results found for query: {query}")
            return f"No results found for query: {query}"
            
        except Exception as e:
            logger.error(f"[GOOGLE_SEARCH] Error: {e}", exc_info=True)
            # If error occurs, raise error (no fallback)
            raise Exception(f"Error using Google Search tool: {str(e)}")

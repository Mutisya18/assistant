"""Main query orchestrator"""
import logging
import re
from typing import Dict, Any, Optional
from core.llm.manager import LLMManager
from core.context_manager import ContextManager
from processors.registry import ProcessorRegistry
from models.response import Response

logger = logging.getLogger(__name__)

class QueryOrchestrator:
    """Coordinates query processing pipeline"""
    
    def __init__(self, llm_manager: LLMManager, processor_registry: ProcessorRegistry,
                 context_manager: ContextManager):
        self.llm_manager = llm_manager
        self.processor_registry = processor_registry
        self.context_manager = context_manager
    
    def process_query(self, query: str, session_id: str,
                     model_preference: Optional[str] = None) -> Response:
        """Process user query through the pipeline"""
        logger.info(f"Processing query for session {session_id}: {query[:50]}...")
        
        try:
            # Step 1: Select LLM provider
            llm_provider = self._select_llm_provider(model_preference)
            
            if not llm_provider:
                return Response(
                    message="AI service is temporarily unavailable. Please try again.",
                    intent="error",
                    confidence=0.0,
                    status="error"
                )
            
            # Step 2: Get context
            context = self.context_manager.get_context(session_id)
            context['original_query'] = query
            
            # Step 3: Get available tools
            available_tools = self.processor_registry.get_all_tools()
            
            # Step 4: LLM selects tool
            tool_call = llm_provider.generate_with_tools(query, context, available_tools)
            
            logger.info(f"Tool selected: {tool_call['tool_name']} (confidence: {tool_call['confidence']})")
            
            # Step 5: Get processor for tool
            processor = self.processor_registry.get_processor_for_tool(tool_call['tool_name'])
            
            if not processor:
                # Fallback to general inquiry
                from processors.general_inquiry.processor import GeneralInquiryProcessor
                processor = GeneralInquiryProcessor()
                tool_call = {'tool_name': 'general_response', 'arguments': {}}
            
            # Step 6: Execute processor
            response = processor.execute(
                tool_name=tool_call['tool_name'],
                arguments=tool_call['arguments'],
                context=context,
                llm_provider=llm_provider
            )
            
            # Step 7: Update context
            account_number = tool_call['arguments'].get('account_number')
            self.context_manager.update_context(
                session_id=session_id,
                query=query,
                response=response,
                intent=response.intent,
                account_number=account_number
            )
            
            logger.info(f"Query processed successfully: {response.intent}")
            return response
            
        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            return Response(
                message="I encountered an error processing your request. Please try again.",
                intent="error",
                confidence=0.0,
                status="error"
            )
    
    def _select_llm_provider(self, preference: Optional[str] = None):
        """Select LLM provider with fallback"""
        # Try preference first
        if preference:
            provider = self.llm_manager.get_provider(preference)
            if provider:
                status = provider.check_connection()
                if status.get('available'):
                    return provider
        
        # Try default provider
        default_provider = self.llm_manager.get_default_provider()
        if default_provider:
            status = default_provider.check_connection()
            if status.get('available'):
                return default_provider
        
        # Try fallback providers
        for provider in self.llm_manager.get_fallback_providers():
            status = provider.check_connection()
            if status.get('available'):
                logger.warning(f"Using fallback provider")
                return provider
        
        return None


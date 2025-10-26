"""General inquiry processor (fallback)"""
import logging
from typing import Dict, Any, List
from processors.base import BaseProcessor, Tool
from models.response import Response

logger = logging.getLogger(__name__)

class GeneralInquiryProcessor(BaseProcessor):
    """Fallback processor for general inquiries and greetings"""
    
    def __init__(self):
        super().__init__()
        self.name = "general_inquiry"
        self.description = "Handles general inquiries and fallback cases"
        self.validation_level = "none"
        
        self.tools = [
            Tool(
                name="general_response",
                description="Handle greetings, general questions, and fallback cases",
                parameters_schema={},
                processor_class=self.__class__
            )
        ]
    
    def get_tools(self) -> List[Tool]:
        """Return available tools"""
        return self.tools
    
    def execute(self, tool_name: str, arguments: Dict[str, Any],
                context: Dict[str, Any], llm_provider: Any) -> Response:
        """Execute tool"""
        query = context.get('original_query', '')
        
        # Check if greeting
        if self._is_greeting(query):
            return self._handle_greeting()
        
        # General fallback
        return self._handle_general(query, llm_provider)
    
    def _is_greeting(self, query: str) -> bool:
        """Check if query is a greeting"""
        greetings = ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening']
        query_lower = query.lower()
        return any(greet in query_lower for greet in greetings)
    
    def _handle_greeting(self) -> Response:
        """Handle greeting queries"""
        from datetime import datetime
        
        hour = datetime.now().hour
        if 5 <= hour < 12:
            greeting = "Good Morning!"
        elif 12 <= hour < 17:
            greeting = "Good Afternoon!"
        else:
            greeting = "Good Evening!"
        
        message = f"""{greeting}

I'm Safina, your AI assistant for NCBA Bank's digital lending queries.

I can help you with:
• Checking customer loan eligibility
• Explaining ineligibility reasons
• Answering questions about digital lending policies
• Providing guidance on loan processes

How can I assist you today?"""
        
        return Response(
            message=message,
            intent="greeting",
            confidence=0.95,
            status="success",
            suggestions=[
                "Check eligibility for account 503446",
                "What are the eligibility requirements?",
                "How does the digital loan process work?"
            ]
        )
    
    def _handle_general(self, query: str, llm_provider: Any) -> Response:
        """Handle general queries"""
        prompt = f"""You are Safina, a professional banking assistant for NCBA Bank's digital lending team.

A staff member asked: "{query}"

Provide a helpful, professional response. If it's about loan eligibility:
- Remind them they need an account number to check specific eligibility
- Mention general eligibility criteria (individual account, sole signatory, mobile banking, 6+ months history)

If it's a general question about digital loans, provide accurate information about NCBA's digital lending services.

Keep the response concise, professional, and actionable."""
        
        try:
            response_text = llm_provider.generate(prompt, max_tokens=300, temperature=0.7)
            return Response(
                message=response_text.strip(),
                intent="general_inquiry",
                confidence=0.75,
                status="success"
            )
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return Response(
                message="I'm here to help with digital lending queries. Please ask about loan eligibility, requirements, or processes.",
                intent="general_inquiry",
                confidence=0.6,
                status="success"
            )

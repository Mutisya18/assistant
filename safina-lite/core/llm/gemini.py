"""Gemini LLM implementation"""
import google.generativeai as genai
import logging
from typing import Dict, Any, List
from core.llm.base import BaseLLM

logger = logging.getLogger(__name__)

class GeminiLLM(BaseLLM):
    """Google Gemini LLM provider"""
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash", 
                 timeout: int = 30):
        self.api_key = api_key
        self.model_name = model
        self.timeout = timeout
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)
        
        logger.info(f"Initialized Gemini LLM: {self.model_name}")
    
    def generate(self, prompt: str, max_tokens: int = 500,
                 temperature: float = 0.7) -> str:
        """Generate text using Gemini"""
        try:
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens
            )
            
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Gemini generation error: {e}")
            raise Exception(f"Gemini API error: {str(e)}")
    
    def generate_with_tools(self, query: str, context: Dict[str, Any],
                           available_tools: List[Dict]) -> Dict[str, Any]:
        """Generate with function calling"""
        try:
            # Build tool prompt
            prompt = self._build_tool_prompt(query, context, available_tools)
            
            # Generate with lower temperature for determinism
            response_text = self.generate(prompt, max_tokens=200, temperature=0.3)
            
            # Parse tool selection
            return self._parse_tool_response(response_text)
            
        except Exception as e:
            logger.error(f"Tool calling error: {e}")
            return {
                'tool_name': 'answer_faq',
                'arguments': {},
                'confidence': 0.5
            }
    
    def check_connection(self) -> Dict[str, Any]:
        """Check Gemini API availability"""
        try:
            # Try a simple generation
            test_response = self.generate("test", max_tokens=5, temperature=0)
            
            return {
                'available': True,
                'latency': None,
                'error': None
            }
        except Exception as e:
            return {
                'available': False,
                'latency': None,
                'error': str(e)
            }
    
    def _build_tool_prompt(self, query: str, context: Dict,
                          tools: List[Dict]) -> str:
        """Build prompt for tool selection"""
        tools_text = "\n".join([
            f"Tool: {tool['name']}\nDescription: {tool['description']}\n"
            for tool in tools
        ])
        
        return f"""You are Safina, an AI assistant for NCBA Bank staff.

Available Tools:
{tools_text}

User Query: "{query}"

Select the most appropriate tool. Respond ONLY with JSON:
{{
    "tool_name": "tool_name",
    "arguments": {{}},
    "reasoning": "brief explanation"
}}"""
    
    def _parse_tool_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM tool selection response"""
        import json
        import re
        
        # Extract JSON
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if not json_match:
            return {
                'tool_name': 'answer_faq',
                'arguments': {},
                'confidence': 0.5
            }
        
        try:
            data = json.loads(json_match.group())
            return {
                'tool_name': data.get('tool_name', 'answer_faq'),
                'arguments': data.get('arguments', {}),
                'confidence': 0.9
            }
        except:
            return {
                'tool_name': 'answer_faq',
                'arguments': {},
                'confidence': 0.5
            }
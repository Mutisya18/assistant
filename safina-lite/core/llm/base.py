"""Base LLM interface"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseLLM(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 500, 
                 temperature: float = 0.7) -> str:
        """Generate text from prompt"""
        pass
    
    @abstractmethod
    def generate_with_tools(self, query: str, context: Dict[str, Any],
                           available_tools: List[Dict]) -> Dict[str, Any]:
        """Generate with tool-calling support"""
        pass
    
    @abstractmethod
    def check_connection(self) -> Dict[str, Any]:
        """Check if LLM service is available"""
        pass

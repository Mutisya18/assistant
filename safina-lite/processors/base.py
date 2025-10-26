"""Base processor interface and tool definition"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class Tool:
    """Tool definition for LLM tool-calling"""
    name: str
    description: str
    parameters_schema: Dict[str, Any]
    processor_class: type

class BaseProcessor(ABC):
    """Abstract base class for all processors"""
    
    def __init__(self):
        self.name = ""
        self.description = ""
        self.validation_level = "light"  # none, light, strict
    
    @abstractmethod
    def get_tools(self) -> List[Tool]:
        """Return list of tools this processor provides"""
        pass
    
    @abstractmethod
    def execute(self, tool_name: str, arguments: Dict[str, Any],
                context: Dict[str, Any], llm_provider: Any) -> 'Response':
        """Execute a tool with given arguments"""
        pass
    
    def validate_response(self, response: 'Response') -> tuple[bool, List[str]]:
        """Validate response quality"""
        if self.validation_level == "none":
            return True, []
        
        issues = []
        
        # Light validation
        if not response.message or len(response.message.strip()) == 0:
            issues.append("Response message is empty")
        
        if len(response.message) > 5000:
            issues.append("Response too long (>5000 chars)")
        
        return len(issues) == 0, issues

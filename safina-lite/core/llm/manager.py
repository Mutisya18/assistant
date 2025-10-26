"""LLM provider management"""
import logging
from typing import Dict, List, Optional
from core.llm.base import BaseLLM

logger = logging.getLogger(__name__)

class LLMManager:
    """Manages multiple LLM providers"""
    
    def __init__(self):
        self.providers: Dict[str, BaseLLM] = {}
        self.default_provider_name: Optional[str] = None
        self.fallback_order: List[str] = []
    
    def register_provider(self, name: str, provider: BaseLLM):
        """Register an LLM provider"""
        self.providers[name] = provider
        logger.info(f"Registered LLM provider: {name}")
    
    def set_default_provider(self, name: str):
        """Set default LLM provider"""
        if name not in self.providers:
            raise ValueError(f"Provider '{name}' not registered")
        self.default_provider_name = name
        logger.info(f"Default provider set to: {name}")
    
    def set_fallback_order(self, order: List[str]):
        """Set fallback provider order"""
        self.fallback_order = order
    
    def get_provider(self, name: Optional[str] = None) -> Optional[BaseLLM]:
        """Get LLM provider by name"""
        if name:
            return self.providers.get(name)
        return self.providers.get(self.default_provider_name)
    
    def get_default_provider(self) -> Optional[BaseLLM]:
        """Get default LLM provider"""
        return self.providers.get(self.default_provider_name)
    
    def get_fallback_providers(self) -> List[BaseLLM]:
        """Get fallback providers in order"""
        providers = []
        for name in self.fallback_order:
            if name in self.providers:
                providers.append(self.providers[name])
        return providers
    
    def get_available_providers(self) -> Dict[str, Any]:
        """Get list of available providers"""
        available = {}
        for name, provider in self.providers.items():
            status = provider.check_connection()
            available[name] = {
                'available': status.get('available', False),
                'latency': status.get('latency')
            }
        return available

"""Processor registry with auto-discovery"""
import logging
from pathlib import Path
from typing import Dict, List, Optional
from processors.base import BaseProcessor, Tool

logger = logging.getLogger(__name__)

class ProcessorRegistry:
    """Registry for managing processors and tools"""
    
    def __init__(self):
        self.processors: Dict[str, BaseProcessor] = {}
        self.tools_map: Dict[str, BaseProcessor] = {}
    
    def register_processor(self, processor: BaseProcessor):
        """Register a processor and its tools"""
        processor_name = processor.name
        self.processors[processor_name] = processor
        
        # Register all tools from this processor
        tools = processor.get_tools()
        for tool in tools:
            self.tools_map[tool.name] = processor
            logger.info(f"Registered tool: {tool.name} -> {processor_name}")
        
        logger.info(f"Registered processor: {processor_name} ({len(tools)} tools)")
    
    def get_processor_for_tool(self, tool_name: str) -> Optional[BaseProcessor]:
        """Get processor that handles a specific tool"""
        return self.tools_map.get(tool_name)
    
    def get_all_tools(self) -> List[Tool]:
        """Get all available tools from all processors"""
        all_tools = []
        for processor in self.processors.values():
            all_tools.extend(processor.get_tools())
        return all_tools
    
    def list_processors(self) -> List[str]:
        """List all registered processor names"""
        return list(self.processors.keys())


"""Standard response structure for all processors"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime

@dataclass
class Response:
    """Standardized response object"""
    message: str
    intent: str
    confidence: float
    status: str = "success"  # success, error, missing_data, not_found
    data: Optional[Dict[str, Any]] = None
    suggestions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'message': self.message,
            'intent': self.intent,
            'confidence': self.confidence,
            'status': self.status,
            'data': self.data or {},
            'suggestions': self.suggestions,
            'metadata': self.metadata,
            'timestamp': self.timestamp
        }
    
    def is_success(self) -> bool:
        """Check if response was successful"""
        return self.status == "success"


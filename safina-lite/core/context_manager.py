"""Context management for conversation sessions"""
import logging
from collections import defaultdict
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ContextManager:
    """Manages conversation context and session history"""
    
    def __init__(self, max_history: int = 10):
        self.max_history = max_history
        self.sessions: Dict[str, List[Dict]] = defaultdict(list)
    
    def get_context(self, session_id: str) -> Dict[str, Any]:
        """Get conversation context for a session"""
        history = self.sessions.get(session_id, [])
        
        last_account = None
        last_intent = None
        
        if history:
            last_interaction = history[-1]
            last_account = last_interaction.get('account_number')
            last_intent = last_interaction.get('intent')
        
        return {
            'session_id': session_id,
            'history_length': len(history),
            'last_account': last_account,
            'last_intent': last_intent,
            'history': history
        }
    
    def update_context(self, session_id: str, query: str, response: Any,
                      intent: str, account_number: Optional[str] = None):
        """Update context with new interaction"""
        interaction = {
            'timestamp': datetime.now().isoformat(),
            'query': query,
            'response': response.message if hasattr(response, 'message') else str(response),
            'intent': intent,
            'account_number': account_number
        }
        
        self.sessions[session_id].append(interaction)
        
        # Maintain max history (sliding window)
        if len(self.sessions[session_id]) > self.max_history:
            self.sessions[session_id].pop(0)
        
        logger.debug(f"Updated context for session {session_id}")

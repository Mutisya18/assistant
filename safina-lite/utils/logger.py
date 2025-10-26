"""Session-based logging system with 2-hour rotation"""
import logging
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any
import threading

# Session state
_session_info = {
    'start_time': None,
    'session_num': 0,
    'log_dir': None,
    'handlers': []
}
_session_lock = threading.Lock()

class JSONFormatter(logging.Formatter):
    """Format logs as JSON"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName
        }
        
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)
        
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)

class MonitoringFormatter(logging.Formatter):
    """Human-readable format with emojis"""
    
    EMOJI_MAP = {
        'DEBUG': '🔍',
        'INFO': '✅',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '🚨'
    }
    
    def format(self, record: logging.LogRecord) -> str:
        emoji = self.EMOJI_MAP.get(record.levelname, 'ℹ️')
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        return f"{timestamp} {emoji} {record.getMessage()}"

class AIModelFilter(logging.Filter):
    """Filter for AI/LLM operations"""
    
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage().lower()
        module = record.name.lower()
        
        ai_keywords = ['llm', 'gemini', 'ollama', 'intent', 'generate', 'model']
        ai_modules = ['gemini', 'ollama', 'intent', 'response']
        
        return (
            any(kw in msg for kw in ai_keywords) or
            any(mod in module for mod in ai_modules)
        )

class SystemFilter(logging.Filter):
    """Filter out AI logs from system log"""
    
    def filter(self, record: logging.LogRecord) -> bool:
        return not AIModelFilter().filter(record)

def _should_rotate_session() -> bool:
    """Check if session should rotate (2 hours)"""
    if _session_info['start_time'] is None:
        return True
    
    elapsed = datetime.now() - _session_info['start_time']
    return elapsed >= timedelta(hours=2)

def _get_new_session_dir(base_log_dir: Path) -> Path:
    """Create new session directory"""
    now = datetime.now()
    _session_info['session_num'] += 1
    
    session_name = (
        f"session-{_session_info['session_num']}--"
        f"{now.strftime('%m-%d-%y--%H-%M')}"
    )
    
    session_dir = base_log_dir / session_name
    session_dir.mkdir(parents=True, exist_ok=True)
    
    return session_dir

def setup_logger(name: str = "safina") -> logging.Logger:
    """Setup session-based logger"""
    from utils.config import get_config
    config = get_config()
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, config.get('logging.level', 'INFO')))
    
    # Create base log directory
    base_log_dir = Path(config.get('logging.base_directory', 'logs'))
    base_log_dir.mkdir(exist_ok=True)
    
    # Initial session setup
    _rotate_session(logger, base_log_dir)
    
    return logger

def _rotate_session(logger: logging.Logger, base_log_dir: Path):
    """Rotate to new session"""
    with _session_lock:
        # Remove old handlers
        for handler in _session_info['handlers']:
            logger.removeHandler(handler)
            handler.close()
        _session_info['handlers'] = []
        
        # Create new session
        session_dir = _get_new_session_dir(base_log_dir)
        _session_info['log_dir'] = session_dir
        _session_info['start_time'] = datetime.now()
        
        # System log
        system_handler = logging.FileHandler(session_dir / 'system.log')
        system_handler.setFormatter(JSONFormatter())
        system_handler.addFilter(SystemFilter())
        logger.addHandler(system_handler)
        _session_info['handlers'].append(system_handler)
        
        # AI operations log
        ai_handler = logging.FileHandler(session_dir / 'ai_operations.log')
        ai_handler.setFormatter(JSONFormatter())
        ai_handler.addFilter(AIModelFilter())
        logger.addHandler(ai_handler)
        _session_info['handlers'].append(ai_handler)
        
        print(f"✓ New log session: {session_dir.name}")
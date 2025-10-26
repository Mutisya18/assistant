"""Flask API application"""
import logging
import uuid
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pathlib import Path

from utils.config import get_config
from utils.logger import setup_logger
from core.llm.manager import LLMManager
from core.llm.gemini import GeminiLLM
from core.orchestrator import QueryOrchestrator
from core.context_manager import ContextManager
from processors.registry import ProcessorRegistry
from processors.digital_lending.processor import DigitalLendingProcessor
from processors.faq.processor import FAQProcessor
from processors.general_inquiry.processor import GeneralInquiryProcessor

logger = logging.getLogger(__name__)

def create_app(config=None):
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    if config is None:
        config = get_config()
    
    # Enable CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": config.get('api.cors_origins', ['*'])
        }
    })
    
    # Initialize components
    logger.info("Initializing application components...")
    
    # 1. LLM Manager
    llm_manager = LLMManager()
    
    # Register Gemini provider
    gemini_config = config.get('llm.providers.gemini')
    if gemini_config and gemini_config.get('enabled'):
        try:
            gemini_provider = GeminiLLM(
                api_key=gemini_config['api_key'],
                model=gemini_config['model'],
                timeout=gemini_config.get('timeout', 30)
            )
            llm_manager.register_provider('gemini', gemini_provider)
            
            # Check connection
            status = gemini_provider.check_connection()
            if status['available']:
                logger.info("✓ Gemini provider connected")
            else:
                logger.warning(f"⚠ Gemini provider unavailable: {status.get('error')}")
        except Exception as e:
            logger.error(f"✗ Gemini provider initialization failed: {e}")
    
    # Set default provider
    default_provider = config.get('llm.default_provider', 'gemini')
    try:
        llm_manager.set_default_provider(default_provider)
    except ValueError as e:
        logger.error(f"Default provider error: {e}")
    
    # Set fallback order
    fallback_order = config.get('llm.fallback_order', [])
    llm_manager.set_fallback_order(fallback_order)
    
    # 2. Processor Registry
    processor_registry = ProcessorRegistry()
    
    # Register processors
    try:
        processor_registry.register_processor(DigitalLendingProcessor())
        logger.info("✓ Digital Lending processor registered")
    except Exception as e:
        logger.error(f"✗ Digital Lending processor failed: {e}")
    
    try:
        processor_registry.register_processor(FAQProcessor())
        logger.info("✓ FAQ processor registered")
    except Exception as e:
        logger.error(f"✗ FAQ processor failed: {e}")
    
    processor_registry.register_processor(GeneralInquiryProcessor())
    logger.info("✓ General Inquiry processor registered")
    
    # 3. Context Manager
    max_history = config.get('context.max_history', 10)
    context_manager = ContextManager(max_history=max_history)
    logger.info(f"✓ Context manager initialized (max history: {max_history})")
    
    # 4. Orchestrator
    orchestrator = QueryOrchestrator(
        llm_manager=llm_manager,
        processor_registry=processor_registry,
        context_manager=context_manager
    )
    logger.info("✓ Orchestrator initialized")
    
    # ==================== API ENDPOINTS ====================
    
    @app.route('/')
    def index():
        """Serve frontend"""
        frontend_dir = Path(__file__).parent.parent / 'frontend'
        return send_from_directory(frontend_dir, 'index.html')
    
    @app.route('/api/query', methods=['POST'])
    def query():
        """Process user query"""
        try:
            data = request.get_json()
            
            if not data or 'query' not in data:
                return jsonify({
                    'status': 'error',
                    'message': 'Missing query parameter'
                }), 400
            
            query_text = data['query']
            session_id = data.get('session_id', str(uuid.uuid4()))
            model_preference = data.get('model_preference')
            
            logger.info(f"Query received: {query_text[:50]}... (session: {session_id})")
            
            # Process query
            response = orchestrator.process_query(
                query=query_text,
                session_id=session_id,
                model_preference=model_preference
            )
            
            # Return response
            result = response.to_dict()
            result['session_id'] = session_id
            
            return jsonify(result), 200
            
        except Exception as e:
            logger.error(f"Query endpoint error: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': 'Internal server error'
            }), 500
    
    @app.route('/api/health', methods=['GET'])
    def health():
        """Health check endpoint"""
        try:
            providers_status = llm_manager.get_available_providers()
            
            overall_status = any(p['available'] for p in providers_status.values())
            
            return jsonify({
                'status': 'healthy' if overall_status else 'degraded',
                'providers': providers_status,
                'processors': processor_registry.list_processors()
            }), 200
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return jsonify({
                'status': 'unhealthy',
                'error': str(e)
            }), 500
    
    @app.route('/api/history/<session_id>', methods=['GET'])
    def history(session_id):
        """Get conversation history for session"""
        try:
            context = context_manager.get_context(session_id)
            return jsonify({
                'session_id': session_id,
                'history': context['history'],
                'history_length': context['history_length']
            }), 200
        except Exception as e:
            logger.error(f"History endpoint error: {e}")
            return jsonify({
                'status': 'error',
                'message': 'Failed to retrieve history'
            }), 500
    
    @app.route('/api/models/list', methods=['GET'])
    def list_models():
        """List available LLM models"""
        try:
            providers = llm_manager.get_available_providers()
            return jsonify({
                'providers': providers,
                'default': llm_manager.default_provider_name
            }), 200
        except Exception as e:
            logger.error(f"List models error: {e}")
            return jsonify({
                'status': 'error',
                'message': 'Failed to list models'
            }), 500
    
    return app


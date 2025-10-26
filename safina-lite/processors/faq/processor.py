"""FAQ processor for general inquiries"""
import logging
import json
from pathlib import Path
from typing import Dict, Any, List
from difflib import get_close_matches
from processors.base import BaseProcessor, Tool
from models.response import Response

logger = logging.getLogger(__name__)

class FAQProcessor(BaseProcessor):
    """Handles general FAQ and knowledge base queries"""
    
    def __init__(self):
        super().__init__()
        self.name = "faq"
        self.description = "Handles general inquiries about digital lending"
        self.validation_level = "light"
        
        # Load FAQs
        self.faqs = self._load_faqs()
        
        self.tools = [
            Tool(
                name="answer_faq",
                description="Answer general questions about digital lending policies, processes, and requirements",
                parameters_schema={
                    "question": {
                        "type": "string",
                        "required": True,
                        "description": "The general question to answer"
                    }
                },
                processor_class=self.__class__
            )
        ]
    
    def _load_faqs(self) -> List[Dict]:
        """Load FAQ database"""
        faq_file = Path("processors/faq/data/faqs.json")
        
        if not faq_file.exists():
            logger.warning("FAQ file not found, returning empty list")
            return []
        
        try:
            with open(faq_file, 'r') as f:
                data = json.load(f)
                # Flatten FAQs from all sections
                all_faqs = []
                for section_name, section_data in data.items():
                    if isinstance(section_data, dict) and 'faqs' in section_data:
                        all_faqs.extend(section_data['faqs'])
                return all_faqs
        except Exception as e:
            logger.error(f"Error loading FAQs: {e}")
            return []
    
    def get_tools(self) -> List[Tool]:
        """Return available tools"""
        return self.tools
    
    def execute(self, tool_name: str, arguments: Dict[str, Any],
                context: Dict[str, Any], llm_provider: Any) -> Response:
        """Execute tool"""
        if tool_name == "answer_faq":
            return self._answer_faq(arguments, context, llm_provider)
        else:
            return Response(
                message="Unknown tool requested",
                intent="error",
                confidence=0.0,
                status="error"
            )
    
    def _answer_faq(self, arguments: Dict, context: Dict, 
                    llm_provider: Any) -> Response:
        """Answer FAQ question"""
        question = arguments.get("question", "")
        
        logger.info(f"Answering FAQ: {question}")
        
        # Find relevant FAQs
        relevant_faqs = self._find_relevant_faqs(question)
        
        # Generate response with LLM
        response_text = self._generate_llm_answer(question, relevant_faqs, llm_provider)
        
        return Response(
            message=response_text,
            intent="general_inquiry",
            confidence=0.85,
            status="success",
            data={'faq_count': len(relevant_faqs)}
        )
    
    def _find_relevant_faqs(self, question: str, min_similarity: float = 0.35) -> List[Dict]:
        """Find FAQs relevant to the question"""
        relevant = []
        question_lower = question.lower()
        
        # Strategy 1: Fuzzy string matching on questions
        all_questions = [faq.get('question', '') for faq in self.faqs]
        matches = get_close_matches(
            question_lower,
            [q.lower() for q in all_questions],
            n=3,
            cutoff=min_similarity
        )
        
        for match in matches:
            for faq in self.faqs:
                if faq.get('question', '').lower() == match:
                    relevant.append(faq)
        
        # Strategy 2: Keyword matching
        if len(relevant) < 2:
            query_words = set(question_lower.split())
            
            for faq in self.faqs:
                if faq in relevant:
                    continue
                
                faq_text = f"{faq.get('question', '')} {faq.get('answer', '')}"
                faq_words = set(faq_text.lower().split())
                
                overlap = len(query_words & faq_words)
                if overlap >= 2:
                    relevant.append(faq)
                    if len(relevant) >= 5:
                        break
        
        return relevant[:5]
    
    def _generate_llm_answer(self, question: str, relevant_faqs: List[Dict],
                            llm_provider: Any) -> str:
        """Generate answer using LLM with FAQ context"""
        if relevant_faqs:
            # Build context from FAQs
            context = "\n\n".join([
                f"Q: {faq.get('question', '')}\nA: {faq.get('answer', '')}"
                for faq in relevant_faqs
            ])
            
            prompt = f"""You are Safina, a professional banking assistant for NCBA Bank's digital lending team.

Based on these FAQs from our knowledge base:

{context}

Answer this question clearly and professionally: "{question}"

Provide a helpful, accurate response based on the FAQs above. Keep it concise and actionable."""
        else:
            # No FAQs found, general knowledge
            prompt = f"""You are Safina, a banking assistant for NCBA Bank.

A staff member asked: "{question}"

Based on general digital loan eligibility principles, provide a helpful answer about common requirements:
- Individual accounts (not joint)
- Sole signatory mandates
- Mobile banking enrollment
- Minimum 6 months banking history
- Good account classification (A5+ for digital, A7+ for mobile)
- No active arrears
- Regular banking activity

Keep the response professional, concise, and actionable."""
        
        try:
            response = llm_provider.generate(prompt, max_tokens=400, temperature=0.7)
            return response.strip()
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return "I encountered an error generating a response. Please try rephrasing your question."


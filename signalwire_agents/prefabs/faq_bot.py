"""
FAQBotAgent - Prefab agent for answering frequently asked questions
"""

from typing import List, Dict, Any, Optional, Union
import json

from signalwire_agents.core.agent_base import AgentBase
from signalwire_agents.core.function_result import SwaigFunctionResult


class FAQBotAgent(AgentBase):
    """
    A prefab agent designed to answer frequently asked questions based on
    a provided list of question/answer pairs.
    
    This agent will:
    1. Match user questions against the FAQ database
    2. Provide the most relevant answer
    3. Suggest other relevant questions when appropriate
    
    Example:
        agent = FAQBotAgent(
            faqs=[
                {
                    "question": "What is SignalWire?",
                    "answer": "SignalWire is a developer-friendly cloud communications platform."
                },
                {
                    "question": "How much does it cost?",
                    "answer": "SignalWire offers pay-as-you-go pricing with no monthly fees."
                }
            ]
        )
    """
    
    def __init__(
        self,
        faqs: List[Dict[str, str]],
        suggest_related: bool = True,
        persona: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize an FAQ bot agent
        
        Args:
            faqs: List of FAQ items, each with:
                - question: The question text
                - answer: The answer text
                - categories: Optional list of category tags
            suggest_related: Whether to suggest related questions
            persona: Optional custom personality description
            **kwargs: Additional arguments for AgentBase
        """
        super().__init__(**kwargs)
        
        self.faqs = faqs
        self.suggest_related = suggest_related
        
        # Build the prompt sections declaratively
        prompt_sections = {
            "Personality": persona or "You are a helpful FAQ bot that provides accurate answers to common questions.",
            
            "Goal": "Answer user questions by matching them to the most similar FAQ in your database.",
            
            "Instructions": [
                "Compare user questions to your FAQ database and find the best match.",
                "Provide the answer from the FAQ database for the matching question.",
                "If no close match exists, politely say you don't have that information.",
                "Be concise and factual in your responses."
            ],
            
            "FAQ Database": {
                "body": "Here is your database of frequently asked questions and answers:"
            }
        }
        
        # Add the FAQs as subsections under FAQ Database
        faq_subsections = []
        for i, faq in enumerate(faqs):
            question = faq.get("question", "")
            answer = faq.get("answer", "")
            categories = faq.get("categories", [])
            
            # Skip invalid entries
            if not question or not answer:
                continue
                
            subsection = {
                "title": question,
                "body": answer
            }
            
            # Add category tags if present
            if categories:
                category_str = "Categories: " + ", ".join(categories)
                subsection["body"] = f"{subsection['body']}\n\n{category_str}"
                
            faq_subsections.append(subsection)
            
        # If there are valid FAQs, add them to the prompt
        if faq_subsections:
            prompt_sections["FAQ Database"]["subsections"] = faq_subsections
            
        # Add section about suggesting related questions if enabled
        if suggest_related:
            prompt_sections["Related Questions"] = {
                "body": "When appropriate, suggest other related questions from the FAQ database that might be helpful."
            }
            
        # Set the custom prompt sections structure
        self.PROMPT_SECTIONS = prompt_sections
        
        # Process the prompt sections
        self._process_prompt_sections()
        
        # Set up post-prompt for summary
        self._setup_post_prompt()
    
    def _setup_post_prompt(self):
        """Set up the post-prompt for summary"""
        post_prompt = """
        Return a JSON summary of this interaction:
        {
            "question": "MAIN_QUESTION_ASKED",
            "matched_faq": "MATCHED_FAQ_QUESTION_OR_null",
            "answered_successfully": true/false,
            "suggested_related": []
        }
        """
        self.set_post_prompt(post_prompt)
    
    def on_summary(self, summary: Dict[str, Any]) -> None:
        """
        Process the interaction summary
        
        Args:
            summary: Summary data from the conversation
        """
        print(f"FAQ interaction summary: {json.dumps(summary, indent=2)}")
        
        # Override this in subclasses to log or save the interaction

"""
Copyright (c) 2025 SignalWire

This file is part of the SignalWire AI Agents SDK.

Licensed under the MIT License.
See LICENSE file in the project root for full license information.
"""

"""
InfoGathererAgent - Prefab agent for collecting answers to a series of questions
"""

from typing import List, Dict, Any, Optional, Union
import json

from signalwire_agents.core.agent_base import AgentBase
from signalwire_agents.core.function_result import SwaigFunctionResult


class InfoGathererAgent(AgentBase):
    """
    A prefab agent designed to collect answers to a series of questions.
    
    This agent will:
    1. Ask if the user is ready to begin
    2. Ask each question in sequence
    3. Store the answers for later use
    
    Example:
        agent = InfoGathererAgent(
            questions=[
                {"key_name": "full_name", "question_text": "What is your full name?"},
                {"key_name": "email", "question_text": "What is your email address?", "confirm": True},
                {"key_name": "reason", "question_text": "How can I help you today?"}
            ]
        )
    """
    
    def __init__(
        self,
        questions: List[Dict[str, str]],
        name: str = "info_gatherer", 
        route: str = "/info_gatherer",
        enable_state_tracking: bool = True,  # Enable state tracking by default for InfoGatherer
        **kwargs
    ):
        """
        Initialize an information gathering agent
        
        Args:
            questions: List of questions to ask, each with:
                - key_name: Identifier for storing the answer
                - question_text: The actual question to ask the user
                - confirm: (Optional) If set to True, the agent will confirm the answer before submitting
            name: Agent name for the route
            route: HTTP route for this agent
            enable_state_tracking: Whether to enable state tracking (default: True)
            **kwargs: Additional arguments for AgentBase
        """
        # Initialize the base agent
        super().__init__(
            name=name,
            route=route,
            use_pom=True,
            enable_state_tracking=enable_state_tracking,  # Pass state tracking parameter to base
            **kwargs
        )
        
        # Validate questions format
        self._validate_questions(questions)
        
        # Set up global data with questions and initial state
        self.set_global_data({
            "questions": questions,
            "question_index": 0,
            "answers": []
        })
        
        # Build a minimal prompt
        self._build_prompt()
        
        # Configure additional agent settings
        self._configure_agent_settings()
    
    def _validate_questions(self, questions):
        """Validate that questions are in the correct format"""
        if not questions:
            raise ValueError("At least one question is required")
            
        for i, question in enumerate(questions):
            if "key_name" not in question:
                raise ValueError(f"Question {i+1} is missing 'key_name' field")
            if "question_text" not in question:
                raise ValueError(f"Question {i+1} is missing 'question_text' field")
    
    def _build_prompt(self):
        """Build a minimal prompt with just the objective"""
        self.prompt_add_section(
            "Objective", 
            body="Your role is to get answers to a series of questions. Begin by asking the user if they are ready to answer some questions. If they confirm they are ready, call the start_questions function to begin the process."
        )
    
    def _configure_agent_settings(self):
        """Configure additional agent settings"""
        # Set AI behavior parameters
        self.set_params({
            "end_of_speech_timeout": 800,
            "speech_event_timeout": 1000  # Slightly longer for thoughtful responses
        })
    
    def _generate_question_instruction(self, question_text: str, needs_confirmation: bool, is_first_question: bool = False) -> str:
        """
        Generate the instruction text for asking a question
        
        Args:
            question_text: The question to ask
            needs_confirmation: Whether confirmation is required
            is_first_question: Whether this is the first question or a subsequent one
            
        Returns:
            Formatted instruction text
        """
        # Start with the appropriate prefix based on whether this is the first question
        if is_first_question:
            instruction = f"Ask the user to answer the following question: {question_text}\n\n"
        else:
            instruction = f"Previous Answer recorded. Now ask the user to answer the following question: {question_text}\n\n"
        
        # Add the common part
        instruction += "Make sure the answer fits the scope and context of the question before submitting it. "
        
        # Add confirmation guidance if needed
        if needs_confirmation:
            instruction += "Insist that the user confirms the answer as many times as needed until they say it is correct."
        else:
            instruction += "You don't need the user to confirm the answer to this question."
            
        return instruction
    
    @AgentBase.tool(
        name="start_questions",
        description="Start the question sequence with the first question",
        parameters={}
    )
    def start_questions(self, args, raw_data):
        """
        Start the question sequence by retrieving the first question
        
        This function gets the current question index from global_data
        and returns the corresponding question.
        """
        # Get global data
        global_data = raw_data.get("global_data", {})
        questions = global_data.get("questions", [])
        question_index = global_data.get("question_index", 0)
        
        # Check if we have questions
        if not questions or question_index >= len(questions):
            return SwaigFunctionResult("I don't have any questions to ask.")
        
        # Get the current question
        current_question = questions[question_index]
        question_text = current_question.get("question_text", "")
        needs_confirmation = current_question.get("confirm", False)
        
        # Generate instruction using the helper method
        instruction = self._generate_question_instruction(
            question_text=question_text,
            needs_confirmation=needs_confirmation,
            is_first_question=True
        )
        
        # Return a prompt to ask the question
        return SwaigFunctionResult(instruction)
    
    @AgentBase.tool(
        name="submit_answer",
        description="Submit an answer to the current question and move to the next one",
        parameters={
            "answer": {
                "type": "string",
                "description": "The user's answer to the current question"
            }
        }
    )
    def submit_answer(self, args, raw_data):
        """
        Submit an answer to the current question and move to the next one
        
        This function:
        1. Stores the answer in global_data
        2. Increments the question index
        3. Returns the next question or completion message
        """
        # Get the answer
        answer = args.get("answer", "")
        
        # Get global data
        global_data = raw_data.get("global_data", {})
        questions = global_data.get("questions", [])
        question_index = global_data.get("question_index", 0)
        answers = global_data.get("answers", [])
        
        # Check if we're within bounds
        if question_index >= len(questions):
            return SwaigFunctionResult("All questions have already been answered.")
        
        # Get the current question
        current_question = questions[question_index]
        key_name = current_question.get("key_name", "")
        
        # Store the answer
        new_answer = {"key_name": key_name, "answer": answer}
        new_answers = answers + [new_answer]
        
        # Increment question index
        new_question_index = question_index + 1
        
        print(f"new_question_index: {new_question_index} len(questions): {len(questions)}")
        
        # Check if we have more questions
        if new_question_index < len(questions):

            print(f"Asking next question: {new_question_index} question: {questions[new_question_index]}")
            
            # Get the next question
            next_question = questions[new_question_index]
            next_question_text = next_question.get("question_text", "")
            needs_confirmation = next_question.get("confirm", False)
            
            # Generate instruction using the helper method
            instruction = self._generate_question_instruction(
                question_text=next_question_text,
                needs_confirmation=needs_confirmation,
                is_first_question=False
            )
            
            # Create response with the global data update and next question
            result = SwaigFunctionResult(instruction)
            
            # Add actions to update global data
            result.add_actions([
                {"set_global_data": {
                    "answers": new_answers,
                    "question_index": new_question_index
                }}
            ])
            
            return result
        else:
            # No more questions - create response with global data update and completion message
            result = SwaigFunctionResult(
                "Thank you! All questions have been answered. You can now summarize the information collected or ask if there's anything else the user would like to discuss."
            )
            
            # Add actions to update global data
            result.add_actions([
                {"set_global_data": {
                    "answers": new_answers,
                    "question_index": new_question_index
                }}
            ])
            
            return result


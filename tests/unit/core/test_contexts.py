"""
Unit tests for contexts module
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any, Optional

from signalwire_agents.core.contexts import (
    ContextBuilder,
    Context,
    Step,
    create_simple_context
)


class TestStep:
    """Test Step functionality"""
    
    def test_basic_initialization(self):
        """Test basic Step initialization"""
        step = Step("greeting")
        
        assert step.name == "greeting"
        assert step._text is None
        assert step._step_criteria is None
        assert step._functions is None
        assert step._valid_steps is None
        assert step._sections == []
    
    def test_set_text(self):
        """Test setting step text"""
        step = Step("greeting")
        
        result = step.set_text("Hello, how can I help you today?")
        
        assert result is step  # Should return self for chaining
        assert step._text == "Hello, how can I help you today?"
    
    def test_add_section(self):
        """Test adding POM sections"""
        step = Step("greeting")
        
        result = step.add_section("Introduction", "Welcome to our service")
        
        assert result is step  # Should return self for chaining
        assert len(step._sections) == 1
        assert step._sections[0]["title"] == "Introduction"
        assert step._sections[0]["body"] == "Welcome to our service"
    
    def test_add_bullets(self):
        """Test adding bullet sections"""
        step = Step("greeting")
        bullets = ["First point", "Second point", "Third point"]
        
        result = step.add_bullets("Key Points", bullets)
        
        assert result is step  # Should return self for chaining
        assert len(step._sections) == 1
        assert step._sections[0]["title"] == "Key Points"
        assert step._sections[0]["bullets"] == bullets
    
    def test_set_step_criteria(self):
        """Test setting step criteria"""
        step = Step("greeting")
        
        result = step.set_step_criteria("User has provided their name")
        
        assert result is step  # Should return self for chaining
        assert step._step_criteria == "User has provided their name"
    
    def test_set_functions(self):
        """Test setting available functions"""
        step = Step("greeting")
        
        # Test with function list
        result = step.set_functions(["get_weather", "search"])
        assert result is step
        assert step._functions == ["get_weather", "search"]
        
        # Test with "none"
        step.set_functions("none")
        assert step._functions == "none"
    
    def test_set_valid_steps(self):
        """Test setting valid steps"""
        step = Step("greeting")
        valid_steps = ["next", "collect_info", "end"]
        
        result = step.set_valid_steps(valid_steps)
        
        assert result is step  # Should return self for chaining
        assert step._valid_steps == valid_steps
    
    def test_text_and_sections_conflict(self):
        """Test that text and sections cannot be mixed"""
        step = Step("greeting")
        
        # Set text first
        step.set_text("Hello")
        
        # Adding sections should raise error
        with pytest.raises(ValueError, match="Cannot add POM sections when set_text"):
            step.add_section("Title", "Body")
        
        with pytest.raises(ValueError, match="Cannot add POM sections when set_text"):
            step.add_bullets("Title", ["bullet"])
    
    def test_sections_and_text_conflict(self):
        """Test that sections and text cannot be mixed"""
        step = Step("greeting")
        
        # Add section first
        step.add_section("Title", "Body")
        
        # Setting text should raise error
        with pytest.raises(ValueError, match="Cannot use set_text\\(\\) when POM sections"):
            step.set_text("Hello")
    
    def test_render_text_with_text(self):
        """Test rendering text when text is set"""
        step = Step("greeting")
        step.set_text("Hello, how can I help you?")
        
        rendered = step._render_text()
        
        assert rendered == "Hello, how can I help you?"
    
    def test_render_text_with_sections(self):
        """Test rendering text from POM sections"""
        step = Step("greeting")
        step.add_section("Welcome", "Hello there!")
        step.add_bullets("Options", ["Option 1", "Option 2"])
        
        rendered = step._render_text()
        
        assert "## Welcome" in rendered
        assert "Hello there!" in rendered
        assert "## Options" in rendered
        assert "- Option 1" in rendered
        assert "- Option 2" in rendered
    
    def test_render_text_no_content(self):
        """Test rendering text when no content is set"""
        step = Step("greeting")
        
        with pytest.raises(ValueError, match="Step 'greeting' has no text or POM sections"):
            step._render_text()
    
    def test_to_dict_basic(self):
        """Test converting step to dictionary"""
        step = Step("greeting")
        step.set_text("Hello!")
        
        result = step.to_dict()
        
        assert result["text"] == "Hello!"
        assert "step_criteria" not in result
        assert "functions" not in result
        assert "valid_steps" not in result
    
    def test_to_dict_complete(self):
        """Test converting step with all fields to dictionary"""
        step = Step("greeting")
        step.set_text("Hello!")
        step.set_step_criteria("User responds")
        step.set_functions(["search"])
        step.set_valid_steps(["next"])
        
        result = step.to_dict()
        
        assert result["text"] == "Hello!"
        assert result["step_criteria"] == "User responds"
        assert result["functions"] == ["search"]
        assert result["valid_steps"] == ["next"]


class TestContext:
    """Test Context functionality"""
    
    def test_basic_initialization(self):
        """Test basic Context initialization"""
        context = Context("customer_service")
        
        assert context.name == "customer_service"
        assert context._steps == {}
        assert context._step_order == []
        assert context._valid_contexts is None
    
    def test_add_step(self):
        """Test adding steps to context"""
        context = Context("customer_service")
        
        step = context.add_step("greeting")
        
        assert isinstance(step, Step)
        assert step.name == "greeting"
        assert "greeting" in context._steps
        assert context._step_order == ["greeting"]
    
    def test_add_multiple_steps(self):
        """Test adding multiple steps"""
        context = Context("customer_service")
        
        step1 = context.add_step("greeting")
        step2 = context.add_step("collect_info")
        step3 = context.add_step("provide_solution")
        
        assert len(context._steps) == 3
        assert context._step_order == ["greeting", "collect_info", "provide_solution"]
        assert all(isinstance(step, Step) for step in [step1, step2, step3])
    
    def test_add_duplicate_step(self):
        """Test adding duplicate step names"""
        context = Context("customer_service")
        
        context.add_step("greeting")
        
        with pytest.raises(ValueError, match="Step 'greeting' already exists"):
            context.add_step("greeting")
    
    def test_set_valid_contexts(self):
        """Test setting valid contexts"""
        context = Context("customer_service")
        valid_contexts = ["sales", "technical_support"]
        
        result = context.set_valid_contexts(valid_contexts)
        
        assert result is context  # Should return self for chaining
        assert context._valid_contexts == valid_contexts
    
    def test_to_dict_basic(self):
        """Test converting context to dictionary"""
        context = Context("customer_service")
        step = context.add_step("greeting")
        step.set_text("Hello!")
        
        result = context.to_dict()
        
        assert "steps" in result
        assert len(result["steps"]) == 1
        assert result["steps"][0]["text"] == "Hello!"
        assert "valid_contexts" not in result
    
    def test_to_dict_with_valid_contexts(self):
        """Test converting context with valid contexts"""
        context = Context("customer_service")
        step = context.add_step("greeting")
        step.set_text("Hello!")
        context.set_valid_contexts(["sales"])
        
        result = context.to_dict()
        
        assert "steps" in result
        assert result["valid_contexts"] == ["sales"]
    
    def test_to_dict_no_steps(self):
        """Test converting context with no steps"""
        context = Context("customer_service")
        
        with pytest.raises(ValueError, match="Context 'customer_service' has no steps"):
            context.to_dict()


class TestContextBuilder:
    """Test ContextBuilder functionality"""
    
    def test_basic_initialization(self):
        """Test basic ContextBuilder initialization"""
        mock_agent = Mock()
        builder = ContextBuilder(mock_agent)
        
        # ContextBuilder doesn't store agent reference, just uses it during init
        assert builder._contexts == {}
    
    def test_add_context(self):
        """Test adding a context"""
        mock_agent = Mock()
        builder = ContextBuilder(mock_agent)
        
        context = builder.add_context("customer_service")
        assert isinstance(context, Context)
        assert "customer_service" in builder._contexts
    
    def test_add_duplicate_context(self):
        """Test adding duplicate context raises error"""
        mock_agent = Mock()
        builder = ContextBuilder(mock_agent)
        
        builder.add_context("customer_service")
        
        # The actual API raises an error for duplicates
        with pytest.raises(ValueError, match="Context 'customer_service' already exists"):
            builder.add_context("customer_service")
    
    def test_validate_success(self):
        """Test successful validation with default context"""
        mock_agent = Mock()
        builder = ContextBuilder(mock_agent)
        
        context = builder.add_context("default")  # Must be named 'default' for single context
        step = context.add_step("greeting")
        step.set_text("Hello!")
        
        # Should not raise any exceptions
        builder.validate()
    
    def test_validate_no_contexts(self):
        """Test validation with no contexts"""
        mock_agent = Mock()
        builder = ContextBuilder(mock_agent)
        
        with pytest.raises(ValueError, match="At least one context must be defined"):
            builder.validate()
    
    def test_validate_context_no_steps(self):
        """Test validation with context having no steps"""
        mock_agent = Mock()
        builder = ContextBuilder(mock_agent)
        
        builder.add_context("default")  # Must be named 'default' for single context
        
        with pytest.raises(ValueError, match="Context 'default' must have at least one step"):
            builder.validate()
    
    def test_to_dict(self):
        """Test converting builder to dictionary"""
        mock_agent = Mock()
        builder = ContextBuilder(mock_agent)
        
        context = builder.add_context("default")  # Must be named 'default' for single context
        step = context.add_step("greeting")
        step.set_text("Hello!")
        
        result = builder.to_dict()
        assert isinstance(result, dict)
        assert "default" in result


class TestCreateSimpleContext:
    """Test create_simple_context factory function"""
    
    def test_create_simple_context_default(self):
        """Test creating simple context with default name"""
        context = create_simple_context()
        
        assert isinstance(context, Context)
        assert context.name == "default"
    
    def test_create_simple_context_custom_name(self):
        """Test creating simple context with custom name"""
        context = create_simple_context("my_context")
        
        assert isinstance(context, Context)
        assert context.name == "my_context"


class TestContextIntegration:
    """Test context integration scenarios"""
    
    def test_complete_context_workflow(self):
        """Test complete context building workflow with multiple contexts"""
        mock_agent = Mock()
        builder = ContextBuilder(mock_agent)
        
        # Create customer service context
        customer_service = builder.add_context("customer_service")
        customer_service.set_valid_contexts(["sales", "technical_support"])
        
        # Add greeting step
        greeting = customer_service.add_step("greeting")
        greeting.set_text("Hello! Welcome to customer service. How can I help you today?")
        greeting.set_step_criteria("User has stated their issue")
        greeting.set_functions(["search_knowledge_base", "escalate_to_human"])
        greeting.set_valid_steps(["next", "gather_info"])  # Use valid step names
        
        # Add information gathering step
        gather_info = customer_service.add_step("gather_info")
        gather_info.add_section("Information Needed", "Please provide the following details:")
        gather_info.add_bullets("Required Information", [
            "Account number or phone number",
            "Description of the issue",
            "When did the issue start?"
        ])
        gather_info.set_step_criteria("All required information has been collected")
        gather_info.set_valid_steps(["next", "greeting"])
        
        # Add resolution step
        resolution = customer_service.add_step("resolution")
        resolution.set_text("Based on the information provided, here's how we can resolve your issue:")
        resolution.set_functions("none")  # No functions needed for final step
        
        # Add the referenced contexts to satisfy validation
        sales = builder.add_context("sales")
        sales_step = sales.add_step("sales_greeting")
        sales_step.set_text("Welcome to sales!")
        
        technical_support = builder.add_context("technical_support")
        tech_step = technical_support.add_step("tech_greeting")
        tech_step.set_text("Welcome to technical support!")
        
        # Validate the complete structure
        builder.validate()
        
        # Convert to dictionary
        result = builder.to_dict()
        assert "customer_service" in result
        assert "sales" in result
        assert "technical_support" in result
        assert len(result["customer_service"]["steps"]) == 3
    
    def test_multiple_contexts(self):
        """Test building multiple contexts"""
        mock_agent = Mock()
        builder = ContextBuilder(mock_agent)
        
        # Create sales context
        sales = builder.add_context("sales")
        sales_step = sales.add_step("pitch")
        sales_step.set_text("Let me tell you about our amazing products!")
        
        # Create support context
        support = builder.add_context("support")
        support_step = support.add_step("diagnose")
        support_step.set_text("Let's troubleshoot your issue.")
        
        # Validate and convert
        builder.validate()
        result = builder.to_dict()
        
        # Verify both contexts exist
        assert "sales" in result
        assert "support" in result
        assert len(result["sales"]["steps"]) == 1
        assert len(result["support"]["steps"]) == 1
    
    def test_complex_step_configuration(self):
        """Test complex step configuration with all features"""
        context = Context("complex")
        
        step = context.add_step("complex_step")
        
        # Use method chaining
        step.add_section("Overview", "This is a complex step with multiple sections") \
            .add_bullets("Features", ["Feature 1", "Feature 2", "Feature 3"]) \
            .add_section("Instructions", "Follow these steps carefully") \
            .set_step_criteria("All features have been demonstrated") \
            .set_functions(["demo_feature_1", "demo_feature_2", "demo_feature_3"]) \
            .set_valid_steps(["next", "previous", "help"])
        
        # Convert to dict and verify
        step_dict = step.to_dict()
        
        # Check that all sections are rendered
        text = step_dict["text"]
        assert "## Overview" in text
        assert "This is a complex step" in text
        assert "## Features" in text
        assert "- Feature 1" in text
        assert "## Instructions" in text
        assert "Follow these steps" in text
        
        # Check other fields
        assert step_dict["step_criteria"] == "All features have been demonstrated"
        assert step_dict["functions"] == ["demo_feature_1", "demo_feature_2", "demo_feature_3"]
        assert step_dict["valid_steps"] == ["next", "previous", "help"] 
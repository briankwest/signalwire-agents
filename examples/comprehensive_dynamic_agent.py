#!/usr/bin/env python3

"""
Comprehensive Dynamic Agent Configuration Example

This example demonstrates the power of the ephemeral agent configurator pattern,
showing how to dynamically configure multiple aspects of an agent based on request parameters.

Features demonstrated:
- Dynamic voice and language selection
- Context-aware prompt configuration  
- Tier-based feature settings
- Industry-specific customization
- A/B testing configuration
- Multi-tenant global data

Usage examples:

1. Premium Healthcare Agent:
   curl "http://localhost:3000/dynamic?tier=premium&industry=healthcare&voice=spore&test_group=A"

2. Standard Finance Agent:
   curl "http://localhost:3000/dynamic?tier=standard&industry=finance&voice=cove&test_group=B"

3. Enterprise Retail Agent:
   curl "http://localhost:3000/dynamic?tier=enterprise&industry=retail&voice=flower&language=es&locale=mx"

4. Developer Testing:
   curl "http://localhost:3000/dynamic/debug?tier=premium&debug=true"

Query Parameters:
- tier: standard|premium|enterprise (affects features and timeouts)
- industry: healthcare|finance|retail|general (customizes prompts and responses)
- voice: cove|marsh|creek|brook|flower|spore (voice selection)
- language: en|es|fr (language support)  
- locale: us|mx|ca|fr (locale-specific customization)
- test_group: A|B (A/B testing configuration)
- debug: true (enables debug features)
- customer_id: <string> (customer-specific data)
"""

from signalwire_agents import AgentBase

class ComprehensiveDynamicAgent(AgentBase):
    def __init__(self, route="/dynamic"):
        super().__init__(
            name="Comprehensive Dynamic Agent",
            route=route,  # Custom path for this agent
            auto_answer=True,
            record_call=True
        )
        
        # Set up dynamic configuration
        self.set_dynamic_config_callback(self.configure_agent_dynamically)
        
        # Define available voice options by tier
        self.voice_options = {
            "standard": ["rime.cove", "rime.marsh", "rime.creek"],
            "premium": ["rime.brook", "rime.flower", "rime.spore"],
            "enterprise": ["rime.brook", "rime.flower", "rime.spore", "rime.cove", "rime.marsh", "rime.creek"]
        }
        
        # Industry-specific configurations
        self.industry_configs = {
            "healthcare": {
                "compliance_level": "high",
                "privacy_emphasis": True,
                "terminology": "medical",
                "response_style": "professional"
            },
            "finance": {
                "compliance_level": "high", 
                "security_emphasis": True,
                "terminology": "financial",
                "response_style": "formal"
            },
            "retail": {
                "compliance_level": "medium",
                "sales_emphasis": True,
                "terminology": "customer_service",
                "response_style": "friendly"
            },
            "general": {
                "compliance_level": "standard",
                "terminology": "general",
                "response_style": "conversational"
            }
        }

    def configure_agent_dynamically(self, query_params, body_params, headers, agent):
        """
        Dynamic configuration callback that demonstrates comprehensive agent customization
        """
        # Extract key parameters
        tier = query_params.get('tier', 'standard').lower()
        industry = query_params.get('industry', 'general').lower()
        requested_voice = query_params.get('voice', '').lower()
        language = query_params.get('language', 'en').lower()
        locale = query_params.get('locale', 'us').lower()
        test_group = query_params.get('test_group', 'A').upper()
        debug_mode = query_params.get('debug', '').lower() == 'true'
        customer_id = query_params.get('customer_id', '')
        
        # === Voice Configuration ===
        self._configure_voice_and_language(agent, tier, requested_voice, language, locale)
        
        # === Tier-based Parameters ===
        self._configure_tier_parameters(agent, tier, test_group)
        
        # === Industry-specific Prompts ===
        self._configure_industry_prompts(agent, industry, tier)
        
        # === Global Data Setup ===
        self._configure_global_data(agent, tier, industry, customer_id, test_group, debug_mode)
        
        # === Debug Features ===
        if debug_mode:
            self._configure_debug_features(agent, query_params)
            
        # === A/B Testing Configuration ===
        self._configure_ab_testing(agent, test_group, tier)

    def _configure_voice_and_language(self, agent, tier, requested_voice, language, locale):
        """Configure voice and language settings"""
        # Determine available voices for tier
        available_voices = self.voice_options.get(tier, self.voice_options["standard"])
        
        # Select voice (use requested if available for tier, otherwise default)
        # Handle both "spore" and "rime.spore" formats
        requested_voice_full = f"rime.{requested_voice}" if requested_voice and not requested_voice.startswith("rime.") else requested_voice
        
        if requested_voice_full and requested_voice_full in available_voices:
            voice = requested_voice_full
        else:
            voice = available_voices[0]  # Default to first available
        
        # Configure language and voice (using proper engine.voice:model format)
        # Default model is mistv2 which is optional
        voice_model = voice  # Already in rime.voice format
        
        if language == "en":
            if locale == "us":
                agent.add_language("English US", "en-US", voice_model)
            elif locale == "ca":
                agent.add_language("English CA", "en-CA", voice_model)
            else:
                agent.add_language("English", "en-US", voice_model)
        elif language == "es":
            # Spanish always uses rime.pablo regardless of requested voice
            if locale == "mx":
                agent.add_language("Spanish MX", "es-MX", "rime.pablo")
            else:
                agent.add_language("Spanish", "es-ES", "rime.pablo")
        elif language == "fr":
            if locale == "ca":
                agent.add_language("French CA", "fr-CA", "rime.alois")
            else:
                agent.add_language("French", "fr-FR", "rime.alois")
        else:
            # Default to English
            agent.add_language("English", "en-US", voice_model)

    def _configure_tier_parameters(self, agent, tier, test_group):
        """Configure parameters based on service tier"""
        params = {}
        
        if tier == "enterprise":
            params.update({
                "end_of_speech_timeout": 800,
                "attention_timeout": 25000,
                "background_file_volume": -35,
                "background_file_loops": -1,
                "digit_timeout": 8000,
                "energy_level": 150
            })
        elif tier == "premium":
            params.update({
                "end_of_speech_timeout": 600,
                "attention_timeout": 20000,
                "background_file_volume": -30,
                "background_file_loops": 5,
                "digit_timeout": 6000,
                "energy_level": 120
            })
        else:  # standard
            params.update({
                "end_of_speech_timeout": 400,
                "attention_timeout": 15000,
                "background_file_volume": -20,
                "background_file_loops": 3,
                "digit_timeout": 4000,
                "energy_level": 100
            })
            
        # A/B test parameter variation
        if test_group == "B":
            params["end_of_speech_timeout"] = int(params["end_of_speech_timeout"] * 1.2)
            
        agent.set_params(params)

    def _configure_industry_prompts(self, agent, industry, tier):
        """Configure industry-specific prompts"""
        config = self.industry_configs.get(industry, self.industry_configs["general"])
        
        # Base introduction
        agent.prompt_add_section(
            "Role and Purpose",
            f"You are a professional AI assistant specialized in {industry} services. "
            f"Your role is to provide helpful, accurate information while maintaining "
            f"{config['response_style']} communication standards."
        )
        
        # Industry-specific guidelines
        if industry == "healthcare":
            agent.prompt_add_section(
                "Healthcare Guidelines",
                "Follow HIPAA compliance standards. Never provide medical diagnoses or treatment advice.",
                bullets=[
                    "Protect patient privacy at all times",
                    "Direct medical questions to qualified healthcare providers", 
                    "Use appropriate medical terminology when helpful",
                    "Maintain professional bedside manner"
                ]
            )
        elif industry == "finance":
            agent.prompt_add_section(
                "Financial Guidelines", 
                "Adhere to financial industry regulations and maintain strict confidentiality.",
                bullets=[
                    "Never provide specific investment advice",
                    "Protect sensitive financial information",
                    "Use precise financial terminology",
                    "Refer complex matters to qualified advisors"
                ]
            )
        elif industry == "retail":
            agent.prompt_add_section(
                "Customer Service Excellence",
                "Focus on customer satisfaction and sales support.",
                bullets=[
                    "Maintain friendly, helpful demeanor",
                    "Understand product features and benefits",
                    "Handle complaints with empathy",
                    "Look for opportunities to enhance customer experience"
                ]
            )
        
        # Tier-specific capabilities
        if tier in ["premium", "enterprise"]:
            agent.prompt_add_section(
                "Enhanced Capabilities",
                f"As a {tier} service, you have access to advanced features:",
                bullets=[
                    "Extended conversation memory",
                    "Priority processing and faster responses", 
                    "Access to specialized knowledge bases",
                    "Advanced personalization options"
                ]
            )

    def _configure_global_data(self, agent, tier, industry, customer_id, test_group, debug_mode):
        """Configure global data for the session"""
        global_data = {
            "service_tier": tier,
            "industry_focus": industry,
            "test_group": test_group,
            "session_start": "2024-01-01T00:00:00Z",  # Would be actual timestamp
            "features_enabled": self._get_enabled_features(tier),
            "compliance_level": self.industry_configs[industry]["compliance_level"]
        }
        
        if customer_id:
            global_data["customer_id"] = customer_id
            global_data["customer_tier"] = tier
            
        if debug_mode:
            global_data["debug_mode"] = True
            global_data["debug_info"] = {
                "voice_options": self.voice_options[tier],
                "available_features": self._get_enabled_features(tier)
            }
            
        agent.set_global_data(global_data)

    def _configure_debug_features(self, agent, query_params):
        """Configure debug-specific features"""
        agent.prompt_add_section(
            "Debug Mode",
            "Debug mode is enabled. Provide additional context and reasoning in responses.",
            bullets=[
                "Show decision-making process when appropriate",
                "Include relevant global data references",
                "Explain feature availability based on tier",
                "Provide timing and performance insights"
            ]
        )
        
        # Add debug-specific speech recognition hints
        agent.add_hints([
            "debug",
            "verbose",
            "reasoning",
            "capabilities",
            "tier"
        ])

    def _configure_ab_testing(self, agent, test_group, tier):
        """Configure A/B testing variations"""
        if test_group == "A":
            # Control group - add speech recognition hints for standard terms
            agent.add_hint("standard")
        else:
            # Test group B - add speech recognition hints for enhanced features
            agent.add_hints(["enhanced", "personalized", "proactive"])
            agent.prompt_add_section(
                "Enhanced Interaction Style",
                "You are using an enhanced conversation style for this session:",
                bullets=[
                    "Ask clarifying questions more frequently",
                    "Provide more detailed explanations",
                    "Offer proactive suggestions when appropriate",
                    "Use more conversational, engaging language"
                ]
            )

    def _get_enabled_features(self, tier):
        """Return list of features enabled for the given tier"""
        features = ["basic_conversation", "function_calling"]
        
        if tier in ["premium", "enterprise"]:
            features.extend([
                "extended_memory",
                "priority_processing", 
                "advanced_analytics"
            ])
            
        if tier == "enterprise":
            features.extend([
                "custom_integration",
                "dedicated_support",
                "advanced_security"
            ])
            
        return features


# Example usage and testing
if __name__ == "__main__":
    agent = ComprehensiveDynamicAgent()
    
    print("🤖 Starting Comprehensive Dynamic Agent")
    print("\nTry these example requests:")
    print("curl 'http://localhost:3000/dynamic?tier=premium&industry=healthcare&voice=spore&test_group=A'")
    print("curl 'http://localhost:3000/dynamic?tier=enterprise&industry=finance&voice=flower&language=es&locale=mx'")
    print("curl 'http://localhost:3000/dynamic?tier=standard&industry=retail&debug=true&customer_id=123'")
    print("curl 'http://localhost:3000/dynamic/debug?tier=premium&industry=healthcare'")
    print()
    
    agent.serve() 
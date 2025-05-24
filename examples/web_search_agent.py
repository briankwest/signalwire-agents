#!/usr/bin/env python3

"""
Web Search Agent Example

This example demonstrates an AI agent that can search the web for information
using Google Custom Search API and web scraping capabilities.

The agent includes a SWAIG function that allows it to:
- Search Google for any query
- Scrape the resulting web pages for content
- Return formatted results with titles, URLs, and extracted text

Required Environment Variables:
- GOOGLE_SEARCH_API_KEY: Your Google Custom Search API key
- GOOGLE_SEARCH_ENGINE_ID: Your Google Custom Search Engine ID

Usage:
    export GOOGLE_SEARCH_API_KEY="your_api_key_here"
    export GOOGLE_SEARCH_ENGINE_ID="your_search_engine_id_here"
    python web_search_agent.py

Available at: http://localhost:3000/

The agent can search for information when users ask questions like:
- "Search for the latest news about AI"
- "Find information about Python programming"
- "Look up the weather in New York"
"""

import os
import requests
import time
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import json
from typing import Optional

from signalwire_agents import AgentBase
from signalwire_agents.core.function_result import SwaigFunctionResult


class GoogleSearchScraper:
    """
    Google Search and Web Scraping functionality
    Extracted and adapted from the standalone google_search_scraper.py
    """
    
    def __init__(self, api_key: str, search_engine_id: str):
        self.api_key = api_key
        self.search_engine_id = search_engine_id
        self.session = requests.Session()
        # Add a user agent to avoid being blocked
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def search_google(self, query: str, num_results: int = 5) -> list:
        """
        Search Google using Custom Search JSON API
        """
        url = "https://www.googleapis.com/customsearch/v1"
        
        params = {
            'key': self.api_key,
            'cx': self.search_engine_id,
            'q': query,
            'num': min(num_results, 10)  # API max is 10 per request
        }
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'items' not in data:
                print(f"No search results found for query: {query}")
                return []
            
            results = []
            for item in data['items'][:num_results]:
                results.append({
                    'title': item.get('title', ''),
                    'url': item.get('link', ''),
                    'snippet': item.get('snippet', '')
                })
            
            return results
            
        except requests.exceptions.RequestException as e:
            print(f"Error making search request: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"Error parsing search response: {e}")
            return []

    def extract_text_from_url(self, url: str, timeout: int = 10) -> str:
        """
        Scrape a URL and extract readable text content
        """
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            
            # Parse HTML content
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            
            # Clean up the text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Limit text length for agent responses
            if len(text) > 2000:
                text = text[:2000] + "... [Content truncated]"
            
            return text
            
        except requests.exceptions.RequestException as e:
            print(f"Error scraping {url}: {e}")
            return ""
        except Exception as e:
            print(f"Error processing {url}: {e}")
            return ""

    def search_and_scrape(self, query: str, num_results: int = 3, delay: float = 1.0) -> str:
        """
        Main function: search Google and scrape the resulting pages
        """
        print(f"Searching for: '{query}' (getting {num_results} results)")
        
        # Get search results
        search_results = self.search_google(query, num_results)
        
        if not search_results:
            return f"No search results found for query: {query}"
        
        print(f"Found {len(search_results)} results to scrape")
        
        all_text = []
        
        for i, result in enumerate(search_results, 1):
            print(f"Processing result {i}/{len(search_results)}: {result['title']}")
            
            # Add result metadata
            text_content = f"=== RESULT {i} ===\n"
            text_content += f"Title: {result['title']}\n"
            text_content += f"URL: {result['url']}\n"
            text_content += f"Snippet: {result['snippet']}\n"
            text_content += f"Content:\n"
            
            # Scrape the page content
            page_text = self.extract_text_from_url(result['url'])
            
            if page_text:
                text_content += page_text
                print(f"Extracted {len(page_text)} characters")
            else:
                text_content += "Failed to extract content from this page."
                print("Failed to extract content")
            
            text_content += f"\n{'='*50}\n\n"
            all_text.append(text_content)
            
            # Be polite to servers
            if i < len(search_results):
                time.sleep(delay)
        
        return '\n'.join(all_text)


class WebSearchAgent(AgentBase):
    """
    An AI agent that can search the web for information and provide results
    """
    
    def __init__(self):
        super().__init__(
            name="Web Search Assistant",
            route="/search",
            auto_answer=True,
            record_call=False
        )
        
        # Get credentials from environment variables
        self.api_key = os.getenv('GOOGLE_SEARCH_API_KEY')
        self.search_engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID')
        
        if not self.api_key or not self.search_engine_id:
            raise ValueError(
                "Missing required environment variables:\n"
                "- GOOGLE_SEARCH_API_KEY\n"
                "- GOOGLE_SEARCH_ENGINE_ID\n"
                "Please set these before running the agent."
            )
        
        # Initialize the search scraper
        self.search_scraper = GoogleSearchScraper(self.api_key, self.search_engine_id)
        
        # Configure agent settings
        self._configure_agent()
    
    def _configure_agent(self):
        """Configure the agent's voice, behavior, and prompts"""
        
        # Voice and language settings
        self.add_language("English", "en-US", "rime.spore:mistv2")
        
        # AI parameters for responsive conversation
        self.set_params({
            "end_of_speech_timeout": 600,
            "attention_timeout": 20000,
            "background_file_volume": -25
        })
        
        # Helpful hints for speech recognition
        self.add_hints([
            "Google", "search", "internet", "web", "information",
            "find", "look up", "research", "query", "results"
        ])
        
        # Global data for context
        self.set_global_data({
            "agent_type": "web_search_assistant",
            "capabilities": ["web_search", "information_retrieval"],
            "search_provider": "Google Custom Search"
        })
        
        # Build the agent's prompt
        self.prompt_add_section(
            "Role and Purpose",
            "You are an intelligent web search assistant. Your primary capability is searching "
            "the internet for current, accurate information on any topic the user requests. "
            "You can help users find news, research topics, get product information, or answer "
            "questions that require up-to-date web content."
        )
        
        self.prompt_add_section(
            "Search Capabilities",
            "When users ask for information, you can:",
            bullets=[
                "Search Google for relevant web pages",
                "Extract and summarize content from multiple sources",
                "Provide URLs for users to explore further",
                "Handle queries on any topic with current web information",
                "Adjust the number of results based on the complexity of the query"
            ]
        )
        
        self.prompt_add_section(
            "Guidelines",
            bullets=[
                "Always use the web_search tool when users ask for information you need to look up",
                "Summarize the search results in a clear, helpful way",
                "Include relevant URLs so users can read more if interested",
                "If search results are limited, mention this and suggest refining the query",
                "For complex topics, consider searching for multiple related queries"
            ]
        )
        
        self.prompt_add_section(
            "Example Interactions",
            bullets=[
                "User: 'What's the latest news about artificial intelligence?' → Use web_search",
                "User: 'Find information about Python programming tutorials' → Use web_search", 
                "User: 'Look up the weather in New York' → Use web_search",
                "User: 'Search for reviews of the iPhone 15' → Use web_search"
            ]
        )

    def perform_web_search(self, query: str, num_results: int = 3) -> str:
        """
        Perform a web search and return formatted results
        
        Args:
            query: The search query
            num_results: Number of results to retrieve and scrape (1-10)
            
        Returns:
            Formatted string with search results
        """
        try:
            # Validate num_results
            num_results = max(1, min(num_results, 10))
            
            print(f"Performing web search for: {query} ({num_results} results)")
            
            # Perform the search and scraping
            results = self.search_scraper.search_and_scrape(
                query=query,
                num_results=num_results,
                delay=0.5  # Shorter delay for agent responses
            )
            
            return results
            
        except Exception as e:
            error_msg = f"Error performing web search: {str(e)}"
            print(error_msg)
            return error_msg

    @AgentBase.tool(
        name="web_search",
        description="Search the web for information on any topic and return detailed results with content from multiple sources",
        parameters={
            "query": {
                "type": "string",
                "description": "The search query - what you want to find information about"
            },
            "num_results": {
                "type": "integer", 
                "description": "Number of web pages to search and extract content from (1-10, default: 3)",
                "minimum": 1,
                "maximum": 10
            }
        }
    )
    def web_search_tool(self, args, raw_data):
        """
        SWAIG function for web searching
        """
        query = args.get("query", "").strip()
        num_results = args.get("num_results", 3)
        
        if not query:
            return SwaigFunctionResult(
                "Please provide a search query. What would you like me to search for?"
            )
        
        # Validate and set defaults
        try:
            num_results = int(num_results)
            num_results = max(1, min(num_results, 10))
        except (ValueError, TypeError):
            num_results = 3
        
        print(f"Web search requested: '{query}' ({num_results} results)")
        
        # Perform the search
        search_results = self.perform_web_search(query, num_results)
        
        if not search_results or "No search results found" in search_results:
            return SwaigFunctionResult(
                f"I couldn't find any results for '{query}'. "
                "This might be due to a very specific query or temporary issues. "
                "Try rephrasing your search or asking about a different topic."
            )
        
        # Format the response for the user
        response = f"I found {num_results} results for '{query}':\n\n{search_results}"
        
        return SwaigFunctionResult(response)


if __name__ == "__main__":
    print("🔍 Starting Web Search Agent")
    print("\nRequired Environment Variables:")
    print("- GOOGLE_SEARCH_API_KEY")
    print("- GOOGLE_SEARCH_ENGINE_ID")
    
    # Check if environment variables are set
    api_key = os.getenv('GOOGLE_SEARCH_API_KEY')
    search_engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID')
    
    if not api_key:
        print("\n❌ ERROR: GOOGLE_SEARCH_API_KEY environment variable not set")
        print("Please set it with: export GOOGLE_SEARCH_API_KEY='your_api_key_here'")
        exit(1)
        
    if not search_engine_id:
        print("\n❌ ERROR: GOOGLE_SEARCH_ENGINE_ID environment variable not set") 
        print("Please set it with: export GOOGLE_SEARCH_ENGINE_ID='your_search_engine_id_here'")
        exit(1)
    
    print(f"\n✅ API Key: {api_key[:10]}...")
    print(f"✅ Search Engine ID: {search_engine_id}")
    
    try:
        agent = WebSearchAgent()
        
        print("\n🤖 Web Search Agent Features:")
        print("- Real-time web search using Google Custom Search API")
        print("- Content extraction from web pages")
        print("- Configurable number of results (1-10)")
        print("- Intelligent summarization of findings")
        
        print(f"\n🌐 Agent available at: http://localhost:3000/search")
        print("\nTry asking the agent:")
        print("- 'Search for the latest AI news'")
        print("- 'Find information about Python programming'")
        print("- 'Look up the weather in New York'")
        print("- 'Search for reviews of electric cars'")
        
        agent.serve(host="0.0.0.0", port=3000)
        
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ Error starting agent: {e}")
        exit(1) 
"""
Copyright (c) 2025 SignalWire

This file is part of the SignalWire AI Agents SDK.

Licensed under the MIT License.
See LICENSE file in the project root for full license information.
"""

import os
import requests
import time
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import json
from typing import Optional, List, Dict, Any

from signalwire_agents.core.skill_base import SkillBase
from signalwire_agents.core.function_result import SwaigFunctionResult

class GoogleSearchScraper:
    """Google Search and Web Scraping functionality"""
    
    def __init__(self, api_key: str, search_engine_id: str):
        self.api_key = api_key
        self.search_engine_id = search_engine_id
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def search_google(self, query: str, num_results: int = 5) -> list:
        """Search Google using Custom Search JSON API"""
        url = "https://www.googleapis.com/customsearch/v1"
        
        params = {
            'key': self.api_key,
            'cx': self.search_engine_id,
            'q': query,
            'num': min(num_results, 10)
        }
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'items' not in data:
                return []
            
            results = []
            for item in data['items'][:num_results]:
                results.append({
                    'title': item.get('title', ''),
                    'url': item.get('link', ''),
                    'snippet': item.get('snippet', '')
                })
            
            return results
            
        except Exception as e:
            return []

    def extract_text_from_url(self, url: str, timeout: int = 10) -> str:
        """Scrape a URL and extract readable text content"""
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove unwanted elements
            for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
                script.decompose()
            
            text = soup.get_text()
            
            # Clean up the text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Limit text length
            if len(text) > 2000:
                text = text[:2000] + "... [Content truncated]"
            
            return text
            
        except Exception as e:
            return ""

    def search_and_scrape(self, query: str, num_results: int = 3, delay: float = 0.5) -> str:
        """Main function: search Google and scrape the resulting pages"""
        search_results = self.search_google(query, num_results)
        
        if not search_results:
            return f"No search results found for query: {query}"
        
        all_text = []
        
        for i, result in enumerate(search_results, 1):
            text_content = f"=== RESULT {i} ===\n"
            text_content += f"Title: {result['title']}\n"
            text_content += f"URL: {result['url']}\n"
            text_content += f"Snippet: {result['snippet']}\n"
            text_content += f"Content:\n"
            
            page_text = self.extract_text_from_url(result['url'])
            
            if page_text:
                text_content += page_text
            else:
                text_content += "Failed to extract content from this page."
            
            text_content += f"\n{'='*50}\n\n"
            all_text.append(text_content)
            
            if i < len(search_results):
                time.sleep(delay)
        
        return '\n'.join(all_text)


class WebSearchSkill(SkillBase):
    """Web search capability using Google Custom Search API"""
    
    SKILL_NAME = "web_search"
    SKILL_DESCRIPTION = "Search the web for information using Google Custom Search API"
    SKILL_VERSION = "1.0.0"
    REQUIRED_PACKAGES = ["bs4", "requests"]
    REQUIRED_ENV_VARS = ["GOOGLE_SEARCH_API_KEY", "GOOGLE_SEARCH_ENGINE_ID"]
    
    def setup(self) -> bool:
        """Setup the web search skill"""
        if not self.validate_env_vars() or not self.validate_packages():
            return False
            
        # Set default parameters
        self.default_num_results = self.params.get('num_results', 1)
        self.default_delay = self.params.get('delay', 0)
        
        # Initialize the search scraper
        self.search_scraper = GoogleSearchScraper(
            api_key=os.getenv('GOOGLE_SEARCH_API_KEY'),
            search_engine_id=os.getenv('GOOGLE_SEARCH_ENGINE_ID')
        )
        
        return True
        
    def register_tools(self) -> None:
        """Register web search tool with the agent"""
        self.agent.define_tool(
            name="web_search",
            description="Search the web for information on any topic and return detailed results with content from multiple sources",
            parameters={
                "query": {
                    "type": "string",
                    "description": "The search query - what you want to find information about"
                },
                "num_results": {
                    "type": "integer", 
                    "description": f"Number of web pages to search and extract content from (1-10, default: {self.default_num_results})",
                    "minimum": 1,
                    "maximum": 10
                }
            },
            handler=self._web_search_handler
        )
        
    def _web_search_handler(self, args, raw_data):
        """Handler for web search tool"""
        query = args.get("query", "").strip()
        num_results = args.get("num_results", self.default_num_results)
        
        if not query:
            return SwaigFunctionResult(
                "Please provide a search query. What would you like me to search for?"
            )
        
        # Validate num_results
        try:
            num_results = int(num_results)
            num_results = max(1, min(num_results, 10))
        except (ValueError, TypeError):
            num_results = self.default_num_results
        
        self.logger.info(f"Web search requested: '{query}' ({num_results} results)")
        
        # Perform the search
        try:
            search_results = self.search_scraper.search_and_scrape(
                query=query,
                num_results=num_results,
                delay=self.default_delay
            )
            
            if not search_results or "No search results found" in search_results:
                return SwaigFunctionResult(
                    f"I couldn't find any results for '{query}'. "
                    "This might be due to a very specific query or temporary issues. "
                    "Try rephrasing your search or asking about a different topic."
                )
            
            response = f"I found {num_results} results for '{query}':\n\n{search_results}"
            return SwaigFunctionResult(response)
            
        except Exception as e:
            self.logger.error(f"Error performing web search: {e}")
            return SwaigFunctionResult(
                "Sorry, I encountered an error while searching. Please try again later."
            )
        
    def get_hints(self) -> List[str]:
        """Return speech recognition hints"""
        return [
            "Google", "search", "internet", "web", "information",
            "find", "look up", "research", "query", "results"
        ]
        
    def get_global_data(self) -> Dict[str, Any]:
        """Return global data for agent context"""
        return {
            "web_search_enabled": True,
            "search_provider": "Google Custom Search"
        }
        
    def get_prompt_sections(self) -> List[Dict[str, Any]]:
        """Return prompt sections to add to agent"""
        return [
            {
                "title": "Web Search Capability",
                "body": "You can search the internet for current, accurate information on any topic.",
                "bullets": [
                    "Use the web_search tool when users ask for information you need to look up",
                    "Search for news, current events, product information, or any current data",
                    "Summarize search results in a clear, helpful way",
                    "Include relevant URLs so users can read more if interested"
                ]
            }
        ] 
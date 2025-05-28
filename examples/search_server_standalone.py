#!/usr/bin/env python3
"""
Standalone Search Server Example

This example shows how to run the SignalWire search service as a standalone
HTTP server that can be accessed by multiple agents or external applications.

Features:
- HTTP API with FastAPI
- Multiple search indexes support
- Health check endpoint
- Dynamic index reloading
- RESTful search interface
- Auto-builds index from concepts guide

Usage:
1. Run the standalone server:
   python examples/search_server_standalone.py

2. Test the API:
   curl -X POST "http://localhost:8001/search" \
        -H "Content-Type: application/json" \
        -d '{"query": "how to create an agent", "index_name": "concepts", "count": 3}'

The server will automatically build a search index from the concepts guide file
(docs/signalwire_agents_concepts_guide.md) if it doesn't already exist.

The server will be available at http://localhost:8001 with the following endpoints:
- POST /search - Search the indexes
- GET /health - Health check and available indexes
- POST /reload_index - Add or reload an index
"""

import os
import sys
import logging
from pathlib import Path

# Add the parent directory to the path so we can import the package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Run the standalone search server"""
    
    # Check if search dependencies are available
    try:
        from signalwire_agents.search import SearchService, IndexBuilder
        logger.info("Search dependencies are available")
    except ImportError as e:
        logger.error("Search dependencies not available")
        logger.error("Install with: pip install signalwire-agents[search-full]")
        logger.error(f"Error: {e}")
        return
    
    # Get the project root directory
    project_root = Path(__file__).parent.parent
    
    # Define the concepts guide file and index
    concepts_guide_file = project_root / "docs" / "signalwire_agents_concepts_guide.md"
    concepts_index_file = project_root / "concepts_guide.swsearch"
    
    # Check if the concepts guide file exists
    if not concepts_guide_file.exists():
        logger.error(f"Concepts guide file not found: {concepts_guide_file}")
        logger.error("Please ensure the concepts guide file exists before running the server")
        return
    
    # Build index if it doesn't exist
    if not concepts_index_file.exists():
        logger.info(f"Building search index from concepts guide: {concepts_guide_file}")
        try:
            builder = IndexBuilder(
                chunking_strategy='sentence',
                max_sentences_per_chunk=50,
                verbose=True
            )
            
            # Use the new multiple sources functionality to build from the specific file
            builder.build_index_from_sources(
                sources=[concepts_guide_file],
                output_file=str(concepts_index_file),
                file_types=['md'],
                exclude_patterns=None,
                languages=['en'],
                tags=['concepts', 'guide', 'sdk']
            )
            
            logger.info(f"Successfully built concepts guide search index: {concepts_index_file}")
            
        except Exception as e:
            logger.error(f"Failed to build search index: {e}")
            return
    else:
        logger.info(f"Using existing concepts guide search index: {concepts_index_file}")
    
    # Define available indexes
    indexes = {
        "concepts": str(concepts_index_file)
    }
    
    # Check for any other .swsearch files in the project root
    for swsearch_file in project_root.glob("*.swsearch"):
        if swsearch_file.name != "concepts_guide.swsearch":
            index_name = swsearch_file.stem
            indexes[index_name] = str(swsearch_file)
            logger.info(f"Found additional index: {index_name} -> {swsearch_file}")
    
    # Create and start the search service
    logger.info(f"Starting search server with {len(indexes)} indexes:")
    for name, path in indexes.items():
        logger.info(f"  {name}: {path}")
    
    try:
        service = SearchService(port=8001, indexes=indexes)
        logger.info("Search server starting on http://localhost:8001")
        logger.info("Available endpoints:")
        logger.info("  POST /search - Search the indexes")
        logger.info("  GET /health - Health check and available indexes")
        logger.info("  POST /reload_index - Add or reload an index")
        logger.info("")
        logger.info("Example search request:")
        logger.info('  curl -X POST "http://localhost:8001/search" \\')
        logger.info('       -H "Content-Type: application/json" \\')
        logger.info('       -d \'{"query": "how to create an agent", "index_name": "concepts", "count": 3}\'')
        logger.info("")
        logger.info("Press Ctrl+C to stop the server")
        
        service.start()
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        logger.error("Make sure you have installed: pip install signalwire-agents[search-full]")

if __name__ == "__main__":
    main() 
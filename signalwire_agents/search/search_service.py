"""
Copyright (c) 2025 SignalWire

This file is part of the SignalWire AI Agents SDK.

Licensed under the MIT License.
See LICENSE file in the project root for full license information.
"""

import logging
from typing import Dict, Any, List, Optional

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
except ImportError:
    FastAPI = None
    HTTPException = None
    BaseModel = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

from .query_processor import preprocess_query
from .search_engine import SearchEngine

logger = logging.getLogger(__name__)

# Pydantic models for API
if BaseModel:
    class SearchRequest(BaseModel):
        query: str
        index_name: str = "default"
        count: int = 3
        distance: float = 0.0
        tags: Optional[List[str]] = None
        language: Optional[str] = None

    class SearchResult(BaseModel):
        content: str
        score: float
        metadata: Dict[str, Any]

    class SearchResponse(BaseModel):
        results: List[SearchResult]
        query_analysis: Optional[Dict[str, Any]] = None
else:
    # Fallback classes when FastAPI is not available
    class SearchRequest:
        def __init__(self, query: str, index_name: str = "default", count: int = 3, 
                     distance: float = 0.0, tags: Optional[List[str]] = None, 
                     language: Optional[str] = None):
            self.query = query
            self.index_name = index_name
            self.count = count
            self.distance = distance
            self.tags = tags
            self.language = language

    class SearchResult:
        def __init__(self, content: str, score: float, metadata: Dict[str, Any]):
            self.content = content
            self.score = score
            self.metadata = metadata

    class SearchResponse:
        def __init__(self, results: List[SearchResult], query_analysis: Optional[Dict[str, Any]] = None):
            self.results = results
            self.query_analysis = query_analysis

class SearchService:
    """Local search service with HTTP API"""
    
    def __init__(self, port: int = 8001, indexes: Dict[str, str] = None):
        self.port = port
        self.indexes = indexes or {}
        self.search_engines = {}
        self.model = None
        
        if FastAPI:
            self.app = FastAPI(title="SignalWire Local Search Service")
            self._setup_routes()
        else:
            self.app = None
            logger.warning("FastAPI not available. HTTP service will not be available.")
        
        self._load_resources()
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        if not self.app:
            return
            
        @self.app.post("/search", response_model=SearchResponse)
        async def search(request: SearchRequest):
            return await self._handle_search(request)
        
        @self.app.get("/health")
        async def health():
            return {"status": "healthy", "indexes": list(self.indexes.keys())}
        
        @self.app.post("/reload_index")
        async def reload_index(index_name: str, index_path: str):
            """Reload or add new index"""
            self.indexes[index_name] = index_path
            self.search_engines[index_name] = SearchEngine(index_path, self.model)
            return {"status": "reloaded", "index": index_name}
    
    def _load_resources(self):
        """Load embedding model and search indexes"""
        # Load model (shared across all indexes)
        if self.indexes and SentenceTransformer:
            # Get model name from first index
            sample_index = next(iter(self.indexes.values()))
            model_name = self._get_model_name(sample_index)
            try:
                self.model = SentenceTransformer(model_name)
            except Exception as e:
                logger.warning(f"Could not load sentence transformer model: {e}")
                self.model = None
        
        # Load search engines for each index
        for index_name, index_path in self.indexes.items():
            try:
                self.search_engines[index_name] = SearchEngine(index_path, self.model)
            except Exception as e:
                logger.error(f"Error loading search engine for {index_name}: {e}")
    
    def _get_model_name(self, index_path: str) -> str:
        """Get embedding model name from index config"""
        try:
            import sqlite3
            conn = sqlite3.connect(index_path)
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM config WHERE key = 'embedding_model'")
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else 'sentence-transformers/all-mpnet-base-v2'
        except Exception as e:
            logger.warning(f"Could not get model name from index: {e}")
            return 'sentence-transformers/all-mpnet-base-v2'
    
    async def _handle_search(self, request: SearchRequest) -> SearchResponse:
        """Handle search request"""
        if request.index_name not in self.search_engines:
            if HTTPException:
                raise HTTPException(status_code=404, detail=f"Index '{request.index_name}' not found")
            else:
                raise ValueError(f"Index '{request.index_name}' not found")
        
        search_engine = self.search_engines[request.index_name]
        
        # Enhance query
        try:
            enhanced = preprocess_query(
                request.query,
                language=request.language or 'auto',
                vector=True
            )
        except Exception as e:
            logger.error(f"Error preprocessing query: {e}")
            enhanced = {
                'enhanced_text': request.query,
                'vector': [],
                'language': 'en'
            }
        
        # Perform search
        try:
            results = search_engine.search(
                query_vector=enhanced.get('vector', []),
                enhanced_text=enhanced['enhanced_text'],
                count=request.count,
                distance_threshold=request.distance,
                tags=request.tags
            )
        except Exception as e:
            logger.error(f"Error performing search: {e}")
            results = []
        
        # Format response
        search_results = [
            SearchResult(
                content=result['content'],
                score=result['score'],
                metadata=result['metadata']
            )
            for result in results
        ]
        
        return SearchResponse(
            results=search_results,
            query_analysis={
                'original_query': request.query,
                'enhanced_query': enhanced['enhanced_text'],
                'detected_language': enhanced.get('language'),
                'pos_analysis': enhanced.get('POS')
            }
        )
    
    def search_direct(self, query: str, index_name: str = "default", count: int = 3, 
                     distance: float = 0.0, tags: Optional[List[str]] = None, 
                     language: Optional[str] = None) -> Dict[str, Any]:
        """Direct search method (non-async) for programmatic use"""
        request = SearchRequest(
            query=query,
            index_name=index_name,
            count=count,
            distance=distance,
            tags=tags,
            language=language
        )
        
        # Use asyncio to run the async method
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        response = loop.run_until_complete(self._handle_search(request))
        
        return {
            'results': [
                {
                    'content': r.content,
                    'score': r.score,
                    'metadata': r.metadata
                }
                for r in response.results
            ],
            'query_analysis': response.query_analysis
        }
    
    def start(self):
        """Start the service"""
        if not self.app:
            raise RuntimeError("FastAPI not available. Cannot start HTTP service.")
        
        try:
            import uvicorn
            uvicorn.run(self.app, host="0.0.0.0", port=self.port)
        except ImportError:
            raise RuntimeError("uvicorn not available. Cannot start HTTP service.")
    
    def stop(self):
        """Stop the service (placeholder for cleanup)"""
        pass 
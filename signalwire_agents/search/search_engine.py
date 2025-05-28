"""
Copyright (c) 2025 SignalWire

This file is part of the SignalWire AI Agents SDK.

Licensed under the MIT License.
See LICENSE file in the project root for full license information.
"""

import sqlite3
import json
import logging
from typing import List, Dict, Any, Optional, Union

try:
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
    NDArray = np.ndarray
except ImportError:
    np = None
    cosine_similarity = None
    NDArray = Any  # Fallback type for when numpy is not available

logger = logging.getLogger(__name__)

class SearchEngine:
    """Hybrid search engine for vector and keyword search"""
    
    def __init__(self, index_path: str, model=None):
        self.index_path = index_path
        self.model = model
        self.config = self._load_config()
        self.embedding_dim = int(self.config.get('embedding_dimensions', 768))
    
    def _load_config(self) -> Dict[str, str]:
        """Load index configuration"""
        try:
            conn = sqlite3.connect(self.index_path)
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM config")
            config = dict(cursor.fetchall())
            conn.close()
            return config
        except Exception as e:
            logger.error(f"Error loading config from {self.index_path}: {e}")
            return {}
    
    def search(self, query_vector: List[float], enhanced_text: str, 
              count: int = 3, distance_threshold: float = 0.0,
              tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Perform hybrid search (vector + keyword)
        
        Args:
            query_vector: Embedding vector for the query
            enhanced_text: Processed query text for keyword search
            count: Number of results to return
            distance_threshold: Minimum similarity score
            tags: Filter by tags
            
        Returns:
            List of search results with scores and metadata
        """
        
        if not np or not cosine_similarity:
            logger.warning("NumPy or scikit-learn not available. Using keyword search only.")
            return self._keyword_search_only(enhanced_text, count, tags)
        
        # Convert query vector to numpy array
        try:
            query_array = np.array(query_vector).reshape(1, -1)
        except Exception as e:
            logger.error(f"Error converting query vector: {e}")
            return self._keyword_search_only(enhanced_text, count, tags)
        
        # Vector search
        vector_results = self._vector_search(query_array, count * 2)
        
        # Keyword search
        keyword_results = self._keyword_search(enhanced_text, count * 2)
        
        # Merge and rank results
        merged_results = self._merge_results(vector_results, keyword_results)
        
        # Filter by tags if specified
        if tags:
            merged_results = self._filter_by_tags(merged_results, tags)
        
        # Filter by distance threshold
        filtered_results = [
            r for r in merged_results 
            if r['score'] >= distance_threshold
        ]
        
        return filtered_results[:count]
    
    def _keyword_search_only(self, enhanced_text: str, count: int, 
                           tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Fallback to keyword search only when vector search is unavailable"""
        keyword_results = self._keyword_search(enhanced_text, count)
        
        if tags:
            keyword_results = self._filter_by_tags(keyword_results, tags)
        
        return keyword_results[:count]
    
    def _vector_search(self, query_vector: Union[NDArray, Any], count: int) -> List[Dict[str, Any]]:
        """Perform vector similarity search"""
        if not np or not cosine_similarity:
            return []
            
        try:
            conn = sqlite3.connect(self.index_path)
            cursor = conn.cursor()
            
            # Get all embeddings (for small datasets, this is fine)
            # For large datasets, we'd use FAISS or similar
            cursor.execute('''
                SELECT id, content, embedding, filename, section, tags, metadata
                FROM chunks
                WHERE embedding IS NOT NULL AND embedding != ''
            ''')
            
            results = []
            for row in cursor.fetchall():
                chunk_id, content, embedding_blob, filename, section, tags_json, metadata_json = row
                
                if not embedding_blob:
                    continue
                
                try:
                    # Convert embedding back to numpy array
                    embedding = np.frombuffer(embedding_blob, dtype=np.float32).reshape(1, -1)
                    
                    # Calculate similarity
                    similarity = cosine_similarity(query_vector, embedding)[0][0]
                    
                    results.append({
                        'id': chunk_id,
                        'content': content,
                        'score': float(similarity),
                        'metadata': {
                            'filename': filename,
                            'section': section,
                            'tags': json.loads(tags_json) if tags_json else [],
                            'metadata': json.loads(metadata_json) if metadata_json else {}
                        },
                        'search_type': 'vector'
                    })
                except Exception as e:
                    logger.warning(f"Error processing embedding for chunk {chunk_id}: {e}")
                    continue
            
            conn.close()
            
            # Sort by similarity score
            results.sort(key=lambda x: x['score'], reverse=True)
            return results[:count]
            
        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            return []
    
    def _keyword_search(self, enhanced_text: str, count: int) -> List[Dict[str, Any]]:
        """Perform full-text search"""
        try:
            conn = sqlite3.connect(self.index_path)
            cursor = conn.cursor()
            
            # Escape FTS5 special characters
            escaped_text = self._escape_fts_query(enhanced_text)
            
            # FTS5 search
            cursor.execute('''
                SELECT c.id, c.content, c.filename, c.section, c.tags, c.metadata,
                       chunks_fts.rank
                FROM chunks_fts
                JOIN chunks c ON chunks_fts.rowid = c.id
                WHERE chunks_fts MATCH ?
                ORDER BY chunks_fts.rank
                LIMIT ?
            ''', (escaped_text, count))
            
            results = []
            for row in cursor.fetchall():
                chunk_id, content, filename, section, tags_json, metadata_json, rank = row
                
                # Convert FTS rank to similarity score (higher rank = lower score)
                # FTS5 rank is negative, so we convert it to a positive similarity score
                score = 1.0 / (1.0 + abs(rank))
                
                results.append({
                    'id': chunk_id,
                    'content': content,
                    'score': float(score),
                    'metadata': {
                        'filename': filename,
                        'section': section,
                        'tags': json.loads(tags_json) if tags_json else [],
                        'metadata': json.loads(metadata_json) if metadata_json else {}
                    },
                    'search_type': 'keyword'
                })
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Error in keyword search: {e}")
            # Fallback to simple LIKE search
            return self._fallback_search(enhanced_text, count)
    
    def _escape_fts_query(self, query: str) -> str:
        """Escape special characters for FTS5 queries"""
        # FTS5 special characters that need escaping
        special_chars = ['"', "'", '(', ')', '*', '-', '+', ':', '^']
        
        escaped = query
        for char in special_chars:
            escaped = escaped.replace(char, f'\\{char}')
        
        return escaped
    
    def _fallback_search(self, enhanced_text: str, count: int) -> List[Dict[str, Any]]:
        """Fallback search using LIKE when FTS fails"""
        try:
            conn = sqlite3.connect(self.index_path)
            cursor = conn.cursor()
            
            # Simple LIKE search
            search_terms = enhanced_text.lower().split()
            like_conditions = []
            params = []
            
            for term in search_terms[:5]:  # Limit to 5 terms to avoid too complex queries
                like_conditions.append("LOWER(processed_content) LIKE ?")
                params.append(f"%{term}%")
            
            if not like_conditions:
                return []
            
            query = f'''
                SELECT id, content, filename, section, tags, metadata
                FROM chunks
                WHERE {" OR ".join(like_conditions)}
                LIMIT ?
            '''
            params.append(count)
            
            cursor.execute(query, params)
            
            results = []
            for row in cursor.fetchall():
                chunk_id, content, filename, section, tags_json, metadata_json = row
                
                # Simple scoring based on term matches
                content_lower = content.lower()
                score = sum(1 for term in search_terms if term.lower() in content_lower) / len(search_terms)
                
                results.append({
                    'id': chunk_id,
                    'content': content,
                    'score': float(score),
                    'metadata': {
                        'filename': filename,
                        'section': section,
                        'tags': json.loads(tags_json) if tags_json else [],
                        'metadata': json.loads(metadata_json) if metadata_json else {}
                    },
                    'search_type': 'fallback'
                })
            
            conn.close()
            
            # Sort by score
            results.sort(key=lambda x: x['score'], reverse=True)
            return results
            
        except Exception as e:
            logger.error(f"Error in fallback search: {e}")
            return []
    
    def _merge_results(self, vector_results: List[Dict], keyword_results: List[Dict]) -> List[Dict[str, Any]]:
        """Merge and rank vector and keyword search results"""
        # Create a combined list with weighted scores
        combined = {}
        
        # Add vector results with weight
        for result in vector_results:
            chunk_id = result['id']
            combined[chunk_id] = result.copy()
            combined[chunk_id]['vector_score'] = result['score']
            combined[chunk_id]['keyword_score'] = 0.0
        
        # Add keyword results with weight
        for result in keyword_results:
            chunk_id = result['id']
            if chunk_id in combined:
                combined[chunk_id]['keyword_score'] = result['score']
            else:
                combined[chunk_id] = result.copy()
                combined[chunk_id]['vector_score'] = 0.0
                combined[chunk_id]['keyword_score'] = result['score']
        
        # Calculate combined score (weighted average)
        vector_weight = 0.7
        keyword_weight = 0.3
        
        for chunk_id, result in combined.items():
            vector_score = result.get('vector_score', 0.0)
            keyword_score = result.get('keyword_score', 0.0)
            result['score'] = (vector_score * vector_weight + keyword_score * keyword_weight)
            
            # Add debug info
            result['metadata']['search_scores'] = {
                'vector': vector_score,
                'keyword': keyword_score,
                'combined': result['score']
            }
        
        # Sort by combined score
        sorted_results = sorted(combined.values(), key=lambda x: x['score'], reverse=True)
        return sorted_results
    
    def _filter_by_tags(self, results: List[Dict], required_tags: List[str]) -> List[Dict[str, Any]]:
        """Filter results by required tags"""
        filtered = []
        for result in results:
            result_tags = result['metadata'].get('tags', [])
            if any(tag in result_tags for tag in required_tags):
                filtered.append(result)
        return filtered
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the search index"""
        conn = sqlite3.connect(self.index_path)
        cursor = conn.cursor()
        
        try:
            # Get total chunks
            cursor.execute("SELECT COUNT(*) FROM chunks")
            total_chunks = cursor.fetchone()[0]
            
            # Get total files
            cursor.execute("SELECT COUNT(DISTINCT filename) FROM chunks")
            total_files = cursor.fetchone()[0]
            
            # Get average chunk size
            cursor.execute("SELECT AVG(LENGTH(content)) FROM chunks")
            avg_chunk_size = cursor.fetchone()[0] or 0
            
            # Get file types
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN filename LIKE '%.md' THEN 'markdown'
                        WHEN filename LIKE '%.py' THEN 'python'
                        WHEN filename LIKE '%.txt' THEN 'text'
                        WHEN filename LIKE '%.pdf' THEN 'pdf'
                        WHEN filename LIKE '%.docx' THEN 'docx'
                        ELSE 'other'
                    END as file_type,
                    COUNT(DISTINCT filename) as count
                FROM chunks 
                GROUP BY file_type
            """)
            file_types = dict(cursor.fetchall())
            
            # Get languages
            cursor.execute("SELECT language, COUNT(*) FROM chunks GROUP BY language")
            languages = dict(cursor.fetchall())
            
            return {
                'total_chunks': total_chunks,
                'total_files': total_files,
                'avg_chunk_size': int(avg_chunk_size),
                'file_types': file_types,
                'languages': languages,
                'config': self.config
            }
            
        finally:
            conn.close() 
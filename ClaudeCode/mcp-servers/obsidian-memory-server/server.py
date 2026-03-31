#!/usr/bin/env python3
"""
MCP Server for Obsidian Memory

This server exposes Obsidian Vault operations as MCP tools for Claude Code.
"""

import os
import sys
import json
from pathlib import Path
from typing import Any, Dict, List

# Add shared module to path
SHARED_PATH = Path(__file__).parent.parent.parent.parent.parent / 'shared'
if str(SHARED_PATH) not in sys.path:
    sys.path.insert(0, str(SHARED_PATH))

from obsidian_memory import ObsidianMemory, get_memory


class ObsidianMemoryMCPServer:
    """MCP Server for Obsidian Memory operations."""
    
    def __init__(self):
        self.memory = get_memory('claude')
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an MCP request."""
        method = request.get('method')
        params = request.get('params', {})
        
        if method == 'store':
            return self._handle_store(params)
        elif method == 'search':
            return self._handle_search(params)
        elif method == 'query':
            return self._handle_query(params)
        elif method == 'history':
            return self._handle_history(params)
        elif method == 'stats':
            return self._handle_stats(params)
        else:
            return {'error': f'Unknown method: {method}'}
    
    def _handle_store(self, params: Dict) -> Dict:
        """Store content in vault."""
        content = params.get('content', '')
        tags = params.get('tags', [])
        metadata = params.get('metadata', {})
        
        try:
            entry = self.memory.store(
                content=content,
                tags=tags,
                metadata=metadata
            )
            return {
                'success': True,
                'id': entry.id,
                'source': entry.source,
                'timestamp': entry.timestamp
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _handle_search(self, params: Dict) -> Dict:
        """Search vault with pattern."""
        pattern = params.get('pattern', '')
        limit = params.get('limit', 5)
        
        try:
            matches = self.memory.search(pattern)
            results = [
                {
                    'path': path,
                    'excerpt': excerpt[:300]  # Limit excerpt length
                }
                for path, excerpt in matches[:limit]
            ]
            return {'success': True, 'results': results, 'total': len(matches)}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _handle_query(self, params: Dict) -> Dict:
        """Query vault for relevant entries."""
        query_text = params.get('query', '')
        n_results = params.get('n_results', 5)
        
        try:
            entries = self.memory.query(query_text, n_results)
            results = [
                {
                    'id': e.id,
                    'source': e.source,
                    'content': e.content[:500],
                    'timestamp': e.timestamp,
                    'tags': e.tags
                }
                for e in entries
            ]
            return {'success': True, 'results': results}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _handle_history(self, params: Dict) -> Dict:
        """Get conversation history."""
        limit = params.get('limit', 10)
        
        try:
            entries = self.memory.get_conversation_history(limit=limit)
            results = [
                {
                    'id': e.id,
                    'source': e.source,
                    'content': e.content[:500],
                    'timestamp': e.timestamp
                }
                for e in entries
            ]
            return {'success': True, 'results': results}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _handle_stats(self, params: Dict) -> Dict:
        """Get memory statistics."""
        try:
            stats = self.memory.get_stats()
            return {'success': True, 'stats': stats}
        except Exception as e:
            return {'success': False, 'error': str(e)}


def main():
    """Main entry point for MCP server."""
    server = ObsidianMemoryMCPServer()
    
    # Read requests from stdin (MCP protocol)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        
        try:
            request = json.loads(line)
            response = server.handle_request(request)
            print(json.dumps(response), flush=True)
        except json.JSONDecodeError as e:
            print(json.dumps({'error': f'Invalid JSON: {e}'}), flush=True)
        except Exception as e:
            print(json.dumps({'error': str(e)}), flush=True)


if __name__ == '__main__':
    main()

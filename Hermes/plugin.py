"""
Hermes Obsidian Memory Plugin

Enables Hermes Agent to use Obsidian Vault as persistent memory.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any

# Add shared module to path
SHARED_PATH = Path(__file__).parent.parent / 'shared'
if str(SHARED_PATH) not in sys.path:
    sys.path.insert(0, str(SHARED_PATH))

from obsidian_memory import ObsidianMemory, get_memory


class HermesMemoryPlugin:
    """
    Hermes plugin for Obsidian Vault memory.
    
    Provides:
    - Store session notes and decisions
    - Search vault for context
    - Retrieve relevant past conversations
    - Query for project knowledge
    """
    
    def __init__(self, vault_path: Optional[str] = None):
        self.memory = get_memory('hermes', vault_path)
    
    def remember(self, content: str, tags: List[str] = None, 
                 metadata: Dict[str, Any] = None) -> str:
        """
        Store a memory in the vault.
        
        Args:
            content: Content to remember
            tags: Optional tags
            metadata: Optional metadata dict
        
        Returns:
            Memory entry ID
        """
        entry = self.memory.store(
            content=content,
            tags=tags or [],
            metadata=metadata
        )
        return entry.id
    
    def recall(self, query: str, n_results: int = 5) -> List[Dict]:
        """
        Recall relevant memories from vault.
        
        Args:
            query: Search query
            n_results: Number of results
        
        Returns:
            List of memory entries as dicts
        """
        entries = self.memory.query(query, n_results)
        return [e.to_dict() for e in entries]
    
    def search(self, pattern: str, limit: int = 10) -> List[Dict]:
        """
        Search vault with regex pattern.
        
        Args:
            pattern: Regex pattern
            limit: Max results
        
        Returns:
            List of matches
        """
        matches = self.memory.search(pattern)
        return [
            {'path': path, 'excerpt': excerpt[:300]}
            for path, excerpt in matches[:limit]
        ]
    
    def get_recent(self, limit: int = 10) -> List[Dict]:
        """Get recent conversation history."""
        entries = self.memory.get_conversation_history(limit=limit)
        return [e.to_dict() for e in entries]
    
    def stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return self.memory.get_stats()


def main():
    """CLI for testing the plugin."""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description='Hermes Obsidian Memory Plugin')
    parser.add_argument('--vault', help='Obsidian vault path')
    
    subparsers = parser.add_subparsers(dest='command', help='Command')
    
    # Remember
    remember_parser = subparsers.add_parser('remember', help='Store a memory')
    remember_parser.add_argument('content', help='Content to store')
    remember_parser.add_argument('--tags', nargs='+', help='Tags')
    
    # Recall
    recall_parser = subparsers.add_parser('recall', help='Recall memories')
    recall_parser.add_argument('query', help='Search query')
    recall_parser.add_argument('-n', type=int, default=5, help='Number of results')
    
    # Search
    search_parser = subparsers.add_parser('search', help='Search vault')
    search_parser.add_argument('pattern', help='Regex pattern')
    search_parser.add_argument('--limit', type=int, default=10)
    
    # Recent
    subparsers.add_parser('recent', help='Get recent history')
    
    # Stats
    subparsers.add_parser('stats', help='Get statistics')
    
    args = parser.parse_args()
    
    plugin = HermesMemoryPlugin(args.vault)
    
    if args.command == 'remember':
        entry_id = plugin.remember(args.content, args.tags)
        print(f"Stored with ID: {entry_id}")
    
    elif args.command == 'recall':
        results = plugin.recall(args.query, args.n)
        print(json.dumps(results, indent=2))
    
    elif args.command == 'search':
        results = plugin.search(args.pattern, args.limit)
        print(json.dumps(results, indent=2))
    
    elif args.command == 'recent':
        results = plugin.get_recent()
        print(json.dumps(results, indent=2))
    
    elif args.command == 'stats':
        stats = plugin.stats()
        print(json.dumps(stats, indent=2))
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

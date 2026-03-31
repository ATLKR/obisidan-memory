#!/usr/bin/env python3
"""Query Obsidian Vault for relevant entries."""

import argparse
import sys
from pathlib import Path

# Add shared module to path
SHARED_PATH = Path(__file__).parent.parent.parent.parent.parent.parent / 'shared'
if str(SHARED_PATH) not in sys.path:
    sys.path.insert(0, str(SHARED_PATH))

from obsidian_memory import get_memory


def main():
    parser = argparse.ArgumentParser(description='Query Obsidian Vault')
    parser.add_argument('query', help='Query text')
    parser.add_argument('-n', type=int, default=5, help='Number of results')
    
    args = parser.parse_args()
    
    memory = get_memory('codex')
    
    try:
        entries = memory.query(args.query, n_results=args.n)
        
        if not entries:
            print("No relevant entries found.")
            return
        
        print(f"Found {len(entries)} relevant entries:\n")
        
        for i, entry in enumerate(entries, 1):
            print(f"{i}. [{entry.agent}] {entry.source}")
            print(f"   Content: {entry.content[:300]}...")
            if entry.tags:
                print(f"   Tags: {', '.join(entry.tags)}")
            print()
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

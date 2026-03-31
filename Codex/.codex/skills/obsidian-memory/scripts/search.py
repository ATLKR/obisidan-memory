#!/usr/bin/env python3
"""Search Obsidian Vault."""

import argparse
import sys
from pathlib import Path

# Add shared module to path
SHARED_PATH = Path(__file__).parent.parent.parent.parent.parent.parent / 'shared'
if str(SHARED_PATH) not in sys.path:
    sys.path.insert(0, str(SHARED_PATH))

from obsidian_memory import get_memory


def main():
    parser = argparse.ArgumentParser(description='Search Obsidian Vault')
    parser.add_argument('pattern', help='Search pattern (regex)')
    parser.add_argument('--limit', type=int, default=5, help='Maximum results')
    
    args = parser.parse_args()
    
    memory = get_memory('codex')
    
    try:
        matches = memory.search(args.pattern)
        
        if not matches:
            print("No matches found.")
            return
        
        print(f"Found {len(matches)} matches:\n")
        
        for i, (path, excerpt) in enumerate(matches[:args.limit], 1):
            print(f"{i}. {path}")
            print(f"   {excerpt[:200]}...")
            print()
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

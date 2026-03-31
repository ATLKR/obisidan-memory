#!/usr/bin/env python3
"""Get conversation history from Obsidian Vault."""

import argparse
import sys
from pathlib import Path

# Add shared module to path
SHARED_PATH = Path(__file__).parent.parent.parent.parent.parent.parent / 'shared'
if str(SHARED_PATH) not in sys.path:
    sys.path.insert(0, str(SHARED_PATH))

from obsidian_memory import get_memory


def main():
    parser = argparse.ArgumentParser(description='Get conversation history')
    parser.add_argument('--limit', type=int, default=10, help='Number of entries')
    
    args = parser.parse_args()
    
    memory = get_memory('codex')
    
    try:
        entries = memory.get_conversation_history(limit=args.limit)
        
        if not entries:
            print("No history found.")
            return
        
        print(f"Recent {len(entries)} entries:\n")
        
        for i, entry in enumerate(entries, 1):
            print(f"{i}. {entry.timestamp[:10]} - {entry.source}")
            content_preview = entry.content[:200].replace('\n', ' ')
            print(f"   {content_preview}...")
            print()
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

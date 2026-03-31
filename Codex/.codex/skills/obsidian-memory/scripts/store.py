#!/usr/bin/env python3
"""Store content in Obsidian Vault."""

import argparse
import sys
from pathlib import Path

# Add shared module to path
# Navigate from Codex/.codex/skills/obsidian-memory/scripts/ to repo root
SHARED_PATH = Path(__file__).parent.parent.parent.parent.parent.parent / 'shared'
if str(SHARED_PATH) not in sys.path:
    sys.path.insert(0, str(SHARED_PATH))

from obsidian_memory import get_memory


def main():
    parser = argparse.ArgumentParser(description='Store memory in Obsidian Vault')
    parser.add_argument('content', help='Content to store')
    parser.add_argument('--tags', nargs='+', help='Tags for categorization')
    parser.add_argument('--metadata', type=str, help='JSON metadata string')
    
    args = parser.parse_args()
    
    memory = get_memory('codex')
    
    metadata = {}
    if args.metadata:
        import json
        metadata = json.loads(args.metadata)
    
    try:
        entry = memory.store(
            content=args.content,
            tags=args.tags or [],
            metadata=metadata
        )
        print(f"Stored: {entry.source}")
        print(f"ID: {entry.id}")
        print(f"Timestamp: {entry.timestamp}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

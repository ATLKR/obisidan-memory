#!/usr/bin/env python3
"""
UserPromptSubmit Hook - Enrich prompts with Obsidian context

This hook runs when a user submits a prompt and:
1. Searches vault for relevant context
2. Appends relevant information to the prompt
"""

import json
import sys
from pathlib import Path

# Add shared module to path
SHARED_PATH = Path(__file__).parent.parent.parent.parent.parent.parent.parent / 'shared'
if str(SHARED_PATH) not in sys.path:
    sys.path.insert(0, str(SHARED_PATH))

from obsidian_memory import get_memory


def main():
    # Read hook input
    try:
        hook_input = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        hook_input = {}
    
    user_prompt = hook_input.get('prompt', '')
    
    # Skip for short prompts or commands
    if len(user_prompt) < 10 or user_prompt.startswith('/') or user_prompt.startswith('$'):
        print(json.dumps({"prompt": user_prompt}))
        return
    
    # Get memory instance
    memory = get_memory('codex')
    
    # Search for relevant context
    relevant_entries = memory.query(user_prompt, n_results=3)
    
    if not relevant_entries:
        print(json.dumps({"prompt": user_prompt}))
        return
    
    # Build context enrichment
    context_lines = ["\n\n### Relevant Context from Obsidian Vault\n"]
    
    for entry in relevant_entries:
        context_lines.append(f"**From [{entry.source}] ({entry.agent}):**")
        content_preview = entry.content[:300].replace('\n', ' ')
        context_lines.append(f"> {content_preview}...")
        if entry.tags:
            context_lines.append(f"> Tags: {', '.join(entry.tags)}")
        context_lines.append("")
    
    enriched_prompt = user_prompt + '\n'.join(context_lines)
    
    output = {
        "prompt": enriched_prompt
    }
    
    print(json.dumps(output))


if __name__ == '__main__':
    main()

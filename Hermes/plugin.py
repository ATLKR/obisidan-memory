"""
Hermes Obsidian Memory Plugin

Provides persistent memory for Hermes Agent using Obsidian Vault.
Supports both Plugin hooks (ctx.register_hook) and Gateway hooks.
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass

# Add shared module to path
SHARED_PATH = Path(__file__).parent.parent / 'shared'
if str(SHARED_PATH) not in sys.path:
    sys.path.insert(0, str(SHARED_PATH))

from obsidian_memory import ObsidianMemory, get_memory


@dataclass
class HermesContext:
    """Mock Hermes context for local testing."""
    register_hook: Optional[Callable] = None


class HermesMemoryPlugin:
    """
    Hermes plugin for Obsidian Vault memory.
    
    Features:
    - Store/retrieve memories via Python API
    - Plugin hooks: ctx.register_hook() for tool interception
    - Automatic context enrichment on agent:start
    """
    
    def __init__(self, vault_path: Optional[str] = None, ctx: Optional[Any] = None):
        self.memory = get_memory('hermes', vault_path)
        self.ctx = ctx
        self._hooks_registered = False
        
        # Register plugin hooks if ctx is provided
        if ctx:
            self._register_plugin_hooks(ctx)
    
    def _register_plugin_hooks(self, ctx):
        """Register plugin hooks via ctx.register_hook()."""
        
        # Hook: agent:start - Load context from vault
        try:
            ctx.register_hook(
                event='agent:start',
                handler=self._on_agent_start
            )
        except AttributeError:
            pass
        
        # Hook: tool:after - Store tool execution results
        try:
            ctx.register_hook(
                event='tool:after',
                handler=self._on_tool_after
            )
        except AttributeError:
            pass
        
        # Hook: message:received - Enrich with vault context
        try:
            ctx.register_hook(
                event='message:received',
                handler=self._on_message_received
            )
        except AttributeError:
            pass
        
        self._hooks_registered = True
    
    def _on_agent_start(self, event_type: str, context: dict):
        """Handler for agent:start event."""
        # Load recent history and add to agent context
        history = self.memory.get_conversation_history(limit=3)
        if history:
            context['obsidian_context'] = {
                'recent_entries': len(history),
                'vault_path': self.memory.vault_path
            }
    
    def _on_tool_after(self, event_type: str, context: dict):
        """Handler for tool:after event - store tool results."""
        tool_name = context.get('tool', 'unknown')
        tool_input = context.get('input', {})
        tool_output = context.get('output', '')
        
        # Store important tool executions
        if tool_name in ['Edit', 'Write', 'Bash']:
            content = f"## Tool Execution: {tool_name}\n\n"
            if 'file_path' in tool_input:
                content += f"**File:** {tool_input['file_path']}\n"
            if 'command' in tool_input:
                content += f"**Command:** `{tool_input['command']}`\n"
            
            try:
                self.memory.store(
                    content=content,
                    tags=['hermes', 'tool-execution', tool_name.lower()],
                    metadata={
                        'tool': tool_name,
                        'tool_input': tool_input,
                        'event_type': event_type
                    }
                )
            except Exception:
                pass  # Hooks should never crash
    
    def _on_message_received(self, event_type: str, context: dict):
        """Handler for message:received - enrich with vault context."""
        message = context.get('message', '')
        
        if len(message) < 10:
            return
        
        # Search vault for relevant content
        relevant = self.memory.query(message, n_results=3)
        if relevant:
            context['obsidian_matches'] = [
                {
                    'id': e.id,
                    'source': e.source,
                    'content': e.content[:200],
                    'tags': e.tags
                }
                for e in relevant
            ]
    
    def remember(self, content: str, tags: List[str] = None, 
                 metadata: Dict[str, Any] = None) -> str:
        """Store a memory in the vault."""
        entry = self.memory.store(
            content=content,
            tags=tags or [],
            metadata=metadata
        )
        return entry.id
    
    def recall(self, query: str, n_results: int = 5) -> List[Dict]:
        """Recall relevant memories from vault."""
        entries = self.memory.query(query, n_results)
        return [e.to_dict() for e in entries]
    
    def search(self, pattern: str, limit: int = 10) -> List[Dict]:
        """Search vault with regex pattern."""
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
    
    # Install hooks
    install_parser = subparsers.add_parser('install-hooks', help='Install Gateway hooks')
    
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
    
    elif args.command == 'install-hooks':
        install_gateway_hooks()
        print("Gateway hooks installed to ~/.hermes/hooks/")
    
    else:
        parser.print_help()


def install_gateway_hooks():
    """Install Gateway hooks to ~/.hermes/hooks/."""
    hooks_dir = Path.home() / '.hermes' / 'hooks' / 'obsidian-memory'
    hooks_dir.mkdir(parents=True, exist_ok=True)
    
    # Create HOOK.yaml
    hook_yaml = hooks_dir / 'HOOK.yaml'
    hook_yaml.write_text("""name: obsidian-memory
description: Load and store context from Obsidian Vault
events:
  - agent:start
  - agent:end
  - message:received
  - tool:after
""")
    
    # Create handler.py
    handler_py = hooks_dir / 'handler.py'
    handler_py.write_text(f'''"""
Gateway hook handler for Obsidian Memory.
Runs in Gateway only (non-blocking).
"""

import sys
from pathlib import Path

# Add shared module to path
SHARED_PATH = Path("{Path(__file__).parent.parent.parent / 'shared'}")
if str(SHARED_PATH) not in sys.path:
    sys.path.insert(0, str(SHARED_PATH))

from obsidian_memory import get_memory

# Initialize memory
memory = get_memory('hermes')

async def handle(event_type: str, context: dict):
    """Called for each subscribed event."""
    
    if event_type == 'agent:start':
        # Load recent history
        history = memory.get_conversation_history(limit=3)
        if history:
            context['obsidian_context'] = f"Loaded {{len(history)}} entries from vault"
    
    elif event_type == 'message:received':
        # Enrich with vault context
        message = context.get('message', '')
        if len(message) > 10:
            relevant = memory.query(message, n_results=2)
            if relevant:
                context['obsidian_matches'] = len(relevant)
    
    elif event_type == 'tool:after':
        # Store important tool results
        tool = context.get('tool', 'unknown')
        if tool in ['Edit', 'Write']:
            try:
                memory.store(
                    content=f"Tool executed: {{tool}}",
                    tags=['gateway', 'tool-execution', tool.lower()]
                )
            except Exception:
                pass  # Never crash
    
    elif event_type == 'agent:end':
        # Session summary could be stored here
        pass
''')
    
    print(f"Installed to: {hooks_dir}")


if __name__ == '__main__':
    main()

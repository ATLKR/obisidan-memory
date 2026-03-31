"""
Obsidian Memory System - Main Coordinator

Entry point for the multi-agent persistent memory system.
Coordinates between Codex, Claude Code, Hermes, and OpenClaw agents.
"""

#!/usr/bin/env python3

import os
import sys
import argparse
import json
from pathlib import Path

# Add shared to path
shared_path = Path(__file__).parent / 'shared'
if str(shared_path) not in sys.path:
    sys.path.insert(0, str(shared_path))

from shared.core.obsidian_memory import get_memory
from shared.protocols.cross_agent_query import create_protocol

# Import agent plugins
try:
    from Codex.agent import CodexAgent
    from ClaudeCode.agent import ClaudeCodeAgent
    from Hermes.agent import HermesAgent
    from OpenClaw.agent import OpenClawAgent
    AGENTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some agents not available: {e}")
    AGENTS_AVAILABLE = False


class ObsidianMemorySystem:
    """Main coordinator for the Obsidian Memory System."""
    
    def __init__(self, vault_path: str = None):
        self.memory = get_memory(vault_path)
        self.protocol = create_protocol(self.memory)
        self.agents = {}
        
        if AGENTS_AVAILABLE:
            self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize and register all agents."""
        # Create agents
        self.agents['codex'] = CodexAgent(self.memory)
        self.agents['claude'] = ClaudeCodeAgent(self.memory)
        self.agents['hermes'] = HermesAgent(self.memory)
        self.agents['openclaw'] = OpenClawAgent(self.memory)
        
        # Register with protocol
        for name, agent in self.agents.items():
            self.protocol.register_agent(agent)
        
        # Initialize Hermes protocol
        if 'hermes' in self.agents:
            self.agents['hermes'].initialize_protocol(self.protocol)
            # Register all agents with Hermes (including itself for queries)
            for name, agent in self.agents.items():
                self.agents['hermes'].register_agent(name, agent)
        
        print(f"Initialized {len(self.agents)} agents: {', '.join(self.agents.keys())}")
    
    def query_agent(self, querier: str, responder: str, question: str) -> dict:
        """
        Execute a cross-agent query with verification.
        
        Args:
            querier: Agent asking the question
            responder: Agent answering
            question: The question text
        
        Returns:
            Query result with verification
        """
        if 'hermes' not in self.agents:
            return {"error": "Hermes orchestrator not available"}
        
        return self.agents['hermes'].orchestrate_query(querier, responder, question)
    
    def store_memory(self, agent: str, content: str, tags: list = None) -> str:
        """Store a memory entry."""
        entry = self.memory.store(
            content=content,
            agent=agent,
            tags=tags or [],
            namespace=agent
        )
        return entry.id
    
    def search_memory(self, query: str, agent: str = None, n: int = 5) -> dict:
        """Search memory."""
        results = self.memory.query(
            query,
            agent_filter=agent,
            n_results=n
        )
        
        return {
            'query': query,
            'confidence': results.confidence,
            'sources': results.sources,
            'results': [
                {
                    'id': e.id,
                    'agent': e.agent,
                    'content': e.content[:300],
                    'confidence': e.confidence,
                    'timestamp': e.timestamp,
                    'source': e.source
                }
                for e in results.results
            ]
        }
    
    def get_stats(self) -> dict:
        """Get system statistics."""
        stats = self.memory.get_stats()
        return {
            'memory': stats,
            'agents': list(self.agents.keys()),
            'protocol_active': self.protocol is not None
        }


def main():
    parser = argparse.ArgumentParser(
        description='Obsidian Memory System - Multi-Agent Persistent Memory',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Query Codex through Hermes
  python main.py query hermes codex "How do I implement a singleton?"
  
  # Store a memory
  python main.py store codex "Important code pattern..." --tags code python
  
  # Search memory
  python main.py search "trading strategy" --agent hermes
  
  # System status
  python main.py status
        """
    )
    
    parser.add_argument('--vault', 
                        default=os.getenv('OBSIDIAN_VAULT_PATH', '~/vaults/AllenPrimaryNotes'),
                        help='Path to Obsidian vault (default: env OBSIDIAN_VAULT_PATH or ~/vaults/AllenPrimaryNotes)')
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Query command
    query_parser = subparsers.add_parser('query', help='Execute cross-agent query')
    query_parser.add_argument('querier', help='Agent asking (e.g., hermes)')
    query_parser.add_argument('responder', help='Agent answering (e.g., codex, claude)')
    query_parser.add_argument('question', help='Question to ask')
    
    # Store command
    store_parser = subparsers.add_parser('store', help='Store a memory')
    store_parser.add_argument('agent', help='Agent name')
    store_parser.add_argument('content', help='Content to store')
    store_parser.add_argument('--tags', nargs='+', help='Tags for categorization')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search memory')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--agent', help='Filter by agent')
    search_parser.add_argument('-n', type=int, default=5, help='Number of results')
    
    # Status command
    subparsers.add_parser('status', help='Show system status')
    
    # Interactive command
    subparsers.add_parser('interactive', help='Start interactive session')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize system
    system = ObsidianMemorySystem(args.vault)
    
    if args.command == 'query':
        result = system.query_agent(args.querier, args.responder, args.question)
        print(json.dumps(result, indent=2))
    
    elif args.command == 'store':
        entry_id = system.store_memory(args.agent, args.content, args.tags)
        print(f"Stored memory: {entry_id}")
    
    elif args.command == 'search':
        results = system.search_memory(args.query, args.agent, args.n)
        print(json.dumps(results, indent=2))
    
    elif args.command == 'status':
        stats = system.get_stats()
        print(json.dumps(stats, indent=2))
    
    elif args.command == 'interactive':
        print("Obsidian Memory System - Interactive Mode")
        print(f"Vault: {args.vault}")
        print("Type 'help' for commands, 'quit' to exit\n")
        
        while True:
            try:
                cmd = input("oms> ").strip()
                
                if cmd == 'quit':
                    break
                elif cmd == 'help':
                    print("""
Commands:
  query <querier> <responder> <question>  - Cross-agent query
  search <query> [--agent <name>]         - Search memory
  store <agent> <content> [--tags ...]    - Store memory
  status                                    - System status
  agents                                    - List agents
  help                                      - This help
  quit                                      - Exit
                    """)
                elif cmd == 'agents':
                    print(f"Available agents: {', '.join(system.agents.keys())}")
                elif cmd.startswith('query '):
                    parts = cmd.split(' ', 2)
                    if len(parts) >= 3:
                        querier_responder = parts[1].split()
                        if len(querier_responder) == 2:
                            result = system.query_agent(
                                querier_responder[0],
                                querier_responder[1],
                                parts[2]
                            )
                            print(json.dumps(result, indent=2))
                elif cmd.startswith('search '):
                    parts = cmd.split(' ', 1)
                    if len(parts) == 2:
                        results = system.search_memory(parts[1])
                        for r in results['results']:
                            print(f"\n[{r['agent']}] {r['id'][:8]}")
                            print(f"  {r['content'][:150]}...")
                elif cmd == 'status':
                    stats = system.get_stats()
                    print(f"Memory entries: {stats['memory']['total_entries']}")
                    print(f"Agents: {', '.join(stats['agents'])}")
                else:
                    print("Unknown command. Type 'help' for available commands.")
                    
            except KeyboardInterrupt:
                print("\nUse 'quit' to exit")
            except Exception as e:
                print(f"Error: {e}")


if __name__ == '__main__':
    main()

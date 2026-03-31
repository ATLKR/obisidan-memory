"""
Hermes Plugin - Hermes Agent Integration

This plugin enables Hermes (this system) to use Obsidian Vault as persistent memory
and participate in cross-agent queries as the orchestrator.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any, Callable

# Add shared to path
shared_path = Path(__file__).parent.parent / 'shared'
if str(shared_path) not in sys.path:
    sys.path.insert(0, str(shared_path))

from shared.core.obsidian_memory import ObsidianMemory, get_memory
from shared.protocols.cross_agent_query import (
    AgentInterface, QueryMessage, Evidence, VerificationResult,
    AgentRole, QueryStatus, CrossAgentQuery
)
from shared.utils.helpers import AgentLogger


class HermesAgent:
    """
    Hermes agent plugin - The orchestrator of the system.
    
    Capabilities:
    - Multi-agent coordination
    - Task delegation and monitoring
    - System-wide memory management
    - Cross-agent query routing
    """
    
    name: str = "hermes"
    capabilities: List[str] = [
        "orchestration",
        "multi_agent_coordination",
        "task_delegation",
        "memory_management",
        "query_routing",
        "system_monitoring",
        "protocol_enforcement"
    ]
    
    def __init__(self, memory: Optional[ObsidianMemory] = None):
        self.memory = memory or get_memory()
        self.logger = AgentLogger("Hermes")
        self.protocol: Optional[CrossAgentQuery] = None
        self._registered_agents: Dict[str, Any] = {}
        self.logger.info("Hermes orchestrator initialized")
    
    def initialize_protocol(self, protocol: CrossAgentQuery) -> None:
        """Initialize the cross-agent query protocol."""
        self.protocol = protocol
        self.logger.info("CrossAgentQuery protocol initialized")
    
    def register_agent(self, name: str, agent_instance: Any) -> None:
        """Register an agent with the orchestrator."""
        self._registered_agents[name] = agent_instance
        if self.protocol:
            self.protocol.register_agent(agent_instance)
        self.logger.info(f"Registered agent: {name}")
    
    def query(self, question: str, request_evidence: bool = True) -> QueryMessage:
        """
        Hermes can also answer queries about the system state.
        """
        self.logger.info(f"Received system query: {question[:50]}...")
        
        # System-related queries
        if 'agent' in question.lower() or 'system' in question.lower():
            answer = self._get_system_status()
            evidence = [Evidence(
                source_type='memory',
                source_id='system:status',
                quote=answer,
                confidence=1.0
            )]
        else:
            # General memory query
            mem_results = self.memory.query(question, n_results=5)
            evidence = []
            for entry in mem_results.results[:3]:
                evidence.append(Evidence(
                    source_type='memory',
                    source_id=entry.id,
                    quote=entry.content[:200],
                    confidence=entry.confidence
                ))
            answer = f"Found {len(evidence)} relevant memories."
        
        return QueryMessage(
            id="",
            thread_id="",
            from_agent=self.name,
            to_agent="",
            role=AgentRole.QUERIER,
            content=question,
            evidence=evidence if request_evidence else []
        )
    
    def respond(self, query: QueryMessage, 
                with_evidence: bool = True) -> QueryMessage:
        """
        Respond to queries about system state or route to appropriate agent.
        """
        self.logger.info(f"Processing query from {query.from_agent}")
        
        content_lower = query.content.lower()
        
        # Check if this is a routing request
        for agent_name, agent in self._registered_agents.items():
            if agent_name.lower() in content_lower:
                # Route to specific agent
                return self._route_to_agent(query, agent_name)
        
        # Handle system queries
        if any(kw in content_lower for kw in ['status', 'stats', 'health']):
            answer = self._get_system_status()
        elif any(kw in content_lower for kw in ['agent', 'registered', 'available']):
            answer = self._get_agent_list()
        else:
            answer = self._handle_general_query(query.content)
        
        # Build evidence
        evidence = []
        if with_evidence:
            mem_stats = self.memory.get_stats()
            evidence.append(Evidence(
                source_type='memory',
                source_id='system:stats',
                quote=f"Total entries: {mem_stats['total_entries']}",
                confidence=1.0
            ))
        
        return QueryMessage(
            id="",
            thread_id=query.thread_id,
            from_agent=self.name,
            to_agent=query.from_agent,
            role=AgentRole.RESPONDER,
            content=answer,
            evidence=evidence,
            parent_id=query.id,
            status=QueryStatus.ANSWERED
        )
    
    def _route_to_agent(self, query: QueryMessage, 
                        agent_name: str) -> QueryMessage:
        """Route a query to a specific agent."""
        agent = self._registered_agents.get(agent_name)
        if not agent:
            return QueryMessage(
                id="",
                thread_id=query.thread_id,
                from_agent=self.name,
                to_agent=query.from_agent,
                role=AgentRole.RESPONDER,
                content=f"Agent '{agent_name}' not found.",
                evidence=[],
                parent_id=query.id,
                status=QueryStatus.ANSWERED
            )
        
        # Delegate to agent
        self.logger.info(f"Routing query to {agent_name}")
        
        # Create a new query for the target agent
        delegated = QueryMessage(
            id="",
            thread_id=query.thread_id,
            from_agent=self.name,
            to_agent=agent_name,
            role=AgentRole.QUERIER,
            content=query.content,
            evidence=query.evidence
        )
        
        # Get response from agent
        response = agent.respond(delegated)
        
        # Add routing note
        response.content = f"[Routed via Hermes to {agent_name}]\n\n{response.content}"
        response.to_agent = query.from_agent  # Return to original querier
        
        return response
    
    def _get_system_status(self) -> str:
        """Get current system status."""
        stats = self.memory.get_stats()
        
        status = f"""# Hermes System Status

**Memory:**
- Total entries: {stats['total_entries']}
- By agent: {stats['by_agent']}
- Indexed tags: {stats['indexed_tags']}
- Vault path: {stats['vault_path']}

**Registered Agents ({len(self._registered_agents)}):**
"""
        for name, agent in self._registered_agents.items():
            caps = getattr(agent, 'capabilities', [])
            status += f"- {name}: {', '.join(caps[:3])}...\n"
        
        return status
    
    def _get_agent_list(self) -> str:
        """Get list of available agents."""
        agents_info = []
        for name, agent in self._registered_agents.items():
            caps = getattr(agent, 'capabilities', [])
            agents_info.append(f"- **{name}**: {', '.join(caps[:5])}")
        
        return "# Available Agents\n\n" + '\n'.join(agents_info)
    
    def _handle_general_query(self, content: str) -> str:
        """Handle general queries using memory."""
        results = self.memory.query(content, n_results=3)
        
        if results.results:
            return f"Found {len(results.results)} relevant memories. Top match: {results.results[0].content[:200]}..."
        else:
            return "No relevant memories found. Try asking a specific agent directly."
    
    def verify(self, answer: QueryMessage, 
               original_query: str) -> VerificationResult:
        """
        Verify an answer using system-wide knowledge.
        """
        # Hermes can verify any answer by checking:
        # 1. Does the evidence exist?
        # 2. Are agents responding consistently?
        # 3. Is the answer protocol-compliant?
        
        issues = []
        
        # Protocol compliance check
        if not answer.evidence and answer.role == AgentRole.RESPONDER:
            issues.append("Responder did not provide evidence")
        
        # Check for evidence in memory
        verifiable = 0
        for ev in answer.evidence:
            if ev.source_type == 'memory':
                result = self.memory.query(ev.quote[:50], n_results=1)
                if result.results:
                    verifiable += 1
        
        confidence = verifiable / len(answer.evidence) if answer.evidence else 0.5
        
        return VerificationResult(
            is_valid=len(issues) == 0 and confidence > 0.5,
            confidence=confidence,
            reasoning=f"Protocol compliance: {len(issues)} issues; Evidence verifiable: {verifiable}/{len(answer.evidence)}",
            discrepancies=issues
        )
    
    def orchestrate_query(self, querier: str, responder: str, 
                          question: str) -> Dict[str, Any]:
        """
        Orchestrate a complete query-answer-verify flow.
        
        This is the main method for cross-agent queries.
        """
        if not self.protocol:
            return {"error": "Protocol not initialized"}
        
        # Check agents exist
        if querier not in self._registered_agents:
            return {"error": f"Querier agent '{querier}' not registered"}
        if responder not in self._registered_agents:
            return {"error": f"Responder agent '{responder}' not registered"}
        
        # Step 1: Create thread
        thread_id = self.protocol.create_thread(querier, responder, question)
        
        self.logger.info(f"Orchestrating query: {querier} -> {responder} (thread: {thread_id})")
        
        # Step 2: Get answer from responder
        responder_agent = self._registered_agents[responder]
        query_msg = QueryMessage(
            id="init",
            thread_id=thread_id,
            from_agent=querier,
            to_agent=responder,
            role=AgentRole.QUERIER,
            content=question
        )
        
        answer = responder_agent.respond(query_msg)
        
        # Step 3: Submit answer to protocol
        answer_msg = self.protocol.submit_answer(
            thread_id=thread_id,
            responder=responder,
            answer=answer.content,
            evidence=answer.evidence
        )
        
        # Step 4: Verify
        verification = self.protocol.verify_answer(thread_id, self.name)
        
        return {
            'thread_id': thread_id,
            'query': question,
            'answer': answer.content,
            'evidence': [e.to_dict() for e in answer.evidence],
            'verification': {
                'is_valid': verification.is_valid,
                'confidence': verification.confidence,
                'reasoning': verification.reasoning,
                'discrepancies': verification.discrepancies
            },
            'suggested_next': 'requery' if not verification.is_valid else 'accept'
        }
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get detailed memory statistics."""
        return self.memory.get_stats()
    
    def search_all_agents(self, query: str) -> Dict[str, List[Dict]]:
        """Search memory across all agents."""
        results = {}
        for agent_name in self._registered_agents.keys():
            mem_results = self.memory.query(
                query,
                agent_filter=agent_name,
                n_results=5
            )
            results[agent_name] = [
                {
                    'id': e.id,
                    'content': e.content[:200],
                    'confidence': e.confidence
                }
                for e in mem_results.results
            ]
        
        return results


def main():
    """CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Hermes Orchestrator Plugin')
    parser.add_argument('--vault', help='Obsidian vault path')
    parser.add_argument('--status', action='store_true', help='Show system status')
    parser.add_argument('--orchestrate', nargs=3, metavar=('QUERIER', 'RESPONDER', 'QUESTION'),
                        help='Orchestrate a query (requires both agents registered)')
    
    args = parser.parse_args()
    
    agent = HermesAgent(get_memory(args.vault))
    
    if args.status:
        print(agent._get_system_status())
    
    elif args.orchestrate:
        querier, responder, question = args.orchestrate
        result = agent.orchestrate_query(querier, responder, question)
        print(json.dumps(result, indent=2))
    
    else:
        print("Hermes Orchestrator Plugin")
        print(f"Capabilities: {', '.join(agent.capabilities)}")
        print(f"Memory: {agent.get_memory_stats()}")


if __name__ == '__main__':
    import json
    main()

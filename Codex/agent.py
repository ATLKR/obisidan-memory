"""
Codex Plugin - OpenAI Codex CLI Agent Integration

This plugin enables Codex to use Obsidian Vault as persistent memory
and participate in cross-agent queries.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any

# Add shared to path
shared_path = Path(__file__).parent.parent / 'shared'
if str(shared_path) not in sys.path:
    sys.path.insert(0, str(shared_path))

from shared.core.obsidian_memory import ObsidianMemory, get_memory
from shared.protocols.cross_agent_query import (
    AgentInterface, QueryMessage, Evidence, VerificationResult,
    AgentRole, QueryStatus
)
from shared.utils.helpers import AgentLogger, format_evidence


class CodexAgent:
    """
    Codex agent plugin for Obsidian Memory.
    
    Capabilities:
    - Code generation and analysis
    - Cross-referencing with vault documentation
    - Evidence-based responses with source citations
    """
    
    name: str = "codex"
    capabilities: List[str] = [
        "code_generation",
        "code_review",
        "technical_documentation",
        "python",
        "typescript",
        "javascript",
        "shell_scripting"
    ]
    
    def __init__(self, memory: Optional[ObsidianMemory] = None):
        self.memory = memory or get_memory()
        self.logger = AgentLogger("Codex")
        self.logger.info("Codex agent initialized")
    
    def query(self, question: str, request_evidence: bool = True) -> QueryMessage:
        """
        Query this agent with a question.
        
        This is typically called by other agents to ask Codex something.
        """
        self.logger.info(f"Received query: {question[:50]}...")
        
        # Search memory for relevant context
        mem_results = self.memory.query(
            question,
            agent_filter='codex',
            n_results=3
        )
        
        # Build evidence from memory
        evidence = []
        if mem_results.results:
            for entry in mem_results.results[:2]:
                evidence.append(Evidence(
                    source_type='memory',
                    source_id=entry.id,
                    quote=entry.content[:200],
                    confidence=entry.confidence
                ))
        
        return QueryMessage(
            id="",  # Will be set by protocol
            thread_id="",
            from_agent=self.name,
            to_agent="",  # Will be set by protocol
            role=AgentRole.QUERIER,
            content=question,
            evidence=evidence if request_evidence else []
        )
    
    def respond(self, query: QueryMessage, 
                with_evidence: bool = True) -> QueryMessage:
        """
        Respond to a query with optional evidence.
        
        This is the main method for answering questions from other agents.
        """
        self.logger.info(f"Responding to query from {query.from_agent}")
        
        # Gather evidence from memory
        evidence = []
        if with_evidence:
            # Search relevant documentation
            mem_results = self.memory.query(
                query.content,
                n_results=5
            )
            
            for entry in mem_results.results:
                evidence.append(Evidence(
                    source_type='memory',
                    source_id=f"memory:{entry.id}",
                    quote=entry.content[:300],
                    confidence=entry.confidence
                ))
            
            # Also search for code patterns if it's a code question
            if any(kw in query.content.lower() for kw in ['code', 'function', 'class', 'error']):
                code_results = self.memory.search_vault(
                    r'(def |class |function |const |let )',
                    '*.py'
                )
                for path in code_results[:3]:
                    content = self.memory.read_vault_file(path)
                    if content:
                        evidence.append(Evidence(
                            source_type='memory',
                            source_id=f"file:{path}",
                            quote=content[:300],
                            confidence=0.8
                        ))
        
        # Construct response based on evidence
        answer = self._construct_answer(query.content, evidence)
        
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
    
    def _construct_answer(self, question: str, evidence: List[Evidence]) -> str:
        """Construct an answer based on gathered evidence."""
        # This is a template - in real use, this would use Codex's actual capabilities
        answer_parts = [f"Based on my search of the memory system:\n"]
        
        if evidence:
            answer_parts.append(f"\nI found {len(evidence)} relevant sources:\n")
            for i, ev in enumerate(evidence[:3], 1):
                answer_parts.append(f"{i}. From {ev.source_id}")
        else:
            answer_parts.append("\nNo specific evidence found in memory.")
        
        answer_parts.append(f"\n\nRegarding your question: {question}")
        answer_parts.append("\n[This is where Codex would provide its actual analysis/code]")
        
        return '\n'.join(answer_parts)
    
    def verify(self, answer: QueryMessage, 
               original_query: str) -> VerificationResult:
        """
        Verify an answer against available evidence.
        
        Codex can verify code-related answers for correctness.
        """
        self.logger.info(f"Verifying answer from {answer.from_agent}")
        
        # Check evidence quality
        if not answer.evidence:
            return VerificationResult(
                is_valid=False,
                confidence=0.3,
                reasoning="No evidence provided with answer",
                discrepancies=["Missing citations"]
            )
        
        # Verify evidence exists in memory
        issues = []
        valid_evidence = 0
        
        for ev in answer.evidence:
            if ev.source_type == 'memory':
                mem_id = ev.source_id.replace('memory:', '')
                # Try to find this in memory
                result = self.memory.query(ev.quote[:50], n_results=1)
                if result.results:
                    valid_evidence += 1
                else:
                    issues.append(f"Cannot verify evidence: {ev.source_id}")
        
        confidence = valid_evidence / len(answer.evidence) if answer.evidence else 0
        
        return VerificationResult(
            is_valid=confidence > 0.5,
            confidence=confidence,
            reasoning=f"Verified {valid_evidence}/{len(answer.evidence)} evidence items",
            discrepancies=issues
        )
    
    def store_code_snippet(self, code: str, description: str,
                         language: str, tags: List[str] = None) -> str:
        """
        Store a code snippet in the vault.
        
        Args:
            code: The code to store
            description: Description of what it does
            language: Programming language
            tags: Additional tags
        
        Returns:
            Memory entry ID
        """
        content = f"## {description}\n\n"
        content += f"```{language}\n{code}\n```\n"
        
        all_tags = ['code', language] + (tags or [])
        
        entry = self.memory.store(
            content=content,
            agent=self.name,
            tags=all_tags,
            namespace='codex'
        )
        
        self.logger.info(f"Stored code snippet: {entry.id}")
        return entry.id
    
    def find_code_patterns(self, pattern: str, language: str = 'python') -> List[Dict]:
        """
        Find code patterns in the vault.
        
        Args:
            pattern: Regex pattern to search for
            language: Language filter
        
        Returns:
            List of matching code snippets
        """
        results = []
        
        # Search in codex namespace
        mem_results = self.memory.query(
            pattern,
            n_results=10
        )
        
        for entry in mem_results.results:
            if 'code' in entry.tags or language in entry.tags:
                results.append({
                    'id': entry.id,
                    'content': entry.content,
                    'tags': entry.tags,
                    'source': entry.source
                })
        
        return results


def main():
    """CLI interface for testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Codex Agent Plugin')
    parser.add_argument('--vault', help='Obsidian vault path')
    parser.add_argument('--query', help='Query to process')
    parser.add_argument('--store-code', help='Store code snippet')
    
    args = parser.parse_args()
    
    agent = CodexAgent(get_memory(args.vault))
    
    if args.query:
        # Simulate receiving a query
        test_query = QueryMessage(
            id="test123",
            thread_id="thread456",
            from_agent="user",
            to_agent="codex",
            role=AgentRole.QUERIER,
            content=args.query
        )
        response = agent.respond(test_query)
        print(format_evidence([e.to_dict() for e in response.evidence]))
        print("\n" + "="*50)
        print(response.content)
    
    elif args.store_code:
        with open(args.store_code, 'r') as f:
            code = f.read()
        agent.store_code_snippet(
            code=code,
            description=f"Code from {args.store_code}",
            language=Path(args.store_code).suffix[1:] or 'text'
        )
        print(f"Stored code from {args.store_code}")
    
    else:
        print("Codex Agent Plugin")
        print(f"Capabilities: {', '.join(agent.capabilities)}")
        print(f"Memory stats: {agent.memory.get_stats()}")


if __name__ == '__main__':
    main()

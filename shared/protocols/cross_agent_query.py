"""
CrossAgentQuery Protocol - Evidence-Based Multi-Agent Verification

Implements patterns from:
- Self-Consistency (2203.11171): Multiple reasoning paths, consistent answer selection
- ChatDev (2307.07924): Communicative agents with structured dialogue

Key concept: Agent A queries Agent B → B responds with evidence → A verifies
"""

import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any, Callable, Protocol
from dataclasses import dataclass, field, asdict
from enum import Enum

from shared.core.obsidian_memory import ObsidianMemory, MemoryEntry, get_memory


class QueryStatus(Enum):
    """Status of a cross-agent query."""
    PENDING = "pending"
    ANSWERED = "answered"
    VERIFIED = "verified"
    REJECTED = "rejected"  # Verification failed
    DISPUTED = "disputed"  # Needs third-party arbitration


class AgentRole(Enum):
    """Role of an agent in the query protocol."""
    QUERIER = "querier"      # Asking the question
    RESPONDER = "responder"  # Answering with evidence
    VERIFIER = "verifier"    # Verifying the answer
    ARBITER = "arbiter"      # Resolving disputes


@dataclass
class Evidence:
    """Evidence citation for an answer."""
    source_type: str  # 'memory', 'arxiv', 'web', 'calculation', 'reasoning'
    source_id: str    # Identifier (e.g., arxiv:2203.11171, memory:abc123)
    quote: str        # Relevant excerpt
    confidence: float = 1.0  # 0.0 to 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QueryMessage:
    """A message in the cross-agent query protocol."""
    id: str
    thread_id: str
    from_agent: str
    to_agent: str
    role: AgentRole
    content: str
    evidence: List[Evidence] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    status: QueryStatus = QueryStatus.PENDING
    parent_id: Optional[str] = None  # For threading replies
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'thread_id': self.thread_id,
            'from_agent': self.from_agent,
            'to_agent': self.to_agent,
            'role': self.role.value,
            'content': self.content,
            'evidence': [e.to_dict() for e in self.evidence],
            'timestamp': self.timestamp,
            'status': self.status.value,
            'parent_id': self.parent_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueryMessage':
        return cls(
            id=data['id'],
            thread_id=data['thread_id'],
            from_agent=data['from_agent'],
            to_agent=data['to_agent'],
            role=AgentRole(data['role']),
            content=data['content'],
            evidence=[Evidence(**e) for e in data.get('evidence', [])],
            timestamp=data['timestamp'],
            status=QueryStatus(data['status']),
            parent_id=data.get('parent_id')
        )


@dataclass
class VerificationResult:
    """Result of verifying an answer."""
    is_valid: bool
    confidence: float  # 0.0 to 1.0
    reasoning: str   # Why it was accepted/rejected
    discrepancies: List[str] = field(default_factory=list)  # Issues found
    suggested_agents: List[str] = field(default_factory=list)  # For dispute resolution


class AgentInterface(Protocol):
    """Protocol for agents that can participate in CrossAgentQuery."""
    
    name: str
    capabilities: List[str]
    
    def query(self, question: str, request_evidence: bool = True) -> QueryMessage:
        """Query this agent with a question."""
        ...
    
    def respond(self, query: QueryMessage, 
                with_evidence: bool = True) -> QueryMessage:
        """Respond to a query with optional evidence."""
        ...
    
    def verify(self, answer: QueryMessage, 
               original_query: str) -> VerificationResult:
        """Verify an answer against available evidence."""
        ...


class CrossAgentQuery:
    """
    Protocol for cross-agent querying with evidence-based verification.
    
    Flow:
    1. Querier → Responder: "What's X?"
    2. Responder → Querier: "X is Y" + evidence
    3. Querier: Verify evidence, check consistency
    4. If disputed → Arbiter resolves
    """
    
    def __init__(self, memory: Optional[ObsidianMemory] = None):
        self.memory = memory or get_memory()
        self._agents: Dict[str, AgentInterface] = {}
        self._active_threads: Dict[str, List[QueryMessage]] = {}
    
    def register_agent(self, agent: AgentInterface) -> None:
        """Register an agent to participate in the protocol."""
        self._agents[agent.name] = agent
    
    def create_thread(self, querier: str, responder: str, 
                      question: str) -> str:
        """
        Create a new query thread.
        
        Args:
            querier: Name of agent asking
            responder: Name of agent being asked
            question: The question text
        
        Returns:
            Thread ID
        """
        thread_id = str(uuid.uuid4())[:8]
        
        query = QueryMessage(
            id=str(uuid.uuid4())[:12],
            thread_id=thread_id,
            from_agent=querier,
            to_agent=responder,
            role=AgentRole.QUERIER,
            content=question,
            status=QueryStatus.PENDING
        )
        
        self._active_threads[thread_id] = [query]
        
        # Store in vault
        self._store_message(query, thread_id)
        
        return thread_id
    
    def submit_answer(self, thread_id: str, responder: str,
                      answer: str, evidence: List[Evidence]) -> QueryMessage:
        """
        Submit an answer to a query.
        
        Args:
            thread_id: Thread ID
            responder: Responding agent name
            answer: Answer content
            evidence: Supporting evidence
        
        Returns:
            The answer message
        """
        thread = self._active_threads.get(thread_id, [])
        if not thread:
            raise ValueError(f"Thread {thread_id} not found")
        
        original_query = thread[0]
        
        answer_msg = QueryMessage(
            id=str(uuid.uuid4())[:12],
            thread_id=thread_id,
            from_agent=responder,
            to_agent=original_query.from_agent,
            role=AgentRole.RESPONDER,
            content=answer,
            evidence=evidence,
            parent_id=original_query.id,
            status=QueryStatus.ANSWERED
        )
        
        thread.append(answer_msg)
        self._store_message(answer_msg, thread_id)
        
        return answer_msg
    
    def verify_answer(self, thread_id: str, verifier: str) -> VerificationResult:
        """
        Verify an answer in a thread.
        
        Args:
            thread_id: Thread ID
            verifier: Agent performing verification
        
        Returns:
            VerificationResult
        """
        thread = self._active_threads.get(thread_id, [])
        if len(thread) < 2:
            return VerificationResult(
                is_valid=False,
                confidence=0.0,
                reasoning="No answer to verify"
            )
        
        query = thread[0]
        answer = thread[-1]  # Last message is the answer
        
        # Check evidence quality
        if not answer.evidence:
            return VerificationResult(
                is_valid=False,
                confidence=0.3,
                reasoning="No evidence provided",
                suggested_agents=self._get_alternative_agents(answer.from_agent)
            )
        
        # Verify evidence against memory
        verification_issues = []
        memory_hits = 0
        
        for ev in answer.evidence:
            if ev.source_type == 'memory':
                # Check if this memory exists
                mem_result = self.memory.query(
                    ev.quote, 
                    n_results=3
                )
                if mem_result.results:
                    memory_hits += 1
                else:
                    verification_issues.append(
                        f"Memory citation not found: {ev.source_id}"
                    )
            elif ev.source_type == 'arxiv':
                # Validate arxiv ID format
                if not ev.source_id.startswith('arxiv:'):
                    verification_issues.append(
                        f"Invalid arxiv citation format: {ev.source_id}"
                    )
        
        # Calculate confidence based on evidence quality
        evidence_confidence = sum(e.confidence for e in answer.evidence) / len(answer.evidence)
        memory_ratio = memory_hits / len(answer.evidence) if answer.evidence else 0
        
        overall_confidence = (evidence_confidence * 0.6) + (memory_ratio * 0.4)
        
        is_valid = overall_confidence > 0.6 and len(verification_issues) < 2
        
        # Record verification
        self._store_verification(thread_id, verifier, is_valid, overall_confidence)
        
        return VerificationResult(
            is_valid=is_valid,
            confidence=overall_confidence,
            reasoning=f"Evidence quality: {evidence_confidence:.2f}, Memory verification: {memory_ratio:.2f}",
            discrepancies=verification_issues,
            suggested_agents=self._get_alternative_agents(answer.from_agent) if not is_valid else []
        )
    
    def _get_alternative_agents(self, exclude: str) -> List[str]:
        """Get alternative agents for dispute resolution."""
        return [name for name in self._agents.keys() if name != exclude]
    
    def _store_message(self, message: QueryMessage, thread_id: str) -> None:
        """Store message in Obsidian vault."""
        # Convert to markdown
        content = f"## Message from {message.from_agent} to {message.to_agent}\n\n"
        content += f"**Role:** {message.role.value}\n\n"
        content += f"**Status:** {message.status.value}\n\n"
        content += f"**Content:**\n\n{message.content}\n\n"
        
        if message.evidence:
            content += "**Evidence:**\n\n"
            for ev in message.evidence:
                content += f"- [{ev.source_type}] {ev.source_id}\n"
                content += f"  > {ev.quote[:100]}...\n"
                content += f"  Confidence: {ev.confidence:.2f}\n\n"
        
        # Store with thread tag
        self.memory.store(
            content=content,
            agent=message.from_agent,
            tags=[f'thread:{thread_id}', 'cross-agent-query', message.role.value],
            evidence=[e.to_dict() for e in message.evidence],
            namespace='conversations'
        )
    
    def _store_verification(self, thread_id: str, verifier: str, 
                           is_valid: bool, confidence: float) -> None:
        """Store verification result."""
        content = f"## Verification by {verifier}\n\n"
        content += f"**Thread:** {thread_id}\n\n"
        content += f"**Result:** {'VALID' if is_valid else 'REJECTED'}\n\n"
        content += f"**Confidence:** {confidence:.2f}\n"
        
        self.memory.store(
            content=content,
            agent=verifier,
            tags=[f'thread:{thread_id}', 'verification', 'cross-agent-query'],
            namespace='conversations'
        )
    
    def get_thread_summary(self, thread_id: str) -> Dict[str, Any]:
        """Get summary of a conversation thread."""
        thread = self._active_threads.get(thread_id, [])
        if not thread:
            return {"error": "Thread not found"}
        
        messages = [m.to_dict() for m in thread]
        
        # Get verification status of last answer
        last_answer = None
        for msg in reversed(thread):
            if msg.role == AgentRole.RESPONDER:
                last_answer = msg
                break
        
        verification_status = "pending"
        if last_answer:
            verification_status = last_answer.status.value
        
        return {
            'thread_id': thread_id,
            'message_count': len(thread),
            'participants': list(set(m.from_agent for m in thread)),
            'current_status': verification_status,
            'messages': messages
        }
    
    def query_with_verification(self, querier: str, responder: str,
                                question: str, auto_verify: bool = True) -> Dict[str, Any]:
        """
        Complete flow: Query → Answer → Verify.
        
        Args:
            querier: Agent asking
            responder: Agent answering
            question: Question text
            auto_verify: Whether to auto-verify the answer
        
        Returns:
            Full result with query, answer, and verification
        """
        # Step 1: Create thread
        thread_id = self.create_thread(querier, responder, question)
        
        # Step 2: Get answer from responder (simulated - in real use, responder agent provides this)
        # In practice, this would be called by the responder agent
        
        result = {
            'thread_id': thread_id,
            'query': {
                'from': querier,
                'to': responder,
                'content': question
            },
            'answer': None,
            'verification': None
        }
        
        if auto_verify:
            # Step 3: Verify (would be done after answer is submitted)
            # This is a placeholder - real verification happens after submit_answer
            result['verification'] = {
                'status': 'pending_answer',
                'note': 'Waiting for responder to submit answer with evidence'
            }
        
        return result


# Factory for creating protocol instances
def create_protocol(memory: Optional[ObsidianMemory] = None) -> CrossAgentQuery:
    """Create a new CrossAgentQuery protocol instance."""
    return CrossAgentQuery(memory)

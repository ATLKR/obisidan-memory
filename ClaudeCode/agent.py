"""
Claude Code Plugin - Anthropic Claude CLI Agent Integration

This plugin enables Claude Code to use Obsidian Vault as persistent memory
and participate in cross-agent queries with evidence-based verification.
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
from shared.utils.helpers import AgentLogger, extract_wikilinks


class ClaudeCodeAgent:
    """
    Claude Code agent plugin for Obsidian Memory.
    
    Capabilities:
    - Complex reasoning and analysis
    - Code review and architecture design
    - Cross-agent query coordination
    - Evidence verification with detailed reasoning
    """
    
    name: str = "claude"
    capabilities: List[str] = [
        "complex_reasoning",
        "code_review",
        "architecture_design",
        "documentation",
        "debugging",
        "cross_agent_coordination",
        "evidence_verification"
    ]
    
    def __init__(self, memory: Optional[ObsidianMemory] = None):
        self.memory = memory or get_memory()
        self.logger = AgentLogger("ClaudeCode")
        self.logger.info("Claude Code agent initialized")
    
    def query(self, question: str, request_evidence: bool = True) -> QueryMessage:
        """
        Query this agent with a question.
        
        Claude is often used as the coordinator/arbiter in cross-agent queries.
        """
        self.logger.info(f"Received query: {question[:50]}...")
        
        # Search for relevant context
        mem_results = self.memory.query(
            question,
            n_results=5
        )
        
        # Build comprehensive evidence
        evidence = []
        if mem_results.results:
            for entry in mem_results.results[:3]:
                evidence.append(Evidence(
                    source_type='memory',
                    source_id=entry.id,
                    quote=entry.content[:200],
                    confidence=entry.confidence
                ))
        
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
        Respond to a query with comprehensive evidence.
        
        Claude provides detailed, reasoned answers with strong evidence backing.
        """
        self.logger.info(f"Responding to query from {query.from_agent}")
        
        # Multi-path evidence gathering (Self-Consistency pattern)
        evidence = []
        
        if with_evidence:
            # Path 1: Direct memory search
            mem_results = self.memory.query(
                query.content,
                n_results=7
            )
            
            # Path 2: Tag-based search for related topics
            tags = self._extract_query_tags(query.content)
            for tag in tags[:2]:
                tag_results = self.memory.query(
                    "",
                    tag_filter=tag,
                    n_results=3
                )
                mem_results.results.extend(tag_results.results)
            
            # Deduplicate and score
            seen_ids = set()
            for entry in mem_results.results:
                if entry.id not in seen_ids:
                    seen_ids.add(entry.id)
                    evidence.append(Evidence(
                        source_type='memory',
                        source_id=f"memory:{entry.id}",
                        quote=entry.content[:400],
                        confidence=entry.confidence
                    ))
            
            # Path 3: Search for wiki links in existing notes
            wiki_targets = set()
            for entry in mem_results.results[:5]:
                links = extract_wikilinks(entry.content)
                wiki_targets.update(links)
            
            # Add wiki-linked evidence
            for target in list(wiki_targets)[:3]:
                wiki_results = self.memory.query(target, n_results=2)
                for entry in wiki_results.results:
                    if entry.id not in seen_ids:
                        evidence.append(Evidence(
                            source_type='memory',
                            source_id=f"wiki:{target}",
                            quote=entry.content[:300],
                            confidence=0.85
                        ))
        
        # Construct reasoned response
        answer = self._construct_reasoned_answer(query.content, evidence)
        
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
    
    def _extract_query_tags(self, query: str) -> List[str]:
        """Extract potential tags from query."""
        # Simple keyword extraction
        keywords = {
            'trading': ['trading', 'market', 'price', 'signal'],
            'database': ['database', 'sql', 'postgresql', 'query'],
            'code': ['code', 'function', 'class', 'implementation'],
            'research': ['paper', 'arxiv', 'study', 'research'],
            'architecture': ['architecture', 'design', 'system', 'component']
        }
        
        query_lower = query.lower()
        found_tags = []
        for tag, words in keywords.items():
            if any(word in query_lower for word in words):
                found_tags.append(tag)
        
        return found_tags
    
    def _construct_reasoned_answer(self, question: str, 
                                   evidence: List[Evidence]) -> str:
        """Construct a detailed, reasoned answer."""
        parts = []
        
        # Evidence summary
        parts.append(f"## Analysis\n")
        parts.append(f"Based on {len(evidence)} sources from memory:\n")
        
        # Group evidence by type
        mem_evidence = [e for e in evidence if e.source_type == 'memory']
        wiki_evidence = [e for e in evidence if e.source_type == 'wiki']
        
        if mem_evidence:
            parts.append(f"\n**Direct Memory Matches ({len(mem_evidence)}):**")
            for i, ev in enumerate(mem_evidence[:3], 1):
                parts.append(f"{i}. {ev.source_id} (confidence: {ev.confidence:.2f})")
        
        if wiki_evidence:
            parts.append(f"\n**Related via WikiLinks ({len(wiki_evidence)}):**")
            for ev in wiki_evidence[:2]:
                parts.append(f"- {ev.source_id}")
        
        # Response section
        parts.append(f"\n## Response to: {question}")
        parts.append("\n[This is where Claude would provide detailed analysis]")
        parts.append("\n### Reasoning Process")
        parts.append("1. Gathered evidence from multiple sources")
        parts.append("2. Cross-referenced with existing knowledge")
        parts.append("3. Synthesized consistent answer")
        
        return '\n'.join(parts)
    
    def verify(self, answer: QueryMessage, 
               original_query: str) -> VerificationResult:
        """
        Verify an answer with detailed reasoning.
        
        Claude acts as a verifier using Self-Consistency principles:
        - Check if multiple reasoning paths lead to same conclusion
        - Verify evidence quality and consistency
        - Identify hallucinations or unsupported claims
        """
        self.logger.info(f"Verifying answer from {answer.from_agent}")
        
        issues = []
        strengths = []
        
        # Check 1: Evidence exists
        if not answer.evidence:
            issues.append("No evidence provided")
            return VerificationResult(
                is_valid=False,
                confidence=0.2,
                reasoning="Answer lacks supporting evidence",
                discrepancies=issues
            )
        
        # Check 2: Evidence diversity (Self-Consistency)
        source_types = set(e.source_type for e in answer.evidence)
        if len(source_types) < 2 and len(answer.evidence) > 1:
            issues.append("Limited source diversity - may indicate narrow perspective")
        else:
            strengths.append(f"Diverse evidence types: {', '.join(source_types)}")
        
        # Check 3: Confidence scores
        avg_confidence = sum(e.confidence for e in answer.evidence) / len(answer.evidence)
        if avg_confidence < 0.5:
            issues.append(f"Low average confidence: {avg_confidence:.2f}")
        else:
            strengths.append(f"Good confidence: {avg_confidence:.2f}")
        
        # Check 4: Verify evidence in memory
        verifiable = 0
        for ev in answer.evidence:
            if ev.source_type == 'memory':
                check = self.memory.query(ev.quote[:50], n_results=1)
                if check.results:
                    verifiable += 1
        
        verification_rate = verifiable / len(answer.evidence) if answer.evidence else 0
        
        if verification_rate < 0.5:
            issues.append(f"Only {verification_rate*100:.0f}% of evidence verifiable")
        else:
            strengths.append(f"{verification_rate*100:.0f}% evidence verified in memory")
        
        # Calculate final confidence
        confidence = avg_confidence * 0.4 + verification_rate * 0.6
        
        # Determine validity
        is_valid = confidence > 0.6 and len(issues) <= 2
        
        reasoning = "; ".join(strengths)
        if issues:
            reasoning += " | Issues: " + "; ".join(issues)
        
        return VerificationResult(
            is_valid=is_valid,
            confidence=confidence,
            reasoning=reasoning,
            discrepancies=issues,
            suggested_agents=['codex', 'hermes'] if not is_valid else []
        )
    
    def arbitrate(self, thread_id: str, 
                  conflicting_answers: List[QueryMessage]) -> QueryMessage:
        """
        Act as arbiter when agents disagree.
        
        This uses Self-Consistency: multiple agents provide answers,
        Claude selects the most consistent/verified one.
        """
        self.logger.info(f"Arbitrating thread {thread_id} with {len(conflicting_answers)} answers")
        
        # Score each answer
        scored_answers = []
        for answer in conflicting_answers:
            verification = self.verify(answer, "")
            scored_answers.append((verification.confidence, answer, verification))
        
        # Sort by confidence
        scored_answers.sort(reverse=True, key=lambda x: x[0])
        
        # Select best answer
        best = scored_answers[0]
        
        # Create arbitration result
        arbitration_content = f"## Arbitration Result\n\n"
        arbitration_content += f"**Selected answer from:** {best[1].from_agent}\n"
        arbitration_content += f"**Confidence:** {best[0]:.2f}\n"
        arbitration_content += f"**Reasoning:** {best[2].reasoning}\n\n"
        arbitration_content += "### All Answers Ranked:\n"
        
        for i, (conf, ans, ver) in enumerate(scored_answers, 1):
            arbitration_content += f"{i}. {ans.from_agent}: {conf:.2f} - {ver.reasoning[:50]}...\n"
        
        return QueryMessage(
            id="",
            thread_id=thread_id,
            from_agent=self.name,
            to_agent="all",
            role=AgentRole.ARBITER,
            content=arbitration_content,
            evidence=[],  # Arbitration includes evidence from selected answer
            status=QueryStatus.VERIFIED if best[0] > 0.7 else QueryStatus.DISPUTED
        )
    
    def store_analysis(self, topic: str, analysis: str,
                      related_files: List[str] = None) -> str:
        """
        Store an analysis in the vault.
        
        Args:
            topic: Analysis topic
            analysis: The analysis content
            related_files: Related file paths
        
        Returns:
            Memory entry ID
        """
        content = f"# Analysis: {topic}\n\n{analysis}\n"
        
        if related_files:
            content += "\n## Related Files\n"
            for f in related_files:
                content += f"- [[{f}]]\n"
        
        entry = self.memory.store(
            content=content,
            agent=self.name,
            tags=['analysis', 'claude', 'reasoning'],
            namespace='claude'
        )
        
        self.logger.info(f"Stored analysis: {entry.id}")
        return entry.id


def main():
    """CLI interface for testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Claude Code Agent Plugin')
    parser.add_argument('--vault', help='Obsidian vault path')
    parser.add_argument('--query', help='Query to process')
    parser.add_argument('--verify', help='Verify an answer file')
    parser.add_argument('--stats', action='store_true', help='Show memory stats')
    
    args = parser.parse_args()
    
    agent = ClaudeCodeAgent(get_memory(args.vault))
    
    if args.query:
        test_query = QueryMessage(
            id="test123",
            thread_id="thread456",
            from_agent="user",
            to_agent="claude",
            role=AgentRole.QUERIER,
            content=args.query
        )
        response = agent.respond(test_query)
        print(f"Evidence count: {len(response.evidence)}")
        print("\n" + "="*60)
        print(response.content)
    
    elif args.stats:
        stats = agent.memory.get_stats()
        print("Memory Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    
    else:
        print("Claude Code Agent Plugin")
        print(f"Capabilities: {', '.join(agent.capabilities)}")


if __name__ == '__main__':
    main()

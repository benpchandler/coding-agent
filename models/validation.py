"""
Validation models for peer review system.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Result of agent validation of previous agent's work"""
    is_valid: bool
    confidence: float
    issues: List[str]
    feedback: str
    can_proceed: bool
    validation_details: Dict[str, Any]
    
    @classmethod
    def from_json_response(cls, json_str: str) -> 'ValidationResult':
        """Parse validation result from JSON response"""
        try:
            # Log the raw response for debugging
            logger.debug(f"Raw validation response: {json_str[:200]}...")

            # Try to extract JSON from the response if it's wrapped in text
            json_start = json_str.find('{')
            json_end = json_str.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_part = json_str[json_start:json_end]
                data = json.loads(json_part)
            else:
                # If no JSON found, create a simple validation result
                logger.warning(f"No JSON found in response, treating as invalid: {json_str[:100]}...")
                return cls(
                    is_valid=False,
                    confidence=0.5,
                    issues=["Response format was not JSON"],
                    feedback=f"The validation response was not in the expected JSON format. Response: {json_str[:200]}...",
                    can_proceed=False,
                    validation_details={"raw_response": json_str}
                )

            return cls(
                is_valid=data.get('is_valid', False),
                confidence=data.get('confidence', 0.0),
                issues=data.get('issues', []),
                feedback=data.get('feedback', ''),
                can_proceed=data.get('can_proceed', False),
                validation_details=data
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse validation result: {e}")
            logger.error(f"Raw response was: {json_str}")
            return cls(
                is_valid=False,
                confidence=0.0,
                issues=[f"Failed to parse validation response: {str(e)}"],
                feedback=f"Validation response was malformed. Error: {str(e)}. Response: {json_str[:200]}...",
                can_proceed=False,
                validation_details={"raw_response": json_str, "error": str(e)}
            )

@dataclass
class AgentResult:
    """Result from agent execution"""
    success: bool
    content: str
    agent_type: str
    task_id: str
    execution_time: float
    model_used: str
    
    # Peer review specific fields
    validation_performed: bool = False
    validation_result: Optional[ValidationResult] = None
    feedback_for_previous_agent: Optional[str] = None
    should_retry_previous: bool = False
    retry_attempt: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'success': self.success,
            'content': self.content,
            'agent_type': self.agent_type,
            'task_id': self.task_id,
            'execution_time': self.execution_time,
            'model_used': self.model_used,
            'validation_performed': self.validation_performed,
            'validation_result': self.validation_result.__dict__ if self.validation_result else None,
            'feedback_for_previous_agent': self.feedback_for_previous_agent,
            'should_retry_previous': self.should_retry_previous,
            'retry_attempt': self.retry_attempt
        }

@dataclass
class FeedbackEntry:
    """Single feedback entry between agents"""
    timestamp: datetime
    from_agent: str
    to_agent: str
    task_id: str
    feedback: str
    validation_confidence: float
    issues: List[str]
    retry_successful: Optional[bool] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'from_agent': self.from_agent,
            'to_agent': self.to_agent,
            'task_id': self.task_id,
            'feedback': self.feedback,
            'validation_confidence': self.validation_confidence,
            'issues': self.issues,
            'retry_successful': self.retry_successful
        }

class FeedbackTracker:
    """Tracks inter-agent feedback and learning patterns"""
    
    def __init__(self):
        self.feedback_log: List[FeedbackEntry] = []
        self.logger = logging.getLogger(f"{__name__}.FeedbackTracker")
    
    def record_feedback(self, from_agent: str, to_agent: str, task_id: str,
                       validation_result: ValidationResult) -> None:
        """Record feedback from one agent to another"""
        entry = FeedbackEntry(
            timestamp=datetime.now(),
            from_agent=from_agent,
            to_agent=to_agent,
            task_id=task_id,
            feedback=validation_result.feedback,
            validation_confidence=validation_result.confidence,
            issues=validation_result.issues
        )
        
        self.feedback_log.append(entry)
        
        # Log for monitoring
        self.logger.info(
            f"FEEDBACK: {from_agent} → {to_agent} (confidence: {validation_result.confidence:.2f}): "
            f"{validation_result.feedback[:100]}..."
        )
        
        # Save to file for analysis
        self._save_feedback_entry(entry)
    
    def update_retry_result(self, task_id: str, from_agent: str, 
                           to_agent: str, success: bool) -> None:
        """Update whether the retry after feedback was successful"""
        for entry in reversed(self.feedback_log):
            if (entry.task_id == task_id and 
                entry.from_agent == from_agent and 
                entry.to_agent == to_agent):
                entry.retry_successful = success
                break
    
    def get_feedback_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get feedback statistics by agent"""
        stats = {}
        
        for entry in self.feedback_log:
            agent = entry.to_agent
            if agent not in stats:
                stats[agent] = {
                    'received_count': 0,
                    'common_issues': [],
                    'retry_success_rate': 0.0,
                    'avg_confidence': 0.0
                }
            
            stats[agent]['received_count'] += 1
            stats[agent]['common_issues'].extend(entry.issues)
        
        # Calculate derived stats
        for agent, agent_stats in stats.items():
            agent_entries = [e for e in self.feedback_log if e.to_agent == agent]
            
            # Common issues (simplified)
            all_issues = []
            for entry in agent_entries:
                all_issues.extend(entry.issues)
            issue_counts = {}
            for issue in all_issues:
                issue_counts[issue] = issue_counts.get(issue, 0) + 1
            agent_stats['common_issues'] = sorted(issue_counts.keys(), 
                                                key=lambda x: issue_counts[x], reverse=True)[:5]
            
            # Retry success rate
            retry_entries = [e for e in agent_entries if e.retry_successful is not None]
            if retry_entries:
                successful_retries = sum(1 for e in retry_entries if e.retry_successful)
                agent_stats['retry_success_rate'] = successful_retries / len(retry_entries)
            
            # Average confidence
            if agent_entries:
                agent_stats['avg_confidence'] = sum(e.validation_confidence for e in agent_entries) / len(agent_entries)
        
        return stats
    
    def get_recent_feedback(self, hours: int = 24, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent feedback entries"""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = [e for e in self.feedback_log if e.timestamp > cutoff]
        recent.sort(key=lambda x: x.timestamp, reverse=True)
        return [e.to_dict() for e in recent[:limit]]
    
    def get_common_issues_for_agent(self, agent_type: str, limit: int = 5) -> List[str]:
        """Get most common issues for a specific agent"""
        agent_entries = [e for e in self.feedback_log if e.to_agent == agent_type]
        all_issues = []
        for entry in agent_entries:
            all_issues.extend(entry.issues)
        
        issue_counts = {}
        for issue in all_issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
        
        return sorted(issue_counts.keys(), key=lambda x: issue_counts[x], reverse=True)[:limit]
    
    def _save_feedback_entry(self, entry: FeedbackEntry) -> None:
        """Save feedback entry to file for analysis"""
        try:
            import os
            from pathlib import Path
            
            feedback_dir = Path("logs/feedback")
            feedback_dir.mkdir(parents=True, exist_ok=True)
            
            filename = feedback_dir / f"feedback_{entry.timestamp.strftime('%Y%m%d')}.jsonl"
            with open(filename, 'a') as f:
                f.write(json.dumps(entry.to_dict()) + '\n')
        except Exception as e:
            self.logger.error(f"Failed to save feedback entry: {e}")

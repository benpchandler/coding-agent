"""
Comprehensive prompt logging system to track the full prompt-response-feedback cycle
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict

@dataclass
class PromptExecution:
    """Complete record of a prompt execution"""
    timestamp: datetime
    task_id: str
    agent_type: str
    attempt_number: int  # 1 for first attempt, 2+ for retries
    
    # Prompt details
    prompt: str
    model: str
    temperature: float
    max_tokens: int
    
    # Response details
    response: str
    execution_time: float
    success: bool
    
    # Feedback cycle
    received_feedback: bool = False
    feedback_content: Optional[str] = None
    feedback_confidence: Optional[float] = None
    needs_retry: bool = False
    
    # Enhanced prompt (for retries)
    original_task: Optional[str] = None
    enhanced_task: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

class PromptLogger:
    """Logs complete prompt-response-feedback cycles for analysis"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.PromptLogger")
        self.executions: List[PromptExecution] = []
        
        # Create logs directory
        self.log_dir = Path("logs/prompts")
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def log_prompt_execution(self, 
                           task_id: str,
                           agent_type: str,
                           prompt: str,
                           response: str,
                           model: str = "gpt-4-turbo",
                           temperature: float = 0.7,
                           max_tokens: int = 4000,
                           execution_time: float = 0.0,
                           success: bool = True,
                           attempt_number: int = 1,
                           original_task: Optional[str] = None,
                           enhanced_task: Optional[str] = None) -> PromptExecution:
        """Log a complete prompt execution"""
        
        execution = PromptExecution(
            timestamp=datetime.now(),
            task_id=task_id,
            agent_type=agent_type,
            attempt_number=attempt_number,
            prompt=prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response=response,
            execution_time=execution_time,
            success=success,
            original_task=original_task,
            enhanced_task=enhanced_task
        )
        
        self.executions.append(execution)
        self._save_execution(execution)
        
        self.logger.info(
            f"PROMPT EXECUTION: {agent_type} attempt #{attempt_number} for {task_id} "
            f"({'SUCCESS' if success else 'FAILED'}) - {execution_time:.1f}s"
        )
        
        return execution
    
    def update_with_feedback(self, 
                           task_id: str, 
                           agent_type: str, 
                           attempt_number: int,
                           feedback_content: str,
                           feedback_confidence: float,
                           needs_retry: bool) -> None:
        """Update execution record with feedback information"""
        
        # Find the matching execution
        for execution in reversed(self.executions):
            if (execution.task_id == task_id and 
                execution.agent_type == agent_type and 
                execution.attempt_number == attempt_number):
                
                execution.received_feedback = True
                execution.feedback_content = feedback_content
                execution.feedback_confidence = feedback_confidence
                execution.needs_retry = needs_retry
                
                # Re-save with updated feedback
                self._save_execution(execution)
                
                self.logger.info(
                    f"FEEDBACK RECEIVED: {agent_type} attempt #{attempt_number} for {task_id} "
                    f"(confidence: {feedback_confidence:.2f}, retry: {needs_retry})"
                )
                break
    
    def get_prompt_success_rate(self, agent_type: str, hours: int = 24) -> Dict[str, Any]:
        """Get first-shot success rate for an agent"""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent_executions = [e for e in self.executions 
                           if e.agent_type == agent_type and e.timestamp > cutoff]
        
        if not recent_executions:
            return {"success_rate": 0.0, "total_attempts": 0, "first_shot_success": 0}
        
        first_attempts = [e for e in recent_executions if e.attempt_number == 1]
        successful_first_attempts = [e for e in first_attempts if not e.needs_retry]
        
        return {
            "success_rate": len(successful_first_attempts) / len(first_attempts) if first_attempts else 0.0,
            "total_attempts": len(recent_executions),
            "first_shot_success": len(successful_first_attempts),
            "first_attempts": len(first_attempts),
            "retry_attempts": len(recent_executions) - len(first_attempts)
        }
    
    def get_prompt_patterns(self, agent_type: str, successful_only: bool = True) -> List[Dict[str, Any]]:
        """Get prompt patterns for successful executions"""
        executions = [e for e in self.executions if e.agent_type == agent_type]
        
        if successful_only:
            executions = [e for e in executions if not e.needs_retry]
        
        patterns = []
        for execution in executions:
            patterns.append({
                "task_id": execution.task_id,
                "prompt_length": len(execution.prompt),
                "response_length": len(execution.response),
                "execution_time": execution.execution_time,
                "attempt_number": execution.attempt_number,
                "enhanced": execution.enhanced_task is not None,
                "feedback_confidence": execution.feedback_confidence
            })
        
        return patterns
    
    def get_feedback_analysis(self, agent_type: str) -> Dict[str, Any]:
        """Analyze feedback patterns for an agent"""
        executions = [e for e in self.executions 
                     if e.agent_type == agent_type and e.received_feedback]
        
        if not executions:
            return {"total_feedback": 0, "avg_confidence": 0.0, "retry_rate": 0.0}
        
        total_feedback = len(executions)
        avg_confidence = sum(e.feedback_confidence for e in executions) / total_feedback
        retry_count = sum(1 for e in executions if e.needs_retry)
        
        # Common feedback themes
        feedback_themes = {}
        for execution in executions:
            if execution.feedback_content:
                # Simple keyword extraction
                words = execution.feedback_content.lower().split()
                for word in words:
                    if len(word) > 4:  # Skip short words
                        feedback_themes[word] = feedback_themes.get(word, 0) + 1
        
        # Top themes
        top_themes = sorted(feedback_themes.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "total_feedback": total_feedback,
            "avg_confidence": avg_confidence,
            "retry_rate": retry_count / total_feedback,
            "common_themes": [{"theme": theme, "count": count} for theme, count in top_themes]
        }
    
    def _save_execution(self, execution: PromptExecution) -> None:
        """Save execution to file"""
        try:
            filename = self.log_dir / f"prompts_{execution.timestamp.strftime('%Y%m%d')}.jsonl"
            with open(filename, 'a') as f:
                f.write(json.dumps(execution.to_dict()) + '\n')
        except Exception as e:
            self.logger.error(f"Failed to save prompt execution: {e}")
    
    def export_analysis(self, output_file: str = "prompt_analysis.json") -> None:
        """Export comprehensive analysis to file"""
        analysis = {}
        
        # Get unique agent types
        agent_types = list(set(e.agent_type for e in self.executions))
        
        for agent_type in agent_types:
            analysis[agent_type] = {
                "success_rate": self.get_prompt_success_rate(agent_type),
                "feedback_analysis": self.get_feedback_analysis(agent_type),
                "prompt_patterns": self.get_prompt_patterns(agent_type)
            }
        
        with open(output_file, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        
        self.logger.info(f"Analysis exported to {output_file}")

# Global instance
prompt_logger = PromptLogger()

# Example usage
if __name__ == "__main__":
    from datetime import timedelta
    
    # Test the logger
    logger = PromptLogger()
    
    # Log a prompt execution
    execution = logger.log_prompt_execution(
        task_id="TEST-001",
        agent_type="code_generation",
        prompt="Create a Python function that validates email addresses",
        response="def validate_email(email): ...",
        execution_time=2.5,
        success=True
    )
    
    # Update with feedback
    logger.update_with_feedback(
        task_id="TEST-001",
        agent_type="code_generation", 
        attempt_number=1,
        feedback_content="Missing error handling",
        feedback_confidence=0.8,
        needs_retry=True
    )
    
    # Get analysis
    success_rate = logger.get_prompt_success_rate("code_generation")
    print(f"Success rate: {success_rate}")
    
    feedback_analysis = logger.get_feedback_analysis("code_generation")
    print(f"Feedback analysis: {feedback_analysis}")

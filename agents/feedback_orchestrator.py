"""
Feedback-aware orchestrator that manages peer review workflow.
"""

import os
import sys
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from models.task import Task, TaskStatus
from models.validation import AgentResult, FeedbackTracker, ValidationResult
from agents import decomposer
from agents.code_generation_agent_enhanced import CodeGenerationAgentEnhanced
from agents.testing_agent_enhanced import TestingAgentEnhanced
from agents.quality_assessment_agent_enhanced import QualityAssessmentAgentEnhanced

class FeedbackOrchestrator:
    """Orchestrator that manages peer review workflow with feedback loops"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.FeedbackOrchestrator")
        
        # Initialize agents
        self.agents = {
            'decomposer': None,  # Will use function-based decomposer
            'code_generation': CodeGenerationAgentEnhanced(),
            'testing': TestingAgentEnhanced(),
            'quality_assessment': QualityAssessmentAgentEnhanced()
        }
        
        # Feedback tracking
        self.feedback_tracker = FeedbackTracker()
        
        # Workflow configuration
        self.workflow = ['decomposer', 'code_generation', 'testing', 'quality_assessment']
        self.max_retries = 2
        self.retry_counts = {}
    
    async def process_task_with_feedback(self, task: Task) -> Dict[str, Any]:
        """Process task through peer review workflow with feedback loops"""
        
        self.logger.info(f"Starting peer review workflow for task {task.task_id}")
        start_time = time.time()
        
        # Initialize tracking
        self.retry_counts[task.task_id] = {agent: 0 for agent in self.workflow}
        outputs = {}
        agent_results = {}
        
        try:
            # Process through workflow
            for i, agent_type in enumerate(self.workflow):
                self.logger.info(f"Processing with {agent_type}")
                
                # Get previous output if available
                previous_output = None
                previous_agent_type = None
                if i > 0:
                    previous_agent_type = self.workflow[i-1]
                    previous_output = outputs.get(previous_agent_type)
                
                # Execute agent with peer review
                result = await self._execute_agent_with_retry(
                    agent_type, task, previous_output, previous_agent_type
                )
                
                agent_results[agent_type] = result
                
                if result.success:
                    outputs[agent_type] = result.content
                    self.logger.info(f"{agent_type} completed successfully")
                else:
                    self.logger.error(f"{agent_type} failed: {result.content}")
                    return self._create_failure_result(task, agent_type, result, agent_results)
            
            # All agents completed successfully
            execution_time = time.time() - start_time
            
            return {
                'success': True,
                'task_id': task.task_id,
                'execution_time': execution_time,
                'outputs': outputs,
                'agent_results': agent_results,
                'feedback_summary': self._generate_feedback_summary(task.task_id),
                'quality_score': self._extract_quality_score(outputs.get('quality_assessment', '')),
                'recommendation': self._get_final_recommendation(outputs.get('quality_assessment', ''))
            }
            
        except Exception as e:
            self.logger.error(f"Workflow failed for task {task.task_id}: {str(e)}")
            execution_time = time.time() - start_time

            return {
                'success': False,
                'task_id': task.task_id,
                'execution_time': execution_time,
                'error': str(e),
                'outputs': outputs,
                'agent_results': agent_results
            }
    
    async def _execute_agent_with_retry(self, agent_type: str, task: Task, 
                                      previous_output: Optional[str],
                                      previous_agent_type: Optional[str]) -> AgentResult:
        """Execute agent with retry logic for feedback loops"""
        
        agent = self.agents[agent_type]
        
        # Handle different agent types
        if agent_type == 'decomposer':
            # Use function-based decomposer
            result = await self._execute_decomposer_function(task)
        else:
            # Enhanced agents with peer review
            result = await agent.execute(task, previous_output, previous_agent_type)
        
        # Handle validation failure and retry
        if not result.success and result.should_retry_previous and previous_agent_type:
            retry_count = self.retry_counts[task.task_id][previous_agent_type]
            
            if retry_count < self.max_retries:
                self.logger.info(f"Retrying {previous_agent_type} due to validation failure")
                
                # Increment retry count
                self.retry_counts[task.task_id][previous_agent_type] += 1
                
                # Retry previous agent with feedback
                previous_agent = self.agents[previous_agent_type]
                
                if previous_agent_type == 'decomposer':
                    # Handle decomposer retry
                    retry_result = await self._retry_decomposer_function_with_feedback(
                        task, result.feedback_for_previous_agent
                    )
                else:
                    # Enhanced agent retry
                    retry_result = await previous_agent.retry_with_feedback(
                        task, result.feedback_for_previous_agent,
                        previous_output if len(self.workflow) > 2 else None
                    )
                
                # Update feedback tracker with retry result
                self.feedback_tracker.update_retry_result(
                    task.task_id, agent_type, previous_agent_type, retry_result.success
                )
                
                if retry_result.success:
                    # Retry current agent with new input
                    self.logger.info(f"Retrying {agent_type} with improved input")
                    if agent_type == 'decomposer':
                        result = await self._execute_decomposer_function(task)
                    else:
                        result = await agent.execute(task, retry_result.content, previous_agent_type)
                else:
                    self.logger.error(f"Retry of {previous_agent_type} failed")
                    return retry_result
            else:
                self.logger.error(f"Max retries exceeded for {previous_agent_type}")
                result.content = f"Max retries exceeded for {previous_agent_type}. Last feedback: {result.feedback_for_previous_agent}"
        
        return result
    
    async def _execute_decomposer_function(self, task: Task) -> AgentResult:
        """Execute function-based decomposer and wrap result"""
        start_time = time.time()

        try:
            # Call the decomposer function
            subtasks = decomposer.decompose_feature(task.description)
            execution_time = time.time() - start_time

            # Format the decomposition content
            content = "TASK DECOMPOSITION:\n\n"
            for i, subtask in enumerate(subtasks, 1):
                content += f"{i}. {subtask.get('title', 'Untitled Task')}\n"
                content += f"   Description: {subtask.get('description', 'No description')}\n"
                content += f"   Priority: {subtask.get('priority', 50)}\n"
                if subtask.get('dependencies'):
                    content += f"   Dependencies: {', '.join(subtask['dependencies'])}\n"
                content += "\n"

            return AgentResult(
                success=True,
                content=content,
                agent_type='decomposer',
                task_id=task.task_id,
                execution_time=execution_time,
                model_used='gpt-5-nano'
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return AgentResult(
                success=False,
                content=f"Decomposer error: {str(e)}",
                agent_type='decomposer',
                task_id=task.task_id,
                execution_time=execution_time,
                model_used='gpt-5-nano'
            )
    
    async def _retry_decomposer_function_with_feedback(self, task: Task, feedback: str) -> AgentResult:
        """Retry function-based decomposer with feedback"""
        # Enhance task description with feedback
        enhanced_description = f"""
        ORIGINAL TASK: {task.description}

        FEEDBACK FROM CODE GENERATION AGENT: {feedback}

        Please improve the task decomposition based on this feedback.
        """

        # Create enhanced task
        enhanced_task = Task(
            description=enhanced_description,
            language=task.language,
            priority=task.priority
        )
        # Copy the task_id
        enhanced_task.task_id = task.task_id

        return await self._execute_decomposer_function(enhanced_task)
    
    def _create_failure_result(self, task: Task, failed_agent: str, 
                             result: AgentResult, agent_results: Dict[str, AgentResult]) -> Dict[str, Any]:
        """Create failure result with diagnostic information"""
        return {
            'success': False,
            'task_id': task.task_id,
            'failed_at': failed_agent,
            'failure_reason': result.content,
            'agent_results': agent_results,
            'feedback_summary': self._generate_feedback_summary(task.task_id),
            'retry_counts': self.retry_counts.get(task.task_id, {}),
            'recommendation': 'Task failed - review feedback and retry'
        }
    
    def _generate_feedback_summary(self, task_id: str) -> Dict[str, Any]:
        """Generate summary of feedback for this task"""
        task_feedback = [
            entry for entry in self.feedback_tracker.feedback_log 
            if entry.task_id == task_id
        ]
        
        summary = {
            'total_feedback_instances': len(task_feedback),
            'feedback_by_agent': {},
            'common_issues': [],
            'retry_success_rate': 0.0
        }
        
        if task_feedback:
            # Group by receiving agent
            for entry in task_feedback:
                agent = entry.to_agent
                if agent not in summary['feedback_by_agent']:
                    summary['feedback_by_agent'][agent] = []
                summary['feedback_by_agent'][agent].append({
                    'from': entry.from_agent,
                    'feedback': entry.feedback[:100] + '...' if len(entry.feedback) > 100 else entry.feedback,
                    'confidence': entry.validation_confidence,
                    'retry_successful': entry.retry_successful
                })
            
            # Calculate retry success rate
            retries_with_outcome = [e for e in task_feedback if e.retry_successful is not None]
            if retries_with_outcome:
                successful_retries = sum(1 for e in retries_with_outcome if e.retry_successful)
                summary['retry_success_rate'] = successful_retries / len(retries_with_outcome)
            
            # Collect common issues
            all_issues = []
            for entry in task_feedback:
                all_issues.extend(entry.issues)
            summary['common_issues'] = list(set(all_issues))
        
        return summary
    
    def _extract_quality_score(self, quality_output: str) -> float:
        """Extract quality score from quality assessment output"""
        try:
            import re
            score_match = re.search(r'OVERALL QUALITY SCORE:\s*(\d+(?:\.\d+)?)', quality_output)
            if score_match:
                return float(score_match.group(1))
        except Exception:
            pass
        return 0.0
    
    def _get_final_recommendation(self, quality_output: str) -> str:
        """Extract final recommendation from quality assessment"""
        if 'APPROVED FOR INTEGRATION' in quality_output:
            return 'APPROVED'
        elif 'NEEDS IMPROVEMENT' in quality_output:
            return 'NEEDS_IMPROVEMENT'
        elif 'REJECTED' in quality_output:
            return 'REJECTED'
        else:
            return 'UNKNOWN'
    
    def get_workflow_stats(self) -> Dict[str, Any]:
        """Get overall workflow statistics"""
        return {
            'feedback_stats': self.feedback_tracker.get_feedback_stats(),
            'recent_feedback': self.feedback_tracker.get_recent_feedback(),
            'workflow_agents': self.workflow,
            'max_retries': self.max_retries
        }

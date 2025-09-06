"""
Enhanced base agent class with peer review capabilities.
"""

import os
import json
import time
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from openai import OpenAI
from dotenv import load_dotenv

from models.task import Task
from models.validation import ValidationResult, AgentResult, FeedbackTracker
from models.prompt_logger import prompt_logger

# Load environment variables
load_dotenv()

class BaseAgentEnhanced(ABC):
    """Enhanced base agent with peer review validation capabilities"""
    
    def __init__(self, agent_type: str, config_path: Optional[str] = None):
        self.agent_type = agent_type
        self.logger = logging.getLogger(f"{__name__}.{agent_type}")
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Model configuration
        self.model = self.config.get("model", "gpt-4-turbo")
        self.temperature = self.config.get("temperature", 0.1)
        self.max_tokens = self.config.get("max_tokens", 4000)
        
        # Feedback tracker (shared instance)
        self.feedback_tracker = FeedbackTracker()
    
    async def execute(self, task: Task, previous_output: Optional[str] = None, 
                     previous_agent_type: Optional[str] = None) -> AgentResult:
        """Execute agent with peer review validation"""
        start_time = time.time()
        
        try:
            # Step 1: Validate previous agent's work (if any)
            validation_result = None
            if previous_output and previous_agent_type:
                self.logger.info(f"Validating output from {previous_agent_type}")
                validation_result = await self._validate_previous_work(previous_output, task)
                
                if not validation_result.is_valid:
                    # Record feedback and request retry
                    self.feedback_tracker.record_feedback(
                        from_agent=self.agent_type,
                        to_agent=previous_agent_type,
                        task_id=task.task_id,
                        validation_result=validation_result
                    )

                    # Update prompt logger with feedback
                    prompt_logger.update_with_feedback(
                        task_id=task.task_id,
                        agent_type=previous_agent_type,
                        attempt_number=1,  # This is feedback on the first attempt
                        feedback_content=validation_result.feedback,
                        feedback_confidence=validation_result.confidence,
                        needs_retry=True
                    )
                    
                    execution_time = time.time() - start_time
                    return AgentResult(
                        success=False,
                        content="",
                        agent_type=self.agent_type,
                        task_id=task.task_id,
                        execution_time=execution_time,
                        model_used=self.model,
                        validation_performed=True,
                        validation_result=validation_result,
                        feedback_for_previous_agent=validation_result.feedback,
                        should_retry_previous=True
                    )
            
            # Step 2: Do our own work
            self.logger.info(f"Executing {self.agent_type} for task {task.task_id}")
            content = await self._do_agent_work(task, previous_output)
            
            execution_time = time.time() - start_time
            
            return AgentResult(
                success=True,
                content=content,
                agent_type=self.agent_type,
                task_id=task.task_id,
                execution_time=execution_time,
                model_used=self.model,
                validation_performed=validation_result is not None,
                validation_result=validation_result
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Error in {self.agent_type}: {str(e)}")
            
            return AgentResult(
                success=False,
                content=f"Error: {str(e)}",
                agent_type=self.agent_type,
                task_id=task.task_id,
                execution_time=execution_time,
                model_used=self.model,
                validation_performed=validation_result is not None,
                validation_result=validation_result
            )
    
    async def retry_with_feedback(self, task: Task, feedback: str, 
                                 previous_output: Optional[str] = None) -> AgentResult:
        """Retry agent execution with specific feedback"""
        self.logger.info(f"Retrying {self.agent_type} with feedback: {feedback[:100]}...")
        
        # Incorporate feedback into the prompt
        enhanced_task = self._enhance_task_with_feedback(task, feedback)
        
        # Execute with enhanced context
        result = await self.execute(enhanced_task, previous_output)
        result.retry_attempt = 1
        
        return result
    
    async def _validate_previous_work(self, previous_output: str, task: Task) -> ValidationResult:
        """Validate the previous agent's output"""
        validation_prompt = self._build_validation_prompt(previous_output, task)
        
        try:
            messages = [{"role": "user", "content": validation_prompt}]
            response_content = await self._make_openai_request(
                messages,
                temperature=0.1,
                task_id=task.task_id,
                attempt_number=1
            )

            return ValidationResult.from_json_response(response_content)
            
        except Exception as e:
            self.logger.error(f"Validation failed: {str(e)}")
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                issues=[f"Validation error: {str(e)}"],
                feedback=f"Could not validate previous work due to error: {str(e)}",
                can_proceed=False,
                validation_details={}
            )
    
    @abstractmethod
    def _build_validation_prompt(self, previous_output: str, task: Task) -> str:
        """Build validation prompt specific to this agent's needs"""
        pass
    
    @abstractmethod
    async def _do_agent_work(self, task: Task, previous_output: Optional[str] = None) -> str:
        """Perform the agent's core work"""
        pass
    
    def _enhance_task_with_feedback(self, task: Task, feedback: str) -> Task:
        """Enhance task description with feedback for retry - creates clean, improved prompt"""
        from agents.feedback_parser import FeedbackParser

        parser = FeedbackParser()
        enhanced_description = parser.create_clean_prompt_enhancement(
            task.description, feedback, self.agent_type
        )

        # Create a copy of the task with enhanced description
        enhanced_task = Task(
            description=enhanced_description,
            language=task.language,
            priority=task.priority
        )
        # Copy the task_id
        enhanced_task.task_id = task.task_id

        return enhanced_task
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load agent configuration"""
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        
        # Default configuration
        return {
            "model": "gpt-4-turbo",
            "temperature": 0.1,
            "max_tokens": 4000
        }
    
    async def _make_openai_request(self, messages: List[Dict[str, str]],
                                  temperature: Optional[float] = None,
                                  task_id: Optional[str] = None,
                                  attempt_number: int = 1) -> str:
        """Make OpenAI API request with error handling and logging"""
        import time
        start_time = time.time()

        # Extract prompt from messages
        prompt = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=self.max_tokens
            )

            execution_time = time.time() - start_time
            response_content = response.choices[0].message.content

            # Log the complete prompt-response cycle
            if task_id:
                prompt_logger.log_prompt_execution(
                    task_id=task_id,
                    agent_type=self.agent_type,
                    prompt=prompt,
                    response=response_content,
                    model=self.model,
                    temperature=temperature or self.temperature,
                    max_tokens=self.max_tokens,
                    execution_time=execution_time,
                    success=True,
                    attempt_number=attempt_number
                )

            return response_content

        except Exception as e:
            execution_time = time.time() - start_time

            # Log failed execution
            if task_id:
                prompt_logger.log_prompt_execution(
                    task_id=task_id,
                    agent_type=self.agent_type,
                    prompt=prompt,
                    response=f"ERROR: {str(e)}",
                    model=self.model,
                    temperature=temperature or self.temperature,
                    max_tokens=self.max_tokens,
                    execution_time=execution_time,
                    success=False,
                    attempt_number=attempt_number
                )

            self.logger.error(f"OpenAI API request failed: {str(e)}")
            raise
    
    def get_common_validation_issues(self) -> List[str]:
        """Get common validation issues this agent has reported"""
        return self.feedback_tracker.get_common_issues_for_agent(self.agent_type)
    
    def get_feedback_stats(self) -> Dict[str, Any]:
        """Get feedback statistics for this agent"""
        all_stats = self.feedback_tracker.get_feedback_stats()
        return all_stats.get(self.agent_type, {
            'received_count': 0,
            'common_issues': [],
            'retry_success_rate': 0.0,
            'avg_confidence': 0.0
        })

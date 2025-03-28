"""
Task model for representing development tasks.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid

class TaskStatus(Enum):
    """Task status enumeration"""
    CREATED = "created"
    DECOMPOSING = "decomposing"
    READY_FOR_IMPLEMENTATION = "ready_for_implementation"
    IMPLEMENTING = "implementing"
    READY_FOR_TESTING = "ready_for_testing"
    TESTING = "testing"
    READY_FOR_QUALITY = "ready_for_quality"
    QUALITY_CHECK = "quality_check"
    READY_FOR_INTEGRATION = "ready_for_integration"
    INTEGRATING = "integrating"
    COMPLETED = "completed"
    FAILED = "failed"
    ERROR = "error"
    NEEDS_REVISION = "needs_revision"

class Task:
    """
    Represents a development task with its associated metadata, code, and status.
    """
    
    def __init__(self, description: str, language: str, requirements: List[str] = None, priority: float = 50.0):
        """
        Initialize a new task.
        
        Args:
            description (str): Task description
            language (str): Programming language
            requirements (List[str], optional): List of requirements. Defaults to None.
            priority (float, optional): Priority score from 0-100. Defaults to 50.0.
                Higher values indicate higher priority.
                - 90-100: Critical/Blocking issues
                - 70-89: High priority features
                - 40-69: Normal priority tasks
                - 20-39: Low priority enhancements
                - 0-19: Nice-to-have features
        """
        self.task_id = f"TASK-{str(uuid.uuid4())[:8]}"
        self.description = description
        self.language = language
        self.requirements = requirements or []
        self.priority = max(0.0, min(100.0, priority))  # Clamp between 0 and 100
        self.status = TaskStatus.CREATED
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.history = []
        
        # Project and task relationships
        self.project_id = None  # Reference to parent project
        self.parent_task_id = None  # Reference to parent task if it's a subtask
        self.subtask_ids = []  # List of child task IDs
        self.related_task_ids = []  # Tasks that are related but not hierarchical
        
        # Implementation details
        self.code = {
            "files": [],
            "tests": []
        }
        self.test_results = None
        self.quality_results = None
        self.integration_results = None
        
    def update_status(self, status: TaskStatus, message: str = None):
        """
        Update the task status and add a history entry.
        
        Args:
            status (TaskStatus): New status
            message (str, optional): Status update message. Defaults to None.
        """
        self.status = status
        self.updated_at = datetime.now().isoformat()
        
        history_entry = {
            "timestamp": self.updated_at,
            "status": status.value,
            "message": message or f"Status updated to {status.value}"
        }
        self.history.append(history_entry)
        
    def update_priority(self, new_priority: float, reason: str = None):
        """
        Update the task's priority score.
        
        Args:
            new_priority (float): New priority score (0-100)
            reason (str, optional): Reason for priority change. Defaults to None.
        """
        old_priority = self.priority
        self.priority = max(0.0, min(100.0, new_priority))  # Clamp between 0 and 100
        self.updated_at = datetime.now().isoformat()
        
        history_entry = {
            "timestamp": self.updated_at,
            "type": "priority_change",
            "old_priority": old_priority,
            "new_priority": self.priority,
            "message": reason or f"Priority updated from {old_priority} to {self.priority}"
        }
        self.history.append(history_entry)
        
    def add_related_task(self, task_id: str, relationship_type: str = "related"):
        """
        Add a related task reference.
        
        Args:
            task_id (str): ID of the related task
            relationship_type (str, optional): Type of relationship. Defaults to "related".
        """
        if task_id not in self.related_task_ids:
            self.related_task_ids.append(task_id)
            self.updated_at = datetime.now().isoformat()
            
            history_entry = {
                "timestamp": self.updated_at,
                "type": "relationship_added",
                "related_task": task_id,
                "relationship_type": relationship_type
            }
            self.history.append(history_entry)
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert task to dictionary representation.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the task
        """
        return {
            "task_id": self.task_id,
            "description": self.description,
            "language": self.language,
            "requirements": self.requirements,
            "priority": self.priority,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "history": self.history,
            "project_id": self.project_id,
            "parent_task_id": self.parent_task_id,
            "subtask_ids": self.subtask_ids,
            "related_task_ids": self.related_task_ids,
            "code": self.code,
            "test_results": self.test_results,
            "quality_results": self.quality_results,
            "integration_results": self.integration_results
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """
        Create a Task instance from a dictionary.
        
        Args:
            data (Dict[str, Any]): Dictionary containing task data
            
        Returns:
            Task: New Task instance
        """
        task = cls(
            data["description"], 
            data["language"], 
            data.get("requirements", []),
            data.get("priority", 50.0)
        )
        task.task_id = data["task_id"]
        task.status = TaskStatus(data["status"])
        task.created_at = data["created_at"]
        task.updated_at = data["updated_at"]
        task.history = data["history"]
        task.project_id = data.get("project_id")
        task.parent_task_id = data.get("parent_task_id")
        task.subtask_ids = data.get("subtask_ids", [])
        task.related_task_ids = data.get("related_task_ids", [])
        task.code = data["code"]
        task.test_results = data.get("test_results")
        task.quality_results = data.get("quality_results")
        task.integration_results = data.get("integration_results")
        return task

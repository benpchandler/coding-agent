"""
Project model for managing collections of related tasks.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
import os
import json
from .task import Task, TaskStatus

class ProjectStatus(Enum):
    """Project status enumeration"""
    CREATED = "created"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    FAILED = "failed"

class Project:
    """
    Represents a development project that contains multiple related tasks.
    """
    
    def __init__(self, name: str, description: str, base_path: str = "projects"):
        """
        Initialize a new project.
        
        Args:
            name (str): Project name
            description (str): Project description
            base_path (str): Base directory for project files
        """
        self.project_id = f"PROJ-{str(uuid.uuid4())[:8]}"
        self.name = name
        self.description = description
        self.root_tasks = []  # Top-level task IDs
        self.all_tasks = []  # List of all task IDs
        self.tasks = {}  # Map of task_id to Task objects
        self.status = ProjectStatus.CREATED
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.base_path = base_path
        self.project_path = os.path.join(base_path, self.project_id)
        
        # Create project directory structure
        self._create_directory_structure()
        
    def _create_directory_structure(self):
        """Create the project's directory structure"""
        dirs = [
            self.project_path,
            os.path.join(self.project_path, "tasks"),
            os.path.join(self.project_path, "implementations"),
            os.path.join(self.project_path, "tests"),
            os.path.join(self.project_path, "docs")
        ]
        for dir_path in dirs:
            os.makedirs(dir_path, exist_ok=True)
            
    def add_task(self, task: Task, parent_task_id: Optional[str] = None) -> None:
        """
        Add a task to the project.
        
        Args:
            task (Task): Task to add
            parent_task_id (Optional[str]): ID of parent task if this is a subtask
        """
        task.project_id = self.project_id
        
        if parent_task_id:
            if parent_task_id not in self.tasks:
                raise ValueError(f"Parent task {parent_task_id} not found")
                
            parent_task = self.tasks[parent_task_id]
            task.parent_task_id = parent_task_id
            parent_task.subtask_ids.append(task.task_id)
            self._save_task(parent_task)
        else:
            self.root_tasks.append(task.task_id)
            
        self.tasks[task.task_id] = task
        self.all_tasks.append(task.task_id)
        self._save_task(task)
        self._save_project_state()
        
    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a task by ID.
        
        Args:
            task_id (str): Task ID to retrieve
            
        Returns:
            Optional[Task]: Task if found, None otherwise
        """
        return self.tasks.get(task_id)
        
    def get_task_subtasks(self, task_id: str) -> List[Task]:
        """
        Get all subtasks for a given task.
        
        Args:
            task_id (str): Task ID to get subtasks for
            
        Returns:
            List[Task]: List of subtask objects
        """
        task = self.get_task(task_id)
        if not task:
            return []
            
        return [self.tasks[subtask_id] for subtask_id in task.subtask_ids]
        
    def update_task_status(self, task_id: str, status: TaskStatus, message: str = None) -> None:
        """
        Update a task's status and propagate changes.
        
        Args:
            task_id (str): Task ID to update
            status (TaskStatus): New status
            message (str, optional): Status update message
        """
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
            
        task.update_status(status, message)
        self._save_task(task)
        
        # If task is completed, check if parent task can be updated
        if status == TaskStatus.COMPLETED and task.parent_task_id:
            self._check_parent_task_completion(task.parent_task_id)
            
        # Update project status based on root tasks
        self._update_project_status()
        
    def _check_parent_task_completion(self, parent_task_id: str) -> None:
        """Check if a parent task can be marked as completed"""
        parent_task = self.get_task(parent_task_id)
        if not parent_task:
            return
            
        # Check if all subtasks are completed
        subtasks = self.get_task_subtasks(parent_task_id)
        if all(task.status == TaskStatus.COMPLETED for task in subtasks):
            self.update_task_status(
                parent_task_id,
                TaskStatus.COMPLETED,
                "All subtasks completed"
            )
            
    def _update_project_status(self) -> None:
        """Update project status based on root tasks"""
        if not self.root_tasks:
            return
            
        root_task_statuses = [
            self.tasks[task_id].status
            for task_id in self.root_tasks
            if task_id in self.tasks
        ]
        
        if all(status == TaskStatus.COMPLETED for status in root_task_statuses):
            self.status = ProjectStatus.COMPLETED
        elif any(status == TaskStatus.FAILED for status in root_task_statuses):
            self.status = ProjectStatus.FAILED
        else:
            self.status = ProjectStatus.ACTIVE
            
        self._save_project_state()
        
    def _save_task(self, task: Task) -> None:
        """Save task to file"""
        task_dir = os.path.join(self.project_path, "tasks")
        task_path = os.path.join(task_dir, f"{task.task_id}.json")
        
        with open(task_path, 'w') as f:
            json.dump(task.to_dict(), f, indent=4)
            
    def _save_project_state(self) -> None:
        """Save project state to file"""
        project_file = os.path.join(self.project_path, "project.json")
        
        project_state = {
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "root_tasks": self.root_tasks,
            "all_tasks": self.all_tasks,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": datetime.now().isoformat()
        }
        
        with open(project_file, 'w') as f:
            json.dump(project_state, f, indent=4)
            
    @classmethod
    def load_project(cls, project_id: str, base_path: str = "projects") -> Optional['Project']:
        """
        Load a project from disk.
        
        Args:
            project_id (str): Project ID to load
            base_path (str): Base directory for project files
            
        Returns:
            Optional[Project]: Project if found, None otherwise
        """
        project_path = os.path.join(base_path, project_id)
        project_file = os.path.join(project_path, "project.json")
        
        if not os.path.exists(project_file):
            return None
            
        with open(project_file, 'r') as f:
            project_data = json.load(f)
            
        project = cls(project_data["name"], project_data["description"], base_path)
        project.project_id = project_data["project_id"]
        project.root_tasks = project_data["root_tasks"]
        project.all_tasks = project_data["all_tasks"]
        project.status = ProjectStatus(project_data["status"])
        project.created_at = project_data["created_at"]
        project.updated_at = project_data["updated_at"]
        
        # Load all tasks
        tasks_dir = os.path.join(project_path, "tasks")
        for task_file in os.listdir(tasks_dir):
            if task_file.endswith(".json"):
                task_path = os.path.join(tasks_dir, task_file)
                with open(task_path, 'r') as f:
                    task_data = json.load(f)
                    task = Task.from_dict(task_data)
                    project.tasks[task.task_id] = task
                    
        return project 

    def save(self) -> None:
        """Save project state to file"""
        self._save_project_state() 
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any], base_path: str = "projects") -> 'Project':
        """
        Create a project from a dictionary.
        
        Args:
            data (Dict[str, Any]): Dictionary containing project data
            base_path (str): Base directory for project files
            
        Returns:
            Project: The created project
        """
        project = cls(data["name"], data["description"], base_path)
        project.project_id = data["project_id"]
        project.root_tasks = data["root_tasks"]
        project.all_tasks = data.get("all_tasks", [])  # For backward compatibility
        project.status = ProjectStatus(data["status"])
        project.created_at = data["created_at"]
        project.updated_at = data["updated_at"]
        return project 
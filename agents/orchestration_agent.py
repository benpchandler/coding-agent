import os
import json
import logging
import subprocess
import sys
import threading
import time
from typing import Dict, Optional, List
from datetime import datetime
from common.logging_utils import setup_logger
from common.json_utils import load_json, save_json
from models.task import Task, TaskStatus
from models.project import Project, ProjectStatus
from agents.decomposer import decompose_task
from agents.code_generation_agent import process_task as generate_code
from agents.testing_agent import validate_implementation as run_tests
from agents.quality_assessment_agent import assess_quality
from agents.integration_agent import integrate_task
from queue import PriorityQueue

class OrchestratorAgent:
    """
    Orchestrates the entire development workflow including task decomposition,
    implementation, testing, and quality assessment.
    """
    
    def __init__(self, base_path: str):
        """
        Initialize the orchestrator with configuration and directory settings.
        
        Args:
            base_path (str): Base directory for project files
        """
        self.base_path = base_path
        self.projects: Dict[str, Project] = {}
        self.tasks: Dict[str, Task] = {}
        self.logger = setup_logger(__name__)
        
        # Initialize locks
        self.tasks_lock = threading.Lock()
        self.task_queue_lock = threading.Lock()
        
        # Initialize task queue
        self.task_queue = PriorityQueue()
        
        # Create directory structure if it doesn't exist
        os.makedirs(os.path.join(base_path, "projects"), exist_ok=True)
        os.makedirs(os.path.join(base_path, "tasks"), exist_ok=True)
        os.makedirs(os.path.join(base_path, "implementations"), exist_ok=True)
        os.makedirs(os.path.join(base_path, "tests"), exist_ok=True)
        os.makedirs(os.path.join(base_path, "quality"), exist_ok=True)
        os.makedirs(os.path.join(base_path, "integration"), exist_ok=True)
        
        # Load projects and tasks
        self.load_projects()
        self.load_tasks()
        
        self.running = False
        self.processing_thread = None
        
        self.logger.info("Orchestrator initialized with directory structure:")
        self.logger.info(f"Projects: {os.path.join(base_path, 'projects')}")
        self.logger.info(f"Tasks: {os.path.join(base_path, 'tasks')}")
        self.logger.info(f"Implementations: {os.path.join(base_path, 'implementations')}")
        self.logger.info(f"Tests: {os.path.join(base_path, 'tests')}")
        self.logger.info(f"Quality Assessment: {os.path.join(base_path, 'quality')}")
        self.logger.info(f"Integration Tests: {os.path.join(base_path, 'integration')}")
    
    def start(self):
        """Start the orchestration agent"""
        self.logger.info("Starting orchestration agent")
        
        # Load existing tasks
        self._load_tasks()
        
        # Start task processing thread
        self.running = True
        self.processing_thread = threading.Thread(target=self._process_tasks)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        self.logger.info("Orchestration agent started")
    
    def stop(self):
        """Stop the orchestration agent"""
        self.logger.info("Stopping orchestration agent")
        self.running = False
        
        if self.processing_thread:
            self.processing_thread.join(timeout=5.0)
            
        self.logger.info("Orchestration agent stopped")
    
    def get_project_structure(self) -> Dict[str, List[str]]:
        """
        Get the current project structure.
        
        Returns:
            Dict[str, List[str]]: Dictionary mapping directory types to their contents
        """
        structure = {}
        
        for dir_name, dir_path in [
            ("projects", os.path.join(self.base_path, "projects")),
            ("tasks", os.path.join(self.base_path, "tasks")),
            ("implementations", os.path.join(self.base_path, "implementations")),
            ("tests", os.path.join(self.base_path, "tests")),
            ("quality", os.path.join(self.base_path, "quality")),
            ("integration", os.path.join(self.base_path, "integration"))
        ]:
            if os.path.exists(dir_path):
                structure[dir_name] = sorted(os.listdir(dir_path))
            else:
                structure[dir_name] = []
        
        return structure
    
    def validate_structure(self) -> List[str]:
        """
        Validate the project structure and relationships between files.
        
        Returns:
            List[str]: List of any issues found
        """
        issues = []
        
        # Get all task IDs
        task_files = [f for f in os.listdir(os.path.join(self.base_path, "tasks")) if f.endswith('.json')]
        task_ids = [os.path.splitext(f)[0] for f in task_files]
        
        for task_id in task_ids:
            # Check for implementation
            impl_py = f"{task_id.lower().replace('-', '_')}.py"
            impl_jsx = f"{task_id.lower().replace('-', '_')}.jsx"
            if not os.path.exists(os.path.join(os.path.join(self.base_path, "implementations"), impl_py)) and \
               not os.path.exists(os.path.join(os.path.join(self.base_path, "implementations"), impl_jsx)):
                issues.append(f"Missing implementation for task {task_id}")
            
            # Check for tests
            test_file = f"test_{task_id.lower().replace('-', '_')}.py"
            if not os.path.exists(os.path.join(os.path.join(self.base_path, "tests"), test_file)):
                issues.append(f"Missing tests for task {task_id}")
            
            # Check for quality results
            quality_dir = os.path.join(os.path.join(self.base_path, "quality"), task_id)
            if not os.path.exists(quality_dir):
                issues.append(f"Missing quality assessment for task {task_id}")
        
        return issues

    def _run_script(self, script_path: str, args: List[str] = None) -> subprocess.CompletedProcess:
        """
        Run a Python script with optional arguments
        
        Args:
            script_path (str): Path to the Python script
            args (List[str], optional): Arguments to pass to the script
        
        Returns:
            subprocess.CompletedProcess: Result of script execution
        """
        cmd = [sys.executable, script_path]
        if args:
            cmd.extend(args)
        
        self.logger.info(f"Running script: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=True
            )
            self.logger.info("Script executed successfully")
            return result
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Script execution failed: {e}")
            self.logger.error(f"STDOUT: {e.stdout}")
            self.logger.error(f"STDERR: {e.stderr}")
            raise
    
    def add_task(self, task: Task) -> Dict:
        """Add a new task with priority"""
        self.logger.info(f"Adding task: {task.task_id} with priority {task.priority}")
        
        # Save task
        if not self._save_task(task):
            raise Exception(f"Failed to save task {task.task_id}")
        
        # Add to memory cache and priority queue
        with self.tasks_lock:
            self.tasks[task.task_id] = task
            
        with self.task_queue_lock:
            # Lower priority score = higher priority in queue
            self.task_queue.put((100 - task.priority, task.task_id))
            
        return task.to_dict()
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a task by its ID.
        
        Args:
            task_id (str): The ID of the task to retrieve
            
        Returns:
            Optional[Task]: The task if found, None otherwise
        """
        # Try memory cache first
        with self.tasks_lock:
            if task_id in self.tasks:
                return self.tasks[task_id]
        
        # Fall back to file system
        task_path = os.path.join(os.path.join(self.base_path, "tasks"), f"{task_id}.json")
        
        if not os.path.exists(task_path):
            self.logger.error(f"Task {task_id} not found")
            return None
        
        try:
            task_data = load_json(task_path)
            task = Task.from_dict(task_data)
            
            # Update cache
            with self.tasks_lock:
                self.tasks[task.task_id] = task
            
            return task
        except Exception as e:
            self.logger.error(f"Error loading task {task_id}: {str(e)}")
            return None
    
    def get_pending_tasks(self) -> List[Dict]:
        """Get list of pending tasks sorted by priority"""
        with self.tasks_lock:
            pending_tasks = [
                task for task in self.tasks.values()
                if task.status in [TaskStatus.PENDING, TaskStatus.TESTING,
                                 TaskStatus.QUALITY_ASSESSMENT, TaskStatus.READY_FOR_INTEGRATION]
            ]
            
        # Sort by priority (higher priority score = higher priority)
        return sorted(
            [task.to_dict() for task in pending_tasks],
            key=lambda x: x['priority'],
            reverse=True
        )
    
    def rebalance_priorities(self, task_ids: List[str] = None) -> bool:
        """
        Rebalance priorities of specified tasks or all tasks
        Ensures even distribution of priorities while maintaining relative ordering
        """
        try:
            with self.tasks_lock:
                if task_ids is None:
                    tasks_to_rebalance = list(self.tasks.values())
                else:
                    tasks_to_rebalance = [self.tasks[tid] for tid in task_ids if tid in self.tasks]
                
                # Sort by current priority
                tasks_to_rebalance.sort(key=lambda x: x.priority, reverse=True)
                
                # Redistribute priorities evenly
                count = len(tasks_to_rebalance)
                if count > 0:
                    step = 100.0 / count
                    for i, task in enumerate(tasks_to_rebalance):
                        new_priority = max(0.0, min(100.0, 100.0 - (i * step)))
                        task.update_priority(new_priority)
                        self._save_task(task)
                
                return True
        except Exception as e:
            self.logger.error(f"Error rebalancing priorities: {str(e)}")
            return False
    
    def update_task_priorities(self, priority_updates: Dict[str, float]) -> bool:
        """
        Bulk update task priorities
        
        Args:
            priority_updates: Dict mapping task_id to new priority value
        """
        try:
            with self.tasks_lock:
                for task_id, new_priority in priority_updates.items():
                    if task_id in self.tasks:
                        task = self.tasks[task_id]
                        task.update_priority(new_priority)
                        self._save_task(task)
                
                return True
        except Exception as e:
            self.logger.error(f"Error updating priorities: {str(e)}")
            return False
    
    def _save_task(self, task: Task) -> bool:
        """Save task to file"""
        task_path = os.path.join(os.path.join(self.base_path, "tasks"), f"{task.task_id}.json")
        
        try:
            task_data = task.to_dict() if isinstance(task, Task) else task
            save_json(task_path, task_data)
            return True
        except Exception as e:
            self.logger.error(f"Error saving task {task.task_id}: {str(e)}")
            return False
    
    def _load_tasks(self):
        """Load existing tasks from storage"""
        self.logger.info("Loading existing tasks")
        
        try:
            task_files = [f for f in os.listdir(os.path.join(self.base_path, "tasks")) if f.endswith('.json')]
            
            for task_file in task_files:
                task_path = os.path.join(os.path.join(self.base_path, "tasks"), task_file)
                task_data = load_json(task_path)
                
                if task_data:
                    task = Task.from_dict(task_data)
                    
                    # Add to memory cache
                    with self.tasks_lock:
                        self.tasks[task.task_id] = task
                    
                    # Add to priority queue if task is not completed or failed
                    if task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                        with self.task_queue_lock:
                            self.task_queue.put((100 - task.priority, task.task_id))
                            
            self.logger.info(f"Loaded {len(task_files)} tasks")
        except Exception as e:
            self.logger.error(f"Error loading tasks: {str(e)}")
    
    def _process_tasks(self):
        """Task processing thread"""
        self.logger.info("Task processing thread started")
        
        while self.running:
            try:
                # Get highest priority task
                with self.task_queue_lock:
                    if not self.task_queue.empty():
                        _, task_id = self.task_queue.get()
                        self.process_task(task_id)
            except Exception as e:
                self.logger.error(f"Error in task processing thread: {str(e)}")
            
            # Sleep to prevent busy waiting
            time.sleep(1)
    
    def process_task(self, task_id: str):
        """
        Process a single task through the entire workflow
        
        Args:
            task_id (str): ID of the task to process
        """
        self.logger.info(f"Processing task: {task_id}")
        
        try:
            # Get task
            task = self.get_task(task_id)
            if not task:
                self.logger.error(f"Task {task_id} not found")
                return
                
            project = self.projects.get(task.project_id)
            
            # Check if task needs decomposition
            if task.status == TaskStatus.CREATED:
                task.update_status(TaskStatus.DECOMPOSING, "Starting task decomposition")
                self._save_task(task)
                
                subtasks = decompose_task(task)
                if subtasks:
                    # Create subtasks
                    for subtask_desc in subtasks:
                        subtask = self.create_task(
                            project_id=task.project_id,
                            description=subtask_desc["description"],
                            language=task.language,
                            requirements=subtask_desc.get("requirements", []),
                            priority=task.priority,
                            parent_task_id=task.task_id
                        )
                        self.logger.info(f"Created subtask {subtask.task_id} for task {task_id}")
                    
                    task.update_status(TaskStatus.DECOMPOSING, f"Created {len(subtasks)} subtasks")
                else:
                    task.update_status(TaskStatus.READY_FOR_IMPLEMENTATION, "No decomposition needed")
                self._save_task(task)
            
            # If task is ready for implementation, run code generation
            elif task.status == TaskStatus.READY_FOR_IMPLEMENTATION:
                task.update_status(TaskStatus.IMPLEMENTING, "Starting implementation")
                self._save_task(task)
                
                success = generate_code(task)
                if success:
                    task.update_status(TaskStatus.READY_FOR_TESTING, "Implementation completed")
                else:
                    task.update_status(TaskStatus.NEEDS_REVISION, "Implementation failed")
                self._save_task(task)
            
            # Check if task is ready for testing
            elif task.status == TaskStatus.READY_FOR_TESTING:
                task.update_status(TaskStatus.TESTING, "Starting tests")
                self._save_task(task)
                
                test_results = run_tests(task)
                if test_results["passed"]:
                    task.update_status(TaskStatus.READY_FOR_QUALITY, "Tests passed")
                else:
                    task.update_status(TaskStatus.NEEDS_REVISION, "Tests failed")
                task.test_results = test_results
                self._save_task(task)
            
            # Check if task is ready for quality assessment
            elif task.status == TaskStatus.READY_FOR_QUALITY:
                task.update_status(TaskStatus.QUALITY_CHECK, "Starting quality assessment")
                self._save_task(task)
                
                quality_results = assess_quality(task)
                if quality_results["passed"]:
                    task.update_status(TaskStatus.READY_FOR_INTEGRATION, "Quality check passed")
                else:
                    task.update_status(TaskStatus.NEEDS_REVISION, "Quality check failed")
                task.quality_results = quality_results
                self._save_task(task)
            
            # Check if task is ready for integration
            elif task.status == TaskStatus.READY_FOR_INTEGRATION:
                # For tasks with subtasks, check if all subtasks are completed
                if task.subtask_ids:
                    all_subtasks_completed = all(
                        self.tasks[subtask_id].status == TaskStatus.COMPLETED
                        for subtask_id in task.subtask_ids
                    )
                    if not all_subtasks_completed:
                        self.logger.info(f"Task {task_id} waiting for subtasks to complete")
                        return
                
                task.update_status(TaskStatus.INTEGRATING, "Starting integration")
                self._save_task(task)
                
                integration_results = integrate_task(task)
                if integration_results["success"]:
                    task.update_status(TaskStatus.COMPLETED, "Integration successful")
                else:
                    task.update_status(TaskStatus.NEEDS_REVISION, "Integration failed")
                task.integration_results = integration_results
                self._save_task(task)
                
                # Update project status if this is a root task
                if project and task.task_id in project.root_tasks:
                    self._update_project_status(project)
            
            self.logger.info(f"Task {task_id} processing completed")
            
        except Exception as e:
            self.logger.error(f"Error processing task {task_id}: {str(e)}")
            if task:
                task.update_status(TaskStatus.ERROR, f"Error: {str(e)}")
                self._save_task(task)
            raise
    
    def _update_project_status(self, project: Project):
        """
        Update project status based on its root tasks.
        
        Args:
            project (Project): Project to update
        """
        if not project.root_tasks:
            return
            
        # Check status of all root tasks
        root_task_statuses = [
            self.tasks[task_id].status
            for task_id in project.root_tasks
            if task_id in self.tasks
        ]
        
        # Update project status
        if all(status == TaskStatus.COMPLETED for status in root_task_statuses):
            project.status = ProjectStatus.COMPLETED
        elif any(status == TaskStatus.ERROR for status in root_task_statuses):
            project.status = ProjectStatus.ERROR
        else:
            project.status = ProjectStatus.ACTIVE
        
        project.save()
        self.logger.info(f"Updated project {project.project_id} status to {project.status.value}")
    
    def get_all_tasks(self) -> List[Dict]:
        """Get list of all tasks"""
        with self.tasks_lock:
            # Convert all tasks to dictionaries and log for debugging
            tasks = [task.to_dict() for task in self.tasks.values()]
            self.logger.debug(f"get_all_tasks: Found {len(tasks)} tasks")
            return tasks
            
    def get_tasks_by_status(self, status: TaskStatus) -> List[Dict]:
        """Get list of tasks with the given status"""
        with self.tasks_lock:
            filtered_tasks = [
                task for task in self.tasks.values()
                if task.status == status
            ]
            
        # Sort by priority (higher priority score = higher priority)
        return sorted(
            [task.to_dict() for task in filtered_tasks],
            key=lambda x: x['priority'],
            reverse=True
        )
        
    def get_next_task(self) -> Optional[Dict]:
        """Get the next task to work on based on priority"""
        with self.task_queue_lock:
            if not self.task_queue.empty():
                _, task_id = self.task_queue.get()
                task = self.get_task(task_id)
                if task:
                    return task.to_dict()
        return None
        
    def mark_task_complete(self, task_id: str, message: str = None) -> bool:
        """Mark a task as completed"""
        task = self.get_task(task_id)
        if task:
            task.update_status(TaskStatus.COMPLETED, message or "Task marked as completed")
            self._save_task(task)
            return True
        return False

    def load_projects(self):
        """Load all projects from disk."""
        projects_dir = os.path.join(self.base_path, "projects")
        if not os.path.exists(projects_dir):
            return
            
        for project_id in os.listdir(projects_dir):
            project_path = os.path.join(projects_dir, project_id)
            if not os.path.isdir(project_path):
                continue
                
            project_file = os.path.join(project_path, "project.json")
            if not os.path.exists(project_file):
                continue
                
            try:
                with open(project_file, 'r') as f:
                    project_data = json.load(f)
                    project = Project.from_dict(project_data, os.path.join(self.base_path, "projects"))
                    self.projects[project.project_id] = project
                    self.logger.info(f"Loaded project {project.project_id}: {project.name}")
            except Exception as e:
                self.logger.error(f"Error loading project from {project_id}: {str(e)}")
    
    def load_tasks(self):
        """Load all tasks from the tasks directory."""
        tasks_dir = os.path.join(self.base_path, "tasks")
        if not os.path.exists(tasks_dir):
            self.logger.warning("Tasks directory does not exist")
            return
            
        loaded_count = 0
        for filename in os.listdir(tasks_dir):
            if not filename.endswith(".json"):
                continue
                
            try:
                task_path = os.path.join(tasks_dir, filename)
                task_data = load_json(task_path)
                task = Task.from_dict(task_data)
                
                # Add to memory cache with lock
                with self.tasks_lock:
                    self.tasks[task.task_id] = task
                    
                self.logger.info(f"Loaded task {task.task_id} with status {task.status.value}")
                loaded_count += 1
            except Exception as e:
                self.logger.error(f"Error loading task from {filename}: {str(e)}")
        
        self.logger.info(f"Successfully loaded {loaded_count} tasks")
    
    def create_project(self, name: str, description: str) -> Project:
        """
        Create a new project.
        
        Args:
            name (str): Project name
            description (str): Project description
            
        Returns:
            Project: The created project
        """
        project = Project(name, description, os.path.join(self.base_path, "projects"))
        self.projects[project.project_id] = project
        project.save()
        self.logger.info(f"Created project {project.project_id}: {name}")
        return project
    
    def create_task(self, project_id: str, description: str, language: str,
                   requirements: List[str] = None, priority: float = 50.0,
                   parent_task_id: str = None) -> Task:
        """
        Create a new task within a project.
        
        Args:
            project_id (str): ID of the project this task belongs to
            description (str): Task description
            language (str): Programming language
            requirements (List[str], optional): List of requirements
            priority (float, optional): Priority score
            parent_task_id (str, optional): ID of parent task if this is a subtask
            
        Returns:
            Task: The created task
        """
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")
            
        task = Task(description, language, requirements, priority)
        task.project_id = project_id
        task.parent_task_id = parent_task_id
        
        # Update parent task if this is a subtask
        if parent_task_id:
            if parent_task_id not in self.tasks:
                raise ValueError(f"Parent task {parent_task_id} not found")
            parent_task = self.tasks[parent_task_id]
            parent_task.subtask_ids.append(task.task_id)
            self._save_task(parent_task)
        
        self.tasks[task.task_id] = task
        self._save_task(task)
        
        # Update project
        project = self.projects[project_id]
        if not parent_task_id:  # Only add to root_tasks if not a subtask
            project.root_tasks.append(task.task_id)
        project.all_tasks.append(task.task_id)
        project.save()
        
        self.logger.info(f"Created task {task.task_id} in project {project_id}")
        return task

    def delete_task(self, task_id: str) -> bool:
        """
        Delete a task and its associated files.
        
        Args:
            task_id (str): The ID of the task to delete
            
        Returns:
            bool: True if task was deleted successfully
        """
        task = self.get_task(task_id)
        if not task:
            self.logger.error(f"Task {task_id} not found")
            return False
        
        # Delete task file
        task_file = os.path.join(self.base_path, "tasks", f"{task_id}.json")
        try:
            os.remove(task_file)
            self.logger.debug(f"Deleted task file {task_file}")
        except OSError as e:
            self.logger.error(f"Failed to delete task file {task_file}: {e}")
            return False
        
        # Delete task from memory
        with self.tasks_lock:
            if task_id in self.tasks:
                del self.tasks[task_id]
                self.logger.debug(f"Removed task {task_id} from memory")
            
        return True

def main():
    """Main entry point"""
    orchestrator = OrchestratorAgent()
    orchestrator.start()
    
    try:
        # Keep the main thread running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        orchestrator.stop()

if __name__ == "__main__":
    main()
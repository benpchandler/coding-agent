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
from queue import PriorityQueue

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OrchestratorAgent:
    """
    Orchestrates the entire development workflow including task decomposition,
    implementation, testing, and quality assessment.
    """
    
    def __init__(self, 
                 config_path: str = None,
                 task_dir: str = "tasks",
                 impl_dir: str = "implementations",
                 test_dir: str = "tests",
                 quality_dir: str = "test_results",
                 integration_dir: str = "integration_tests"):
        """
        Initialize the orchestrator with configuration and directory settings.
        
        Args:
            config_path (str): Path to configuration file
            task_dir (str): Directory for task definitions and tracking
            impl_dir (str): Directory for implemented code
            test_dir (str): Directory for unit tests
            quality_dir (str): Directory for quality assessment results
            integration_dir (str): Directory for integration tests
        """
        # Set up logging
        self.logger = setup_logger(f"{__name__}.OrchestratorAgent")
        
        # Load configuration
        config_path = config_path or "./config/config.json"
        self.config = load_json(config_path) or {}
        
        # Set up directory structure
        self.task_dir = self.config.get("directories", {}).get("tasks", task_dir)
        self.impl_dir = self.config.get("directories", {}).get("implementations", impl_dir)
        self.test_dir = self.config.get("directories", {}).get("tests", test_dir)
        self.quality_dir = self.config.get("directories", {}).get("quality", quality_dir)
        self.integration_dir = self.config.get("directories", {}).get("integration", integration_dir)
        
        # Create directories if they don't exist
        for directory in [self.task_dir, self.impl_dir, self.test_dir, 
                         self.quality_dir, self.integration_dir]:
            os.makedirs(directory, exist_ok=True)
        
        # Replace task queue with priority queue
        self.task_queue = PriorityQueue()
        self.task_queue_lock = threading.Lock()
        
        # Track tasks in memory for faster access
        self.tasks = {}
        self.tasks_lock = threading.Lock()
        
        self.running = False
        self.processing_thread = None
        
        self.logger.info("Orchestrator initialized with directory structure:")
        self.logger.info(f"Tasks: {self.task_dir}")
        self.logger.info(f"Implementations: {self.impl_dir}")
        self.logger.info(f"Tests: {self.test_dir}")
        self.logger.info(f"Quality Assessment: {self.quality_dir}")
        self.logger.info(f"Integration Tests: {self.integration_dir}")
    
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
            ("tasks", self.task_dir),
            ("implementations", self.impl_dir),
            ("tests", self.test_dir),
            ("quality", self.quality_dir),
            ("integration", self.integration_dir)
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
        task_files = [f for f in os.listdir(self.task_dir) if f.endswith('.json')]
        task_ids = [os.path.splitext(f)[0] for f in task_files]
        
        for task_id in task_ids:
            # Check for implementation
            impl_py = f"{task_id.lower().replace('-', '_')}.py"
            impl_jsx = f"{task_id.lower().replace('-', '_')}.jsx"
            if not os.path.exists(os.path.join(self.impl_dir, impl_py)) and \
               not os.path.exists(os.path.join(self.impl_dir, impl_jsx)):
                issues.append(f"Missing implementation for task {task_id}")
            
            # Check for tests
            test_file = f"test_{task_id.lower().replace('-', '_')}.py"
            if not os.path.exists(os.path.join(self.test_dir, test_file)):
                issues.append(f"Missing tests for task {task_id}")
            
            # Check for quality results
            quality_dir = os.path.join(self.quality_dir, task_id)
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
        """Get task by ID"""
        # Try memory cache first
        with self.tasks_lock:
            if task_id in self.tasks:
                return self.tasks[task_id]
        
        # Fall back to file system
        task_path = os.path.join(self.task_dir, f"{task_id}.json")
        
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
        task_path = os.path.join(self.task_dir, f"{task.task_id}.json")
        
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
            task_files = [f for f in os.listdir(self.task_dir) if f.endswith('.json')]
            
            for task_file in task_files:
                task_path = os.path.join(self.task_dir, task_file)
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
                
            # Check if task needs decomposition
            if task.status == TaskStatus.CREATED:
                # Run decomposer agent
                self.logger.info("Running Decomposer Agent")
                try:
                    # Update task status before running decomposer
                    task.update_status(TaskStatus.DECOMPOSING, "Starting task decomposition")
                    self._save_task(task)
                    
                    # Run decomposer with task description and task ID
                    self._run_script(os.path.join('agents', 'decomposer.py'), [task.description, task_id])
                    
                    # Task status will be updated by the decomposer
                    return  # Exit to let the orchestrator pick up the subtasks
                except subprocess.CalledProcessError as e:
                    if "No subtasks needed" in (e.stderr or ""):
                        # Task doesn't need decomposition, proceed with implementation
                        task.update_status(TaskStatus.READY_FOR_IMPLEMENTATION, "Task will be implemented directly")
                        self._save_task(task)
                    else:
                        raise  # Re-raise if it's a different error
            
            # If task is ready for implementation, run code generation
            if task.status == TaskStatus.READY_FOR_IMPLEMENTATION:
                # 1. Code Generation Agent
                self.logger.info("Running Code Generation Agent")
                self._run_script(os.path.join('agents', 'code_generation_agent.py'), [task_id])
                
                # 2. Testing Agent
                self.logger.info("Running Testing Agent")
                self._run_script('testing_agent.py', [task_id])
                
                # 3. Quality Assessment Agent
                self.logger.info("Running Quality Assessment Agent")
                quality_agent_result = self._run_script('quality_assessment_agent.py', [task_id])
                
                # Parse quality assessment
                quality_assessment = self._parse_quality_assessment(quality_agent_result.stdout)
                
                # 4. Decide next steps
                if quality_assessment.get('needs_rewrite', False):
                    self.logger.info(f"Task {task_id} needs revision")
                    task.update_status(TaskStatus.NEEDS_REVISION, "Quality assessment indicates revision needed")
                    self._save_task(task)
                    # Optionally trigger rewrite process
                    self._run_rewrite_process(task_id)
                else:
                    # 5. Integration Agent
                    self.logger.info("Running Integration Agent")
                    self._run_script('integration_agent.py', [task_id])
                    
                    # Update task status to completed
                    task.update_status(TaskStatus.COMPLETED, "Task completed successfully")
                    self._save_task(task)
                
                self.logger.info(f"Task {task_id} processing completed")
            
        except Exception as e:
            self.logger.error(f"Error processing task {task_id}: {str(e)}")
            if task:
                task.update_status(TaskStatus.ERROR, f"Error: {str(e)}")
                self._save_task(task)
            raise
    
    def _parse_quality_assessment(self, assessment_output: str) -> Dict:
        """Parse quality assessment output"""
        try:
            return json.loads(assessment_output)
        except json.JSONDecodeError:
            self.logger.error("Failed to parse quality assessment output")
            return {"needs_rewrite": True}
    
    def _update_task_status(self, task_id: str, status: TaskStatus):
        """Update task status"""
        task = self.get_task(task_id)
        if task:
            task.update_status(status, f"Status updated to {status.value}")
            self._save_task(task)
    
    def _run_rewrite_process(self, task_id: str):
        """Handle task rewrite process"""
        self.logger.info(f"Initiating rewrite process for task {task_id}")
        # Add rewrite logic here
        pass

    def get_all_tasks(self) -> List[Dict]:
        """Get list of all tasks"""
        with self.tasks_lock:
            # Convert all tasks to dictionaries
            return [task.to_dict() for task in self.tasks.values()]
            
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
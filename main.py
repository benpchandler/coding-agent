"""
Main entry point for the AI-Driven Development Workflow System.
"""

import os
import sys
import logging
import argparse
from typing import Optional
from pathlib import Path

from agents.orchestration_agent import OrchestratorAgent
from models.task import Task, TaskStatus
from models.project import Project, ProjectStatus

def load_environment():
    """Load environment variables from .env file if it exists"""
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    if key and value:
                        os.environ[key] = value

def setup_logging():
    """Set up logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/main.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def create_project(orchestrator: OrchestratorAgent, name: str, description: str) -> Project:
    """
    Create a new project.
    
    Args:
        orchestrator (OrchestratorAgent): The orchestrator agent
        name (str): Project name
        description (str): Project description
        
    Returns:
        Project: The created project
    """
    project = orchestrator.create_project(name, description)
    logger.info(f"Created project {project.project_id}: {name}")
    return project

def create_task(orchestrator: OrchestratorAgent, project_id: str, description: str,
                language: str = "python", requirements: Optional[list] = None,
                priority: float = 50.0, parent_task_id: Optional[str] = None) -> Task:
    """
    Create a new task.
    
    Args:
        orchestrator (OrchestratorAgent): The orchestrator agent
        project_id (str): ID of the project this task belongs to
        description (str): Task description
        language (str, optional): Programming language. Defaults to "python".
        requirements (List[str], optional): List of requirements. Defaults to None.
        priority (float, optional): Priority score. Defaults to 50.0.
        parent_task_id (str, optional): ID of parent task if this is a subtask.
        
    Returns:
        Task: The created task
    """
    task = orchestrator.create_task(
        project_id=project_id,
        description=description,
        language=language,
        requirements=requirements,
        priority=priority,
        parent_task_id=parent_task_id
    )
    logger.info(f"Created task {task.task_id} in project {project_id}")
    return task

def list_projects(orchestrator: OrchestratorAgent):
    """List all projects and their status"""
    logger.info("Listing all projects:")
    for project_id, project in orchestrator.projects.items():
        logger.info(f"Project {project_id}: {project.name}")
        logger.info(f"  Status: {project.status.value}")
        logger.info(f"  Root tasks: {len(project.root_tasks)}")
        logger.info(f"  All tasks: {len(project.all_tasks)}")
        logger.info("  Description:")
        for line in project.description.split('\n'):
            logger.info(f"    {line}")
        logger.info("")

def list_tasks(orchestrator: OrchestratorAgent, project_id: Optional[str] = None):
    """
    List all tasks, optionally filtered by project.
    
    Args:
        orchestrator (OrchestratorAgent): The orchestrator agent
        project_id (str, optional): Project ID to filter tasks. Defaults to None.
    """
    tasks = orchestrator.get_all_tasks()
    logger.info(f"Retrieved {len(tasks)} tasks from orchestrator")
    
    if project_id:
        logger.info(f"Filtering tasks for project {project_id}")
        tasks = [task for task in tasks if task.get('project_id') == project_id]
        logger.info(f"Found {len(tasks)} tasks for project {project_id}")
    
    if not tasks:
        logger.info("No tasks found.")
        return
    
    logger.info(f"Listing {'all' if not project_id else f'project {project_id}'} tasks:")
    for task in tasks:
        logger.info("=" * 80)
        logger.info(f"Task ID: {task['task_id']}")
        logger.info(f"Status: {task['status']}")
        logger.info(f"Priority: {task['priority']}")
        logger.info(f"Language: {task['language']}")
        if task['parent_task_id']:
            logger.info(f"Parent Task: {task['parent_task_id']}")
        if task['subtask_ids']:
            logger.info(f"Subtasks: {', '.join(task['subtask_ids'])}")
        logger.info("Description:")
        for line in task['description'].split('\n'):
            logger.info(f"  {line}")
        if task['requirements']:
            logger.info("Requirements:")
            for req in task['requirements']:
                logger.info(f"  - {req}")
        logger.info("=" * 80)
        logger.info("")

def delete_task(orchestrator: OrchestratorAgent, task_id: str) -> bool:
    """
    Delete a task.
    
    Args:
        orchestrator (OrchestratorAgent): The orchestrator agent
        task_id (str): ID of the task to delete
        
    Returns:
        bool: True if task was deleted successfully
    """
    task = orchestrator.get_task(task_id)
    if not task:
        logger.error(f"Task {task_id} not found")
        return False
        
    success = orchestrator.delete_task(task_id)
    if success:
        logger.info(f"Successfully deleted task {task_id}")
    else:
        logger.error(f"Failed to delete task {task_id}")
    return success

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="AI-Driven Development Workflow System")
    
    # Project commands
    parser.add_argument('--create-project', action='store_true',
                       help='Create a new project')
    parser.add_argument('--project-name',
                       help='Name for the new project')
    parser.add_argument('--project-description',
                       help='Description for the new project')
    parser.add_argument('--list-projects', action='store_true',
                       help='List all projects')
    
    # Task commands
    parser.add_argument('--create-task', action='store_true',
                       help='Create a new task')
    parser.add_argument('--project-id',
                       help='Project ID for the task')
    parser.add_argument('--task-description',
                       help='Description for the new task')
    parser.add_argument('--language', default='python',
                       help='Programming language for the task')
    parser.add_argument('--requirements', nargs='+',
                       help='Requirements for the task')
    parser.add_argument('--priority', type=float, default=50.0,
                       help='Priority score for the task (0-100)')
    parser.add_argument('--parent-task',
                       help='Parent task ID if this is a subtask')
    parser.add_argument('--list-tasks', action='store_true',
                       help='List all tasks')
    parser.add_argument('--delete-task', action='store_true',
                       help='Delete a task')
    parser.add_argument('--task-id',
                       help='ID of the task to delete')
    
    args = parser.parse_args()
    
    # Load environment variables first
    load_environment()

    # Set up logging
    global logger
    logger = setup_logging()
    logger.info("Starting AI-Driven Development Workflow System")

    # Check if API key is available
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and api_key.startswith('sk-'):
        logger.info("✓ OpenAI API key loaded successfully")
    else:
        logger.warning("⚠ No valid OpenAI API key found. Set OPENAI_API_KEY environment variable or create .env file")
    
    # Initialize orchestrator
    base_path = os.path.dirname(os.path.abspath(__file__))
    orchestrator = OrchestratorAgent(base_path)
    logger.info("Initialized orchestrator")
    
    try:
        if args.create_project:
            if not args.project_name or not args.project_description:
                logger.error("Project name and description are required")
                sys.exit(1)
            project = create_project(orchestrator, args.project_name, args.project_description)
            if not project:
                sys.exit(1)
        
        elif args.list_projects:
            list_projects(orchestrator)
        
        elif args.create_task:
            if not args.project_id or not args.task_description:
                logger.error("Project ID and task description are required")
                sys.exit(1)
            task = create_task(
                orchestrator,
                args.project_id,
                args.task_description,
                args.language,
                args.requirements,
                args.priority,
                args.parent_task
            )
            if not task:
                sys.exit(1)
        
        elif args.list_tasks:
            list_tasks(orchestrator, args.project_id)
        
        elif args.delete_task:
            if not args.task_id:
                logger.error("Task ID is required")
                sys.exit(1)
            if not delete_task(orchestrator, args.task_id):
                sys.exit(1)
        
        else:
            # Process existing tasks
            for task_id, task in orchestrator.tasks.items():
                if task.status not in [TaskStatus.COMPLETED, TaskStatus.ERROR]:
                    logger.info(f"Processing task {task_id}")
                    orchestrator.process_task(task_id)
        
        logger.info("AI-Driven Development Workflow System completed successfully")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)
    
    finally:
        logger.info("Stopping AI-Driven Development Workflow System")

if __name__ == "__main__":
    main()
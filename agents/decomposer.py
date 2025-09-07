import os
import json
import sys
from openai import OpenAI
from dotenv import load_dotenv
import logging
from typing import List, Dict, Any

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from models.task import Task, TaskStatus
from common.logging_utils import setup_logger
from common.json_utils import load_json, save_json

# Load environment variables from project root
load_dotenv(os.path.join(project_root, ".env"))

# Setup logging
logger = setup_logger(__name__)

# Configure OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
if not client.api_key:
    logger.error("No OpenAI API key found in .env file")
    raise ValueError("Please set OPENAI_API_KEY in your .env file")

def update_parent_task_status(task_id: str, output_dir: str = "tasks") -> None:
    """
    Update the parent task's status after decomposition.
    
    Args:
        task_id (str): The task ID to update
        output_dir (str, optional): Output directory. Defaults to "tasks".
    """
    task_path = os.path.join(output_dir, f"{task_id}.json")
    if os.path.exists(task_path):
        task_data = load_json(task_path)
        task = Task.from_dict(task_data)
        task.update_status(TaskStatus.READY_FOR_IMPLEMENTATION, "Task decomposition completed")
        save_json(task_path, task.to_dict())
        logger.info(f"Updated task {task_id} status to {TaskStatus.READY_FOR_IMPLEMENTATION}")

def decompose_feature(feature_description: str) -> List[Dict[str, Any]]:
    """
    Break down a feature into smaller, actionable tasks.
    
    Args:
        feature_description (str): Description of the feature to decompose
        
    Returns:
        List[Dict[str, Any]]: List of task dictionaries
    """
    prompt = f"""
You are a technical project manager for a development team.
Break down this feature into 3-5 specific, actionable tasks:

FEATURE:
{feature_description}

For each task, provide:
1. A clear title (max 10 words)
2. A concise description (2-3 sentences)
3. Priority score (0-100):
   - 90-100: Critical/Blocking issues
   - 70-89: High priority features
   - 40-69: Normal priority tasks
   - 20-39: Low priority enhancements
   - 0-19: Nice-to-have features
4. Dependencies (list any prerequisite tasks by title)
5. Estimated time to complete (in hours)
6. 2-3 specific acceptance criteria that will determine if the task is complete

Generate only tasks that are clearly scoped, independently testable, and can be completed in 4 hours or less.
Consider dependencies when assigning priority scores - dependent tasks should generally have lower priority than their prerequisites.

FORMAT YOUR RESPONSE AS A JSON ARRAY.
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Using cost-effective model for task decomposition
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        
        # Extract JSON from the response
        content = response.choices[0].message.content
        
        # Handle potential markdown formatting in the response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
            
        tasks = json.loads(content)
        return tasks
    
    except Exception as e:
        logger.error(f"Error decomposing feature: {str(e)}")
        return []

def save_tasks(tasks: List[Dict[str, Any]], language: str = "python", output_dir: str = "tasks") -> List[Task]:
    """
    Save tasks to individual JSON files.
    
    Args:
        tasks (List[Dict[str, Any]]): List of task dictionaries
        language (str, optional): Programming language. Defaults to "python".
        output_dir (str, optional): Output directory. Defaults to "tasks".
        
    Returns:
        List[Task]: List of created Task objects
    """
    os.makedirs(output_dir, exist_ok=True)
    created_tasks = []
    
    for task_data in tasks:
        # Create Task object
        task = Task(
            description=task_data["description"],
            language=language,
            requirements=task_data.get("acceptance_criteria", []),
            priority=float(task_data.get("priority", 50.0))
        )
        
        # Add dependencies to requirements if any
        if task_data.get("dependencies"):
            task.requirements.extend([f"Depends on: {dep}" for dep in task_data["dependencies"]])
        
        # Save task
        task_path = os.path.join(output_dir, f"{task.task_id}.json")
        save_json(task_path, task.to_dict())
        
        created_tasks.append(task)
        logger.info(f"Saved task: {task_data['title']} ({task.task_id})")
        
    return created_tasks

def decompose_task(task: Task) -> List[Dict[str, Any]]:
    """
    Decompose a task into subtasks.
    
    Args:
        task (Task): The task to decompose
        
    Returns:
        List[Dict[str, Any]]: List of subtask descriptions
    """
    logger.info(f"Decomposing task {task.task_id}")
    
    # Get subtasks from feature decomposition
    subtasks = decompose_feature(task.description)
    
    # Format subtasks for the orchestrator
    formatted_subtasks = []
    for subtask in subtasks:
        formatted_subtasks.append({
            "description": f"{subtask['title']}\n\n{subtask['description']}\n\nAcceptance Criteria:\n" + 
                         "\n".join(f"- {criterion}" for criterion in subtask['acceptance_criteria']),
            "requirements": subtask.get('acceptance_criteria', []) +
                          [f"Depends on: {dep}" for dep in subtask.get('dependencies', [])],
            "priority": float(subtask.get('priority', 50.0))
        })
    
    logger.info(f"Generated {len(formatted_subtasks)} subtasks for task {task.task_id}")
    return formatted_subtasks

def main():
    """Main entry point"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python decomposer.py <feature_description> [task_id]")
        sys.exit(1)
        
    # Get feature description from command line, handling spaces and quotes
    feature = " ".join(sys.argv[1:]) if len(sys.argv) > 2 else sys.argv[1]
    language = "python"  # Default to Python
    
    if not feature.strip():
        logger.error("No feature description provided")
        return
        
    logger.info("Decomposing feature into tasks...")
    tasks = decompose_feature(feature)
    
    if tasks:
        logger.info(f"Generated {len(tasks)} tasks")
        created_tasks = save_tasks(tasks, language)
        
        # Print summary
        print("\nGenerated Tasks:")
        print("---------------")
        for task in created_tasks:
            print(f"- [{task.task_id}] {task.description}")
            print(f"  Priority: {task.priority:.1f}, Requirements: {len(task.requirements)}")
        print(f"\nTasks saved to the 'tasks' directory")
        
        # Update parent task status if task_id is provided
        if len(sys.argv) > 2:
            parent_task_id = sys.argv[-1]
            if parent_task_id.startswith("TASK-"):
                update_parent_task_status(parent_task_id)
        
        sys.exit(0)
    else:
        logger.error("Failed to generate tasks")
        sys.exit(1)

if __name__ == "__main__":
    main()
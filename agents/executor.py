import os
import json
from pathlib import Path
from glob import glob

# Get the absolute path to the tasks directory using pathlib for better path handling
TASKS_DIR = Path(__file__).parent.parent / "tasks"

def list_tasks(status="not_started"):
    """List all tasks with the given status."""
    tasks = []
    try:
        # Use pathlib for better path handling
        task_files = list(TASKS_DIR.glob("*.json"))
        print(f"Looking for tasks in: {TASKS_DIR}")
        print(f"Found {len(task_files)} task files")
        
        for task_file in task_files:
            try:
                with task_file.open('r', encoding='utf-8') as f:
                    task = json.load(f)
                    task_status = task.get("status", "not_started")
                    # Consider 'created' tasks as 'not_started'
                    if status == "not_started" and task_status == "created":
                        tasks.append(task)
                    elif task_status == status:
                        tasks.append(task)
            except Exception as e:
                print(f"Error reading task file {task_file}: {str(e)}")
    except Exception as e:
        print(f"Error listing tasks: {str(e)}")
    
    # Sort by priority (lower number = higher priority)
    return sorted(tasks, key=lambda x: x.get("priority", 5))

def mark_task_complete(task_id):
    """Mark a task as completed."""
    task_file = TASKS_DIR / f"{task_id}.json"
    
    if not task_file.exists():
        print(f"Task {task_id} not found")
        return False
    
    try:
        with task_file.open('r', encoding='utf-8') as f:
            task = json.load(f)
        
        task["status"] = "completed"
        
        with task_file.open('w', encoding='utf-8') as f:
            json.dump(task, f, indent=2)
        
        print(f"Task {task_id} marked as completed")
        return True
    except Exception as e:
        print(f"Error marking task complete: {str(e)}")
        return False

def get_next_task():
    """Get the next task to work on."""
    not_started = list_tasks("not_started")
    if not not_started:
        print("No more tasks to complete!")
        return None
    
    # Get the highest priority task
    return not_started[0]

def main():
    print("Task Execution Tool")
    print("------------------")
    print("1. List all tasks")
    print("2. List not started tasks")
    print("3. List completed tasks")
    print("4. Get next task")
    print("5. Mark task as complete")
    print("6. Exit")
    
    choice = input("\nEnter your choice (1-6): ")
    
    if choice == "1":
        all_tasks = list_tasks("not_started") + list_tasks("completed")
        for task in all_tasks:
            print(f"[{task['status']}] {task['task_id']}: {task['title']} (Priority: {task['priority']})")
    
    elif choice == "2":
        not_started = list_tasks("not_started")
        for task in not_started:
            print(f"{task['task_id']}: {task['title']} (Priority: {task['priority']})")
    
    elif choice == "3":
        completed = list_tasks("completed")
        for task in completed:
            print(f"{task['task_id']}: {task['title']}")
    
    elif choice == "4":
        next_task = get_next_task()
        if next_task:
            print("\nNext task to work on:")
            print(f"ID: {next_task['task_id']}")
            print(f"Title: {next_task['title']}")
            print(f"Description: {next_task['description']}")
            print(f"Priority: {next_task['priority']}")
            print(f"Est. Time: {next_task['estimated_time']}")
            print("\nAcceptance Criteria:")
            for i, criterion in enumerate(next_task['acceptance_criteria'], 1):
                print(f"{i}. {criterion}")
    
    elif choice == "5":
        task_id = input("Enter task ID to mark as complete: ")
        mark_task_complete(task_id)
    
    elif choice == "6":
        print("Goodbye!")
        return
    
    else:
        print("Invalid choice. Please try again.")
    
    # Recurse to show menu again
    print("\n")
    main()

if __name__ == "__main__":
    main()
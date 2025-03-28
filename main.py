import os
import sys
import argparse
import json
from common.logging_utils import setup_logger
from agents.orchestration_agent import OrchestratorAgent
from models.task import Task, TaskStatus

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='AI-Driven Development Workflow System')
    
    parser.add_argument('--config', type=str, default='./config/config.json',
                       help='Path to configuration file')
    parser.add_argument('--task', type=str, 
                       help='Create a new task with the given description')
    parser.add_argument('--language', type=str, default='python',
                       help='Programming language for the task (default: python)')
    parser.add_argument('--list-tasks', action='store_true',
                       help='List all tasks')
    parser.add_argument('--task-info', type=str,
                       help='Get information about a specific task')
    parser.add_argument('--code-file', type=str,
                       help='Path to a code file to use for the task')
    
    return parser.parse_args()

def main():
    """Main entry point"""
    logger = setup_logger('main')
    logger.info('Starting AI-Driven Development Workflow System')
    
    # Parse arguments
    args = parse_arguments()
    
    # Initialize orchestration agent
    orchestration_agent = OrchestratorAgent(args.config)
    orchestration_agent.start()
    
    try:
        if args.task:
            # Create a new task
            code = None
            
            # If code file is provided, read it
            if args.code_file and os.path.exists(args.code_file):
                with open(args.code_file, 'r') as f:
                    code_content = f.read()
                    
                code = {
                    "files": [
                        {
                            "path": os.path.basename(args.code_file),
                            "content": code_content,
                            "type": args.language
                        }
                    ],
                    "tests": []
                }
            
            # Create Task object
            task = Task(
                description=args.task,
                language=args.language,
                priority=1.0  # Default priority
            )
            
            # Update code if provided
            if code:
                task.code = code
            
            # Add task using orchestration agent
            task_dict = orchestration_agent.add_task(task)
            print(f"Created task: {task_dict['task_id']}")
            
        elif args.list_tasks:
            # List all tasks
            tasks = orchestration_agent.get_all_tasks()
            
            if not tasks:
                print("No tasks found")
            else:
                print(f"Found {len(tasks)} tasks:")
                for task in tasks:
                    print(f"  {task['task_id']}: {task['description']} (Status: {task['status']})")
                    
        elif args.task_info:
            # Get task information
            task = orchestration_agent.get_task(args.task_info)
            
            if not task:
                print(f"Task {args.task_info} not found")
            else:
                task_dict = task.to_dict()
                print(f"Task ID: {task_dict['task_id']}")
                print(f"Description: {task_dict['description']}")
                print(f"Status: {task_dict['status']}")
                print(f"Language: {task_dict['language']}")
                print(f"Created: {task_dict['created_at']}")
                print(f"Updated: {task_dict['updated_at']}")
                
                if task_dict['status'] in ['completed', 'failed']:
                    print("\nHistory:")
                    for entry in task_dict['history']:
                        print(f"  {entry['timestamp']}: {entry['status']} - {entry['message']}")
                        
        else:
            # Run in server mode
            print("Running in server mode. Press Ctrl+C to exit.")
            
            while True:
                # Just keep the main thread alive
                # The orchestration agent runs in its own thread
                import time
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        # Stop orchestration agent
        orchestration_agent.stop()
        
    logger.info('AI-Driven Development Workflow System stopped')

if __name__ == '__main__':
    main()
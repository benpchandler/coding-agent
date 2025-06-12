#!/usr/bin/env python3
"""
Debug script to check tasks and verify they are readable
"""
import os
import json
import sys
from pathlib import Path

# Get the absolute path to the tasks directory
TASKS_DIR = Path(__file__).parent / "tasks"

def check_tasks():
    """Check that tasks are readable and print basic info"""
    print(f"Looking for tasks in: {TASKS_DIR}")
    print(f"Does tasks directory exist? {TASKS_DIR.exists()}")
    
    if not TASKS_DIR.exists():
        print(f"ERROR: Tasks directory does not exist!")
        return
    
    # List all files in the directory
    all_files = list(TASKS_DIR.iterdir())
    print(f"Directory has {len(all_files)} total files/directories")
    
    # Find JSON files
    json_files = list(TASKS_DIR.glob("*.json"))
    print(f"Found {len(json_files)} JSON files")
    
    # Read each task file
    tasks = []
    for task_file in json_files:
        try:
            print(f"Reading {task_file.name}...")
            with open(task_file, 'r', encoding='utf-8') as f:
                task = json.load(f)
                tasks.append(task)
                print(f"  Task ID: {task.get('task_id', 'Unknown')}")
                print(f"  Status: {task.get('status', 'Unknown')}")
                print(f"  Description: {task.get('description', 'No description')[:50]}...")
        except Exception as e:
            print(f"ERROR reading {task_file.name}: {str(e)}")
    
    print(f"\nSummary:")
    print(f"  Total task files found: {len(json_files)}")
    print(f"  Tasks successfully loaded: {len(tasks)}")
    
    # Count by status
    statuses = {}
    for task in tasks:
        status = task.get('status', 'unknown')
        statuses[status] = statuses.get(status, 0) + 1
    
    print("\nTask status counts:")
    for status, count in statuses.items():
        print(f"  {status}: {count}")

if __name__ == "__main__":
    check_tasks() 
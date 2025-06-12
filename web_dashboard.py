#!/usr/bin/env python3
"""
Web-based Task Management Dashboard
Provides a web interface for viewing and managing tasks and projects
"""
import http.server
import socketserver
import webbrowser
import urllib.parse
import json
import os
import uuid
import datetime
import threading
import traceback
from pathlib import Path
import random
import string

# Constants and configuration
PORT = 8000
BASE_DIR = Path(__file__).parent
TASKS_DIR = BASE_DIR / "tasks"
PROJECTS_DIR = BASE_DIR / "projects"
IMPLEMENTATIONS_DIR = BASE_DIR / "implementations"
AGENTS_DIR = BASE_DIR / "agents"

# Ensure directories exist
TASKS_DIR.mkdir(exist_ok=True)
PROJECTS_DIR.mkdir(exist_ok=True)
IMPLEMENTATIONS_DIR.mkdir(exist_ok=True)

# HTML templates and styling
HTML_HEADER = """
<!DOCTYPE html>
<html>
<head>
    <title>Task Manager</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f8f9fa;
        }
        h1, h2, h3, h4 {
            color: #2c3e50;
        }
        .header {
            background-color: #3498db;
            color: white;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 5px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header a {
            color: white;
            text-decoration: none;
            margin-left: 15px;
        }
        .card {
            background-color: white;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            padding: 20px;
            margin-bottom: 20px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        th, td {
            text-align: left;
            padding: 12px 15px;
            border-bottom: 1px solid #e1e1e1;
        }
        th {
            background-color: #f2f2f2;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .parent-task {
            background-color: #f8f9fa;
        }
        .subtask {
            background-color: #fff;
        }
        .subtask td {
            border-bottom: 1px solid #eee;
        }
        .status {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 0.85em;
        }
        .status-not_started {
            background-color: #e74c3c;
            color: white;
        }
        .status-in_progress {
            background-color: #3498db;
            color: white;
        }
        .status-complete {
            background-color: #2ecc71;
            color: white;
        }
        .status-blocked {
            background-color: #f39c12;
            color: white;
        }
        .btn {
            display: inline-block;
            background-color: #3498db;
            color: white;
            padding: 8px 12px;
            text-decoration: none;
            border-radius: 4px;
            border: none;
            cursor: pointer;
            font-size: 14px;
            transition: background-color 0.2s;
        }
        .btn:hover {
            background-color: #2980b9;
        }
        .btn-success {
            background-color: #2ecc71;
        }
        .btn-success:hover {
            background-color: #27ae60;
        }
        .btn-danger {
            background-color: #e74c3c;
        }
        .btn-danger:hover {
            background-color: #c0392b;
        }
        .btn-danger:disabled {
            background-color: #e74c3c;
            opacity: 0.5;
            cursor: not-allowed;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input[type="text"], textarea, select {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        textarea {
            height: 100px;
        }
        .checkbox-cell {
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Task Manager</h1>
        <div>
            <a href="/">Home</a>
            <a href="/feature_form">Add Feature</a>
        </div>
    </div>
"""

HTML_FOOTER = """
    <footer style="margin-top: 40px; padding: 20px; text-align: center; color: #666; border-top: 1px solid #eee;">
        <p>Task Manager v1.0.0 | Developed with ♥</p>
    </footer>
</body>
</html>
"""

# Data loading functions
def get_all_tasks():
    """Get all tasks from files"""
    tasks = []
    try:
        if TASKS_DIR.exists():
            for file in TASKS_DIR.glob("*.json"):
                try:
                    with open(file, 'r') as f:
                        task = json.load(f)
                        tasks.append(task)
                except Exception as e:
                    print(f"Error reading task file {file}: {e}")
    except Exception as e:
        print(f"Error accessing tasks directory: {e}")
    return tasks

def read_task_data(task_id):
    """Read data for a specific task"""
    try:
        task_file = TASKS_DIR / f"TASK-{task_id}.json"
        if task_file.exists():
            with open(task_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error reading task {task_id}: {e}")
    return None

def get_all_projects():
    """Get all projects from files"""
    projects = []
    try:
        if PROJECTS_DIR.exists():
            project_dirs = [d for d in PROJECTS_DIR.iterdir() if d.is_dir()]
            for project_dir in project_dirs:
                project_file = project_dir / "project.json"
                if project_file.exists():
                    try:
                        with open(project_file, 'r', encoding='utf-8') as f:
                            project = json.load(f)
                            projects.append(project)
                    except Exception as e:
                        print(f"Error reading project file {project_file}: {str(e)}")
    except Exception as e:
        print(f"Error listing projects: {str(e)}")
    
    return projects

def get_agent_status():
    """Get status of agents"""
    agents = []
    if AGENTS_DIR.exists():
        agent_files = [f for f in AGENTS_DIR.glob("*.py") if f.name != "__init__.py"]
        now = datetime.datetime.now()
        
        for agent_file in agent_files:
            try:
                # Check if agent file has been modified recently (within 5 minutes)
                mod_time = datetime.datetime.fromtimestamp(agent_file.stat().st_mtime)
                time_diff = (now - mod_time).total_seconds() / 60
                
                # Check file size as a simple heuristic for implementation
                size = agent_file.stat().st_size
                
                agent = {
                    "name": agent_file.stem,
                    "active": time_diff < 5,  # Consider active if modified in last 5 minutes
                    "last_activity": mod_time.isoformat(),
                    "size": size,
                    "implemented": size > 1000  # Simple heuristic - non-stub files are typically > 1KB
                }
                agents.append(agent)
            except Exception as e:
                print(f"Error checking agent {agent_file}: {str(e)}")
    
    return agents

# HTML generation functions
def generate_organized_tasks_html(tasks, projects):
    """Generate HTML for tasks organized by project and parent task"""
    if not tasks:
        return "<p>No tasks found</p>"
    
    # Create project info lookup dict
    project_dict = {p.get('project_id'): p for p in projects}
    
    # Organize tasks by project
    tasks_by_project = {}
    for task in tasks:
        project_id = task.get('project_id')
        if project_id not in tasks_by_project:
            tasks_by_project[project_id] = []
        tasks_by_project[project_id].append(task)
    
    # Generate HTML for each project
    html = """
    <form action="/bulk_delete" method="post" id="bulk-delete-form">
    <button type="submit" class="btn btn-danger" id="bulk-delete-btn" disabled style="margin-bottom: 20px;">
        Delete Selected Tasks
    </button>
    """
    
    # Sort projects by name
    sorted_project_ids = sorted(
        tasks_by_project.keys(),
        key=lambda pid: project_dict.get(pid, {}).get('name', 'Unknown') if pid else 'zzz'  # Unknown at the end
    )
    
    for project_id in sorted_project_ids:
        project = project_dict.get(project_id, {})
        project_name = project.get('name', 'Unknown Project')
        project_tasks = tasks_by_project[project_id]
        
        # Group tasks by parent task
        root_tasks = [t for t in project_tasks if not t.get('parent_task_id')]
        tasks_by_parent = {}
        subtasks = [t for t in project_tasks if t.get('parent_task_id')]
        
        for task in subtasks:
            parent_id = task.get('parent_task_id')
            if parent_id not in tasks_by_parent:
                tasks_by_parent[parent_id] = []
            tasks_by_parent[parent_id].append(task)
        
        # Start project section
        html += f"""
        <div class="card" style="margin-bottom: 20px;">
            <h3>
                <a href="/project?project_id={project_id}" style="text-decoration: none;">
                    {project_name}
                </a>
            </h3>
        """
        
        # Table for root tasks
        if root_tasks:
            html += """
            <table style="width: 100%;">
                <tr>
                    <th style="width: 30px;"><input type="checkbox" class="project-select-all"></th>
                    <th style="width: 120px;">Task ID</th>
                    <th>Description</th>
                    <th style="width: 100px;">Status</th>
                    <th style="width: 80px;">Priority</th>
                    <th style="width: 100px;">Actions</th>
                </tr>
            """
            
            # Sort root tasks by priority (higher first)
            sorted_root_tasks = sorted(root_tasks, key=lambda t: float(t.get('priority', 0)), reverse=True)
            
            for task in sorted_root_tasks:
                task_id = task.get('task_id', '')
                description = task.get('description', '')
                status = task.get('status', '')
                priority = task.get('priority', '')
                has_subtasks = task_id in tasks_by_parent
                
                # Determine status class
                status_class = f"status-{status}" if status else ""
                
                # Generate root task row
                html += f"""
                <tr class="parent-task">
                    <td><input type="checkbox" name="selected_tasks" value="{task_id}" class="task-checkbox"></td>
                    <td>{task_id}</td>
                    <td>
                        <a href="/view?task_id={task_id}">{description}</a>
                        {' <span style="color: #888;">(has subtasks)</span>' if has_subtasks else ''}
                    </td>
                    <td><span class="status {status_class}">{status}</span></td>
                    <td>{priority}</td>
                    <td>
                        <a href="/view?task_id={task_id}" class="btn">View</a>
                    </td>
                </tr>
                """
                
                # Add subtasks with indentation
                if has_subtasks:
                    # Sort subtasks by priority
                    sorted_subtasks = sorted(tasks_by_parent[task_id], key=lambda t: float(t.get('priority', 0)), reverse=True)
                    
                    for subtask in sorted_subtasks:
                        subtask_id = subtask.get('task_id', '')
                        subtask_desc = subtask.get('description', '')
                        subtask_status = subtask.get('status', '')
                        subtask_priority = subtask.get('priority', '')
                        
                        # Determine status class
                        subtask_status_class = f"status-{subtask_status}" if subtask_status else ""
                        
                        # Generate subtask row with indentation
                        html += f"""
                        <tr class="subtask">
                            <td><input type="checkbox" name="selected_tasks" value="{subtask_id}" class="task-checkbox"></td>
                            <td>{subtask_id}</td>
                            <td style="padding-left: 20px;">
                                <span style="color: #666;">↳</span> <a href="/view?task_id={subtask_id}">{subtask_desc}</a>
                            </td>
                            <td><span class="status {subtask_status_class}">{subtask_status}</span></td>
                            <td>{subtask_priority}</td>
                            <td>
                                <a href="/view?task_id={subtask_id}" class="btn">View</a>
                            </td>
                        </tr>
                        """
            
            html += "</table>"
        else:
            html += "<p>No tasks in this project</p>"
        
        html += """
        <div style="margin-top: 10px;">
            <a href="/feature_form" class="btn btn-success">Add Feature</a>
        </div>
        </div>
        """
    
    # Add JavaScript for checkbox handling
    html += """
    <script>
    // Handle select all checkboxes for each project
    document.querySelectorAll('.project-select-all').forEach(function(checkbox) {
        checkbox.addEventListener('change', function() {
            var projectCard = this.closest('.card');
            var checkboxes = projectCard.querySelectorAll('.task-checkbox');
            checkboxes.forEach(function(box) {
                box.checked = checkbox.checked;
            });
            updateDeleteButton();
        });
    });
    
    // Handle individual checkboxes
    document.querySelectorAll('.task-checkbox').forEach(function(checkbox) {
        checkbox.addEventListener('change', updateDeleteButton);
    });
    
    function updateDeleteButton() {
        var checkboxes = document.querySelectorAll('.task-checkbox:checked');
        var deleteButton = document.getElementById('bulk-delete-btn');
        deleteButton.disabled = checkboxes.length === 0;
        
        if (checkboxes.length > 0) {
            deleteButton.textContent = 'Delete Selected Tasks (' + checkboxes.length + ')';
        } else {
            deleteButton.textContent = 'Delete Selected Tasks';
        }
    }
    
    document.getElementById('bulk-delete-form').addEventListener('submit', function(e) {
        var checkboxes = document.querySelectorAll('.task-checkbox:checked');
        
        if (checkboxes.length === 0) {
            e.preventDefault();
            alert('Please select at least one task to delete.');
            return false;
        }
        
        if (!confirm('Are you sure you want to delete ' + checkboxes.length + ' task(s)? This cannot be undone.')) {
            e.preventDefault();
            return false;
        }
    });
    </script>
    </form>
    """
    
    return html

def generate_new_feature_form():
    """Generate HTML for the feature request form"""
    # Get all projects for the dropdown
    projects = get_all_projects()
    
    project_options = ""
    for project in projects:
        project_id = project.get('project_id', '')
        project_name = project.get('name', '')
        project_options += f'<option value="{project_id}">{project_name}</option>'
    
    html = """
    <div class="card">
        <h2>Add New Feature</h2>
        <form action="/add_feature" method="post">
            <div class="form-group">
                <label for="description">Feature Title:</label>
                <input type="text" id="description" name="description" required placeholder="Brief description of the feature">
            </div>
            
            <div class="form-group">
                <label for="details">Details:</label>
                <textarea id="details" name="details" placeholder="Detailed explanation of the feature, user stories, etc."></textarea>
            </div>
            
            <div class="form-group">
                <label for="priority">Priority:</label>
                <select id="priority" name="priority">
                    <option value="1">Low</option>
                    <option value="2" selected>Medium</option>
                    <option value="3">High</option>
                </select>
            </div>
            
            <div class="form-group">
                <label for="project_id">Project:</label>
                <select id="project_id" name="project_id">
                    <option value="">-- No Project --</option>
    """
    
    html += project_options
    
    html += """
                </select>
            </div>
            
            <button type="submit" class="btn btn-success">Add Feature</button>
        </form>
    </div>
    """
    
    return html

def generate_task_view_html(task_id):
    """Generate HTML for a task view"""
    task = read_task_data(task_id)
    if not task:
        return "<p>Task not found</p>"
    
    # Get parent task if it exists
    parent_task = None
    parent_task_id = task.get('parent_task_id')
    if parent_task_id:
        parent_task = read_task_data(parent_task_id)
    
    # Get subtasks if any exist
    subtasks = []
    all_tasks = get_all_tasks()
    for t in all_tasks:
        if t.get('parent_task_id') == task_id:
            subtasks.append(t)
    
    # Sort subtasks by priority
    subtasks = sorted(subtasks, key=lambda t: float(t.get('priority', 0)), reverse=True)
    
    # Get project info
    project_id = task.get('project_id')
    project_name = "Unknown Project"
    if project_id:
        all_projects = get_all_projects()
        for p in all_projects:
            if p.get('project_id') == project_id:
                project_name = p.get('name', 'Unknown Project')
                break
    
    # Determine status class
    status = task.get('status', '')
    status_class = f"status-{status}" if status else ""
    
    # Format dates
    created_at = task.get('created_at', '')
    if created_at:
        try:
            # Parse ISO format and convert to more readable format
            created_dt = datetime.datetime.fromisoformat(created_at)
            created_at = created_dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            pass  # Keep original format if parsing fails
    
    updated_at = task.get('updated_at', '')
    if updated_at:
        try:
            updated_dt = datetime.datetime.fromisoformat(updated_at)
            updated_at = updated_dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            pass
    
    html = f"""
    <div class="card">
        <h2>Task: {task.get('description', 'No Description')}</h2>
        
        <div class="task-metadata">
            <p><strong>Task ID:</strong> {task_id}</p>
            <p><strong>Status:</strong> <span class="status {status_class}">{status}</span></p>
            <p><strong>Priority:</strong> {task.get('priority', 'Not set')}</p>
            <p><strong>Project:</strong> <a href="/project?project_id={project_id}">{project_name}</a></p>
            
            {f'<p><strong>Parent Task:</strong> <a href="/view?task_id={parent_task_id}">{parent_task.get("description", "Unknown")}</a></p>' if parent_task else ''}
            
            <p><strong>Created:</strong> {created_at}</p>
            <p><strong>Last Updated:</strong> {updated_at}</p>
            {f'<p><strong>Due:</strong> {task.get("due_date", "Not set")}</p>' if task.get('due_date') else ''}
        </div>
        
        <div class="task-content">
            <h3>Details</h3>
            <pre>{task.get('details', task.get('requirements', ['No details provided'])[0] if task.get('requirements') else 'No details provided')}</pre>
        </div>
        
        <div class="task-actions" style="margin-top: 20px;">
            <a href="/edit?task_id={task_id}" class="btn">Edit Task</a>
            <form action="/delete_task" method="post" style="display: inline-block; margin-left: 10px;">
                <input type="hidden" name="task_id" value="{task_id}">
                <button type="submit" class="btn btn-danger" onclick="return confirm('Are you sure you want to delete this task?');">Delete Task</button>
            </form>
            <a href="/" class="btn" style="margin-left: 10px;">Back to Dashboard</a>
        </div>
        
        {generate_subtasks_section(subtasks) if subtasks else ''}
        
        <div style="margin-top: 20px;">
            <h3>Add Subtask</h3>
            <form action="/add_subtask" method="post">
                <input type="hidden" name="parent_task_id" value="{task_id}">
                <input type="hidden" name="project_id" value="{project_id}">
                
                <div class="form-group">
                    <label for="description">Description:</label>
                    <input type="text" id="description" name="description" required>
                </div>
                
                <div class="form-group">
                    <label for="details">Details:</label>
                    <textarea id="details" name="details"></textarea>
                </div>
                
                <div class="form-group">
                    <label for="priority">Priority:</label>
                    <select id="priority" name="priority">
                        <option value="1">Low</option>
                        <option value="2" selected>Medium</option>
                        <option value="3">High</option>
                    </select>
                </div>
                
                <button type="submit" class="btn btn-success">Add Subtask</button>
            </form>
        </div>
    </div>
    """
    
    return html

def generate_subtasks_section(subtasks):
    """Generate HTML for subtasks section"""
    if not subtasks:
        return ""
    
    html = """
    <div style="margin-top: 20px;">
        <h3>Subtasks</h3>
        <table style="width: 100%;">
            <tr>
                <th style="width: 120px;">Task ID</th>
                <th>Description</th>
                <th style="width: 100px;">Status</th>
                <th style="width: 80px;">Priority</th>
                <th style="width: 100px;">Actions</th>
            </tr>
    """
    
    for task in subtasks:
        task_id = task.get('task_id', '')
        description = task.get('description', '')
        status = task.get('status', '')
        priority = task.get('priority', '')
        
        # Determine status class
        status_class = f"status-{status}" if status else ""
        
        html += f"""
        <tr>
            <td>{task_id}</td>
            <td><a href="/view?task_id={task_id}">{description}</a></td>
            <td><span class="status {status_class}">{status}</span></td>
            <td>{priority}</td>
            <td>
                <a href="/view?task_id={task_id}" class="btn">View</a>
            </td>
        </tr>
        """
    
    html += "</table></div>"
    return html

def generate_task_details_html(task_id, tasks, projects):
    """Generate HTML for task details"""
    # Find the task with the given ID
    task = next((t for t in tasks if t.get('task_id') == task_id), None)
    
    if not task:
        return f"<p>Task {task_id} not found</p>"
    
    # Get project info if available
    project_id = task.get('project_id')
    project = next((p for p in projects if p.get('project_id') == project_id), None)
    project_name = project.get('name', 'Unknown') if project else 'Unknown'
    
    # Generate details
    description = task.get('description', 'No description')
    status = task.get('status', 'unknown')
    priority = task.get('priority', 'N/A')
    language = task.get('language', 'python')
    created_at = task.get('created_at', '')
    updated_at = task.get('updated_at', '')
    
    # History entries
    history = task.get('history', [])
    history_html = ""
    if history:
        history_html += "<h3>History</h3><ul>"
        for entry in history:
            timestamp = entry.get('timestamp', '')
            status = entry.get('status', '')
            message = entry.get('message', '')
            history_html += f"<li><strong>{timestamp}</strong>: {status} - {message}</li>"
        history_html += "</ul>"
    
    # Code files
    code = task.get('code', {})
    code_files = code.get('files', [])
    code_html = "<h3>Code Files</h3>"
    
    if code_files:
        code_html += "<ul>"
        for file_item in code_files:
            # Handle both simple file paths and complex objects with path and content
            if isinstance(file_item, dict):
                file_path = file_item.get('path', '')
                content_preview = file_item.get('content', '')[:200] + '...' if len(file_item.get('content', '')) > 200 else file_item.get('content', '')
            else:
                file_path = file_item
                content_preview = ""
                
                # Try to read file from filesystem
                try:
                    # Check in implementations directory first
                    impl_file = IMPLEMENTATIONS_DIR / f"task_{task_id.split('-')[1]}.py"
                    if impl_file.exists():
                        with open(impl_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            content_preview = content[:200] + '...' if len(content) > 200 else content
                    # Then check the exact path
                    elif Path(file_path).exists():
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            content_preview = content[:200] + '...' if len(content) > 200 else content
                except Exception as e:
                    content_preview = f"Error reading file: {str(e)}"
            
            file_name = os.path.basename(file_path)
            code_html += f"""
            <li>
                <strong>{file_name}</strong> ({file_path})
                <div class="code-block">{content_preview}</div>
            </li>
            """
        code_html += "</ul>"
    else:
        code_html += "<p>No code files associated with this task</p>"
        # Add button to trigger agent if no code files
        code_html += f"""
        <p>
            <a href="/trigger_agent?task_id={task_id}" class="btn btn-success">
                Trigger Agent Processing
            </a>
        </p>
        """
    
    # Test results
    test_results = task.get('test_results')
    test_html = "<h3>Test Results</h3>"
    if test_results:
        passed = test_results.get('passed', False)
        status = "Passed" if passed else "Failed"
        details = test_results.get('details', [])
        
        test_html += f"<p><strong>Status:</strong> {status}</p>"
        
        if details:
            test_html += "<ul>"
            for detail in details:
                test_html += f"<li>{detail}</li>"
            test_html += "</ul>"
    else:
        test_html += "<p>No test results available</p>"
    
    # Put it all together
    html = f"""
    <div class="card">
        <h2>Task Details: {task_id}</h2>
        <p><strong>Description:</strong> {description}</p>
        <p><strong>Status:</strong> <span class="status status-{status}">{status}</span></p>
        <p><strong>Priority:</strong> {priority}</p>
        <p><strong>Language:</strong> {language}</p>
        <p><strong>Project:</strong> <a href="/project?project_id={project_id}">{project_name}</a></p>
        <p><strong>Created:</strong> {created_at}</p>
        <p><strong>Updated:</strong> {updated_at}</p>
        
        <p>
            <a href="/" class="btn">Back to Dashboard</a>
            <a href="/trigger_agent?task_id={task_id}" class="btn btn-success">
                Trigger Agent Processing
            </a>
        </p>
    </div>
    
    {history_html}
    {code_html}
    {test_html}
    """
    
    return html

def trigger_agent_processing(task_id):
    """Trigger agent processing for a task by updating its status"""
    task_file = TASKS_DIR / f"{task_id}.json"
    if task_file.exists():
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                task = json.load(f)
            
            # Add a history entry for agent triggering
            if 'history' not in task:
                task['history'] = []
                
            timestamp = datetime.datetime.now().isoformat()
            task['history'].append({
                "timestamp": timestamp,
                "status": "implementing",
                "message": "Agent processing manually triggered"
            })
            
            # Update status to implementing (matches TaskStatus enum in models/task.py)
            task['status'] = "implementing"
            task['updated_at'] = timestamp
            
            with open(task_file, 'w', encoding='utf-8') as f:
                json.dump(task, f, indent=2)
            
            # Start agent processing in a separate thread to avoid blocking
            threading.Thread(target=process_task_with_agent, args=(task_id,), daemon=True).start()
            print(f"Triggered agent processing for task {task_id}")
            
            return True
        except Exception as e:
            print(f"Error triggering agent for task {task_id}: {str(e)}")
    
    return False

def process_task_with_agent(task_id):
    """Process a task using the orchestration agent API directly"""
    try:
        # Import the OrchestratorAgent here to avoid circular imports
        from agents.orchestration_agent import OrchestratorAgent
        import os
        
        # Initialize the orchestrator with the current directory
        base_path = os.path.dirname(os.path.abspath(__file__))
        orchestrator = OrchestratorAgent(base_path)
        
        # Load the task
        task = orchestrator.get_task(task_id)
        
        if task:
            print(f"Processing task {task_id} with priority {task.priority}")
            
            # Add the task to the processing queue
            with orchestrator.task_queue_lock:
                # Lower priority score = higher priority in queue
                priority_value = 100 - float(task.priority)
                orchestrator.task_queue.put((priority_value, task_id))
            
            # Start processing if not already running
            if not orchestrator.running:
                orchestrator.start()
                
            print(f"Task {task_id} added to processing queue with priority {priority_value}")
        else:
            print(f"Task {task_id} not found in orchestrator tasks - may need to restart the orchestration agent")
            print("This can happen if the task status was manually changed to an invalid status value")
            print("The status has been updated, so trying again or restarting the web dashboard may help")
    except Exception as e:
        print(f"Error during task processing: {str(e)}")
        import traceback
        traceback.print_exc()

def generate_project_view_html(project_id):
    """Generate HTML for a project view"""
    # Get all projects
    all_projects = get_all_projects()
    
    # Find the current project
    project = None
    for p in all_projects:
        if p.get('project_id') == project_id:
            project = p
            break
    
    if not project:
        return "<p>Project not found</p>"
    
    # Get all tasks for the project
    all_tasks = get_all_tasks()
    project_tasks = [t for t in all_tasks if t.get('project_id') == project_id]
    
    # Organize tasks by parent/child relationships
    root_tasks = [t for t in project_tasks if not t.get('parent_task_id')]
    tasks_by_parent = {}
    
    for task in project_tasks:
        parent_id = task.get('parent_task_id')
        if parent_id:
            if parent_id not in tasks_by_parent:
                tasks_by_parent[parent_id] = []
            tasks_by_parent[parent_id].append(task)
    
    html = f"""
    <div class="card">
        <h2>Project: {project.get('name', 'Unnamed Project')}</h2>
        
        <div class="project-metadata">
            <p><strong>Project ID:</strong> {project_id}</p>
            <p><strong>Description:</strong> {project.get('description', 'No description')}</p>
        </div>
        
        <div style="margin-top: 20px;">
            <a href="/feature_form?project_id={project_id}" class="btn btn-success">Add Feature</a>
            <a href="/" class="btn">Back to Dashboard</a>
        </div>
        
        <div style="margin-top: 20px;">
            <h3>Tasks</h3>
    """
    
    if project_tasks:
        html += """
        <table style="width: 100%;">
            <tr>
                <th style="width: 120px;">Task ID</th>
                <th>Description</th>
                <th style="width: 100px;">Status</th>
                <th style="width: 80px;">Priority</th>
                <th style="width: 100px;">Actions</th>
            </tr>
        """
        
        # Sort root tasks by priority
        root_tasks = sorted(root_tasks, key=lambda t: float(t.get('priority', 0)), reverse=True)
        
        for task in root_tasks:
            task_id = task.get('task_id', '')
            description = task.get('description', '')
            status = task.get('status', '')
            priority = task.get('priority', '')
            has_subtasks = task_id in tasks_by_parent
            
            # Determine status class
            status_class = f"status-{status}" if status else ""
            
            html += f"""
            <tr class="parent-task">
                <td>{task_id}</td>
                <td>
                    <a href="/view?task_id={task_id}">{description}</a>
                    {' <span style="color: #888;">(has subtasks)</span>' if has_subtasks else ''}
                </td>
                <td><span class="status {status_class}">{status}</span></td>
                <td>{priority}</td>
                <td>
                    <a href="/view?task_id={task_id}" class="btn">View</a>
                </td>
            </tr>
            """
            
            # Add subtasks if they exist
            if has_subtasks:
                subtasks = sorted(tasks_by_parent[task_id], key=lambda t: float(t.get('priority', 0)), reverse=True)
                
                for subtask in subtasks:
                    subtask_id = subtask.get('task_id', '')
                    subtask_desc = subtask.get('description', '')
                    subtask_status = subtask.get('status', '')
                    subtask_priority = subtask.get('priority', '')
                    
                    # Determine status class
                    subtask_status_class = f"status-{subtask_status}" if subtask_status else ""
                    
                    html += f"""
                    <tr class="subtask">
                        <td>{subtask_id}</td>
                        <td style="padding-left: 20px;">
                            <span style="color: #666;">↳</span> <a href="/view?task_id={subtask_id}">{subtask_desc}</a>
                        </td>
                        <td><span class="status {subtask_status_class}">{subtask_status}</span></td>
                        <td>{subtask_priority}</td>
                        <td>
                            <a href="/view?task_id={subtask_id}" class="btn">View</a>
                        </td>
                    </tr>
                    """
        
        html += "</table>"
    else:
        html += "<p>No tasks in this project</p>"
    
    html += """
        </div>
    </div>
    """
    
    return html

def generate_agent_status_html():
    """Generate HTML for agent status dashboard"""
    agents = get_agent_status()
    
    html = "<h2>Agent Status</h2>"
    
    if not agents:
        html += "<p>No agents found</p>"
        return html
    
    html += """
    <table>
        <tr>
            <th>Agent</th>
            <th>Status</th>
            <th>Last Activity</th>
            <th>Size</th>
        </tr>
    """
    
    for agent in agents:
        name = agent.get('name', 'Unknown')
        active = agent.get('active', False)
        last_activity = agent.get('last_activity', 'Unknown')
        size = agent.get('size', 0)
        implemented = agent.get('implemented', False)
        
        # Determine status
        if active:
            status_class = "agent-active"
            status_text = "Active"
        elif implemented:
            status_class = "agent-inactive"
            status_text = "Inactive"
        else:
            status_class = "agent-unknown"
            status_text = "Not Implemented"
        
        html += f"""
        <tr>
            <td>{name}</td>
            <td><span class="agent-status {status_class}"></span> {status_text}</td>
            <td>{last_activity}</td>
            <td>{size} bytes</td>
        </tr>
        """
    
    html += "</table>"
    return html

def delete_tasks(task_ids):
    """Delete multiple tasks"""
    if not task_ids:
        return 0
    
    # Convert to list if it's a string
    if isinstance(task_ids, str):
        task_ids = [task_ids]
    
    deleted_count = 0
    for task_id in task_ids:
        task_file = TASKS_DIR / f"{task_id}.json"
        if task_file.exists():
            try:
                task_file.unlink()
                deleted_count += 1
                print(f"Deleted task {task_id}")
            except Exception as e:
                print(f"Error deleting task {task_id}: {str(e)}")
    
    return deleted_count

def generate_edit_task_form(task_id):
    """Generate HTML for editing a task"""
    task = read_task_data(task_id)
    if not task:
        return "<p>Task not found</p>"
    
    # Get all projects for the dropdown
    projects = get_all_projects()
    
    project_options = ""
    current_project_id = task.get('project_id', '')
    
    for project in projects:
        project_id = project.get('project_id', '')
        project_name = project.get('name', '')
        selected = 'selected' if project_id == current_project_id else ''
        project_options += f'<option value="{project_id}" {selected}>{project_name}</option>'
    
    html = f"""
    <div class="card">
        <h2>Edit Task</h2>
        <form action="/update_task" method="post">
            <input type="hidden" name="task_id" value="{task_id}">
            
            <div class="form-group">
                <label for="description">Description:</label>
                <input type="text" id="description" name="description" value="{task.get('description', '')}" required>
            </div>
            
            <div class="form-group">
                <label for="details">Details:</label>
                <textarea id="details" name="details">{task.get('details', '')}</textarea>
            </div>
            
            <div class="form-group">
                <label for="status">Status:</label>
                <select id="status" name="status">
                    <option value="not_started" {"selected" if task.get('status') == 'not_started' else ''}>Not Started</option>
                    <option value="in_progress" {"selected" if task.get('status') == 'in_progress' else ''}>In Progress</option>
                    <option value="complete" {"selected" if task.get('status') == 'complete' else ''}>Complete</option>
                    <option value="blocked" {"selected" if task.get('status') == 'blocked' else ''}>Blocked</option>
                </select>
            </div>
            
            <div class="form-group">
                <label for="priority">Priority:</label>
                <select id="priority" name="priority">
                    <option value="1" {"selected" if task.get('priority') == '1' else ''}>Low</option>
                    <option value="2" {"selected" if task.get('priority') == '2' else ''}>Medium</option>
                    <option value="3" {"selected" if task.get('priority') == '3' else ''}>High</option>
                </select>
            </div>
            
            <div class="form-group">
                <label for="project_id">Project:</label>
                <select id="project_id" name="project_id">
                    <option value="">-- No Project --</option>
                    {project_options}
                </select>
            </div>
            
            <div class="form-group">
                <label for="due_date">Due Date (optional):</label>
                <input type="date" id="due_date" name="due_date" value="{task.get('due_date', '')}">
            </div>
            
            <button type="submit" class="btn btn-success">Update Task</button>
            <a href="/view?task_id={task_id}" class="btn">Cancel</a>
        </form>
    </div>
    """
    
    return html

def update_task(task_id, updated_data):
    """Update a task with new data"""
    task_file = os.path.join(TASKS_DIR, f"{task_id}.json")
    
    if not os.path.exists(task_file):
        return False
    
    try:
        # Read existing task data
        with open(task_file, 'r') as f:
            task_data = json.load(f)
        
        # Update task data with new values
        for key, value in updated_data.items():
            if value or value == 0:  # Update if value is not empty
                task_data[key] = value
        
        # Write updated data back to file
        with open(task_file, 'w') as f:
            json.dump(task_data, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error updating task: {e}")
        return False

def generate_bulk_delete_confirmation_html(selected_tasks):
    """Generate HTML for bulk delete confirmation"""
    if not selected_tasks:
        return """
        <div class="card">
            <h2>No Tasks Selected</h2>
            <p>No tasks were selected for deletion.</p>
            <a href="/" class="btn">Return to Dashboard</a>
        </div>
        """
    
    # Get task data for each task ID
    task_data = []
    for task_id in selected_tasks:
        task = read_task_data(task_id)
        if task:
            task_data.append({
                'task_id': task_id,
                'description': task.get('description', 'No description')
            })
    
    html = """
    <div class="card">
        <h2>Confirm Deletion</h2>
        <p>Are you sure you want to delete the following tasks? This action cannot be undone.</p>
        
        <table style="width: 100%;">
            <tr>
                <th style="width: 120px;">Task ID</th>
                <th>Description</th>
            </tr>
    """
    
    for task in task_data:
        html += f"""
        <tr>
            <td>{task['task_id']}</td>
            <td>{task['description']}</td>
        </tr>
        """
    
    html += """
        </table>
        
        <div style="margin-top: 20px;">
            <form action="/confirm_delete" method="post">
    """
    
    # Add hidden inputs for each task ID
    for task_id in selected_tasks:
        html += f'<input type="hidden" name="confirm_tasks" value="{task_id}">'
    
    html += """
                <button type="submit" class="btn btn-danger">Confirm Delete</button>
                <a href="/" class="btn">Cancel</a>
            </form>
        </div>
    </div>
    """
    
    return html

def get_html_page(page_name, **kwargs):
    """Return HTML for specified page"""
    html = HTML_HEADER
    
    if page_name == "home":
        tasks = get_all_tasks()
        projects = get_all_projects()
        html += "<h2>Task Dashboard</h2>"
        html += generate_organized_tasks_html(tasks, projects)
    elif page_name == "feature_form":
        html += generate_new_feature_form()
    elif page_name == "feature_added":
        task_id = kwargs.get('task_id', '')
        html += f"""
        <div class="card">
            <h2>Feature Request Added</h2>
            <p>Your feature request has been added successfully as task {task_id}.</p>
            <p><a href="/" class="btn">Return to Dashboard</a></p>
            <p><a href="/view?task_id={task_id}" class="btn">View Task</a></p>
        </div>
        """
    elif page_name == "view_task":
        task_id = kwargs.get('task_id', '')
        html += generate_task_view_html(task_id)
    elif page_name == "edit_task":
        task_id = kwargs.get('task_id', '')
        html += generate_edit_task_form(task_id)
    elif page_name == "project":
        project_id = kwargs.get('project_id', '')
        html += generate_project_view_html(project_id)
    elif page_name == "bulk_delete_confirmation":
        selected_tasks = kwargs.get('selected_tasks', [])
        html += generate_bulk_delete_confirmation_html(selected_tasks)
    elif page_name == "tasks_deleted":
        count = kwargs.get('count', 0)
        html += f"""
        <div class="card">
            <h2>Tasks Deleted</h2>
            <p>{count} task(s) have been deleted successfully.</p>
            <p><a href="/" class="btn">Return to Dashboard</a></p>
        </div>
        """
    
    html += HTML_FOOTER
    return html

def add_feature(form_data):
    """Handle adding a new feature task."""
    try:
        project_id = form_data.get('project_id')
        
        # Check if we need to create a new project
        if project_id == 'new_project':
            project_name = form_data.get('new_project_name')
            project_description = form_data.get('new_project_description')
            
            if not project_name:
                return "Error: New project name is required"
            
            # Create a new project
            project_id = f"PROJ-{uuid.uuid4().hex[:8]}"
            project_dir = PROJECTS_DIR / project_id
            project_dir.mkdir(exist_ok=True)
            
            project = {
                "project_id": project_id,
                "name": project_name,
                "description": project_description,
                "status": "active",
                "created_at": datetime.datetime.now().isoformat(),
                "updated_at": datetime.datetime.now().isoformat(),
                "root_tasks": []
            }
            
            with open(project_dir / "project.json", 'w', encoding='utf-8') as f:
                json.dump(project, f, indent=2)
            
            print(f"Created new project: {project_name} ({project_id})")
        
        # Now create the task with the project_id
        description = form_data.get('description')
        language = form_data.get('language', 'python')
        priority = float(form_data.get('priority', 50))
        
        task_id = f"TASK-{uuid.uuid4().hex[:8]}"
        task = {
            "task_id": task_id,
            "description": description,
            "language": language,
            "requirements": [],
            "priority": priority,
            "status": "created",
            "created_at": datetime.datetime.now().isoformat(),
            "updated_at": datetime.datetime.now().isoformat(),
            "history": [],
            "project_id": project_id,
            "parent_task_id": None,
            "subtask_ids": [],
            "related_task_ids": [],
            "code": {
                "files": [],
                "tests": []
            },
            "test_results": None,
            "quality_results": None,
            "integration_results": None
        }
        
        task_file = TASKS_DIR / f"{task_id}.json"
        with open(task_file, 'w', encoding='utf-8') as f:
            json.dump(task, f, indent=2)
        
        # If this is a new task for an existing project, add it to the project's root_tasks
        if project_id != 'new_project':
            project_file = list(PROJECTS_DIR.glob(f"{project_id}/project.json"))
            if project_file:
                with open(project_file[0], 'r', encoding='utf-8') as f:
                    project = json.load(f)
                
                if "root_tasks" not in project:
                    project["root_tasks"] = []
                
                project["root_tasks"].append(task_id)
                project["updated_at"] = datetime.datetime.now().isoformat()
                
                with open(project_file[0], 'w', encoding='utf-8') as f:
                    json.dump(project, f, indent=2)
        
        return task_id
    except Exception as e:
        error_message = f"Error adding feature: {str(e)}"
        print(error_message)
        traceback.print_exc()
        return None

def create_task(description, details=None, priority=None, project_id=None, parent_task_id=None):
    """Create a new task and return its ID"""
    # Generate a random task ID
    task_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    # Create task data
    task_data = {
        'task_id': task_id,
        'description': description,
        'status': 'not_started',
        'creation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Add optional fields if provided
    if details:
        task_data['details'] = details
    if priority:
        task_data['priority'] = priority
    if project_id:
        task_data['project_id'] = project_id
    if parent_task_id:
        task_data['parent_task_id'] = parent_task_id
    
    # Write task to file
    task_file = os.path.join(TASKS_DIR, f"{task_id}.json")
    try:
        with open(task_file, 'w') as f:
            json.dump(task_data, f, indent=2)
        return task_id
    except Exception as e:
        print(f"Error creating task: {e}")
        return None

def main():
    """Main function to start the web dashboard"""
    print("Starting Task Manager Web Dashboard...")
    print(f"Looking for tasks in: {TASKS_DIR}")
    print(f"Looking for projects in: {PROJECTS_DIR}")
    
    # Define the request handler
    class TaskManagerHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            """Handle GET requests"""
            parsed_url = urllib.parse.urlparse(self.path)
            path = parsed_url.path
            query = urllib.parse.parse_qs(parsed_url.query)
            
            # Route to appropriate handlers
            if path == "/":
                self._send_response(get_html_page("home"))
            elif path == "/refresh":
                self.send_response(302)  # Redirect
                self.send_header('Location', '/')
                self.end_headers()
            elif path == "/feature_form":
                self._send_response(get_html_page("feature_form"))
            elif path == "/feature_added":
                task_id = query.get('task_id', [''])[0]
                self._send_response(get_html_page("feature_added", task_id=task_id))
            elif path == "/view":
                task_id = query.get('task_id', [''])[0]
                self._send_response(get_html_page("view_task", task_id=task_id))
            elif path == "/project":
                project_id = query.get('project_id', [''])[0]
                self._send_response(get_html_page("project", project_id=project_id))
            elif path == "/agent_status":
                self._send_response(get_html_page("agent_status"))
            elif path == "/trigger_agent":
                task_id = query.get('task_id', [''])[0]
                success = trigger_agent_processing(task_id)
                if success:
                    self._send_response(get_html_page("agent_triggered", task_id=task_id))
                else:
                    self._send_response(f"<p>Error triggering agent for task {task_id}</p>")
            elif path == "/kanban":
                self._send_response("<h2>Kanban Board</h2><p>Kanban board feature coming soon!</p>")
            else:
                self.send_response(404)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b"404 - Not Found")
                
        def do_POST(self):
            """Handle POST requests"""
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            form_data = urllib.parse.parse_qs(post_data)
            
            # Convert form data from lists to single values
            single_value_form_data = {k: v[0] for k, v in form_data.items() if len(v) == 1}
            
            if self.path == "/add_feature":
                # Process the feature request
                task_id = add_feature(single_value_form_data)
                
                if task_id:
                    # Redirect to a success page
                    self.send_response(302)
                    self.send_header('Location', '/feature_added?task_id=' + task_id)
                    self.end_headers()
                else:
                    # Show error message
                    self._send_response("Error adding feature")
            elif self.path == "/bulk_delete":
                # Handle bulk deletion of tasks
                selected_tasks = form_data.get('selected_tasks', [])
                if not selected_tasks:
                    self._send_response("No tasks selected for deletion", 400)
                else:
                    # Show confirmation page instead of deleting directly
                    response = get_html_page("bulk_delete_confirmation", selected_tasks=selected_tasks)
                    self._send_response(response)
            elif self.path == "/confirm_delete":
                # Handle confirmed deletion
                confirm_tasks = form_data.get('confirm_tasks', [])
                if not confirm_tasks:
                    self._send_response("No tasks selected for deletion", 400)
                else:
                    # Delete the confirmed tasks
                    deleted_count = delete_tasks(confirm_tasks)
                    
                    # Redirect to a success page
                    self.send_response(303)
                    self.send_header('Location', f'/tasks_deleted?count={deleted_count}')
                    self.end_headers()
            elif self.path == "/add_subtask":
                # Handle adding a subtask
                parent_task_id = single_value_form_data.get('parent_task_id')
                description = single_value_form_data.get('description')
                details = single_value_form_data.get('details')
                priority = single_value_form_data.get('priority', '2')
                project_id = single_value_form_data.get('project_id')
                
                if not description or not parent_task_id:
                    self._send_response("Missing required fields", 400)
                else:
                    task_id = create_task(
                        description=description,
                        details=details,
                        priority=priority,
                        project_id=project_id,
                        parent_task_id=parent_task_id
                    )
                    
                    if task_id:
                        # Redirect back to the parent task view
                        self.send_response(303)
                        self.send_header('Location', f'/view?task_id={parent_task_id}')
                        self.end_headers()
                    else:
                        self._send_response("Failed to create subtask", 500)
            elif self.path == "/update_task":
                # Handle updating a task
                task_id = single_value_form_data.get('task_id')
                if not task_id:
                    self._send_response("Missing task ID", 400)
                else:
                    # Collect the form data
                    updated_data = {
                        'description': single_value_form_data.get('description'),
                        'details': single_value_form_data.get('details'),
                        'status': single_value_form_data.get('status'),
                        'priority': single_value_form_data.get('priority'),
                        'project_id': single_value_form_data.get('project_id'),
                        'due_date': single_value_form_data.get('due_date')
                    }
                    
                    # Remove empty values
                    updated_data = {k: v for k, v in updated_data.items() if v}
                    
                    success = update_task(task_id, updated_data)
                    if success:
                        # Redirect to the task view page
                        self.send_response(303)
                        self.send_header('Location', f'/view?task_id={task_id}')
                        self.end_headers()
                    else:
                        self._send_response("Failed to update task", 500)
            elif self.path == "/delete_task":
                # Handle single task deletion
                task_id = single_value_form_data.get('task_id')
                if not task_id:
                    self._send_response("No task selected for deletion", 400)
                else:
                    # Delete the task
                    deleted = delete_tasks([task_id])
                    
                    # Redirect to dashboard
                    self.send_response(303)
                    self.send_header('Location', '/')
                    self.end_headers()
            else:
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b"Form received")
        
        def _send_response(self, content):
            """Send a standard HTML response"""
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(content.encode())
            
    # Set up the HTTP server
    port = PORT
    handler = TaskManagerHandler
    
    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"Server started at http://localhost:{port}")
            print("Opening browser...")
            webbrowser.open(f"http://localhost:{port}")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
    except Exception as e:
        print(f"Error starting server: {str(e)}")

if __name__ == "__main__":
    main() 
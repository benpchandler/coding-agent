import os
import sys
import json
from openai import OpenAI
from dotenv import load_dotenv
import logging

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from typing import Optional, Tuple
from models.task import Task, TaskStatus
from common.logging_utils import setup_logger
from common.json_utils import load_json, save_json

# Load environment variables from config directory
load_dotenv(os.path.join(project_root, "config", ".env"))

# Setup logging
logger = setup_logger(__name__)

# Configure OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
if not client.api_key:
    logger.error("No OpenAI API key found in .env file")
    raise ValueError("Please set OPENAI_API_KEY in your .env file")

def load_task(task_id: str) -> Optional[Task]:
    """
    Load a task from its JSON file.
    
    Args:
        task_id (str): The ID of the task to load
        
    Returns:
        Optional[Task]: The loaded task or None if not found
    """
    task_data = load_json(os.path.join("tasks", f"{task_id}.json"))
    if not task_data:
        logger.error(f"Task file not found: {task_id}")
        return None
        
    return Task.from_dict(task_data)

def determine_implementation_type(task: Task) -> str:
    """
    Determine the type of implementation needed based on task description.
    
    Args:
        task (Task): The task to analyze
        
    Returns:
        str: The determined implementation type
    """
    description = task.description.lower()
    
    # Match keywords to implementation types
    if any(kw in description for kw in ["frontend", "ui", "react", "component", "interface"]):
        return "react"
    elif any(kw in description for kw in ["api", "endpoint", "fastapi", "route"]):
        return "api"
    elif any(kw in description for kw in ["database", "model", "schema", "sql"]):
        return "database"
    elif any(kw in description for kw in ["pdf", "extract", "document", "parse"]):
        return "python"
    elif any(kw in description for kw in ["financial", "calculate", "metric", "analyze"]):
        return "financial"
    else:
        return "python"  # Default to Python

def create_python_prompt(task: Task):
    """Create prompt for Python implementation."""
    return f"""
You are an expert Python developer implementing a specific task for a financial analysis application.
Generate a complete Python implementation for the following task:

TASK ID: {task.task_id}

TASK DESCRIPTION: {task.description}

DEVELOPMENT GUIDELINES:
1. Write clean, well-documented code following PEP 8 standards
2. Include comprehensive error handling:
   - Use specific exception types instead of generic exceptions
   - Provide informative error messages
   - Handle edge cases explicitly
3. Add detailed docstrings with:
   - Function/class purpose
   - Parameter descriptions with types
   - Return value descriptions
   - Example usage
   - Exceptions that may be raised
4. Performance considerations:
   - Use generators/streaming for large data processing
   - Implement pagination or chunking for large datasets
   - Consider memory usage in data structures
5. Security measures:
   - Validate and sanitize all inputs
   - Set appropriate size limits for inputs
   - Handle sensitive data securely
   - Implement proper access controls
6. Testing considerations:
   - Write code that is easily testable
   - Include edge cases in the implementation
   - Consider adding input validation
7. Make the code modular and reusable:
   - Use clear interfaces
   - Minimize dependencies
   - Follow SOLID principles

Create a complete, self-contained Python module that implements this functionality.
Include all necessary imports at the top of the file.
"""

def create_react_prompt(task: Task):
    """Create prompt for React component implementation."""
    return f"""
You are an expert React developer implementing a specific UI component for a financial analysis application.
Generate a complete React component for the following task:

TASK ID: {task.task_id}

TASK DESCRIPTION: {task.description}

DEVELOPMENT GUIDELINES:
1. Write clean, well-documented React code using functional components
2. Use TypeScript for type safety
3. Use Material UI for UI components
4. Implement proper error handling and loading states
5. Make the component responsive
6. Follow React best practices (hooks, context, etc.)
7. Include comments explaining complex logic
8. Handle edge cases gracefully
9. Ensure the component is accessible

Create a complete, self-contained React component that implements this functionality.
Include all necessary imports at the top of the file.
"""

def create_api_prompt(task: Task):
    """Create prompt for FastAPI endpoint implementation."""
    return f"""
You are an expert FastAPI developer implementing a specific API endpoint for a financial analysis application.
Generate a complete FastAPI endpoint implementation for the following task:

TASK ID: {task.task_id}

TASK DESCRIPTION: {task.description}

DEVELOPMENT GUIDELINES:
1. Write clean, well-documented FastAPI code
2. API Security:
   - Implement proper input validation using Pydantic models
   - Set appropriate rate limits and timeouts
   - Add file size limits for uploads
   - Use proper content type validation
   - Implement authentication/authorization if needed
3. Performance:
   - Use async/await for I/O operations
   - Implement streaming for large files
   - Add pagination for list endpoints
   - Use caching where appropriate
4. Error Handling:
   - Use specific HTTP status codes
   - Return detailed error messages
   - Handle all possible error scenarios
   - Add request validation
5. Documentation:
   - Add OpenAPI/Swagger documentation
   - Include example requests/responses
   - Document all error responses
6. Testing:
   - Make endpoints easily testable
   - Consider test scenarios in design
   - Handle edge cases explicitly
7. Monitoring:
   - Add appropriate logging
   - Include request tracing
   - Monitor performance metrics

Create a complete FastAPI endpoint that implements this functionality.
Include all necessary imports, models, and dependencies.
"""

def create_database_prompt(task: Task):
    """Create prompt for database model implementation."""
    return f"""
You are an expert SQLAlchemy developer implementing database models for a financial analysis application.
Generate a complete SQLAlchemy model implementation for the following task:

TASK ID: {task.task_id}

TASK DESCRIPTION: {task.description}

DEVELOPMENT GUIDELINES:
1. Write clean, well-documented SQLAlchemy models
2. Define appropriate column types and constraints
3. Include relationships with other models
4. Add indexes for performance
5. Implement proper data validation
6. Use best practices for SQLAlchemy ORM
7. Include appropriate __repr__ method
8. Add helpful methods for common operations

Create a complete SQLAlchemy model implementation that includes:
- Model definition with appropriate columns
- Relationships
- Indexes
- Helper methods
"""

def create_financial_prompt(task: Task):
    """Create prompt for financial analysis implementation."""
    return f"""
You are an expert developer implementing financial analysis algorithms for a financial analysis application.
Generate a complete implementation for the following financial analysis task:

TASK ID: {task.task_id}

TASK DESCRIPTION: {task.description}

DEVELOPMENT GUIDELINES:
1. Write clean, well-documented code with clear mathematical explanations
2. Use NumPy/Pandas for efficient numerical operations
3. Include proper error handling for financial edge cases
4. Add docstrings with formula explanations
5. Validate inputs and outputs
6. Include unit tests for key calculations
7. Handle edge cases (zero division, negative values, etc.)
8. Use proper financial calculation best practices

Create a complete, well-documented module that implements this financial functionality.
Include all necessary imports at the top of the file.
"""

def implement_task(task: Task) -> Tuple[Optional[str], Optional[str]]:
    """
    Generate implementation code for a task.
    
    Args:
        task (Task): The task to implement
        
    Returns:
        Tuple[Optional[str], Optional[str]]: The implementation code and file extension, or (None, None) if failed
    """
    # Determine implementation type
    impl_type = determine_implementation_type(task)
    logger.info(f"Determined implementation type: {impl_type}")
    
    # Create an implementation prompt based on type
    if impl_type == "react":
        prompt = create_react_prompt(task)
        file_extension = ".jsx"
    elif impl_type == "api":
        prompt = create_api_prompt(task)
        file_extension = ".py"
    elif impl_type == "database":
        prompt = create_database_prompt(task)
        file_extension = ".py"
    elif impl_type == "financial":
        prompt = create_financial_prompt(task)
        file_extension = ".py"
    else:
        prompt = create_python_prompt(task)
        file_extension = ".py"
    
    try:
        logger.info(f"Generating implementation for task: {task.description}")
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",  # Using GPT-4 for better code generation
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        
        implementation = response.choices[0].message.content
        
        # Extract code from markdown if necessary
        if "```" in implementation:
            code_blocks = []
            lines = implementation.split("\n")
            in_code_block = False
            code_block = []
            
            for line in lines:
                if "```" in line:
                    if not in_code_block:
                        in_code_block = True
                        # Skip the language identifier line
                    else:
                        in_code_block = False
                        code_blocks.append("\n".join(code_block))
                        code_block = []
                elif in_code_block:
                    code_block.append(line)
            
            if code_blocks:
                implementation = code_blocks[0]  # Use the first code block
        
        return implementation, file_extension
    
    except Exception as e:
        logger.error(f"Error generating implementation: {str(e)}")
        return None, None

def save_implementation(task: Task, implementation: str, file_extension: str) -> bool:
    """
    Save the implementation code to a file.
    
    Args:
        task (Task): The task being implemented
        implementation (str): The implementation code
        file_extension (str): The file extension to use
        
    Returns:
        bool: True if save was successful, False otherwise
    """
    try:
        # Create implementations directory if it doesn't exist
        os.makedirs("implementations", exist_ok=True)
        
        # Generate filename from task ID
        filename = f"{task.task_id.lower().replace('-', '_')}{file_extension}"
        filepath = os.path.join("implementations", filename)
        
        # Save implementation
        with open(filepath, "w") as f:
            f.write(implementation)
            
        # Update task with implementation details
        task.code["files"].append({
            "path": filename,
            "content": implementation,
            "type": file_extension[1:]  # Remove the dot
        })
        
        # Update task status
        task.update_status(TaskStatus.READY_FOR_TESTING, "Implementation completed")
        
        # Save updated task
        task_path = os.path.join("tasks", f"{task.task_id}.json")
        return save_json(task_path, task.to_dict())
        
    except Exception as e:
        logger.error(f"Error saving implementation: {str(e)}")
        return False

def process_task(task_id: str) -> bool:
    """
    Process a single task through the code generation pipeline.
    
    Args:
        task_id (str): The ID of the task to process
        
    Returns:
        bool: True if processing was successful, False otherwise
    """
    # Load task
    task = load_task(task_id)
    if not task:
        return False
        
    # Update status to implementing
    task.update_status(TaskStatus.IMPLEMENTING, "Starting implementation")
    save_json(os.path.join("tasks", f"{task.task_id}.json"), task.to_dict())
    
    # Generate implementation
    implementation, file_extension = implement_task(task)
    if not implementation:
        task.update_status(TaskStatus.FAILED, "Failed to generate implementation")
        save_json(os.path.join("tasks", f"{task.task_id}.json"), task.to_dict())
        return False
        
    # Save implementation
    if not save_implementation(task, implementation, file_extension):
        task.update_status(TaskStatus.FAILED, "Failed to save implementation")
        save_json(os.path.join("tasks", f"{task.task_id}.json"), task.to_dict())
        return False
        
    return True

def main():
    """Main entry point"""
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python code_generation_agent.py <task_id>")
        sys.exit(1)
        
    task_id = sys.argv[1]
    success = process_task(task_id)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
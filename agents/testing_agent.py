import os
import json
from openai import OpenAI
from dotenv import load_dotenv
import logging
import glob
import ast
import subprocess
import sys
import importlib.util
import inspect
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configure OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
if not client.api_key:
    logger.error("No OpenAI API key found in .env file")
    raise ValueError("Please set OPENAI_API_KEY in your .env file")

def get_implementation(impl_id: str) -> Optional[str]:
    """Get implementation file path by ID."""
    # Convert TASK-1 format to task_1 format
    file_prefix = impl_id.lower().replace('-', '_')
    
    # Try both .py and .jsx extensions
    py_path = f"implementations/{file_prefix}.py"
    jsx_path = f"implementations/{file_prefix}.jsx"
    
    if os.path.exists(py_path):
        return py_path
    elif os.path.exists(jsx_path):
        return jsx_path
    else:
        return None

def get_task(task_id: str) -> Optional[Dict]:
    """Get task by ID."""
    task_path = f"tasks/{task_id}.json"
    if not os.path.exists(task_path):
        logger.error(f"Task not found: {task_path}")
        return None
        
    with open(task_path, "r") as f:
        return json.load(f)

def load_implementation(impl_path):
    """Dynamically load a Python module from a file path."""
    module_name = os.path.splitext(os.path.basename(impl_path))[0]
    spec = importlib.util.spec_from_file_location(module_name, impl_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def run_test_case(impl_module, test_case):
    """
    Run a specific test case against an implementation.
    
    Args:
        impl_module (module): The dynamically loaded implementation module
        test_case (dict): Test case details including name and criterion
    
    Returns:
        dict: Test result with pass/fail status and details
    """
    try:
        # Find a function that matches the test case name or can be tested
        test_function = None
        for name, func in inspect.getmembers(impl_module, inspect.isfunction):
            # Try to match function name or find a suitable function to test the criterion
            if test_case['name'].lower() in name.lower():
                test_function = func
                break
        
        if not test_function:
            return {
                'passed': False,
                'reason': f"No suitable test function found for criterion: {test_case['criterion']}"
            }
        
        # Run the test function
        result = test_function()
        
        return {
            'passed': bool(result),
            'details': f"Tested criterion: {test_case['criterion']}"
        }
    
    except Exception as e:
        return {
            'passed': False,
            'reason': str(e)
        }

def static_code_analysis(code: str, file_ext: str) -> List[str]:
    """Perform basic static code analysis."""
    issues = []
    
    if file_ext == ".py":
        try:
            # Check syntax
            ast.parse(code)
            
            # Check for common issues
            if "import *" in code:
                issues.append("Using wildcard imports is not recommended")
            
            if "except:" in code and "except Exception:" not in code:
                issues.append("Using bare except clause is not recommended")
            
            # Check for docstrings
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and not ast.get_docstring(node):
                    issues.append(f"Function '{node.name}' missing docstring")
        
        except SyntaxError as e:
            issues.append(f"Syntax error: {str(e)}")
    
    elif file_ext == ".jsx":
        # Basic JSX checks
        if "useState" in code and "import { useState }" not in code and "import React, { useState }" not in code:
            issues.append("Using useState without importing it")
        
        if "useEffect" in code and "import { useEffect }" not in code and "import React, { useEffect }" not in code:
            issues.append("Using useEffect without importing it")
    
    return issues

def analyze_implementation(code: str, task: Dict, file_ext: str) -> Dict:
    """Generate AI review of the implementation."""
    prompt = f"""
Review this implementation for the following task:

TASK:
{task['title']}
{task['description']}

ACCEPTANCE CRITERIA:
{chr(10).join(['- ' + criterion for criterion in task['acceptance_criteria']])}

IMPLEMENTATION:
```{file_ext[1:]}
{code}
```

Provide a detailed review covering:

1. Code Quality (0-10):
   - Clean and readable code
   - Proper documentation and comments
   - Consistent style and formatting
   - SOLID principles adherence
   - Code modularity and reusability

2. Error Handling (0-10):
   - Specific exception types used
   - Informative error messages
   - Edge cases handled
   - Proper error recovery
   - Graceful failure modes

3. Performance (0-10):
   - Efficient algorithms and data structures
   - Proper handling of large data/files
   - Memory usage optimization
   - Use of streaming/pagination where appropriate
   - Caching considerations

4. Security (0-10):
   - Input validation and sanitization
   - Proper access controls
   - Size limits and timeouts
   - Secure data handling
   - Protection against common vulnerabilities

5. Testing & Maintainability (0-10):
   - Code testability
   - Edge case coverage
   - Clear interfaces
   - Dependency management
   - Monitoring and logging

Format your response as a JSON object with these keys:
{{
    "quality_score": <average of all scores>,
    "meets_criteria": <boolean>,
    "code_quality": {{
        "score": <number 0-10>,
        "details": <string>,
        "issues": [<array of strings>]
    }},
    "error_handling": {{
        "score": <number 0-10>,
        "details": <string>,
        "issues": [<array of strings>]
    }},
    "performance": {{
        "score": <number 0-10>,
        "details": <string>,
        "issues": [<array of strings>]
    }},
    "security": {{
        "score": <number 0-10>,
        "details": <string>,
        "issues": [<array of strings>]
    }},
    "testing": {{
        "score": <number 0-10>,
        "details": <string>,
        "issues": [<array of strings>]
    }},
    "improvements": [<array of strings>]
}}
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        
        review = json.loads(response.choices[0].message.content)
        return review
    
    except Exception as e:
        logger.error(f"Error generating review: {str(e)}")
        return {
            "quality_score": 0,
            "meets_criteria": False,
            "code_quality": {"score": 0, "details": "Error generating review", "issues": []},
            "error_handling": {"score": 0, "details": "Error generating review", "issues": []},
            "performance": {"score": 0, "details": "Error generating review", "issues": []},
            "security": {"score": 0, "details": "Error generating review", "issues": []},
            "testing": {"score": 0, "details": "Error generating review", "issues": []},
            "improvements": ["Error generating review"]
        }

def generate_comprehensive_test_suite(implementations_dir):
    """
    Generate a comprehensive test suite across all implementations.
    
    Args:
        implementations_dir (str): Directory containing implementation files
    
    Returns:
        dict: Comprehensive test suite with results for all implementations
    """
    comprehensive_results = {
        'total_implementations': 0,
        'passed_implementations': 0,
        'failed_implementations': 0,
        'implementation_details': {}
    }
    
    # Discover implementation files
    impl_files = (
        glob.glob(f"{implementations_dir}/*.py") + 
        glob.glob(f"{implementations_dir}/*.jsx")
    )
    
    comprehensive_results['total_implementations'] = len(impl_files)
    
    for impl_path in impl_files:
        # Extract task ID
        filename = os.path.basename(impl_path)
        task_id = filename.split('.')[0].upper().replace('_', '-')
        
        # Get task details
        task = get_task(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found, skipping...")
            continue
        
        # Generate test cases based on task criteria
        test_cases = [
            {
                'name': f"test_{criterion.replace(' ', '_').lower()}",
                'criterion': criterion
            } 
            for criterion in task.get('acceptance_criteria', [])
        ]
        
        # Load implementation
        try:
            impl_module = load_implementation(impl_path)
            
            # Run tests for this implementation
            impl_results = {
                'task_id': task_id,
                'file_path': impl_path,
                'tests': []
            }
            
            impl_passed = True
            for test_case in test_cases:
                test_result = run_test_case(impl_module, test_case)
                impl_results['tests'].append(test_result)
                
                if not test_result['passed']:
                    impl_passed = False
            
            # Update comprehensive results
            if impl_passed:
                comprehensive_results['passed_implementations'] += 1
            else:
                comprehensive_results['failed_implementations'] += 1
            
            comprehensive_results['implementation_details'][task_id] = impl_results
        
        except Exception as e:
            logger.error(f"Error processing implementation {task_id}: {e}")
            comprehensive_results['implementation_details'][task_id] = {
                'task_id': task_id,
                'error': str(e)
            }
            comprehensive_results['failed_implementations'] += 1
    
    return comprehensive_results

def generate_tests(code: str, task: Dict, file_ext: str) -> Optional[str]:
    """Generate test code for the implementation."""
    prompt = f"""
Generate comprehensive tests for this implementation:

TASK:
{task['title']}
{task['description']}

ACCEPTANCE CRITERIA:
{chr(10).join(['- ' + criterion for criterion in task['acceptance_criteria']])}

IMPLEMENTATION:
```{file_ext[1:]}
{code}
```

Generate tests that:
1. Cover all acceptance criteria
2. Include edge cases
3. Test error conditions
4. Follow testing best practices
5. Are well-documented

For Python, use pytest.
For React, use Jest and React Testing Library.

Return ONLY the test code without any markdown formatting or explanations.
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        
        test_code = response.choices[0].message.content
        
        # Extract code from markdown if necessary
        if "```" in test_code:
            code_blocks = []
            lines = test_code.split("\n")
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
                test_code = code_blocks[0]  # Use the first code block
        
        # Save test code to file
        test_file = f"tests/test_{task['task_id'].lower().replace('-', '_')}.py"
        os.makedirs("tests", exist_ok=True)
        
        # Only write the file if it doesn't exist or if force_update is True
        if not os.path.exists(test_file):
            with open(test_file, "w") as f:
                f.write(test_code)
            logger.info(f"Generated test file: {test_file}")
        
        return test_code
    
    except Exception as e:
        logger.error(f"Error generating tests: {str(e)}")
        return None

def validate_implementation(impl_path: str, task: Dict) -> Dict:
    """Validate an implementation against its task requirements."""
    # Read implementation code
    with open(impl_path, "r") as f:
        code = f.read()
    
    # Determine file type
    file_ext = os.path.splitext(impl_path)[1]
    
    # Run static analysis
    analysis_issues = static_code_analysis(code, file_ext)
    
    # Generate AI review
    review = analyze_implementation(code, task, file_ext)
    
    # Generate tests if they don't exist
    test_code = generate_tests(code, task, file_ext)
    
    # Run tests
    test_suite_results = generate_comprehensive_test_suite(os.path.dirname(impl_path))
    
    # Get task-specific test details using task_id
    task_id = task.get('task_id')
    task_test_details = test_suite_results.get('implementation_details', {}).get(task_id, {})
    
    return {
        "static_analysis": analysis_issues,
        "review": review,
        "test_results": task_test_details
    }

def store_test_results(task_id: str, validation_results: Dict) -> str:
    """Store test results in a JSON file with robust symlink handling."""
    # Create results directory if it doesn't exist
    results_dir = os.path.join("test_results", task_id)
    os.makedirs(results_dir, exist_ok=True)
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create results file with full path
    results_filename = f"run_{timestamp}.json"
    results_file = os.path.join(results_dir, results_filename)
    with open(results_file, "w") as f:
        json.dump({
            "timestamp": timestamp,
            "task_id": task_id,
            "results": validation_results
        }, f, indent=2)
    
    # Update latest symlink
    latest_file = os.path.join(results_dir, "latest.json")
    try:
        # Safely remove existing symlink or file
        if os.path.exists(latest_file):
            if os.path.islink(latest_file):
                os.unlink(latest_file)
            else:
                # If it's a regular file, remove it
                os.remove(latest_file)
        
        # Create symlink using absolute path
        os.symlink(results_filename, latest_file)
        
        logger.info(f"Created symlink from {latest_file} to {results_filename}")
    
    except OSError as e:
        logger.error(f"Failed to create symlink: {e}")
        
        # Fallback mechanism
        try:
            import shutil
            shutil.copy2(results_file, latest_file)
            logger.warning(f"Created a copy instead of symlink at {latest_file}")
        except Exception as copy_error:
            logger.error(f"Failed to create copy as fallback: {copy_error}")
    
    logger.info(f"Test results stored in: {results_file}")
    return results_file

def get_test_history(task_id: str) -> List[Dict]:
    """Get the test history for a task."""
    task_results_dir = os.path.join("test_results", task_id)
    if not os.path.exists(task_results_dir):
        return []
    
    history = []
    result_files = glob.glob(os.path.join(task_results_dir, "run_*.json"))
    
    for file in sorted(result_files):  # Sort by timestamp
        with open(file, "r") as f:
            history.append(json.load(f))
    
    return history

def get_previous_results(task_id: str) -> Dict:
    """Get the previous test results for a task."""
    history = get_test_history(task_id)
    if not history:
        return None
    
    previous_results = history[-1]["results"]
    
    return previous_results

def compare_with_previous_run(task_id: str, current_results: Dict) -> Dict:
    """Compare current test results with the previous run."""
    previous_results = get_previous_results(task_id)
    if not previous_results:
        return {
            "test_status": "New ✓",
            "quality_change": "New ✓",
            "error_handling_change": "New ✓",
            "performance_change": "New ✓",
            "security_change": "New ✓"
        }
    
    changes = {}
    
    # Compare test status
    current_tests = current_results.get("test_results", {})
    previous_tests = previous_results.get("test_results", {})
    current_success = all(test.get("passed", False) for test in current_tests.get("tests", []))
    previous_success = all(test.get("passed", False) for test in previous_tests.get("tests", []))
    
    if current_success == previous_success:
        changes["test_status"] = "No Change -"
    elif current_success:
        changes["test_status"] = "Improved ✓"
    else:
        changes["test_status"] = "Regressed ✗"
    
    # Compare review scores
    current_review = current_results.get("review", {})
    previous_review = previous_results.get("review", {})
    
    for metric in ["code_quality", "error_handling", "performance", "security", "testing"]:
        current_score = current_review.get(metric, {}).get("score", 0)
        previous_score = previous_review.get(metric, {}).get("score", 0)
        
        if current_score == previous_score:
            changes[f"{metric}_change"] = "No Change -"
        elif current_score > previous_score:
            changes[f"{metric}_change"] = "Improved ✓"
        else:
            changes[f"{metric}_change"] = "Regressed ✗"
    
    return changes

def update_task_status(task_id: str, validation_results: Dict) -> bool:
    """Update task status based on validation results."""
    try:
        task_file = f"tasks/{task_id}.json"
        if not os.path.exists(task_file):
            logger.error(f"Task file not found: {task_file}")
            return False
        
        with open(task_file, "r") as f:
            task = json.load(f)
        
        # Store test results
        results_file = store_test_results(task_id, validation_results)
        
        # Update task status based on validation results
        task["status"] = "completed" if (
            validation_results["review"]["meets_criteria"] and  # Meets acceptance criteria
            not validation_results["static_analysis"] and  # No static analysis issues
            all(test.get("passed", False) for test in validation_results.get("test_results", {}).get("tests", []))  # Tests pass
        ) else "in_progress"
        
        # Save updated task
        with open(task_file, "w") as f:
            json.dump(task, f, indent=2)
        
        # Compare with previous run
        comparison = compare_with_previous_run(task_id, validation_results)
        if comparison:
            print("\nChanges since last run:")
            for change, status in comparison.items():
                print(f"{change}: {status}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error updating task status: {str(e)}")
        return False

def main():
    print("Comprehensive Testing Agent")
    print("---------------------------")
    
    # Get all implementation files
    impl_files = glob.glob("implementations/*.py") + glob.glob("implementations/*.jsx")
    
    if not impl_files:
        print("No implementations found to test")
        return
    
    # Run comprehensive test suite first to get an overview
    comprehensive_results = generate_comprehensive_test_suite("implementations")
    
    # Print comprehensive test suite summary
    print("\nComprehensive Test Suite Summary:")
    print(f"Total Implementations: {comprehensive_results['total_implementations']}")
    print(f"Passed Implementations: {comprehensive_results['passed_implementations']}")
    print(f"Failed Implementations: {comprehensive_results['failed_implementations']}")
    
    # Process each implementation in detail
    for impl_path in impl_files:
        # Extract task ID from filename
        filename = os.path.basename(impl_path)
        task_id = filename.split('.')[0].upper().replace('_', '-')
        
        print(f"\nTesting implementation for task: {task_id}")
        
        # Get task details
        task = get_task(task_id)
        if not task:
            print(f"Task {task_id} not found, skipping...")
            continue
        
        # Validate implementation
        validation_results = validate_implementation(impl_path, task)
        
        # Print results
        print("\nStatic Analysis Results:")
        for issue in validation_results["static_analysis"]:
            print(f"- {issue}")
        
        print("\nAI Review:")
        review = validation_results["review"]
        print(f"Quality Score: {review['quality_score']}/10")
        print(f"Meets Criteria: {'Yes' if review['meets_criteria'] else 'No'}")
        print(f"Error Handling: {review['error_handling']}")
        print(f"Performance: {review['performance']}")
        print(f"Security: {review['security']}")
        print("\nSuggested Improvements:")
        for improvement in review["improvements"]:
            print(f"- {improvement}")
        
        # Print test results from comprehensive suite
        impl_details = comprehensive_results['implementation_details'].get(task_id, {})
        print("\nTest Results:")
        if 'tests' in impl_details:
            for test in impl_details['tests']:
                status = "PASSED ✓" if test['passed'] else "FAILED ✗"
                print(f"- {test.get('details', 'Unknown Test')}: {status}")
                if not test['passed']:
                    print(f"  Reason: {test.get('reason', 'No details')}")
        elif 'error' in impl_details:
            print(f"Error: {impl_details['error']}")
        
        # Update task status and store results
        if update_task_status(task_id, validation_results):
            print(f"\nTask {task_id} status updated")
        else:
            print(f"\nFailed to update task {task_id} status")
    
    return comprehensive_results

if __name__ == "__main__":
    main()
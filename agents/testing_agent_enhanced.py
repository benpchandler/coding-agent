"""
Enhanced Testing Agent with peer review validation capabilities.
"""

import os
import sys
import ast
import re
from typing import Optional, List, Dict, Any

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from agents.base_agent_enhanced import BaseAgentEnhanced
from models.task import Task

class TestingAgentEnhanced(BaseAgentEnhanced):
    """Testing agent that validates code generation output before writing tests"""
    
    def __init__(self, config_path: Optional[str] = None):
        super().__init__("testing", config_path)
    
    def _build_validation_prompt(self, previous_output: str, task: Task) -> str:
        """Build validation prompt for code generation output"""
        return f"""
        I'm about to write tests for this generated code. First, let me evaluate if the code is testable and complete.

        TASK REQUIREMENTS: {task.description}
        
        GENERATED CODE FROM PREVIOUS AGENT:
        {previous_output}
        
        CODE VALIDATION CHECKLIST:
        1. Does the code have clear function/class interfaces?
        2. Are there obvious syntax errors?
        3. Does the code address the task requirements?
        4. Are there missing imports or dependencies?
        5. Is the code structured in a way that's testable?
        6. Are there any obvious logical errors?
        7. Are function signatures and return types clear?
        8. Is error handling implemented properly?
        9. Are there any security vulnerabilities?
        10. Is the code following best practices?
        
        Respond in JSON format:
        {{
            "is_valid": true/false,
            "confidence": 0.9,
            "syntax_issues": ["issue1", "issue2"],
            "logic_concerns": ["concern1", "concern2"],
            "missing_requirements": ["req1", "req2"],
            "testability_issues": ["issue1", "issue2"],
            "feedback": "Specific feedback for the code generation agent",
            "can_write_tests": true/false,
            "syntax_score": 8,
            "completeness_score": 7,
            "testability_score": 9
        }}
        
        If is_valid is false, the code needs to be regenerated.
        Be specific about what needs to be fixed.
        """
    
    async def _do_agent_work(self, task: Task, previous_output: Optional[str] = None) -> str:
        """Generate comprehensive tests for the code"""
        
        if not previous_output:
            return "No code provided to test"
        
        # Analyze the code to understand what to test
        code_analysis = self._analyze_code(previous_output)
        
        # Build test generation prompt
        prompt = self._build_test_generation_prompt(task, previous_output, code_analysis)
        
        # Generate tests
        messages = [{"role": "user", "content": prompt}]
        response = await self._make_openai_request(messages)
        
        # Save tests to file
        self._save_tests(task.task_id, response)

        # Try to run the tests and report results
        test_results = self._run_tests(task.task_id, response)
        
        return f"""
        GENERATED TESTS:
        {response}
        
        TEST EXECUTION RESULTS:
        {test_results}
        """
    
    def _analyze_code(self, code: str) -> Dict[str, Any]:
        """Analyze code to understand structure for testing"""
        analysis = {
            "functions": [],
            "classes": [],
            "imports": [],
            "has_main": False,
            "language": "python",
            "complexity": "medium"
        }
        
        try:
            # Parse Python code
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    analysis["functions"].append({
                        "name": node.name,
                        "args": [arg.arg for arg in node.args.args],
                        "returns": ast.get_source_segment(code, node.returns) if node.returns else None,
                        "is_async": isinstance(node, ast.AsyncFunctionDef)
                    })
                elif isinstance(node, ast.ClassDef):
                    analysis["classes"].append({
                        "name": node.name,
                        "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    })
                elif isinstance(node, ast.Import):
                    analysis["imports"].extend([alias.name for alias in node.names])
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    analysis["imports"].extend([f"{module}.{alias.name}" for alias in node.names])
            
            # Check if has main block
            analysis["has_main"] = 'if __name__ == "__main__"' in code
            
        except SyntaxError as e:
            analysis["syntax_error"] = str(e)
        except Exception as e:
            analysis["analysis_error"] = str(e)
        
        return analysis
    
    def _build_test_generation_prompt(self, task: Task, code: str, 
                                    code_analysis: Dict[str, Any]) -> str:
        """Build comprehensive test generation prompt"""
        
        functions_info = ""
        if code_analysis.get("functions"):
            functions_info = "FUNCTIONS TO TEST:\n"
            for func in code_analysis["functions"]:
                functions_info += f"- {func['name']}({', '.join(func['args'])})\n"
        
        classes_info = ""
        if code_analysis.get("classes"):
            classes_info = "CLASSES TO TEST:\n"
            for cls in code_analysis["classes"]:
                classes_info += f"- {cls['name']} (methods: {', '.join(cls['methods'])})\n"
        
        return f"""
        Generate comprehensive tests for this code implementation.

        TASK: {task.description}
        
        CODE TO TEST:
        {code}
        
        {functions_info}
        {classes_info}
        
        TEST REQUIREMENTS:
        1. Write unit tests for all functions and methods
        2. Test normal operation with valid inputs
        3. Test edge cases and boundary conditions
        4. Test error handling with invalid inputs
        5. Test integration between components
        6. Include performance tests if relevant
        7. Mock external dependencies
        8. Use proper test fixtures and setup/teardown
        
        TESTING GUIDELINES:
        - Use pytest framework
        - Include docstrings for all test functions
        - Use descriptive test names
        - Group related tests in classes
        - Use parametrized tests for multiple scenarios
        - Include both positive and negative test cases
        - Test async functions properly if present
        - Add performance benchmarks where appropriate
        
        Generate complete test file with:
        - All necessary imports (pytest, mock, etc.)
        - Test fixtures and setup functions
        - Comprehensive test coverage
        - Clear test documentation
        - Proper assertions
        - Error case testing
        
        The tests should be runnable with: pytest test_file.py
        """
    
    def _save_tests(self, task_id: str, tests: str) -> None:
        """Save tests to file"""
        try:
            from pathlib import Path
            
            # Create tests directory
            tests_dir = Path("tests")
            tests_dir.mkdir(exist_ok=True)
            
            # Save tests
            filename = tests_dir / f"test_{task_id}.py"
            with open(filename, 'w') as f:
                f.write(tests)
            
            self.logger.info(f"Tests saved to {filename}")
            
        except Exception as e:
            self.logger.error(f"Failed to save tests: {e}")
    
    def _run_tests(self, task_id: str, tests: str) -> str:
        """Try to run the generated tests"""
        try:
            import subprocess
            from pathlib import Path
            
            test_file = Path("tests") / f"test_{task_id}.py"
            
            if not test_file.exists():
                return "Test file not found"
            
            # Try to run pytest
            result = subprocess.run(
                ["python", "-m", "pytest", str(test_file), "-v"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return f"✅ All tests passed!\n\nOutput:\n{result.stdout}"
            else:
                return f"❌ Some tests failed.\n\nStdout:\n{result.stdout}\n\nStderr:\n{result.stderr}"
                
        except subprocess.TimeoutExpired:
            return "⏰ Tests timed out after 30 seconds"
        except FileNotFoundError:
            return "❌ pytest not found. Install with: pip install pytest"
        except Exception as e:
            return f"❌ Error running tests: {str(e)}"
    
    def _check_syntax_errors(self, code: str) -> List[str]:
        """Check for syntax errors in code"""
        errors = []
        try:
            ast.parse(code)
        except SyntaxError as e:
            errors.append(f"Syntax error at line {e.lineno}: {e.msg}")
        except Exception as e:
            errors.append(f"Parse error: {str(e)}")
        
        return errors
    
    def _check_missing_imports(self, code: str) -> List[str]:
        """Check for potentially missing imports"""
        missing = []
        
        # Common patterns that suggest missing imports
        patterns = {
            r'\bpd\.': 'pandas',
            r'\bnp\.': 'numpy', 
            r'\bplt\.': 'matplotlib.pyplot',
            r'\brequests\.': 'requests',
            r'\bjson\.': 'json',
            r'\bos\.': 'os',
            r'\bsys\.': 'sys',
            r'\bre\.': 're',
            r'\bdatetime\.': 'datetime',
            r'\bPath\(': 'pathlib.Path'
        }
        
        for pattern, module in patterns.items():
            if re.search(pattern, code) and f"import {module}" not in code:
                missing.append(f"Possibly missing import: {module}")
        
        return missing

"""
Enhanced Code Generation Agent with peer review validation capabilities.
"""

import os
import sys
import json
from typing import Optional, Dict, Any

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from agents.base_agent_enhanced import BaseAgentEnhanced
from models.task import Task

class CodeGenerationAgentEnhanced(BaseAgentEnhanced):
    """Code generation agent that validates decomposer output before implementing"""
    
    def __init__(self, config_path: Optional[str] = None):
        super().__init__("code_generation", config_path)
    
    def _build_validation_prompt(self, previous_output: str, task: Task) -> str:
        """Build validation prompt for decomposer output"""
        return f"""
        I'm about to implement code based on this task decomposition. First, let me evaluate if the decomposition is clear and actionable.

        ORIGINAL TASK: {task.description}
        
        DECOMPOSITION FROM PREVIOUS AGENT:
        {previous_output}
        
        VALIDATION CHECKLIST:
        1. Are the subtasks clearly defined and actionable?
        2. Do the subtasks actually solve the original problem?
        3. Are there any missing critical components?
        4. Are the acceptance criteria specific enough to implement?
        5. Are dependencies between subtasks clear?
        6. Is the technical approach feasible?
        7. Are there any obvious gaps in the decomposition?
        
        IMPORTANT: You must respond with ONLY a valid JSON object, no other text.

        Respond in this exact JSON format:
        {{
            "is_valid": true,
            "confidence": 0.8,
            "issues": ["issue1", "issue2"],
            "feedback": "Specific feedback for the decomposer agent",
            "missing_components": ["component1", "component2"],
            "can_proceed": true,
            "clarity_score": 8,
            "completeness_score": 7,
            "feasibility_score": 9
        }}

        If is_valid is false, I cannot proceed with implementation.
        Be specific about what needs to be clarified or added.
        Remember: ONLY return the JSON object, no explanatory text before or after.
        """
    
    async def _do_agent_work(self, task: Task, previous_output: Optional[str] = None) -> str:
        """Generate code implementation"""
        
        # Determine implementation approach based on task
        implementation_type = self._determine_implementation_type(task)
        
        # Build implementation prompt
        prompt = self._build_implementation_prompt(task, previous_output, implementation_type)
        
        # Generate code
        messages = [{"role": "user", "content": prompt}]
        response = await self._make_openai_request(messages, task_id=task.task_id)
        
        # Save implementation to file
        self._save_implementation(task.task_id, response, implementation_type)
        
        return response
    
    def _determine_implementation_type(self, task: Task) -> str:
        """Determine the type of implementation needed"""
        description = task.description.lower()
        language = task.language.lower() if task.language else "python"
        
        if "api" in description or "endpoint" in description:
            return "api"
        elif "ui" in description or "interface" in description or "react" in description:
            return "ui"
        elif "database" in description or "sql" in description:
            return "database"
        elif "test" in description:
            return "test"
        else:
            return "general"
    
    def _build_implementation_prompt(self, task: Task, decomposition: Optional[str], 
                                   implementation_type: str) -> str:
        """Build implementation prompt based on task type"""
        
        base_context = f"""
        TASK: {task.description}
        LANGUAGE: {task.language or 'Python'}
        
        """
        
        if decomposition:
            base_context += f"""
        TASK DECOMPOSITION:
        {decomposition}
        
        """
        
        # Type-specific prompts
        if implementation_type == "api":
            return base_context + self._get_api_implementation_prompt()
        elif implementation_type == "ui":
            return base_context + self._get_ui_implementation_prompt()
        elif implementation_type == "database":
            return base_context + self._get_database_implementation_prompt()
        elif implementation_type == "test":
            return base_context + self._get_test_implementation_prompt()
        else:
            return base_context + self._get_general_implementation_prompt()
    
    def _get_api_implementation_prompt(self) -> str:
        """Get API implementation prompt"""
        return """
        You are an expert FastAPI developer implementing API endpoints.

        IMPLEMENTATION GUIDELINES:
        1. Use proper HTTP status codes and error handling
        2. Implement request/response validation with Pydantic models
        3. Add comprehensive documentation with docstrings
        4. Include authentication and authorization where needed
        5. Follow REST API best practices
        6. Add proper logging and monitoring
        7. Include input validation and sanitization
        8. Handle edge cases and error conditions
        
        Provide complete, production-ready code with:
        - All necessary imports
        - Pydantic models for request/response
        - Error handling
        - Documentation
        - Example usage
        """
    
    def _get_ui_implementation_prompt(self) -> str:
        """Get UI implementation prompt"""
        return """
        You are an expert React developer implementing UI components.

        IMPLEMENTATION GUIDELINES:
        1. Use functional components with TypeScript
        2. Use Material UI or similar component library
        3. Implement proper error handling and loading states
        4. Make components responsive and accessible
        5. Follow React best practices (hooks, context)
        6. Add proper prop validation
        7. Include comprehensive styling
        8. Handle user interactions gracefully
        
        Provide complete, production-ready code with:
        - All necessary imports
        - TypeScript interfaces
        - Error boundaries
        - Loading states
        - Responsive design
        - Accessibility features
        """
    
    def _get_database_implementation_prompt(self) -> str:
        """Get database implementation prompt"""
        return """
        You are an expert database developer implementing data layer functionality.

        IMPLEMENTATION GUIDELINES:
        1. Use proper SQL practices and indexing
        2. Implement connection pooling and error handling
        3. Add data validation and constraints
        4. Follow security best practices (prevent SQL injection)
        5. Include proper transaction management
        6. Add comprehensive logging
        7. Handle concurrent access properly
        8. Include migration scripts if needed
        
        Provide complete, production-ready code with:
        - All necessary imports
        - Connection management
        - Error handling
        - Security measures
        - Performance optimizations
        - Documentation
        """
    
    def _get_test_implementation_prompt(self) -> str:
        """Get test implementation prompt"""
        return """
        You are an expert test developer implementing comprehensive test suites.

        IMPLEMENTATION GUIDELINES:
        1. Cover all major code paths and edge cases
        2. Include unit tests, integration tests, and end-to-end tests
        3. Use proper test fixtures and mocking
        4. Follow testing best practices
        5. Add performance and load tests where appropriate
        6. Include negative test cases
        7. Ensure tests are maintainable and readable
        8. Add proper test documentation
        
        Provide complete test suite with:
        - All necessary imports and fixtures
        - Comprehensive test coverage
        - Clear test descriptions
        - Proper assertions
        - Mock objects where needed
        - Performance benchmarks
        """
    
    def _get_general_implementation_prompt(self) -> str:
        """Get general implementation prompt"""
        return """
        You are an expert software developer implementing functionality.

        IMPLEMENTATION GUIDELINES:
        1. Write clean, well-documented code following best practices
        2. Include comprehensive error handling
        3. Add detailed docstrings with examples
        4. Consider performance implications
        5. Implement security measures (input validation, sanitization)
        6. Make code modular and reusable
        7. Follow language-specific conventions
        8. Include proper logging
        
        Provide complete, production-ready code with:
        - All necessary imports
        - Error handling
        - Documentation
        - Example usage
        - Security considerations
        - Performance optimizations
        """
    
    def _save_implementation(self, task_id: str, implementation: str, 
                           implementation_type: str) -> None:
        """Save implementation to file"""
        try:
            import os
            from pathlib import Path
            
            # Create implementations directory
            impl_dir = Path("implementations")
            impl_dir.mkdir(exist_ok=True)
            
            # Save implementation
            filename = impl_dir / f"{task_id}_{implementation_type}.py"
            with open(filename, 'w') as f:
                f.write(implementation)
            
            self.logger.info(f"Implementation saved to {filename}")
            
        except Exception as e:
            self.logger.error(f"Failed to save implementation: {e}")

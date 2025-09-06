"""
Feedback Parser - Converts raw feedback into clean prompt improvements
"""

import re
from typing import Dict, List, Tuple
from dataclasses import dataclass

@dataclass
class PromptImprovement:
    """Represents a specific improvement to add to a prompt"""
    category: str  # 'requirement', 'constraint', 'guideline', 'technical_detail'
    improvement: str
    priority: int  # 1-10, higher = more important

class FeedbackParser:
    """Parses feedback and converts it to clean prompt improvements"""
    
    def __init__(self):
        # Patterns to extract specific requirements from feedback
        self.requirement_patterns = [
            (r"lacks tests for ([^.]+)", "Include tests for {}", 9),
            (r"missing ([^.]+)", "Include {}", 9),
            (r"add ([^.]+)", "Add {}", 8),
            (r"include ([^.]+)", "Include {}", 8),
            (r"ensure ([^.]+)", "Ensure {}", 7),
            (r"consider ([^.]+)", "Consider {}", 6),
            (r"needs? ([^.]+)", "Needs {}", 8),
            (r"requires? ([^.]+)", "Requires {}", 9),
            (r"could benefit from ([^.]+)", "Include {}", 7),
        ]
        
        # Patterns for technical issues
        self.technical_patterns = [
            (r"ImportError", "Ensure all necessary imports are included", 9),
            (r"execution failed", "Make code executable and testable", 9),
            (r"syntax error", "Use correct syntax", 10),
            (r"dependency issues", "Include all required dependencies", 8),
            (r"configuration.*issues", "Include proper configuration", 7),
        ]
        
        # Patterns for test-specific improvements
        self.test_patterns = [
            (r"test coverage", "comprehensive test coverage", 8),
            (r"edge cases", "edge case testing", 7),
            (r"integration tests", "integration tests", 8),
            (r"performance tests", "performance testing", 6),
            (r"error handling", "proper error handling", 8),
            (r"international characters", "international character support", 7),
            (r"length constraints", "length validation", 6),
            (r"cleanup procedures", "test cleanup and isolation", 7),
        ]
    
    def parse_feedback(self, feedback: str, agent_type: str) -> List[PromptImprovement]:
        """Parse feedback into specific prompt improvements"""
        improvements = []
        feedback_lower = feedback.lower()
        
        # Extract requirements using patterns
        for pattern, template, priority in self.requirement_patterns:
            matches = re.findall(pattern, feedback_lower)
            for match in matches:
                improvement = template.format(match)
                improvements.append(PromptImprovement(
                    category="requirement",
                    improvement=improvement,
                    priority=priority
                ))
        
        # Extract technical issues
        for pattern, improvement, priority in self.technical_patterns:
            if re.search(pattern, feedback_lower):
                improvements.append(PromptImprovement(
                    category="technical",
                    improvement=improvement,
                    priority=priority
                ))
        
        # Extract test-specific improvements
        if agent_type == "testing":
            for pattern, improvement, priority in self.test_patterns:
                if re.search(pattern, feedback_lower):
                    improvements.append(PromptImprovement(
                        category="testing",
                        improvement=improvement,
                        priority=priority
                    ))
        
        # Remove duplicates and sort by priority
        unique_improvements = self._deduplicate_improvements(improvements)
        return sorted(unique_improvements, key=lambda x: x.priority, reverse=True)
    
    def _deduplicate_improvements(self, improvements: List[PromptImprovement]) -> List[PromptImprovement]:
        """Remove duplicate improvements"""
        seen = set()
        unique = []
        
        for improvement in improvements:
            key = (improvement.category, improvement.improvement.lower())
            if key not in seen:
                seen.add(key)
                unique.append(improvement)
        
        return unique
    
    def enhance_task_description(self, original_task: str, improvements: List[PromptImprovement]) -> str:
        """Create enhanced task description with improvements"""
        if not improvements:
            return original_task
        
        # Group improvements by category
        grouped = {}
        for imp in improvements:
            if imp.category not in grouped:
                grouped[imp.category] = []
            grouped[imp.category].append(imp.improvement)
        
        # Build enhanced description
        enhanced = original_task
        
        # Add technical requirements
        if "technical" in grouped:
            tech_reqs = ", ".join(grouped["technical"])
            enhanced += f". {tech_reqs}"
        
        # Add specific requirements
        if "requirement" in grouped:
            requirements = ", ".join(grouped["requirement"][:3])  # Top 3
            enhanced += f". Requirements: {requirements}"
        
        # Add testing specifics
        if "testing" in grouped:
            test_reqs = ", ".join(grouped["testing"][:3])  # Top 3
            enhanced += f". Testing: {test_reqs}"
        
        return enhanced
    
    def create_clean_prompt_enhancement(self, original_task: str, feedback: str, agent_type: str) -> str:
        """Create a clean, enhanced task description from feedback"""
        improvements = self.parse_feedback(feedback, agent_type)
        return self.enhance_task_description(original_task, improvements)

# Example usage and testing
if __name__ == "__main__":
    parser = FeedbackParser()
    
    # Test with actual feedback
    feedback = """The test suite appears to be well-structured with a good range of input 
    scenarios tested. However, the test execution failed due to an ImportError, which needs 
    to be resolved. Additionally, consider adding integration tests and tests for more 
    complex email formats, including international characters and length constraints."""
    
    original_task = "Create a simple Python function that validates email addresses using regex"
    
    enhanced_task = parser.create_clean_prompt_enhancement(original_task, feedback, "testing")
    
    print("ORIGINAL TASK:")
    print(original_task)
    print("\nFEEDBACK:")
    print(feedback)
    print("\nENHANCED TASK:")
    print(enhanced_task)
    
    print("\nPARSED IMPROVEMENTS:")
    improvements = parser.parse_feedback(feedback, "testing")
    for imp in improvements:
        print(f"- {imp.category}: {imp.improvement} (priority: {imp.priority})")

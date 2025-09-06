"""
Enhanced Quality Assessment Agent with peer review validation capabilities.
"""

import os
import sys
import re
from typing import Optional, Dict, Any, List

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from agents.base_agent_enhanced import BaseAgentEnhanced
from models.task import Task

class QualityAssessmentAgentEnhanced(BaseAgentEnhanced):
    """Quality assessment agent that validates testing output before final assessment"""
    
    def __init__(self, config_path: Optional[str] = None):
        super().__init__("quality_assessment", config_path)
    
    def _build_validation_prompt(self, previous_output: str, task: Task) -> str:
        """Build validation prompt for testing output"""
        return f"""
        I'm about to do quality assessment. First, let me evaluate if the testing was comprehensive and successful.

        TASK: {task.description}
        
        TEST RESULTS FROM PREVIOUS AGENT:
        {previous_output}
        
        TESTING VALIDATION CHECKLIST:
        1. Were all major code paths tested?
        2. Were edge cases and error conditions tested?
        3. Are test results clearly reported?
        4. Did tests actually run successfully?
        5. Are there any obvious gaps in test coverage?
        6. Are the tests well-structured and maintainable?
        7. Do tests validate the actual requirements?
        8. Are performance tests included where relevant?
        9. Are integration tests present if needed?
        10. Is the test documentation adequate?
        
        Respond in JSON format:
        {{
            "is_valid": true/false,
            "confidence": 0.85,
            "coverage_gaps": ["gap1", "gap2"],
            "missing_test_types": ["unit", "integration", "edge_case"],
            "test_quality_issues": ["issue1", "issue2"],
            "execution_problems": ["problem1", "problem2"],
            "feedback": "Specific feedback for the testing agent",
            "sufficient_for_quality_check": true/false,
            "coverage_score": 8,
            "quality_score": 7,
            "execution_score": 9
        }}
        
        If is_valid is false, the testing needs to be improved.
        Be specific about what testing gaps need to be addressed.
        """
    
    async def _do_agent_work(self, task: Task, previous_output: Optional[str] = None) -> str:
        """Perform comprehensive quality assessment"""
        
        if not previous_output:
            return "No test results provided for quality assessment"
        
        # Parse test results
        test_analysis = self._analyze_test_results(previous_output)
        
        # Build quality assessment prompt
        prompt = self._build_quality_assessment_prompt(task, previous_output, test_analysis)
        
        # Generate quality assessment
        messages = [{"role": "user", "content": prompt}]
        response = await self._make_openai_request(messages)
        
        # Save quality report
        self._save_quality_report(task.task_id, response)

        # Generate final quality score
        quality_score = self._calculate_quality_score(response, test_analysis)
        
        return f"""
        QUALITY ASSESSMENT REPORT:
        {response}
        
        OVERALL QUALITY SCORE: {quality_score}/10
        
        RECOMMENDATION: {'APPROVED FOR INTEGRATION' if quality_score >= 7 else 'NEEDS IMPROVEMENT'}
        """
    
    def _analyze_test_results(self, test_output: str) -> Dict[str, Any]:
        """Analyze test results to understand quality metrics"""
        analysis = {
            "tests_passed": 0,
            "tests_failed": 0,
            "tests_total": 0,
            "has_coverage_info": False,
            "coverage_percentage": 0,
            "execution_successful": False,
            "has_performance_tests": False,
            "has_integration_tests": False,
            "test_types": []
        }
        
        # Parse test execution results
        if "✅ All tests passed!" in test_output:
            analysis["execution_successful"] = True
        elif "❌ Some tests failed" in test_output:
            analysis["execution_successful"] = False
        
        # Extract test counts from pytest output
        passed_match = re.search(r'(\d+) passed', test_output)
        if passed_match:
            analysis["tests_passed"] = int(passed_match.group(1))
        
        failed_match = re.search(r'(\d+) failed', test_output)
        if failed_match:
            analysis["tests_failed"] = int(failed_match.group(1))
        
        analysis["tests_total"] = analysis["tests_passed"] + analysis["tests_failed"]
        
        # Check for coverage information
        if "coverage" in test_output.lower():
            analysis["has_coverage_info"] = True
            coverage_match = re.search(r'(\d+)%', test_output)
            if coverage_match:
                analysis["coverage_percentage"] = int(coverage_match.group(1))
        
        # Check for different test types
        if "test_performance" in test_output or "benchmark" in test_output.lower():
            analysis["has_performance_tests"] = True
            analysis["test_types"].append("performance")
        
        if "test_integration" in test_output or "integration" in test_output.lower():
            analysis["has_integration_tests"] = True
            analysis["test_types"].append("integration")
        
        if "test_unit" in test_output or any(word in test_output for word in ["test_", "def test"]):
            analysis["test_types"].append("unit")
        
        return analysis
    
    def _build_quality_assessment_prompt(self, task: Task, test_output: str, 
                                       test_analysis: Dict[str, Any]) -> str:
        """Build comprehensive quality assessment prompt"""
        
        return f"""
        Perform a comprehensive quality assessment of this software implementation.

        TASK REQUIREMENTS: {task.description}
        
        TEST RESULTS AND CODE:
        {test_output}
        
        TEST ANALYSIS SUMMARY:
        - Tests passed: {test_analysis['tests_passed']}
        - Tests failed: {test_analysis['tests_failed']}
        - Execution successful: {test_analysis['execution_successful']}
        - Test types present: {', '.join(test_analysis['test_types']) if test_analysis['test_types'] else 'None detected'}
        - Has performance tests: {test_analysis['has_performance_tests']}
        - Has integration tests: {test_analysis['has_integration_tests']}
        
        QUALITY ASSESSMENT CRITERIA:
        
        1. FUNCTIONALITY (25 points):
           - Does the code meet all stated requirements?
           - Are all features implemented correctly?
           - Does it handle edge cases appropriately?
        
        2. CODE QUALITY (25 points):
           - Is the code clean, readable, and well-structured?
           - Are best practices followed?
           - Is there proper error handling?
           - Are there security considerations?
        
        3. TESTING QUALITY (25 points):
           - Is test coverage adequate?
           - Are tests comprehensive and well-written?
           - Do tests validate actual requirements?
           - Are edge cases and error conditions tested?
        
        4. MAINTAINABILITY (25 points):
           - Is the code well-documented?
           - Is it modular and extensible?
           - Are dependencies managed properly?
           - Is it easy to understand and modify?
        
        Provide detailed assessment in this format:
        
        ## FUNCTIONALITY ASSESSMENT (X/25)
        [Detailed analysis of functionality]
        
        ## CODE QUALITY ASSESSMENT (X/25)
        [Detailed analysis of code quality]
        
        ## TESTING QUALITY ASSESSMENT (X/25)
        [Detailed analysis of testing]
        
        ## MAINTAINABILITY ASSESSMENT (X/25)
        [Detailed analysis of maintainability]
        
        ## OVERALL SCORE: X/100
        
        ## KEY STRENGTHS:
        - [Strength 1]
        - [Strength 2]
        
        ## AREAS FOR IMPROVEMENT:
        - [Improvement 1]
        - [Improvement 2]
        
        ## SECURITY CONSIDERATIONS:
        [Any security issues or recommendations]
        
        ## PERFORMANCE CONSIDERATIONS:
        [Any performance issues or recommendations]
        
        ## RECOMMENDATION:
        [APPROVED/NEEDS_MINOR_IMPROVEMENTS/NEEDS_MAJOR_IMPROVEMENTS/REJECTED]
        
        Be thorough but concise. Focus on actionable feedback.
        """
    
    def _calculate_quality_score(self, assessment: str, test_analysis: Dict[str, Any]) -> float:
        """Calculate overall quality score from assessment"""
        try:
            # Extract score from assessment
            score_match = re.search(r'OVERALL SCORE:\s*(\d+)/100', assessment)
            if score_match:
                return float(score_match.group(1)) / 10  # Convert to 1-10 scale
            
            # Fallback: calculate based on test results
            base_score = 5.0  # Start with middle score
            
            if test_analysis["execution_successful"]:
                base_score += 2.0
            
            if test_analysis["tests_total"] > 0:
                pass_rate = test_analysis["tests_passed"] / test_analysis["tests_total"]
                base_score += pass_rate * 2.0
            
            if test_analysis["has_performance_tests"]:
                base_score += 0.5
            
            if test_analysis["has_integration_tests"]:
                base_score += 0.5
            
            return min(base_score, 10.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating quality score: {e}")
            return 5.0  # Default middle score
    
    def _save_quality_report(self, task_id: str, report: str) -> None:
        """Save quality assessment report to file"""
        try:
            from pathlib import Path
            
            # Create quality reports directory
            reports_dir = Path("quality_reports")
            reports_dir.mkdir(exist_ok=True)
            
            # Save report
            filename = reports_dir / f"quality_report_{task_id}.md"
            with open(filename, 'w') as f:
                f.write(f"# Quality Assessment Report - Task {task_id}\n\n")
                f.write(report)
            
            self.logger.info(f"Quality report saved to {filename}")
            
        except Exception as e:
            self.logger.error(f"Failed to save quality report: {e}")
    
    def _extract_recommendations(self, assessment: str) -> List[str]:
        """Extract actionable recommendations from assessment"""
        recommendations = []
        
        # Look for improvement sections
        improvement_section = re.search(r'AREAS FOR IMPROVEMENT:(.*?)(?=##|$)', assessment, re.DOTALL)
        if improvement_section:
            lines = improvement_section.group(1).strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('-') or line.startswith('*'):
                    recommendations.append(line[1:].strip())
        
        return recommendations
    
    def _check_security_issues(self, code_and_tests: str) -> List[str]:
        """Basic security issue detection"""
        issues = []
        
        # Common security anti-patterns
        security_patterns = {
            r'eval\s*\(': 'Use of eval() can be dangerous',
            r'exec\s*\(': 'Use of exec() can be dangerous', 
            r'input\s*\([^)]*\)': 'Raw input() usage may be unsafe',
            r'shell=True': 'subprocess with shell=True can be dangerous',
            r'pickle\.loads?\s*\(': 'Pickle deserialization can be unsafe',
            r'sql.*%.*%': 'Potential SQL injection vulnerability',
            r'password.*=.*["\'][^"\']*["\']': 'Hardcoded password detected'
        }
        
        for pattern, message in security_patterns.items():
            if re.search(pattern, code_and_tests, re.IGNORECASE):
                issues.append(message)
        
        return issues

"""
Conflict resolver for handling code conflicts during integration.
"""

import os
import difflib
import logging
from typing import Dict, List, Tuple

class ConflictResolver:
    """Handles code conflict detection and resolution."""
    
    def __init__(self):
        """Initialize conflict resolver."""
        self.logger = logging.getLogger(__name__)
    
    def analyze_conflict(self, conflict_data: Dict) -> Dict:
        """
        Analyze a code conflict to determine severity and resolvability.
        
        Args:
            conflict_data (Dict): Conflict information including:
                - file: File path
                - type: Conflict type
                - repo_content: Current content in repo
                - new_content: New content to merge
                
        Returns:
            Dict: Analysis results including:
                - severity: low/medium/high
                - auto_resolvable: bool
                - strategy: Suggested resolution strategy
        """
        try:
            # Compare file contents
            diff = difflib.unified_diff(
                conflict_data["repo_content"].splitlines(),
                conflict_data["new_content"].splitlines(),
                lineterm=""
            )
            diff_lines = list(diff)
            
            # Count changes
            additions = len([l for l in diff_lines if l.startswith("+")])
            deletions = len([l for l in diff_lines if l.startswith("-")])
            total_changes = additions + deletions
            
            # Determine severity
            if total_changes <= 5:
                severity = "low"
            elif total_changes <= 20:
                severity = "medium"
            else:
                severity = "high"
                
            # Determine if auto-resolvable
            # For now, only consider low severity conflicts as auto-resolvable
            auto_resolvable = severity == "low"
            
            return {
                "severity": severity,
                "auto_resolvable": auto_resolvable,
                "strategy": "merge" if auto_resolvable else "manual"
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing conflict: {str(e)}")
            return {
                "severity": "high",
                "auto_resolvable": False,
                "strategy": "manual"
            }
    
    def suggest_resolution(self, analysis: Dict) -> Dict:
        """
        Suggest a resolution strategy based on conflict analysis.
        
        Args:
            analysis (Dict): Conflict analysis results
            
        Returns:
            Dict: Resolution suggestion including:
                - strategy: Resolution strategy
                - description: Strategy description
                - steps: List of steps to resolve
        """
        if analysis["auto_resolvable"]:
            return {
                "strategy": "merge",
                "description": "Automatically merge changes",
                "steps": ["Apply new changes", "Keep existing structure"]
            }
        else:
            return {
                "strategy": "manual",
                "description": "Manual resolution required",
                "steps": ["Review changes manually", "Resolve conflicts", "Verify resolution"]
            }
    
    def apply_resolution(self, repo_dir: str, conflict_data: Dict, resolution: Dict) -> Tuple[bool, str]:
        """
        Apply a conflict resolution.
        
        Args:
            repo_dir (str): Repository directory
            conflict_data (Dict): Conflict information
            resolution (Dict): Resolution strategy
            
        Returns:
            Tuple[bool, str]: Success status and message/error
        """
        try:
            if resolution["strategy"] == "merge":
                # Write the new content
                file_path = os.path.join(repo_dir, conflict_data["file"])
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w") as f:
                    f.write(conflict_data["new_content"])
                return True, "Changes merged successfully"
            else:
                return False, "Manual resolution required"
        except Exception as e:
            return False, str(e)

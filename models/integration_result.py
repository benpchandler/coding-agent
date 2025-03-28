"""
Model for tracking integration results.
"""

from typing import Dict, List, Optional
from datetime import datetime

class IntegrationResult:
    """Represents the result of an integration process."""
    
    def __init__(self, task_id: str):
        """
        Initialize integration result.
        
        Args:
            task_id (str): ID of the task being integrated
        """
        self.task_id = task_id
        self.status = "pending"
        self.start_time = datetime.now()
        self.end_time = None
        self.integration_branch = None
        self.commit_id = None
        self.issues = []
        
    def set_status(self, status: str):
        """
        Set integration status.
        
        Args:
            status (str): New status
        """
        self.status = status
        if status in ["success", "failure"]:
            self.end_time = datetime.now()
    
    def set_integration_details(self, integration_branch: Optional[str] = None, commit_id: Optional[str] = None):
        """
        Set integration details.
        
        Args:
            integration_branch (str, optional): Integration branch name. Defaults to None.
            commit_id (str, optional): Commit ID. Defaults to None.
        """
        if integration_branch:
            self.integration_branch = integration_branch
        if commit_id:
            self.commit_id = commit_id
    
    def add_issue(self, issue_type: str, file_path: str, message: str, resolution: Optional[str] = None):
        """
        Add an integration issue.
        
        Args:
            issue_type (str): Type of issue
            file_path (str): Path to affected file
            message (str): Issue description
            resolution (str, optional): Resolution status. Defaults to None.
        """
        self.issues.append({
            "type": issue_type,
            "file": file_path,
            "message": message,
            "resolution": resolution,
            "timestamp": datetime.now().isoformat()
        })
    
    def to_dict(self) -> Dict:
        """
        Convert to dictionary.
        
        Returns:
            Dict: Dictionary representation
        """
        return {
            "task_id": self.task_id,
            "status": self.status,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "integration_branch": self.integration_branch,
            "commit_id": self.commit_id,
            "issues": self.issues
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'IntegrationResult':
        """
        Create from dictionary.
        
        Args:
            data (Dict): Dictionary data
            
        Returns:
            IntegrationResult: New instance
        """
        result = cls(data["task_id"])
        result.status = data["status"]
        result.start_time = datetime.fromisoformat(data["start_time"])
        result.end_time = datetime.fromisoformat(data["end_time"]) if data["end_time"] else None
        result.integration_branch = data["integration_branch"]
        result.commit_id = data["commit_id"]
        result.issues = data["issues"]
        return result

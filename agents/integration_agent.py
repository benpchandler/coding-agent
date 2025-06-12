import os
import json
import tempfile
import shutil
from datetime import datetime
from common.logging_utils import setup_logger
from common.json_utils import load_json, save_json
from components.integration.repository_handler import RepositoryHandler
from components.integration.conflict_resolver import ConflictResolver
from components.integration.dependency_manager import DependencyManager
from components.integration.integration_tester import IntegrationTester
from components.integration.documentation_generator import DocumentationGenerator
from models.task import Task, TaskStatus
from models.integration_result import IntegrationResult
from typing import Dict

logger = setup_logger(__name__)

def integrate_task(task: Task) -> Dict:
    """
    Integrate a task's code changes into the main codebase.
    
    Args:
        task (Task): The task to integrate
        
    Returns:
        Dict: Integration results
    """
    try:
        agent = IntegrationAgent()
        agent.process_task(task)
        return task.integration_results
    except Exception as e:
        logger.error(f"Error integrating task {task.task_id}: {str(e)}")
        return {
            'status': 'failure',
            'message': str(e),
            'issues': [{'type': 'error', 'message': str(e)}]
        }

class IntegrationAgent:
    def __init__(self, config_path=None):
        self.logger = setup_logger(f"{__name__}.IntegrationAgent")
        
        # Load configuration
        config_path = config_path or "./config/integration_config.json"
        self.config = load_json(config_path)
        
        if not self.config:
            self.logger.error(f"Failed to load configuration from {config_path}")
            self.config = {}
            
        # Initialize components
        self.repo_handler = RepositoryHandler(self.config.get("repository", {}))
        self.conflict_resolver = ConflictResolver()
        self.dependency_manager = DependencyManager(self.config.get("dependencies", {}))
        self.integration_tester = IntegrationTester(self.config.get("integration", {}))
        self.doc_generator = DocumentationGenerator()
        
    def process_task(self, task_data):
        """Process a task for integration"""
        self.logger.info(f"Processing task {task_data['task_id']} for integration")
        
        # Convert task data to Task object if necessary
        task = task_data if isinstance(task_data, Task) else Task.from_dict(task_data)
        
        # Check if task is ready for integration
        if task.status != TaskStatus.READY_FOR_INTEGRATION:
            self.logger.error(f"Task {task.task_id} is not ready for integration (status: {task.status})")
            return task
            
        # Update task status
        task.update_status(TaskStatus.INTEGRATING, "Starting integration process")
        
        # Initialize integration result
        integration_result = IntegrationResult(task.task_id)
        
        try:
            # 1. Prepare integration environment
            integration_env = self._prepare_environment(task)
            
            #
            # 2. Clone repository
            repo_dir = os.path.join(integration_env["working_dir"], "repo")
            clone_success, clone_message = self.repo_handler.clone_repository(repo_dir)
            
            if not clone_success:
                self.logger.error(f"Failed to clone repository: {clone_message}")
                integration_result.set_status("failure")
                integration_result.add_issue("repository", "N/A", f"Failed to clone repository: {clone_message}")
                task.integration_results = integration_result.to_dict()
                task.update_status(TaskStatus.FAILED, "Integration failed: Repository clone failed")
                return task
                
            # 3. Create integration branch
            branch_success, integration_branch = self.repo_handler.create_integration_branch(
                repo_dir,
                self.config["repository"]["branches"]["development"],
                task.task_id
            )
            
            if not branch_success:
                self.logger.error(f"Failed to create integration branch: {integration_branch}")
                integration_result.set_status("failure")
                integration_result.add_issue("branch", "N/A", f"Failed to create integration branch: {integration_branch}")
                task.integration_results = integration_result.to_dict()
                task.update_status(TaskStatus.FAILED, "Integration failed: Branch creation failed")
                return task
                
            integration_result.set_integration_details(integration_branch=integration_branch)
            
            # 4. Detect conflicts
            conflicts = self.repo_handler.detect_conflicts(
                repo_dir,
                task.code["files"],
                integration_branch
            )
            
            # 5. Resolve conflicts if auto-resolve is enabled
            if conflicts and self.config["integration"]["auto_resolve_conflicts"]:
                self.logger.info(f"Resolving {len(conflicts)} conflicts")
                
                for conflict in conflicts:
                    # Get file content from repo and task
                    file_path = conflict["file"]
                    
                    # Find file content from task
                    task_file = next((f for f in task.code["files"] if f["path"] == file_path), None)
                    
                    if not task_file:
                        self.logger.warning(f"File {file_path} not found in task files")
                        integration_result.add_issue(
                            "conflict",
                            file_path,
                            "File in conflict not found in task files",
                            "Skipped"
                        )
                        continue
                        
                    # Get file content from repo
                    try:
                        with open(os.path.join(repo_dir, file_path), 'r') as f:
                            repo_content = f.read()
                    except Exception as e:
                        self.logger.error(f"Error reading file {file_path} from repo: {str(e)}")
                        repo_content = ""
                        
                    # Enhanced conflict data
                    conflict_data = {
                        "file": file_path,
                        "type": conflict["type"],
                        "repo_content": repo_content,
                        "new_content": task_file["content"]
                    }
                    
                    # Analyze conflict
                    analysis = self.conflict_resolver.analyze_conflict(conflict_data)
                    
                    # If conflict is auto-resolvable, apply resolution
                    if analysis["auto_resolvable"]:
                        resolution = self.conflict_resolver.suggest_resolution(analysis)
                        
                        resolved, message = self.conflict_resolver.apply_resolution(
                            repo_dir,
                            conflict_data,
                            resolution
                        )
                        
                        if resolved:
                            integration_result.add_issue(
                                "conflict_resolved",
                                file_path,
                                f"Conflict resolved: {analysis['severity']} severity",
                                resolution["strategy"]
                            )
                        else:
                            integration_result.add_issue(
                                "conflict_resolution_failed",
                                file_path,
                                f"Failed to resolve conflict: {message}",
                                "Manual resolution required"
                            )
                    else:
                        integration_result.add_issue(
                            "conflict_manual",
                            file_path,
                            f"Manual resolution required: {analysis['severity']} severity",
                            "Manual resolution required"
                        )
            elif conflicts:
                # Log conflicts that require manual resolution
                for conflict in conflicts:
                    integration_result.add_issue(
                        "conflict",
                        conflict["file"],
                        "Conflict detected, manual resolution required",
                        "None"
                    )
                    
            # 6. Merge code changes
            self.logger.info("Merging code changes")
            merge_success, merge_message = self.repo_handler.merge_changes(
                repo_dir,
                task.code["files"],
                integration_branch
            )
            
            if not merge_success:
                self.logger.error(f"Failed to merge changes: {merge_message}")
                integration_result.set_status("failure")
                integration_result.add_issue("merge", "N/A", f"Failed to merge changes: {merge_message}")
                task.integration_results = integration_result.to_dict()
                task.update_status(TaskStatus.FAILED, "Integration failed: Merge failed")
                return task
                
            # 7. Commit and push changes
            commit_msg = f"Integration of task {task.task_id}: {task.description}"
            commit_success, commit_id = self.repo_handler.commit_changes(
                repo_dir,
                commit_msg
            )
            
            if not commit_success:
                self.logger.error(f"Failed to commit changes: {commit_id}")
                integration_result.set_status("failure")
                integration_result.add_issue("commit", "N/A", f"Failed to commit changes: {commit_id}")
                task.integration_results = integration_result.to_dict()
                task.update_status(TaskStatus.FAILED, "Integration failed: Commit failed")
                return task
                
            integration_result.set_integration_details(commit_id=commit_id)
            
            # 8. Check dependencies
            self.logger.info("Checking dependencies")
            dependency_changes = self.dependency_manager.detect_dependency_changes(
                repo_dir,
                task.code["files"],
                task.language
            )
            
            if dependency_changes["added"] or dependency_changes["updated"]:
                # Update dependency files
                self.dependency_manager.update_dependency_files(
                    repo_dir,
                    dependency_changes,
                    task.language
                )
                
                # Commit dependency changes
                dep_commit_msg = f"Update dependencies for task {task.task_id}"
                self.repo_handler.commit_changes(
                    repo_dir,
                    dep_commit_msg
                )
                
            # 9. Verify dependencies
            dep_verify_success, dep_verify_msg = self.dependency_manager.verify_dependency_compatibility(
                repo_dir,
                task.language
            )
            
            if not dep_verify_success:
                self.logger.warning(f"Dependency verification warning: {dep_verify_msg}")
                integration_result.add_issue(
                    "dependency",
                    "N/A",
                    f"Dependency verification warning: {dep_verify_msg}",
                    "Proceeding with integration"
                )
                
            # 10. Update documentation
            if self.config["integration"]["documentation_update_strategy"] != "skip":
                self.logger.info("Updating documentation")
                
                # Get old code (from repo)
                old_code = []
                for file_info in task.code["files"]:
                    file_path = file_info["path"]
                    try:
                        with open(os.path.join(repo_dir, file_path), 'r') as f:
                            old_content = f.read()
                            old_code.append({
                                "path": file_path,
                                "content": old_content
                            })
                    except FileNotFoundError:
                        # File doesn't exist in repo (new file)
                        pass
                        
                # Analyze code changes
                code_changes = self.doc_generator.analyze_code_changes(old_code, task.code["files"])
                
                # Update API docs
                api_docs = self.doc_generator.update_api_docs(repo_dir, code_changes)
                for doc_file in api_docs:
                    integration_result.add_documentation_update(doc_file)
                    
                # Update usage examples
                examples = self.doc_generator.update_usage_examples(repo_dir, code_changes)
                for example_file in examples:
                    integration_result.add_documentation_update(example_file)
                    
                # Update changelog
                changelog_file = self.doc_generator.generate_changelog_entry(
                    repo_dir,
                    task.to_dict(),
                    code_changes
                )
                integration_result.add_documentation_update(changelog_file)
                
                # Commit documentation changes
                doc_commit_msg = f"Update documentation for task {task.task_id}"
                self.repo_handler.commit_changes(
                    repo_dir,
                    doc_commit_msg
                )
                
            # 11. Run integration tests
            self.logger.info("Running integration tests")
            test_env = self.integration_tester.prepare_test_environment(repo_dir)
            test_results = self.integration_tester.run_integration_tests(repo_dir)
            
            # Update integration result with test results
            integration_result.set_test_results(
                test_results["status"],
                test_results.get("total", 0),
                test_results.get("passed", 0),
                test_results.get("failed", 0),
                test_results.get("skipped", 0)
            )
            
            # 12. Push changes to remote
            push_success, push_message = self.repo_handler.push_changes(repo_dir, integration_branch)
            
            if not push_success:
                self.logger.error(f"Failed to push changes: {push_message}")
                integration_result.set_status("partial_success")
                integration_result.add_issue("push", "N/A", f"Failed to push changes: {push_message}")
                task.integration_results = integration_result.to_dict()
                task.update_status(TaskStatus.FAILED, "Integration partially failed: Push failed")
                return task
                
            # 13. Create pull request if configured
            if self.config["integration"]["strategy"] == "pull_request":
                pr_success, pr_url = self.repo_handler.create_pull_request(
                    repo_dir,
                    self.config["repository"]["branches"]["development"],
                    integration_branch,
                    f"Integration of task {task.task_id}",
                    f"This PR integrates task {task.task_id}: {task.description}\n\n"
                    f"Changes include {len(task.code['files'])} files and "
                    f"{len(integration_result.integration_tests['test_results'])} tests."
                )
                
                if pr_success:
                    integration_result.set_integration_details(pull_request_url=pr_url)
                    integration_result.add_next_step(
                        "review",
                        "Pull request ready for human review",
                        pr_url
                    )
                else:
                    integration_result.add_issue(
                        "pull_request",
                        "N/A",
                        f"Failed to create pull request: {pr_url}",
                        "Manual PR creation required"
                    )
                    
            # 14. Set final status
            if test_results["status"] == "passed" and not any(
                issue["type"].startswith("conflict_resolution_failed") 
                for issue in integration_result.issues
            ):
                integration_result.set_status("success")
                status_message = "Integration completed successfully"
            elif test_results["status"] == "failed":
                integration_result.set_status("partial_success")
                status_message = "Integration completed with test failures"
            else:
                integration_result.set_status("partial_success")
                status_message = "Integration completed with issues"
                
            # Update task status
            task.integration_results = integration_result.to_dict()
            task.update_status(TaskStatus.COMPLETED, status_message)
            
            # Clean up temporary directory
            self._cleanup_environment(integration_env)
            
            return task
            
        except Exception as e:
            self.logger.error(f"Integration process failed with error: {str(e)}")
            integration_result.set_status("failure")
            integration_result.add_issue("error", "N/A", f"Integration process error: {str(e)}")
            task.integration_results = integration_result.to_dict()
            task.update_status(TaskStatus.FAILED, f"Integration failed: {str(e)}")
            return task
        
    def _prepare_environment(self, task):
        """Prepare integration environment"""
        self.logger.info(f"Preparing integration environment for task {task.task_id}")
        
        # Create temporary directory
        working_dir = tempfile.mkdtemp(prefix=f"integration_{task.task_id}_")
        
        integration_env = {
            "task_id": task.task_id,
            "working_dir": working_dir,
            "timestamp": datetime.now().isoformat(),
            "language": task.language
        }
        
        self.logger.info(f"Created integration environment at {working_dir}")
        return integration_env
        
    def _cleanup_environment(self, integration_env):
        """Clean up integration environment"""
        self.logger.info(f"Cleaning up integration environment: {integration_env['working_dir']}")
        
        try:
            shutil.rmtree(integration_env["working_dir"])
            self.logger.info("Integration environment cleaned up")
        except Exception as e:
            self.logger.warning(f"Failed to clean up integration environment: {str(e)}")
"""
Integration components for handling code integration, conflict resolution, and documentation.
"""

from .repository_handler import RepositoryHandler
from .conflict_resolver import ConflictResolver
from .dependency_manager import DependencyManager
from .integration_tester import IntegrationTester
from .documentation_generator import DocumentationGenerator

__all__ = [
    'RepositoryHandler',
    'ConflictResolver',
    'DependencyManager',
    'IntegrationTester',
    'DocumentationGenerator'
] 
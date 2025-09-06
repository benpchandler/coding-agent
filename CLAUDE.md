# Coding Agent - CLAUDE.md

This file provides specific guidance for working with the Coding Agent system within the sample-organizer repository.

## Agent Architecture Overview

The Coding Agent system uses a multi-agent architecture where specialized agents handle different phases of the development workflow:

```
OrchestratorAgent (Main Coordinator)
    ├── Decomposer (Task Breakdown)
    ├── CodeGenerationAgent (Implementation)
    ├── TestingAgent (Test Creation & Execution)
    ├── QualityAssessmentAgent (Code Quality)
    └── IntegrationAgent (Integration & Deployment)
```

## State Machine & Task Flow

### Task States
```python
class TaskState(Enum):
    CREATED = "created"
    DECOMPOSING = "decomposing"
    READY_FOR_IMPLEMENTATION = "ready_for_implementation"
    IMPLEMENTING = "implementing"
    READY_FOR_TESTING = "ready_for_testing"
    TESTING = "testing"
    READY_FOR_QUALITY = "ready_for_quality"
    QUALITY_CHECK = "quality_check"
    READY_FOR_INTEGRATION = "ready_for_integration"
    INTEGRATING = "integrating"
    COMPLETED = "completed"
    FAILED = "failed"
```

### State Transitions
- Tasks must progress through states sequentially
- Each agent is responsible for specific state transitions
- Failed states can be retried or manually reset

## Agent-Specific Development Patterns

### Creating New Agents
```python
from agents.base_agent import BaseAgent
from models.task import Task, TaskState

class CustomAgent(BaseAgent):
    """Custom agent for specific workflow phase."""
    
    def __init__(self, config_path: str = "config/custom_config.json"):
        super().__init__(config_path)
        self.name = "CustomAgent"
    
    async def process_task(self, task: Task) -> Task:
        """Process task according to agent's responsibility."""
        try:
            # Agent-specific logic here
            result = await self._perform_custom_operation(task)
            
            # Update task state
            task.state = TaskState.NEXT_STATE
            task.add_to_history(f"{self.name}: Operation completed")
            
            # Store results
            task.metadata["custom_result"] = result
            
            return task
        except Exception as e:
            return self._handle_error(task, e)
```

### Agent Communication Protocols
```python
# Agents communicate through task metadata
task.metadata = {
    "decomposition": {
        "subtasks": [...],
        "dependencies": {...}
    },
    "implementation": {
        "code": "...",
        "language": "python",
        "file_path": "implementations/task_123.py"
    },
    "testing": {
        "test_file": "tests/test_123.py",
        "coverage": 85.5,
        "passed": True
    },
    "quality": {
        "pylint_score": 9.2,
        "mypy_passed": True,
        "issues": []
    }
}
```

## API Interaction Best Practices

### OpenAI API Configuration
```python
# config/code_generation_config.json
{
    "model": "gpt-4-turbo-preview",
    "temperature": 0.7,
    "max_tokens": 4000,
    "system_prompt": "You are an expert Python developer...",
    "retry_config": {
        "max_retries": 3,
        "initial_delay": 1.0,
        "exponential_base": 2.0,
        "max_delay": 60.0
    }
}
```

### Rate Limiting & Retry Strategies
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60)
)
async def call_openai_api(prompt: str) -> str:
    """Call OpenAI API with automatic retry."""
    try:
        response = await openai.ChatCompletion.acreate(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature
        )
        return response.choices[0].message.content
    except openai.error.RateLimitError:
        logger.warning("Rate limit hit, retrying...")
        raise
    except openai.error.APIError as e:
        logger.error(f"API error: {e}")
        raise
```

## Task Priority Algorithm

### Priority Calculation
```python
def calculate_effective_priority(task: Task) -> float:
    """Calculate effective priority with age factor."""
    base_priority = task.priority  # 0-100
    
    # Age factor: increase priority by 1 point per hour
    age_hours = (datetime.now() - task.created_at).total_seconds() / 3600
    age_boost = min(age_hours, 20)  # Cap at 20 points
    
    # Dependency factor: boost if blocking other tasks
    dependency_boost = 10 if task.blocking_tasks else 0
    
    # Failed task boost
    failure_boost = 15 if task.retry_count > 0 else 0
    
    return base_priority + age_boost + dependency_boost + failure_boost
```

### Priority Ranges
- 90-100: Critical/Blocking tasks
- 70-89: High priority features
- 40-69: Normal development tasks
- 20-39: Low priority enhancements
- 0-19: Nice-to-have improvements

## Web Dashboard Integration

### API Endpoints
```python
# FastAPI endpoints for dashboard
@app.get("/api/tasks")
async def get_tasks(
    status: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = 50
):
    """Get tasks with optional filtering."""
    # Implementation...

@app.post("/api/tasks/{task_id}/transition")
async def transition_task(task_id: str, new_state: TaskState):
    """Manually transition task state."""
    # Implementation...

@app.get("/api/agents/status")
async def get_agent_status():
    """Get current status of all agents."""
    # Implementation...
```

### Real-time Updates
```javascript
// WebSocket connection for real-time updates
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
    const update = JSON.parse(event.data);
    if (update.type === 'task_update') {
        updateTaskInUI(update.task);
    } else if (update.type === 'agent_status') {
        updateAgentStatus(update.agent, update.status);
    }
};
```

## Error Handling & Recovery

### Common Error Scenarios
```python
# 1. API Timeout
class APITimeoutError(Exception):
    """Raised when API call times out."""
    recovery_action = "retry_with_backoff"

# 2. Invalid Task State
class InvalidStateTransition(Exception):
    """Raised when invalid state transition attempted."""
    recovery_action = "reset_to_previous_state"

# 3. Resource Exhaustion
class ResourceExhaustedError(Exception):
    """Raised when system resources exhausted."""
    recovery_action = "pause_and_alert"
```

### Recovery Procedures
```python
async def recover_failed_task(task: Task) -> Task:
    """Recover a failed task based on failure type."""
    failure_reason = task.metadata.get("failure_reason", "unknown")
    
    recovery_strategies = {
        "api_timeout": self._retry_with_increased_timeout,
        "invalid_code": self._regenerate_with_refined_prompt,
        "test_failure": self._fix_and_retest,
        "quality_issues": self._refactor_code
    }
    
    strategy = recovery_strategies.get(failure_reason, self._manual_intervention)
    return await strategy(task)
```

## Model Selection Guidelines

### Task Complexity Mapping
```python
MODEL_SELECTION = {
    "simple": "gpt-3.5-turbo",      # Basic CRUD, simple logic
    "moderate": "gpt-4",             # Complex logic, algorithms
    "complex": "gpt-4-turbo",        # Architecture, system design
    "critical": "gpt-4-turbo-preview" # Mission-critical, security
}

def select_model_for_task(task: Task) -> str:
    """Select appropriate model based on task complexity."""
    complexity_indicators = {
        "simple": ["crud", "basic", "simple"],
        "moderate": ["algorithm", "optimize", "refactor"],
        "complex": ["architect", "design", "integrate"],
        "critical": ["security", "payment", "auth"]
    }
    
    # Analyze task description
    task_lower = task.description.lower()
    for level, indicators in complexity_indicators.items():
        if any(ind in task_lower for ind in indicators):
            return MODEL_SELECTION[level]
    
    return MODEL_SELECTION["moderate"]  # Default
```

## Debugging Tips

### Enable Verbose Logging
```bash
# Set environment variables
export LOG_LEVEL=DEBUG
export AGENT_DEBUG=1
export TRACE_API_CALLS=1

# Run with debug output
python main.py --debug --verbose
```

### Task Inspection Commands
```bash
# Inspect task details
python main.py --inspect-task --task-id TASK-XXX

# Show task history
python main.py --task-history --task-id TASK-XXX

# Export task metadata
python main.py --export-task --task-id TASK-XXX --format json
```

### Agent Health Checks
```python
# Check agent health
python main.py --health-check

# Test specific agent
python main.py --test-agent --agent-name CodeGenerationAgent

# Benchmark agent performance
python main.py --benchmark-agents
```

## Performance Optimization

### Concurrent Task Processing
```python
MAX_CONCURRENT_TASKS = 5  # Limit concurrent API calls

async def process_tasks_concurrently(tasks: List[Task]):
    """Process multiple tasks concurrently with limit."""
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    
    async def process_with_limit(task):
        async with semaphore:
            return await process_task(task)
    
    results = await asyncio.gather(
        *[process_with_limit(task) for task in tasks],
        return_exceptions=True
    )
    return results
```

### Caching Strategies
```python
# Cache decomposition results
decomposition_cache = {}

def get_cached_decomposition(task_description: str) -> Optional[Dict]:
    """Check if similar task was decomposed before."""
    # Generate cache key from description
    cache_key = hashlib.md5(task_description.encode()).hexdigest()
    
    if cache_key in decomposition_cache:
        logger.info(f"Using cached decomposition for: {task_description[:50]}...")
        return decomposition_cache[cache_key]
    
    return None
```

## Configuration Management

### Environment-Specific Configs
```python
# config/environments/
# ├── development.json
# ├── staging.json
# └── production.json

import os
import json

def load_config():
    """Load configuration based on environment."""
    env = os.getenv("CODING_AGENT_ENV", "development")
    config_path = f"config/environments/{env}.json"
    
    with open(config_path) as f:
        config = json.load(f)
    
    # Override with environment variables
    config["openai_api_key"] = os.getenv("OPENAI_API_KEY", config.get("openai_api_key"))
    
    return config
```

## Best Practices Summary

1. **Always validate task state** before processing
2. **Use appropriate retry strategies** for API calls
3. **Log all state transitions** for debugging
4. **Cache expensive operations** when possible
5. **Monitor agent health** continuously
6. **Set reasonable timeouts** for all operations
7. **Handle errors gracefully** with recovery strategies
8. **Use type hints** for better code clarity
9. **Write comprehensive tests** for each agent
10. **Document API changes** in configuration files
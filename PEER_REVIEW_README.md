# 🔄 Peer Review System

An intelligent peer review system where AI agents validate each other's work, creating a self-correcting development workflow.

## 🎯 Overview

The Peer Review System implements a novel approach where each AI agent acts as both a worker and a quality checker for the previous agent's output. This creates a natural feedback loop that improves output quality and catches errors early.

### 🏗️ Architecture

```
Task Input
    ↓
Decomposer Agent ────┐
    ↓                │
Code Generation ←────┘ (validates decomposition)
    ↓                │
Testing Agent ←──────┘ (validates code)
    ↓                │
Quality Agent ←──────┘ (validates tests)
    ↓
Final Output
```

Each agent:
1. **Validates** the previous agent's work
2. **Provides feedback** if validation fails
3. **Triggers retries** with specific improvement suggestions
4. **Performs its own work** only after validation passes

## 🚀 Quick Start

### 1. Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set your OpenAI API key
export OPENAI_API_KEY="your-api-key-here"
# OR create .env file with: OPENAI_API_KEY=your-api-key-here
```

### 2. Run Demo
```bash
python demo_peer_review.py
```

### 3. Interactive Mode
```bash
python main_peer_review.py
```

### 4. Web Dashboard
```bash
python web_dashboard.py
# Visit http://localhost:8000
# Click "Peer Review" tab
```

## 🤖 Agent Responsibilities

### **Decomposer Agent**
- **Input**: Task description
- **Output**: Structured task breakdown
- **Validation**: N/A (first in chain)

### **Code Generation Agent**
- **Input**: Task decomposition
- **Validation**: Checks if decomposition is clear, actionable, and complete
- **Output**: Implementation code
- **Feedback**: "Decomposition lacks clarity in step 3, please specify the data structure"

### **Testing Agent**
- **Input**: Generated code
- **Validation**: Checks syntax, completeness, testability
- **Output**: Comprehensive test suite
- **Feedback**: "Code is missing error handling for file not found scenario"

### **Quality Assessment Agent**
- **Input**: Test results and code
- **Validation**: Checks test coverage, execution success
- **Output**: Quality report with score and recommendations
- **Feedback**: "Tests don't cover edge cases, missing integration tests"

## 📊 Validation Criteria

### **Code Generation validates Decomposition:**
- ✅ Subtasks are clearly defined
- ✅ Requirements are actionable
- ✅ Dependencies are specified
- ✅ Acceptance criteria are testable

### **Testing validates Code:**
- ✅ Syntax is correct
- ✅ Code addresses requirements
- ✅ Functions have clear interfaces
- ✅ Error handling is present

### **Quality validates Testing:**
- ✅ Tests cover major code paths
- ✅ Edge cases are tested
- ✅ Tests execute successfully
- ✅ Coverage is adequate

## 🔄 Feedback Loop Process

1. **Agent A** produces output
2. **Agent B** validates output
3. If validation fails:
   - **Agent B** provides specific feedback
   - **Agent A** retries with feedback
   - Process repeats (max 2 retries)
4. If validation passes:
   - **Agent B** proceeds with its work

## 📈 Monitoring & Analytics

### **Web Dashboard Features:**
- Real-time feedback tracking
- Agent performance metrics
- Retry success rates
- Common issue patterns
- Quality score trends

### **Key Metrics:**
- **Feedback Frequency**: How often agents provide feedback
- **Retry Success Rate**: % of retries that succeed
- **Validation Confidence**: Agent confidence in validations
- **Quality Scores**: Overall output quality trends

## 🛠️ Usage Examples

### **Simple Task**
```python
from main_peer_review import process_task_with_peer_review

result = await process_task_with_peer_review(
    "Create a function to calculate fibonacci numbers",
    language="python",
    priority=80
)
```

### **Complex Task**
```python
result = await process_task_with_peer_review(
    "Build a REST API for user authentication with JWT tokens",
    language="python",
    priority=90
)
```

### **Check Feedback Stats**
```python
from models.validation import FeedbackTracker

tracker = FeedbackTracker()
stats = tracker.get_feedback_stats()
print(f"Code generation received {stats['code_generation']['received_count']} feedback instances")
```

## 📁 Generated Files

For each processed task, the system creates:

```
implementations/
├── TASK-abc123_general.py      # Generated code
tests/
├── test_TASK-abc123.py         # Test suite
quality_reports/
├── quality_report_TASK-abc123.md  # Quality assessment
logs/feedback/
├── feedback_20250906.jsonl    # Feedback log
```

## 🎛️ Configuration

### **Agent Settings**
```json
{
  "model": "gpt-4-turbo",
  "temperature": 0.1,
  "max_tokens": 4000,
  "max_retries": 2
}
```

### **Quality Thresholds**
- Minimum quality score: 7/10
- Required test coverage: 80%
- Maximum retry attempts: 2

## 🔧 Advanced Features

### **Custom Validation Prompts**
Each agent can be configured with custom validation criteria:

```python
class CustomCodeAgent(CodeGenerationAgentEnhanced):
    def _build_validation_prompt(self, previous_output, task):
        return f"""
        Custom validation for {task.language}:
        1. Check for security vulnerabilities
        2. Validate performance considerations
        3. Ensure accessibility compliance
        ...
        """
```

### **Feedback Analysis**
```python
# Get common issues for specific agent
issues = tracker.get_common_issues_for_agent("code_generation")
print(f"Most common issues: {issues}")

# Analyze feedback patterns
patterns = tracker.get_feedback_stats()
for agent, stats in patterns.items():
    print(f"{agent}: {stats['retry_success_rate']:.1%} retry success")
```

## 🎯 Benefits

1. **Self-Correcting**: Agents catch and fix each other's mistakes
2. **Quality Assurance**: Built-in validation at every step
3. **Transparency**: Clear feedback on what went wrong
4. **Learning**: System improves through feedback patterns
5. **Reliability**: Multiple validation layers prevent bad output

## 🚨 Troubleshooting

### **Common Issues:**

**"Validation response was malformed"**
- Agent didn't return valid JSON
- Check validation prompts for clarity

**"Max retries exceeded"**
- Task may be too complex
- Check feedback messages for guidance

**"No API key configured"**
- Set OPENAI_API_KEY environment variable
- Or use web dashboard API settings

### **Debug Mode:**
```bash
export LOG_LEVEL=DEBUG
python main_peer_review.py --task "your task here"
```

## 📚 API Reference

### **Main Functions**
- `process_task_with_peer_review()`: Process single task
- `FeedbackOrchestrator.process_task_with_feedback()`: Core workflow
- `FeedbackTracker.get_feedback_stats()`: Analytics

### **Web Endpoints**
- `GET /feedback_dashboard`: Feedback overview
- `GET /peer_review_stats`: Detailed statistics
- `GET /api_key_settings`: API key management

## 🎉 Next Steps

1. **Try the demo**: `python demo_peer_review.py`
2. **Explore the dashboard**: Visit http://localhost:8000
3. **Process your own tasks**: Use interactive mode
4. **Analyze feedback patterns**: Check the peer review stats
5. **Customize agents**: Modify validation criteria for your needs

The peer review system represents a new paradigm in AI-driven development - where agents collaborate and improve each other's work, creating higher quality outputs through intelligent feedback loops.

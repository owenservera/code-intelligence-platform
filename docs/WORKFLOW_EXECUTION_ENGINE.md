# Workflow Execution Engine Design

## Overview

The Workflow Execution Engine is the core system that orchestrates guided workflows in CIP CLI v2.0. It provides a framework for defining, executing, and managing complex multi-step operations with state persistence, error recovery, and user interaction.

## Architecture

### Core Components

```
WorkflowEngine
├── WorkflowRegistry (Workflow definitions)
├── WorkflowExecutor (Execution orchestration)
├── StateManager (State persistence)
├── StepExecutor (Individual step execution)
├── ErrorHandler (Error handling & recovery)
└── UIAdapter (User interface integration)
```

## Workflow Definition System

### Workflow Schema

```python
from dataclasses import dataclass
from typing import List, Dict, Optional, Callable
from enum import Enum

class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"

class WorkflowStatus(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"

@dataclass
class WorkflowStep:
    """Single step in a workflow."""
    id: str
    name: str
    description: str
    handler: Callable  # Function to execute the step
    dependencies: List[str] = None  # Step IDs this depends on
    optional: bool = False
    timeout: int = 300  # seconds
    retry_count: int = 0
    rollback_handler: Callable = None  # Function to rollback this step
    validation_handler: Callable = None  # Function to validate step completion
    metadata: Dict = None

@dataclass
class WorkflowDefinition:
    """Complete workflow definition."""
    id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    category: str  # "pre-commit", "diagnosis", etc.
    version: str = "1.0"
    author: str = "CIP"
    metadata: Dict = None

@dataclass
class StepExecution:
    """Execution state of a single step."""
    step_id: str
    status: StepStatus
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    output: Optional[str] = None
    error: Optional[str] = None
    retry_count: int = 0
    metadata: Dict = None

@dataclass
class WorkflowExecution:
    """Execution state of a complete workflow."""
    workflow_id: str
    execution_id: str
    status: WorkflowStatus
    steps: Dict[str, StepExecution]  # step_id -> StepExecution
    started_at: float
    completed_at: Optional[float] = None
    context: Dict = None  # Shared context across steps
    user_inputs: Dict = None  # User decisions and inputs
    metadata: Dict = None
```

## Workflow Registry

```python
class WorkflowRegistry:
    """Central registry for workflow definitions."""
    
    def __init__(self):
        self.workflows: Dict[str, WorkflowDefinition] = {}
        self.categories: Dict[str, List[str]] = {}
    
    def register(self, workflow: WorkflowDefinition):
        """Register a workflow definition."""
        self.workflows[workflow.id] = workflow
        
        # Update category index
        if workflow.category not in self.categories:
            self.categories[workflow.category] = []
        self.categories[workflow.category].append(workflow.id)
    
    def get(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Get workflow by ID."""
        return self.workflows.get(workflow_id)
    
    def list_by_category(self, category: str) -> List[WorkflowDefinition]:
        """List all workflows in a category."""
        workflow_ids = self.categories.get(category, [])
        return [self.workflows[wid] for wid in workflow_ids]
    
    def list_all(self) -> List[WorkflowDefinition]:
        """List all registered workflows."""
        return list(self.workflows.values())
```

## Workflow Executor

```python
class WorkflowExecutor:
    """Execute workflows with state management and error recovery."""
    
    def __init__(self, root: str, config: dict):
        self.root = root
        self.config = config
        self.registry = WorkflowRegistry()
        self.state_manager = StateManager(root)
        self._load_builtin_workflows()
    
    def _load_builtin_workflows(self):
        """Load built-in workflow definitions."""
        # Pre-commit workflow
        pre_commit = WorkflowDefinition(
            id="pre-commit",
            name="Pre-Commit Workflow",
            description="Comprehensive checks before committing changes",
            category="git",
            steps=[
                WorkflowStep(
                    id="analyze_changes",
                    name="Analyze Changes",
                    description="Detect and analyze changed files",
                    handler=self._step_analyze_changes
                ),
                WorkflowStep(
                    id="run_audit",
                    name="Run Audit",
                    description="Audit changed files for quality issues",
                    handler=self._step_run_audit,
                    dependencies=["analyze_changes"]
                ),
                WorkflowStep(
                    id="check_impact",
                    name="Check Impact",
                    description="Analyze impact of changes",
                    handler=self._step_check_impact,
                    dependencies=["analyze_changes"]
                ),
                WorkflowStep(
                    id="verify_tests",
                    name="Verify Tests",
                    description="Run relevant tests",
                    handler=self._step_verify_tests,
                    dependencies=["run_audit"]
                ),
                WorkflowStep(
                    id="generate_report",
                    name="Generate Report",
                    description="Generate comprehensive report",
                    handler=self._step_generate_report,
                    dependencies=["run_audit", "check_impact", "verify_tests"]
                )
            ]
        )
        self.registry.register(pre_commit)
        
        # Diagnosis workflow
        diagnosis = WorkflowDefinition(
            id="diagnosis",
            name="Repository Diagnosis",
            description="Diagnose repository issues and suggest fixes",
            category="maintenance",
            steps=[
                WorkflowStep(
                    id="health_check",
                    name="Health Check",
                    description="Check repository health",
                    handler=self._step_health_check
                ),
                WorkflowStep(
                    id="index_check",
                    name="Index Check",
                    description="Verify index integrity",
                    handler=self._step_index_check
                ),
                WorkflowStep(
                    id="dependency_check",
                    name="Dependency Check",
                    description="Check for dependency issues",
                    handler=self._step_dependency_check
                ),
                WorkflowStep(
                    id="analyze_issues",
                    name="Analyze Issues",
                    description="Analyze detected issues",
                    handler=self._step_analyze_issues,
                    dependencies=["health_check", "index_check", "dependency_check"]
                ),
                WorkflowStep(
                    id="suggest_fixes",
                    name="Suggest Fixes",
                    description="Suggest fixes for detected issues",
                    handler=self._step_suggest_fixes,
                    dependencies=["analyze_issues"]
                )
            ]
        )
        self.registry.register(diagnosis)
    
    def execute(self, workflow_id: str, resume: bool = False) -> WorkflowExecution:
        """Execute a workflow."""
        workflow = self.registry.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        if resume:
            execution = self.state_manager.load_latest(workflow_id)
            if not execution:
                raise ValueError("No previous execution to resume")
        else:
            execution = self._create_execution(workflow)
        
        try:
            self._execute_workflow(workflow, execution)
        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.metadata['error'] = str(e)
            self.state_manager.save(execution)
            raise
        
        return execution
    
    def _create_execution(self, workflow: WorkflowDefinition) -> WorkflowExecution:
        """Create new workflow execution."""
        import time
        import uuid
        
        steps = {}
        for step in workflow.steps:
            steps[step.id] = StepExecution(
                step_id=step.id,
                status=StepStatus.PENDING
            )
        
        return WorkflowExecution(
            workflow_id=workflow.id,
            execution_id=str(uuid.uuid4()),
            status=WorkflowStatus.NOT_STARTED,
            steps=steps,
            started_at=time.time(),
            context={},
            user_inputs={},
            metadata={}
        )
    
    def _execute_workflow(self, workflow: WorkflowDefinition, execution: WorkflowExecution):
        """Execute workflow steps in dependency order."""
        execution.status = WorkflowStatus.IN_PROGRESS
        self.state_manager.save(execution)
        
        # Build execution order based on dependencies
        execution_order = self._build_execution_order(workflow)
        
        for step_id in execution_order:
            step = next(s for s in workflow.steps if s.id == step_id)
            step_exec = execution.steps[step_id]
            
            # Skip if already completed (resume case)
            if step_exec.status == StepStatus.COMPLETED:
                continue
            
            # Skip if optional and dependency failed
            if step.optional and self._dependency_failed(step, execution):
                step_exec.status = StepStatus.SKIPPED
                continue
            
            # Execute step
            self._execute_step(step, step_exec, execution)
            
            # Save state after each step
            self.state_manager.save(execution)
            
            # Check if step failed
            if step_exec.status == StepStatus.FAILED:
                if step.retry_count > step_exec.retry_count:
                    # Retry
                    step_exec.retry_count += 1
                    step_exec.status = StepStatus.PENDING
                    self._execute_step(step, step_exec, execution)
                else:
                   execution.status = WorkflowStatus.FAILED
                    raise WorkflowExecutionError(f"Step {step_id} failed")
        
        execution.status = WorkflowStatus.COMPLETED
        execution.completed_at = time.time()
        self.state_manager.save(execution)
    
    def _build_execution_order(self, workflow: WorkflowDefinition) -> List[str]:
        """Build topological order of steps based on dependencies."""
        from collections import defaultdict, deque
        
        # Build dependency graph
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        
        for step in workflow.steps:
            in_degree[step.id] = 0
        
        for step in workflow.steps:
            for dep in step.dependencies or []:
                graph[dep].append(step.id)
                in_degree[step.id] += 1
        
        # Topological sort
        queue = deque([sid for sid in in_degree if in_degree[sid] == 0])
        order = []
        
        while queue:
            step_id = queue.popleft()
            order.append(step_id)
            
            for neighbor in graph[step_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return order
    
    def _execute_step(self, step: WorkflowStep, step_exec: StepExecution, execution: WorkflowExecution):
        """Execute a single step."""
        import time
        
        step_exec.status = StepStatus.RUNNING
        step_exec.started_at = time.time()
        self.state_manager.save(execution)
        
        try:
            # Execute step handler
            result = step.handler(execution.context, execution.user_inputs)
            
            # Validate result if validation handler provided
            if step.validation_handler:
                if not step.validation_handler(result, execution.context):
                    raise ValueError("Step validation failed")
            
            step_exec.status = StepStatus.COMPLETED
            step_exec.completed_at = time.time()
            step_exec.output = str(result) if result else None
            
            # Update shared context
            if isinstance(result, dict):
                execution.context.update(result)
            
        except Exception as e:
            step_exec.status = StepStatus.FAILED
            step_exec.error = str(e)
            step_exec.completed_at = time.time()
            
            # Attempt rollback if provided
            if step.rollback_handler:
                try:
                    step.rollback_handler(execution.context)
                except Exception as rollback_error:
                    step_exec.metadata['rollback_error'] = str(rollback_error)
```

## State Manager

```python
class StateManager:
    """Manage workflow execution state persistence."""
    
    def __init__(self, root: str):
        self.root = root
        self.state_dir = self._get_state_dir()
    
    def _get_state_dir(self) -> str:
        """Get state directory path."""
        from cipkg.base import data_dir
        import os
        
        state_dir = os.path.join(data_dir(self.root), "workflow_states")
        os.makedirs(state_dir, exist_ok=True)
        return state_dir
    
    def save(self, execution: WorkflowExecution):
        """Save workflow execution state."""
        import json
        import os
        
        workflow_dir = os.path.join(self.state_dir, execution.workflow_id)
        os.makedirs(workflow_dir, exist_ok=True)
        
        state_file = os.path.join(workflow_dir, f"{execution.execution_id}.json")
        
        # Convert to serializable format
        state = {
            'workflow_id': execution.workflow_id,
            'execution_id': execution.execution_id,
            'status': execution.status.value,
            'steps': {
                step_id: {
                    'step_id': step_exec.step_id,
                    'status': step_exec.status.value,
                    'started_at': step_exec.started_at,
                    'completed_at': step_exec.completed_at,
                    'output': step_exec.output,
                    'error': step_exec.error,
                    'retry_count': step_exec.retry_count,
                    'metadata': step_exec.metadata
                }
                for step_id, step_exec in execution.steps.items()
            },
            'started_at': execution.started_at,
            'completed_at': execution.completed_at,
            'context': execution.context,
            'user_inputs': execution.user_inputs,
            'metadata': execution.metadata
        }
        
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def load(self, workflow_id: str, execution_id: str) -> Optional[WorkflowExecution]:
        """Load workflow execution state."""
        import json
        import os
        
        state_file = os.path.join(self.state_dir, workflow_id, f"{execution_id}.json")
        
        if not os.path.exists(state_file):
            return None
        
        with open(state_file, 'r') as f:
            state = json.load(f)
        
        # Reconstruct execution object
        steps = {}
        for step_id, step_data in state['steps'].items():
            steps[step_id] = StepExecution(
                step_id=step_data['step_id'],
                status=StepStatus(step_data['status']),
                started_at=step_data['started_at'],
                completed_at=step_data['completed_at'],
                output=step_data['output'],
                error=step_data['error'],
                retry_count=step_data['retry_count'],
                metadata=step_data['metadata']
            )
        
        return WorkflowExecution(
            workflow_id=state['workflow_id'],
            execution_id=state['execution_id'],
            status=WorkflowStatus(state['status']),
            steps=steps,
            started_at=state['started_at'],
            completed_at=state['completed_at'],
            context=state['context'],
            user_inputs=state['user_inputs'],
            metadata=state['metadata']
        )
    
    def load_latest(self, workflow_id: str) -> Optional[WorkflowExecution]:
        """Load the most recent execution for a workflow."""
        import os
        import glob
        
        workflow_dir = os.path.join(self.state_dir, workflow_id)
        if not os.path.exists(workflow_dir):
            return None
        
        # Get all state files sorted by modification time
        state_files = glob.glob(os.path.join(workflow_dir, "*.json"))
        state_files.sort(key=os.path.getmtime, reverse=True)
        
        if not state_files:
            return None
        
        # Extract execution_id from filename
        latest_file = state_files[0]
        execution_id = os.path.basename(latest_file).replace('.json', '')
        
        return self.load(workflow_id, execution_id)
    
    def list_executions(self, workflow_id: str) -> List[str]:
        """List all execution IDs for a workflow."""
        import os
        import glob
        
        workflow_dir = os.path.join(self.state_dir, workflow_id)
        if not os.path.exists(workflow_dir):
            return []
        
        state_files = glob.glob(os.path.join(workflow_dir, "*.json"))
        return [os.path.basename(f).replace('.json', '') for f in state_files]
    
    def cleanup_old_executions(self, workflow_id: str, keep_count: int = 10):
        """Remove old execution states, keeping only the most recent."""
        import os
        import glob
        
        workflow_dir = os.path.join(self.state_dir, workflow_id)
        if not os.path.exists(workflow_dir):
            return
        
        state_files = glob.glob(os.path.join(workflow_dir, "*.json"))
        state_files.sort(key=os.path.getmtime, reverse=True)
        
        # Remove old files
        for old_file in state_files[keep_count:]:
            os.remove(old_file)
```

## Error Handler

```python
class WorkflowExecutionError(Exception):
    """Base exception for workflow execution errors."""
    pass

class ErrorHandler:
    """Handle workflow errors with recovery strategies."""
    
    def __init__(self, executor: WorkflowExecutor):
        self.executor = executor
    
    def handle_error(self, execution: WorkflowExecution, error: Exception):
        """Handle workflow execution error."""
        error_type = type(error).__name__
        
        # Get recovery strategy based on error type
        recovery = self._get_recovery_strategy(error_type)
        
        if recovery:
            return recovery(execution, error)
        else:
            # Default: pause workflow for user intervention
            execution.status = WorkflowStatus.PAUSED
            execution.metadata['pause_reason'] = str(error)
            execution.metadata['pause_error_type'] = error_type
            self.executor.state_manager.save(execution)
            
            return {
                'action': 'pause',
                'message': f'Workflow paused due to error: {str(error)}',
                'suggestion': 'Review the error and resume with --resume flag'
            }
    
    def _get_recovery_strategy(self, error_type: str) -> Optional[Callable]:
        """Get recovery strategy for error type."""
        strategies = {
            'FileNotFoundError': self._recover_file_not_found,
            'PermissionError': self._recover_permission_error,
            'TimeoutError': self._recover_timeout,
            'ValueError': self._recover_value_error
        }
        return strategies.get(error_type)
    
    def _recover_file_not_found(self, execution: WorkflowExecution, error: Exception):
        """Recover from file not found errors."""
        return {
            'action': 'suggest_fix',
            'message': 'Required file not found',
            'suggestion': 'Check file paths and run cip sync to update index'
        }
    
    def _recover_permission_error(self, execution: WorkflowExecution, error: Exception):
        """Recover from permission errors."""
        return {
            'action': 'suggest_fix',
            'message': 'Permission denied',
            'suggestion': 'Check file permissions and try running with appropriate privileges'
        }
```

## UI Adapter

```python
class UIAdapter:
    """Adapt workflow execution to user interface."""
    
    def __init__(self, executor: WorkflowExecutor):
        self.executor = executor
    
    def display_progress(self, execution: WorkflowExecution):
        """Display workflow execution progress."""
        workflow = self.executor.registry.get(execution.workflow_id)
        
        print("╔═══════════════════════════════════════════════════════════════╗")
        print(f"║  {workflow.name}                                              ║")
        print("╠═══════════════════════════════════════════════════════════════╣")
        
        for step in workflow.steps:
            step_exec = execution.steps[step.id]
            status_icon = self._get_status_icon(step_exec.status)
            
            print(f"║  {status_icon} {step.name}")
            if step_exec.status == StepStatus.RUNNING:
                print(f"║     {step.description}...")
            elif step_exec.status == StepStatus.COMPLETED:
                print(f"║     ✓ {step.description}")
            elif step_exec.status == StepStatus.FAILED:
                print(f"║     ✗ {step.description}")
                if step_exec.error:
                    print(f"║     Error: {step_exec.error}")
        
        print("╚═══════════════════════════════════════════════════════════════╝")
    
    def _get_status_icon(self, status: StepStatus) -> str:
        """Get icon for step status."""
        icons = {
            StepStatus.PENDING: '⏳',
            StepStatus.RUNNING: '🔄',
            StepStatus.COMPLETED: '✅',
            StepStatus.FAILED: '❌',
            StepStatus.SKIPPED: '⏭️',
            StepStatus.CANCELLED: '🚫'
        }
        return icons.get(status, '⏳')
    
    def prompt_user(self, step: WorkflowStep, context: Dict) -> Dict:
        """Prompt user for input during workflow execution."""
        print(f"\n{step.name}")
        print(f"{step.description}")
        
        # This would be implemented based on specific step requirements
        user_input = input("Continue? [y/N]: ")
        
        return {'continue': user_input.lower() == 'y'}
```

## CLI Integration

```python
def handle_workflow_command(root, args):
    """Handle workflow command."""
    from cipkg.interactive import WorkflowExecutor
    from cipkg.base import load_config
    
    executor = WorkflowExecutor(root, load_config(root))
    
    if args.list:
        # List available workflows
        workflows = executor.registry.list_all()
        print("Available Workflows:")
        for workflow in workflows:
            print(f"  • {workflow.id}: {workflow.name}")
        return
    
    if args.resume:
        # Resume previous execution
        execution = executor.execute(args.workflow, resume=True)
    else:
        # Start new execution
        execution = executor.execute(args.workflow)
    
    # Display results
    ui_adapter = UIAdapter(executor)
    ui_adapter.display_progress(execution)
```

## Built-in Workflow Implementations

### Pre-commit Workflow Steps

```python
def _step_analyze_changes(self, context: Dict, user_inputs: Dict) -> Dict:
    """Analyze changed files."""
    import subprocess
    
    # Get changed files
    result = subprocess.run(
        ['git', 'diff', '--name-only'],
        cwd=self.root,
        capture_output=True,
        text=True
    )
    
    changed_files = [f for f in result.stdout.split('\n') if f.strip()]
    
    return {
        'changed_files': changed_files,
        'file_count': len(changed_files)
    }

def _step_run_audit(self, context: Dict, user_inputs: Dict) -> Dict:
    """Run audit on changed files."""
    from cipkg import audit
    
    changed_files = context.get('changed_files', [])
    audit_results = []
    
    for file_path in changed_files:
        result = audit.audit_file(self.root, file_path)
        audit_results.append(result)
    
    return {
        'audit_results': audit_results,
        'total_issues': sum(len(r.get('issues', [])) for r in audit_results)
    }

def _step_check_impact(self, context: Dict, user_inputs: Dict) -> Dict:
    """Check impact of changes."""
    from cipkg import impact
    
    changed_files = context.get('changed_files', [])
    impact_results = []
    
    for file_path in changed_files:
        result = impact.analyze(self.root, file_path)
        impact_results.append(result)
    
    return {
        'impact_results': impact_results,
        'high_impact_changes': sum(1 for r in impact_results if r.get('severity') == 'high')
    }
```

## Configuration

### Workflow Configuration

```toml
[workflows]
enabled = true
state_retention_days = 30
max_executions_per_workflow = 10
auto_resume_on_error = false

[workflows.pre_commit]
enabled = true
auto_run_on_git_hooks = true
required_checks = ["audit", "impact", "tests"]
optional_checks = ["lint", "format"]

[workflows.diagnosis]
enabled = true
auto_run_on_health_below = 70
schedule = "weekly"
```

## Testing Strategy

### Unit Tests

```python
def test_workflow_execution_order():
    """Test workflow steps execute in correct order."""
    executor = WorkflowExecutor(test_root, test_config)
    workflow = executor.registry.get("pre-commit")
    
    order = executor._build_execution_order(workflow)
    
    assert order[0] == "analyze_changes"
    assert "generate_report" in order
    assert order.index("analyze_changes") < order.index("run_audit")

def test_workflow_resume():
    """Test workflow resume from saved state."""
    executor = WorkflowExecutor(test_root, test_config)
    
    # Start execution
    execution1 = executor.execute("pre-commit")
    
    # Simulate failure
    execution1.steps["run_audit"].status = StepStatus.FAILED
    executor.state_manager.save(execution1)
    
    # Resume execution
    execution2 = executor.execute("pre-commit", resume=True)
    
    assert execution2.execution_id == execution1.execution_id
```

## Future Enhancements

### Parallel Step Execution

```python
class ParallelWorkflowExecutor(WorkflowExecutor):
    """Execute independent steps in parallel."""
    
    def _execute_workflow(self, workflow, execution):
        """Execute workflow with parallel step execution."""
        # Identify independent step groups
        step_groups = self._identify_parallel_groups(workflow)
        
        for group in step_groups:
            # Execute steps in group in parallel
            self._execute_step_group(group, execution)
```

### Workflow Composition

```python
class ComposableWorkflow:
    """Combine multiple workflows into larger workflows."""
    
    def compose(self, workflow_ids: List[str]) -> WorkflowDefinition:
        """Compose multiple workflows into one."""
        # Combine steps from multiple workflows
        # Handle dependencies across workflows
        # Create unified workflow definition
        pass
```

## Conclusion

The Workflow Execution Engine provides a robust framework for defining and executing complex multi-step operations in CIP CLI v2.0. With features like dependency management, state persistence, error recovery, and resume capability, it enables sophisticated guided workflows that significantly improve user productivity while maintaining reliability and flexibility.

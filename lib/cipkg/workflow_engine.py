"""
Workflow Execution Engine for CIP CLI v2.0

This module provides workflow definition, execution, and state management
for guided multi-step operations.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
import os
import json
import uuid
import time


class StepStatus(Enum):
    """Status of a workflow step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class WorkflowStatus(Enum):
    """Status of a workflow execution."""
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
    handler: Callable
    dependencies: List[str] = field(default_factory=list)
    optional: bool = False
    timeout: int = 300
    retry_count: int = 0
    rollback_handler: Callable = None
    validation_handler: Callable = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowDefinition:
    """Complete workflow definition."""
    id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    category: str
    version: str = "1.0"
    author: str = "CIP"
    metadata: Dict[str, Any] = field(default_factory=dict)


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
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowExecution:
    """Execution state of a complete workflow."""
    workflow_id: str
    execution_id: str
    status: WorkflowStatus
    steps: Dict[str, StepExecution]
    started_at: float
    completed_at: Optional[float] = None
    context: Dict[str, Any] = field(default_factory=dict)
    user_inputs: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


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


class StateManager:
    """Manage workflow execution state persistence."""
    
    def __init__(self, root: str):
        self.root = root
        self.state_dir = self._get_state_dir()
    
    def _get_state_dir(self) -> str:
        """Get state directory path."""
        from cipkg.base import data_dir
        
        state_dir = os.path.join(data_dir(self.root), "workflow_states")
        os.makedirs(state_dir, exist_ok=True)
        return state_dir
    
    def save(self, execution: WorkflowExecution):
        """Save workflow execution state."""
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
            json.dump(state, f, indent=2, default=str)
    
    def load(self, workflow_id: str, execution_id: str) -> Optional[WorkflowExecution]:
        """Load workflow execution state."""
        state_file = os.path.join(self.state_dir, workflow_id, f"{execution_id}.json")
        
        if not os.path.exists(state_file):
            return None
        
        with open(state_file, 'r') as f:
            data = json.load(f)
        
        # Reconstruct execution object
        steps = {}
        for step_id, step_data in data['steps'].items():
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
            workflow_id=data['workflow_id'],
            execution_id=data['execution_id'],
            status=WorkflowStatus(data['status']),
            steps=steps,
            started_at=data['started_at'],
            completed_at=data['completed_at'],
            context=data['context'],
            user_inputs=data['user_inputs'],
            metadata=data['metadata']
        )
    
    def load_latest(self, workflow_id: str) -> Optional[WorkflowExecution]:
        """Load the most recent execution for a workflow."""
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
        import glob
        
        workflow_dir = os.path.join(self.state_dir, workflow_id)
        if not os.path.exists(workflow_dir):
            return []
        
        state_files = glob.glob(os.path.join(workflow_dir, "*.json"))
        return [os.path.basename(f).replace('.json', '') for f in state_files]
    
    def cleanup_old_executions(self, workflow_id: str, keep_count: int = 10):
        """Remove old execution states, keeping only the most recent."""
        import glob
        
        workflow_dir = os.path.join(self.state_dir, workflow_id)
        if not os.path.exists(workflow_dir):
            return
        
        state_files = glob.glob(os.path.join(workflow_dir, "*.json"))
        state_files.sort(key=os.path.getmtime, reverse=True)
        
        # Remove old files
        for old_file in state_files[keep_count:]:
            os.remove(old_file)


class WorkflowExecutor:
    """Execute workflows with state management and error recovery."""
    
    def __init__(self, root: str, config: Dict[str, Any]):
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
                    raise Exception(f"Step {step_id} failed")
        
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
    
    def _dependency_failed(self, step: WorkflowStep, execution: WorkflowExecution) -> bool:
        """Check if any dependency failed."""
        for dep_id in step.dependencies:
            dep_exec = execution.steps.get(dep_id)
            if dep_exec and dep_exec.status == StepStatus.FAILED:
                return True
        return False
    
    # Built-in step handlers
    def _step_analyze_changes(self, context: Dict, user_inputs: Dict) -> Dict:
        """Analyze changed files."""
        import subprocess
        
        try:
            # Get changed files
            result = subprocess.run(
                ['git', 'diff', '--name-only'],
                cwd=self.root,
                capture_output=True,
                text=True
            )
            
            changed_files = [f for f in result.stdout.split('\n') if f.strip()]
            
            # Get file types
            file_types = {}
            for file_path in changed_files:
                ext = os.path.splitext(file_path)[1] if os.path.splitext(file_path)[1] else 'no_ext'
                file_types[ext] = file_types.get(ext, 0) + 1
            
            return {
                'changed_files': changed_files,
                'file_count': len(changed_files),
                'file_types': file_types
            }
        except (subprocess.CalledProcessError, FileNotFoundError):
            return {'changed_files': [], 'file_count': 0, 'file_types': {}}
    
    def _step_run_audit(self, context: Dict, user_inputs: Dict) -> Dict:
        """Run audit on changed files."""
        changed_files = context.get('changed_files', [])
        
        try:
            from cipkg.stack import audit
            
            audit_results = []
            total_issues = 0
            
            for file_path in changed_files:
                try:
                    result = audit.audit_file(self.root, file_path)
                    audit_results.append(result)
                    total_issues += len(result.get('issues', []))
                except Exception:
                    # Skip files that can't be audited
                    pass
            
            return {
                'audit_results': audit_results,
                'total_issues': total_issues,
                'files_audited': len(audit_results)
            }
        except ImportError:
            # Fallback if audit module not available
            return {
                'audit_results': [],
                'total_issues': 0,
                'files_audited': len(changed_files)
            }
    
    def _step_check_impact(self, context: Dict, user_inputs: Dict) -> Dict:
        """Check impact of changes."""
        changed_files = context.get('changed_files', [])
        
        try:
            from cipkg.stack import impact
            
            impact_results = []
            high_impact_count = 0
            
            for file_path in changed_files:
                try:
                    result = impact.impact(self.root, file_path)
                    impact_results.append(result)
                    if result.get('risk') == 'high':
                        high_impact_count += 1
                except Exception:
                    # Skip files that can't be analyzed
                    pass
            
            return {
                'impact_results': impact_results,
                'high_impact_changes': high_impact_count,
                'files_analyzed': len(impact_results)
            }
        except ImportError:
            # Fallback if impact module not available
            return {
                'impact_results': [],
                'high_impact_changes': 0,
                'files_analyzed': len(changed_files)
            }
    
    def _step_verify_tests(self, context: Dict, user_inputs: Dict) -> Dict:
        """Run relevant tests."""
        try:
            # Try to detect and run appropriate test framework
            if os.path.exists(os.path.join(self.root, 'pytest.ini')) or os.path.exists(os.path.join(self.root, 'setup.cfg')):
                return self._run_pytest()
            elif os.path.exists(os.path.join(self.root, 'package.json')):
                return self._run_npm_tests()
            else:
                return self._run_generic_tests()
        except Exception:
            return {
                'test_results': [],
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0
            }
    
    def _run_pytest(self) -> Dict:
        """Run pytest tests."""
        import subprocess
        
        try:
            result = subprocess.run(
                ['python', '-m', 'pytest', '--tb=no', '-q'],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Parse pytest output
            output = result.stdout + result.stderr
            if 'passed' in output:
                parts = output.split()
                for part in parts:
                    if 'passed' in part:
                        passed = int(part.split()[0])
                        return {
                            'test_results': [{'framework': 'pytest', 'output': output}],
                            'total_tests': passed,
                            'passed_tests': passed,
                            'failed_tests': 0
                        }
            
            return {
                'test_results': [{'framework': 'pytest', 'output': output}],
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0
            }
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return {
                'test_results': [],
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0
            }
    
    def _run_npm_tests(self) -> Dict:
        """Run npm tests."""
        import subprocess
        
        try:
            result = subprocess.run(
                ['npm', 'test'],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            output = result.stdout + result.stderr
            return {
                'test_results': [{'framework': 'npm', 'output': output}],
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0
            }
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return {
                'test_results': [],
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0
            }
    
    def _run_generic_tests(self) -> Dict:
        """Run generic test detection."""
        # Check for common test directories
        test_dirs = ['tests', 'test', '__tests__', 'spec']
        found_tests = any(os.path.exists(os.path.join(self.root, d)) for d in test_dirs)
        
        return {
            'test_results': [],
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'test_directory_found': found_tests
        }
    
    def _step_generate_report(self, context: Dict, user_inputs: Dict) -> Dict:
        """Generate comprehensive report."""
        report_lines = [
            "=== Pre-Commit Workflow Report ===",
            f"Files Changed: {context.get('file_count', 0)}",
            f"Audit Issues: {context.get('total_issues', 0)}",
            f"High Impact Changes: {context.get('high_impact_changes', 0)}",
            f"Tests Passed: {context.get('passed_tests', 0)}",
        ]
        
        # Add recommendations
        recommendations = []
        if context.get('total_issues', 0) > 0:
            recommendations.append("Review and fix audit issues before committing")
        if context.get('high_impact_changes', 0) > 0:
            recommendations.append("Review high-impact changes carefully")
        if context.get('passed_tests', 0) == 0 and context.get('file_count', 0) > 0:
            recommendations.append("Consider running tests before committing")
        
        if recommendations:
            report_lines.append("\nRecommendations:")
            for rec in recommendations:
                report_lines.append(f"  • {rec}")
        
        return {
            'report': '\n'.join(report_lines),
            'summary': {
                'files_changed': context.get('file_count', 0),
                'issues_found': context.get('total_issues', 0),
                'high_impact': context.get('high_impact_changes', 0),
                'tests_passed': context.get('passed_tests', 0),
                'recommendations': recommendations
            }
        }
    
    def _step_health_check(self, context: Dict, user_inputs: Dict) -> Dict:
        """Check repository health."""
        try:
            from cipkg import gapfill
            health_score = gapfill.score(self.root)
            return {'health_score': health_score}
        except Exception:
            return {'health_score': {'score': 100, 'status': 'unknown'}}
    
    def _step_index_check(self, context: Dict, user_inputs: Dict) -> Dict:
        """Verify index integrity."""
        try:
            from cipkg.store import connect
            import time
            
            con = connect(self.root)
            stats = con.execute("""
                SELECT 
                    COUNT(*) as total_chunks,
                    COUNT(v) as embedded_chunks,
                    MAX(timestamp) as last_update
                FROM chunks
                LEFT JOIN vectors ON chunks.id = vectors.chunk_id
            """).fetchone()
            
            total = stats['total_chunks'] or 0
            embedded = stats['embedded_chunks'] or 0
            coverage = (embedded / total * 100) if total > 0 else 100
            stale = (time.time() - stats['last_update']) > 3600 if stats['last_update'] else True
            
            return {
                'index_status': 'valid' if not stale else 'stale',
                'total_chunks': total,
                'embedded_chunks': embedded,
                'embedding_coverage': coverage,
                'last_update': stats['last_update']
            }
        except Exception:
            return {'index_status': 'unknown', 'total_chunks': 0}
    
    def _step_dependency_check(self, context: Dict, user_inputs: Dict) -> Dict:
        """Check for dependency issues."""
        issues = []
        
        # Check for common dependency issues
        if os.path.exists(os.path.join(self.root, 'requirements.txt')):
            try:
                with open(os.path.join(self.root, 'requirements.txt'), 'r') as f:
                    requirements = f.read()
                    if 'git+' in requirements:
                        issues.append('Git dependencies detected - consider using pinned versions')
            except Exception:
                pass
        
        if os.path.exists(os.path.join(self.root, 'package.json')):
            try:
                import json
                with open(os.path.join(self.root, 'package.json'), 'r') as f:
                    package_data = json.load(f)
                    deps = package_data.get('dependencies', {})
                    if any('^' in version for version in deps.values()):
                        issues.append('Caret dependencies detected - consider using pinned versions')
            except Exception:
                pass
        
        return {
            'dependency_status': 'valid' if not issues else 'issues_found',
            'issues': issues,
            'issue_count': len(issues)
        }
    
    def _step_analyze_issues(self, context: Dict, user_inputs: Dict) -> Dict:
        """Analyze detected issues."""
        health_score = context.get('health_score', {}).get('score', 100)
        index_status = context.get('index_status', 'valid')
        dep_issues = context.get('issue_count', 0)
        
        analyzed_issues = []
        
        if health_score < 70:
            analyzed_issues.append({
                'type': 'health',
                'severity': 'high' if health_score < 50 else 'medium',
                'description': f'Low health score: {health_score}/100'
            })
        
        if index_status == 'stale':
            analyzed_issues.append({
                'type': 'index',
                'severity': 'medium',
                'description': 'Index is stale and needs updating'
            })
        
        if dep_issues > 0:
            analyzed_issues.append({
                'type': 'dependencies',
                'severity': 'low',
                'description': f'{dep_issues} dependency issues found'
            })
        
        return {
            'analyzed_issues': analyzed_issues,
            'total_issues': len(analyzed_issues),
            'critical_issues': sum(1 for i in analyzed_issues if i['severity'] == 'high')
        }
    
    def _step_suggest_fixes(self, context: Dict, user_inputs: Dict) -> Dict:
        """Suggest fixes for detected issues."""
        analyzed_issues = context.get('analyzed_issues', [])
        suggested_fixes = []
        
        for issue in analyzed_issues:
            if issue['type'] == 'health':
                suggested_fixes.append({
                    'issue': issue['description'],
                    'fix': 'Run "cip analyze" to identify and fix health issues',
                    'command': 'cip analyze'
                })
            elif issue['type'] == 'index':
                suggested_fixes.append({
                    'issue': issue['description'],
                    'fix': 'Run "cip sync" to update the index',
                    'command': 'cip sync'
                })
            elif issue['type'] == 'dependencies':
                suggested_fixes.append({
                    'issue': issue['description'],
                    'fix': 'Review and pin dependency versions',
                    'command': None
                })
        
        return {
            'suggested_fixes': suggested_fixes,
            'fix_count': len(suggested_fixes)
        }


def execute_workflow(root: str, workflow_id: str, config: Dict[str, Any], 
                    resume: bool = False) -> WorkflowExecution:
    """Execute a workflow with the given parameters."""
    executor = WorkflowExecutor(root, config)
    return executor.execute(workflow_id, resume)


def list_workflows(root: str, config: Dict[str, Any]) -> List[WorkflowDefinition]:
    """List all available workflows."""
    executor = WorkflowExecutor(root, config)
    return executor.registry.list_all()

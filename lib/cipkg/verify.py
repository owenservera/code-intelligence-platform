"""Verification gate: combines broken tests, typecheck, lint, and audit findings.
Provides mandatory completion check for agent tasks."""
import os, subprocess
from .base import repo_root, load_config
from .store import connect
from .runtime_adapters import broken
from .stack import audit as stack_audit

def verify(root=None, typecheck=False, lint=False, audit_check=True):
    """Run comprehensive verification checks.
    
    Returns verification result with:
    - broken_tests: failing tests and type errors
    - typecheck_result: typecheck status if enabled
    - lint_result: lint status if enabled  
    - audit_findings: critical audit findings
    - can_proceed: whether all checks pass
    """
    root = root or repo_root()
    cfg = load_config(root)
    
    result = {
        "broken_tests": {},
        "typecheck_result": None,
        "lint_result": None,
        "audit_findings": [],
        "can_proceed": True,
        "blocked_by": []
    }
    
    # Check broken tests and type errors
    try:
        broken_result = broken(root)
        result["broken_tests"] = broken_result
        
        if broken_result.get("files") or broken_result.get("errors", 0) > 0:
            result["can_proceed"] = False
            result["blocked_by"].append("broken_tests")
    except Exception as e:
        result["broken_tests"] = {"error": str(e)}
    
    # Run typecheck if requested
    if typecheck:
        try:
            typecheck_result = _run_typecheck(root)
            result["typecheck_result"] = typecheck_result
            
            if typecheck_result.get("has_errors"):
                result["can_proceed"] = False
                result["blocked_by"].append("typecheck")
        except Exception as e:
            result["typecheck_result"] = {"error": str(e)}
    
    # Run lint if requested
    if lint:
        try:
            lint_result = _run_lint(root)
            result["lint_result"] = lint_result
            
            if lint_result.get("has_errors"):
                result["can_proceed"] = False
                result["blocked_by"].append("lint")
        except Exception as e:
            result["lint_result"] = {"error": str(e)}
    
    # Check critical audit findings
    if audit_check:
        try:
            critical_findings = stack_audit.findings(root, severity="critical", limit=10)
            result["audit_findings"] = critical_findings
            
            if critical_findings:
                result["can_proceed"] = False
                result["blocked_by"].append("critical_findings")
        except Exception as e:
            result["audit_findings"] = {"error": str(e)}
    
    return result

def _run_typecheck(root):
    """Run typecheck (tsc for TypeScript projects)."""
    # Detect TypeScript project
    if os.path.exists(os.path.join(root, "tsconfig.json")):
        try:
            result = subprocess.run(
                ["npx", "tsc", "--noEmit"],
                capture_output=True,
                text=True,
                cwd=root,
                timeout=60
            )
            return {
                "has_errors": result.returncode != 0,
                "error_count": result.stdout.count("error") if result.stdout else 0,
                "output": result.stdout[-2000:] if result.stdout else ""
            }
        except Exception as e:
            return {"error": str(e), "has_errors": False}
    
    return {"has_errors": False, "message": "No TypeScript project detected"}

def _run_lint(root):
    """Run lint (eslint for JS/TS projects)."""
    # Detect ESLint
    if os.path.exists(os.path.join(root, "package.json")):
        try:
            result = subprocess.run(
                ["npx", "eslint", ".", "--format", "json"],
                capture_output=True,
                text=True,
                cwd=root,
                timeout=60
            )
            return {
                "has_errors": result.returncode != 0,
                "output": result.stdout[-2000:] if result.stdout else ""
            }
        except Exception as e:
            return {"error": str(e), "has_errors": False}
    
    return {"has_errors": False, "message": "No ESLint detected"}

def verification_gate(root=None, blocking=True):
    """Run verification and optionally block if checks fail.
    
    If blocking=True, returns exit code 1 if verification fails.
    Always returns verification result regardless of blocking.
    """
    result = verify(root)
    
    if blocking and not result["can_proceed"]:
        print("VERIFICATION FAILED - Task cannot proceed:")
        for blocker in result["blocked_by"]:
            print(f"  - {blocker}")
        return 1
    
    return result
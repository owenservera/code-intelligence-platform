"""Agent integration hooks: post-edit, pre-edit, session management.
Enables CIP to automatically fire on file operations without explicit agent calls."""
import os, json, subprocess
from .base import repo_root, load_config
from .store import connect
from .stack import audit as stack_audit, impact as stack_impact

def post_edit_hook(file_path, root=None):
    """Post-edit hook: runs impact analysis and file-scoped audit after edits.
    
    Returns structured results that can be injected back into agent context.
    """
    root = root or repo_root()
    
    if not os.path.exists(os.path.join(root, file_path)):
        return {"ok": False, "error": f"File not found: {file_path}"}
    
    try:
        # Run impact analysis for the edited file
        impact_result = stack_impact.impact(root, target=file_path, depth=2)
        
        # Run file-scoped audit
        audit_result = stack_audit.findings(root, path=file_path, limit=10)
        
        return {
            "ok": True,
            "file": file_path,
            "impact": {
                "callers": len(impact_result.get("callers", [])),
                " callees": len(impact_result.get("callees", [])),
                "risk_score": impact_result.get("risk_score", 0),
                "summary": impact_result.get("summary", "")
            },
            "audit": {
                "findings_count": len(audit_result),
                "has_critical": any(f.get("severity") == "critical" for f in audit_result),
                "findings": audit_result[:3]  # Top 3 findings
            }
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

def pre_edit_hook(file_path, diff_content, root=None):
    """Pre-edit hook: validates proposed changes against audit rules.
    
    Returns warnings if the edit would introduce flagged patterns.
    Non-blocking by design - warnings are informational, not hard blocks.
    """
    root = root or repo_root()
    
    warnings = []
    
    # Check for known rule violations in the diff
    rule_patterns = {
        "SEC-HARDCODED-SECRET": [
            r"sk_live_[A-Za-z0-9]{10,}",
            r"AKIA[0-9A-Z]{16}",
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----"
        ],
        "DB-NO-AWAIT": [
            r"prisma\.\w+\.(findMany|findFirst|create|update|delete)\([^)]*\)(?!\s*\.)"
        ],
        "QA-CONSOLE": [
            r"console\.log"
        ]
    }
    
    for rule_id, patterns in rule_patterns.items():
        import re
        for pattern in patterns:
            if re.search(pattern, diff_content):
                warnings.append({
                    "rule": rule_id,
                    "pattern_matched": pattern,
                    "suggestion": f"Review before committing: {rule_id} pattern detected"
                })
    
    # Check Tauri-specific rules if applicable
    tauri_dir = os.path.join(root, "src-tauri")
    if os.path.isdir(tauri_dir) and file_path.startswith("src-tauri"):
        # Check for ungated command patterns
        if re.search(r"#\[tauri::command\]", diff_content):
            warnings.append({
                "rule": "TAURI-UNGATED-COMMAND",
                "pattern_matched": "#[tauri::command]",
                "suggestion": "Ensure new Tauri commands have capability grants"
            })
    
    return {
        "ok": True,
        "file": file_path,
        "warnings": warnings,
        "proceed": True  # Always allow, warnings are informational
    }

def install_agent_hooks(root, agent_type="claude-code"):
    """Install hook configuration files for specific agent types."""
    hooks_dir = os.path.join(root, ".cip", "hooks")
    os.makedirs(hooks_dir, exist_ok=True)
    
    if agent_type == "claude-code":
        hook_config = {
            "version": "1.0",
            "hooks": {
                "PostToolUse": {
                    "Edit": {
                        "command": "cip",
                        "args": ["hook", "post-edit", "{file}"],
                        "inject_result": True
                    },
                    "Write": {
                        "command": "cip", 
                        "args": ["hook", "post-edit", "{file}"],
                        "inject_result": True
                    }
                },
                "PreToolUse": {
                    "Edit": {
                        "command": "cip",
                        "args": ["hook", "pre-edit", "{file}", "{diff}"],
                        "inject_result": True,
                        "blocking": False
                    }
                }
            }
        }
    elif agent_type == "opencode":
        hook_config = {
            "version": "1.0", 
            "hooks": {
                "on_edit_complete": {
                    "command": "cip",
                    "args": ["hook", "post-edit", "{file}"],
                    "context_injection": "tool_result"
                },
                "before_edit": {
                    "command": "cip",
                    "args": ["hook", "pre-edit", "{file}", "{diff}"],
                    "context_injection": "warning",
                    "blocking": False
                }
            }
        }
    else:
        return {"ok": False, "error": f"Unknown agent type: {agent_type}"}
    
    config_path = os.path.join(hooks_dir, f"{agent_type}.json")
    with open(config_path, 'w') as f:
        json.dump(hook_config, f, indent=2)
    
    return {"ok": True, "config_path": config_path}

def run_hook_command(args):
    """CLI entry point for running hooks."""
    if len(args) < 2:
        return {"ok": False, "error": "Usage: cip hook <type> <args...>"}
    
    hook_type = args[0]
    hook_args = args[1:]
    
    if hook_type == "post-edit":
        if not hook_args:
            return {"ok": False, "error": "post-edit requires file path"}
        return post_edit_hook(hook_args[0])
    
    elif hook_type == "pre-edit":
        if len(hook_args) < 2:
            return {"ok": False, "error": "pre-edit requires file path and diff content"}
        file_path, diff_content = hook_args[0], hook_args[1]
        return pre_edit_hook(file_path, diff_content)
    
    else:
        return {"ok": False, "error": f"Unknown hook type: {hook_type}"}
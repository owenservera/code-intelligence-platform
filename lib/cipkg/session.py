"""Session management for agent integration: standing context, session lifecycle.
Provides budget-capped repo context packets and session-end learning loops."""
import os, json, time
from .base import repo_root, load_config
from .store import connect
from . import summarize, gitindex, retrieve
from .stack import audit as stack_audit
from .verify import verify

def session_start(root=None):
    """Initialize session with compact repo context packet.
    
    Returns budget-capped context including:
    - Architecture map and subsystem overview
    - Currently broken tests
    - Recently co-changed files (hotspots)
    - High-severity open audit findings
    """
    root = root or repo_root()
    cfg = load_config(root)
    con = connect(root)
    
    session_data = {
        "session_id": int(time.time()),
        "start_time": time.time(),
        "root": root,
        "architecture": {},
        "broken_tests": [],
        "hotspots": [],
        "critical_findings": [],
        "context_budget": int(cfg.get("retrieval", {}).get("context_budget_tokens", 6000))
    }
    
    # Architecture map
    try:
        arch_map = summarize.map_(root)
        session_data["architecture"] = {
            "subsystems": len(arch_map.get("subsystems", [])),
            "total_files": arch_map.get("total_files", 0),
            "overview": arch_map.get("overview", "")
        }
    except Exception:
        session_data["architecture"] = {"error": "architecture map unavailable"}
    
    # Broken tests
    try:
        broken = retrieve.runtime_adapters.broken(root)
        session_data["broken_tests"] = broken.get("files", [])[:5]
    except Exception:
        session_data["broken_tests"] = []
    
    # Hotspots (recently co-changed files)
    try:
        hotspots = gitindex.hotspots(root, k=10)
        session_data["hotspots"] = hotspots[:10]
    except Exception:
        session_data["hotspots"] = []
    
    # Critical findings
    try:
        critical_findings = stack_audit.findings(root, severity="critical", limit=5)
        session_data["critical_findings"] = [
            {
                "rule": f.get("rule"),
                "path": f.get("path"),
                "title": f.get("title")
            }
            for f in critical_findings
        ]
    except Exception:
        session_data["critical_findings"] = []
    
    # Save session state
    session_file = os.path.join(root, ".cip", "session.json")
    os.makedirs(os.path.dirname(session_file), exist_ok=True)
    with open(session_file, 'w') as f:
        json.dump(session_data, f, indent=2)
    
    return session_data

def session_end(root=None, session_id=None):
    """End session with learning loop data collection and verification gate.
    
    Logs session summary for learning loop integration:
    - Files edited during session
    - Audit findings delta
    - Test results changes
    - Verification gate results
    """
    root = root or repo_root()
    
    session_file = os.path.join(root, ".cip", "session.json")
    if not os.path.exists(session_file):
        return {"error": "No active session found"}
    
    with open(session_file, 'r') as f:
        session_data = json.load(f)
    
    session_data["end_time"] = time.time()
    session_data["duration_seconds"] = time.time() - session_data["start_time"]
    
    # Run verification gate before session end
    verification_result = verify(root, typecheck=False, lint=False, audit_check=True)
    session_data["verification"] = verification_result
    
    # Collect learning data
    learning_data = {
        "session_id": session_data["session_id"],
        "duration": session_data["duration_seconds"],
        "files_edited": _collect_edited_files(root, session_data["start_time"]),
        "audit_delta": _collect_audit_delta(root),
        "test_delta": _collect_test_delta(root),
        "verification_passed": verification_result["can_proceed"]
    }
    
    session_data["learning"] = learning_data
    
    # Save final session state
    with open(session_file, 'w') as f:
        json.dump(session_data, f, indent=2)
    
    # Archive session for learning loop
    learning_dir = os.path.join(root, ".cip", "data", "learning")
    os.makedirs(learning_dir, exist_ok=True)
    archive_file = os.path.join(learning_dir, f"session_{session_data['session_id']}.json")
    
    with open(archive_file, 'w') as f:
        json.dump(session_data, f, indent=2)
    
    # Clean up active session
    os.remove(session_file)
    
    return {
        "session_id": session_data["session_id"],
        "duration": session_data["duration_seconds"],
        "files_edited": len(learning_data["files_edited"]),
        "audit_delta": learning_data["audit_delta"],
        "verification_passed": verification_result["can_proceed"],
        "blocked_by": verification_result.get("blocked_by", []),
        "archived": archive_file
    }

def _collect_edited_files(root, session_start_time):
    """Collect files edited during session via git log."""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"--since={session_start_time}"],
            capture_output=True,
            text=True,
            cwd=root
        )
        return [f.strip() for f in result.stdout.split('\n') if f.strip()]
    except Exception:
        return []

def _collect_audit_delta(root):
    """Collect audit findings delta during session."""
    try:
        current_findings = stack_audit.findings(root, limit=1000)
        return {
            "total": len(current_findings),
            "critical": len([f for f in current_findings if f.get("severity") == "critical"]),
            "high": len([f for f in current_findings if f.get("severity") == "high"])
        }
    except Exception:
        return {"error": "audit delta collection failed"}

def _collect_test_delta(root):
    """Collect test results delta during session."""
    try:
        broken = retrieve.runtime_adapters.broken(root)
        return {
            "failing_tests": len(broken.get("files", [])),
            "test_errors": broken.get("errors", 0)
        }
    except Exception:
        return {"error": "test delta collection failed"}

def get_active_session(root=None):
    """Get current active session data if exists."""
    root = root or repo_root()
    session_file = os.path.join(root, ".cip", "session.json")
    
    if not os.path.exists(session_file):
        return None
    
    with open(session_file, 'r') as f:
        return json.load(f)
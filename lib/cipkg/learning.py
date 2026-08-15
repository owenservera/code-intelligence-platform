"""Learning loop: feed agent-caused audit deltas back into prediction model.
Analyzes session data to improve routing confidence and detect agent-specific patterns."""
import os, json, time
from collections import defaultdict, Counter
from .base import repo_root, load_config
from .store import connect

def analyze_sessions(root=None, limit=50):
    """Analyze recent sessions to identify patterns and learning signals.
    
    Returns:
    - agent_patterns: Failure patterns by agent type
    - audit_drift: Findings that appear after agent edits
    - prediction_improvements: Routing confidence adjustments
    """
    root = root or repo_root()
    learning_dir = os.path.join(root, ".cip", "data", "learning")
    
    if not os.path.exists(learning_dir):
        return {"error": "No learning data available yet - run sessions first"}
    
    # Load recent session files
    session_files = []
    for filename in os.listdir(learning_dir):
        if filename.startswith("session_") and filename.endswith(".json"):
            session_files.append(os.path.join(learning_dir, filename))
    
    # Sort by session ID (timestamp) and take most recent
    session_files.sort(reverse=True)
    session_files = session_files[:limit]
    
    if not session_files:
        return {"error": "No session files found"}
    
    # Analyze patterns across sessions
    agent_patterns = defaultdict(lambda: {
        "total_sessions": 0,
        "files_edited": 0,
        "verification_passed": 0,
        "verification_failed": 0,
        "common_failures": Counter(),
        "blocked_by": Counter()
    })
    
    audit_drift = Counter()
    file_failure_rates = defaultdict(lambda: {"edits": 0, "failures": 0})
    
    for session_file in session_files:
        try:
            with open(session_file, 'r') as f:
                session = json.load(f)
        except Exception:
            continue
        
        # Count agent patterns (placeholder - would need agent type in session data)
        agent_type = "unknown"  # TODO: Add agent type to session metadata
        agent_patterns[agent_type]["total_sessions"] += 1
        
        learning = session.get("learning", {})
        files_edited = learning.get("files_edited", [])
        agent_patterns[agent_type]["files_edited"] += len(files_edited)
        
        # Track verification results
        verification_passed = learning.get("verification_passed", False)
        if verification_passed:
            agent_patterns[agent_type]["verification_passed"] += 1
        else:
            agent_patterns[agent_type]["verification_failed"] += 1
            
            # Track what blocked verification
            blocked_by = session.get("verification", {}).get("blocked_by", [])
            for blocker in blocked_by:
                agent_patterns[agent_type]["blocked_by"][blocker] += 1
        
        # Track audit findings drift
        audit_delta = learning.get("audit_delta", {})
        critical_count = audit_delta.get("critical", 0)
        high_count = audit_delta.get("high", 0)
        
        if critical_count > 0:
            audit_drift["critical_findings_introduced"] += critical_count
        if high_count > 0:
            audit_drift["high_findings_introduced"] += high_count
        
        # Track file-specific failure rates
        for file_path in files_edited:
            file_failure_rates[file_path]["edits"] += 1
            if not verification_passed:
                file_failure_rates[file_path]["failures"] += 1
    
    # Calculate failure rates for files
    risky_files = []
    for file_path, stats in file_failure_rates.items():
        if stats["edits"] >= 2:  # Only consider files edited multiple times
            failure_rate = stats["failures"] / stats["edits"]
            if failure_rate > 0.5:  # More than 50% failure rate
                risky_files.append({
                    "file": file_path,
                    "edits": stats["edits"],
                    "failures": stats["failures"],
                    "failure_rate": round(failure_rate * 100, 1)
                })
    
    # Sort by failure rate
    risky_files.sort(key=lambda x: x["failure_rate"], reverse=True)
    
    return {
        "sessions_analyzed": len(session_files),
        "agent_patterns": dict(agent_patterns),
        "audit_drift": dict(audit_drift),
        "risky_files": risky_files[:20]
    }

def update_prediction_confidence(root=None):
    """Update prediction model confidence based on learning data.
    
    Adjusts routing confidence scores based on historical success rates.
    """
    analysis = analyze_sessions(root)
    
    if "error" in analysis:
        return analysis
    
    # Extract patterns for confidence adjustments
    confidence_adjustments = {}
    
    # Reduce confidence for operations that frequently fail verification
    blocked_by = analysis["agent_patterns"].get("unknown", {}).get("blocked_by", Counter())
    for blocker, count in blocked_by.items():
        if blocker == "broken_tests":
            confidence_adjustments["test_operations"] = -0.1
        elif blocker == "critical_findings":
            confidence_adjustments["audit_operations"] = -0.15
        elif blocker == "typecheck":
            confidence_adjustments["schema_operations"] = -0.1
    
    # Increase confidence for successful patterns
    verification_rate = 0
    total_sessions = analysis["agent_patterns"].get("unknown", {}).get("total_sessions", 0)
    passed = analysis["agent_patterns"].get("unknown", {}).get("verification_passed", 0)
    
    if total_sessions > 0:
        verification_rate = passed / total_sessions
    
    if verification_rate > 0.8:
        confidence_adjustments["baseline_confidence"] = 0.05
    
    # Save confidence adjustments
    confidence_file = os.path.join(root, ".cip", "data", "learning", "confidence_adjustments.json")
    os.makedirs(os.path.dirname(confidence_file), exist_ok=True)
    
    with open(confidence_file, 'w') as f:
        json.dump({
            "updated_at": time.time(),
            "verification_rate": round(verification_rate * 100, 1),
            "adjustments": confidence_adjustments
        }, f, indent=2)
    
    return {
        "updated": True,
        "verification_rate": round(verification_rate * 100, 1),
        "confidence_adjustments": confidence_adjustments,
        "saved_to": confidence_file
    }

def detect_agent_patterns(root=None):
    """Detect patterns specific to different agent types.
    
    Currently placeholder - would need agent type tracking in sessions.
    Future: Detect Claude Code vs opencode vs other agent patterns.
    """
    analysis = analyze_sessions(root)
    
    if "error" in analysis:
        return analysis
    
    # Placeholder for agent-specific pattern detection
    # In future, would look for:
    # - Claude Code: tends to create many small edits, good at context
    # - opencode: tends to batch edits, good at refactoring
    # - Other agents: specific patterns
    
    return {
        "note": "Agent-specific pattern detection requires agent type tracking in sessions",
        "sessions_analyzed": analysis["sessions_analyzed"],
        "recommendation": "Add agent_type field to session metadata for granular analysis"
    }

def apply_learning_to_predictions(root=None, query="", current_predictions=None):
    """Apply learned confidence adjustments to current predictions.
    
    Modifies prediction confidence scores based on historical success rates.
    """
    if not current_predictions:
        return current_predictions
    
    confidence_file = os.path.join(root, ".cip", "data", "learning", "confidence_adjustments.json")
    
    if not os.path.exists(confidence_file):
        return current_predictions
    
    try:
        with open(confidence_file, 'r') as f:
            adjustments = json.load(f)
    except Exception:
        return current_predictions
    
    adjustments_dict = adjustments.get("adjustments", {})
    
    # Apply adjustments to predictions
    adjusted_predictions = []
    for pred in current_predictions:
        tool = pred.get("tool", "")
        confidence = pred.get("confidence", 0.5)
        
        # Apply specific adjustments
        if "test" in tool and "test_operations" in adjustments_dict:
            confidence += adjustments_dict["test_operations"]
        elif "audit" in tool and "audit_operations" in adjustments_dict:
            confidence += adjustments_dict["audit_operations"]
        elif "schema" in tool and "schema_operations" in adjustments_dict:
            confidence += adjustments_dict["schema_operations"]
        
        # Apply baseline adjustment
        if "baseline_confidence" in adjustments_dict:
            confidence += adjustments_dict["baseline_confidence"]
        
        # Clamp confidence to valid range
        confidence = max(0.0, min(1.0, confidence))
        
        pred["confidence"] = round(confidence, 2)
        pred["confidence_adjusted"] = True
        adjusted_predictions.append(pred)
    
    return adjusted_predictions

def generate_learning_report(root=None):
    """Generate a comprehensive learning report.
    
    Returns actionable insights from session analysis.
    """
    analysis = analyze_sessions(root)
    
    if "error" in analysis:
        return analysis
    
    confidence_update = update_prediction_confidence(root)
    
    report = {
        "generated_at": time.time(),
        "summary": {
            "sessions_analyzed": analysis["sessions_analyzed"],
            "verification_rate": confidence_update.get("verification_rate", 0)
        },
        "findings": {
            "risky_files": analysis.get("risky_files", [])[:10],
            "audit_drift": analysis.get("audit_drift", {}),
            "blocked_patterns": analysis["agent_patterns"].get("unknown", {}).get("blocked_by", {})
        },
        "recommendations": [],
        "confidence_adjustments": confidence_update.get("confidence_adjustments", {})
    }
    
    # Generate recommendations
    risky_files = analysis.get("risky_files", [])
    if risky_files:
        report["recommendations"].append(
            f"Files with high failure rate: {len(risky_files)}. Consider adding tests or reviewing changes."
        )
    
    audit_drift = analysis.get("audit_drift", {})
    if audit_drift.get("critical_findings_introduced", 0) > 0:
        report["recommendations"].append(
            f"Critical findings introduced in {audit_drift['critical_findings_introduced']} sessions. Review audit rules."
        )
    
    verification_rate = confidence_update.get("verification_rate", 0)
    if verification_rate < 70:
        report["recommendations"].append(
            f"Low verification rate ({verification_rate}%). Consider tightening pre-edit hooks."
        )
    
    return report
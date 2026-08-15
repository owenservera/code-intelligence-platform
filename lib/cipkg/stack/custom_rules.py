"""Custom rule loader for repo-specific audit rules.
Allows projects to define their own architectural invariants without modifying CIP core."""
import os, importlib.util

def load_custom_rules(root, cfg):
    """Load custom rules from .cip/rules.py if present.
    
    This allows repos to define project-specific architectural invariants
    that integrate with CIP's audit system. The rules file should export
    a list of (rule_id, rule_function) tuples matching the RULES format.
    
    Example .cip/rules.py:
        def rule_no_direct_chrome(con, root, cfg):
            # Custom invariant checking
            return []
        
        CUSTOM_RULES = [
            ("NO-DIRECT-CHROME", rule_no_direct_chrome),
        ]
    """
    custom_rules_path = os.path.join(root, ".cip", "rules.py")
    
    if not os.path.exists(custom_rules_path):
        return []
    
    try:
        spec = importlib.util.spec_from_file_location("custom_rules", custom_rules_path)
        if spec is None or spec.loader is None:
            return []
        
        custom_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(custom_module)
        
        if hasattr(custom_module, 'CUSTOM_RULES'):
            return custom_module.CUSTOM_RULES
        
        return []
    except Exception:
        # Don't fail the entire audit if custom rules have errors
        return []

def get_all_rules(root, cfg):
    """Get both built-in and custom rules."""
    from .rules import RULES
    custom_rules = load_custom_rules(root, cfg)
    return RULES + custom_rules
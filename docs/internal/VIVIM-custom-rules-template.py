# .cip/rules.py - Vivim-specific custom rules template
# 
# This file demonstrates how Vivim can integrate its existing architectural
# invariants (from devops/invariants.ts) with CIP's audit system.
# 
# To use: Copy this to .cip/rules.py in the vivim-final repository
# 
# IMPORTANT: Vivim already enforces these invariants via devops/invariants.ts.
# This integration is for reporting consistency, not duplicate enforcement.

import os, re
from lib.cipkg.stack.rules import F
from lib.cipkg.base import is_test_path

def rule_vivim_governor_canon(con, root, cfg):
    """Vivim B1: Governor Canon - CDP transport exclusivity.
    
    This rule integrates with Vivim's existing B1 invariant check.
    ChromeGovernor should be the only direct CDP transport owner.
    """
    # Vivim already enforces this via devops/invariants.ts checkB1_GovernorCanon()
    # This is a reporting integration point, not duplicate enforcement
    
    # If you want to surface B1 violations through CIP audit:
    # 1. Run Vivim's invariant checker
    # 2. Parse the output
    # 3. Convert to CIP finding format
    
    # Example integration (pseudo-code):
    # try:
    #     result = subprocess.run(["bun", "run", "devops", "invariants", "check", "--category", "B"],
    #                          capture_output=True, text=True, cwd=root)
    #     violations = parse_vivim_invariants(result.stdout)
    #     return [convert_to_cip_finding(v) for v in violations if v.id == "B1"]
    # except Exception:
    #     return []
    
    return []

def rule_vivim_store_contract_isolation(con, root, cfg):
    """Vivim B2: Store Contract Isolation.
    
    Engines should depend on storage contracts, not concrete implementations.
    """
    # Integration with Vivim's checkB2_StoreContractIsolation()
    # Similar pattern to above
    
    return []

def rule_vivim_provider_manifest_drift(con, root, cfg):
    """PROVIDER-MANIFEST-DRIFT: Cross-check declared vs implemented capabilities.
    
    Checks seeds/providers/manifests.ts declarations against actual implementations.
    """
    manifests_path = os.path.join(root, "seeds", "providers", "manifests.ts")
    
    if not os.path.exists(manifests_path):
        return []
    
    try:
        with open(manifests_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except OSError:
        return []
    
    # Extract declared capabilities (simplified pattern)
    declared_caps = set(re.findall(r'capability:\s*["\']([^"\']+)["\']', content))
    
    # This would need to check against actual implementations
    # For now, return empty - full implementation would require parsing
    
    return []

# Vivim-specific custom rules
CUSTOM_RULES = [
    # Uncomment these to integrate with Vivim's existing invariant system
    # ("VIVIM-GOVERNOR-CANON", rule_vivim_governor_canon),
    # ("VIVIM-STORE-CONTRACT", rule_vivim_store_contract_isolation),
    ("VIVIM-PROVIDER-DRIFT", rule_vivim_provider_manifest_drift),
]

# Note: These rules are OPTIONAL. Vivim's primary enforcement remains
# via devops/invariants.ts and devops/audit-code/. This integration
# allows CIP to report on the same architectural boundaries.
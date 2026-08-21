# 📄 Master Data Model (L0–LA) Surgical Diffs

This document contains the complete, clean unified diffs for all modified core files in the CIP platform.

---

## 1. `lib/cipkg/store.py`

```diff
--- a/lib/cipkg/store.py
+++ b/lib/cipkg/store.py
@@ -5,3 +5,3 @@
-SCHEMA_VERSION = 4
+SCHEMA_VERSION = 5
 
@@ -118,2 +118,12 @@
     _ensure_tokenizer(con)
+    _ensure_mdm(con)
     con.commit()
     return con
+
+def _ensure_mdm(con):
+    """Ensure MDM L0-LA tables exist and are migrated to v5."""
+    try:
+        from .mdm_schema import init_mdm_schema
+        init_mdm_schema(con)
+    except Exception as e:
+        from .base import log_swallowed
+        log_swallowed("store._ensure_mdm", e)
```

---

## 2. `lib/cipkg/analysis.py`

```diff
--- a/lib/cipkg/analysis.py
+++ b/lib/cipkg/analysis.py
@@ -280,3 +280,17 @@
         })
     
     return recommendations
+
+def mdm_analysis(root=None):
+    """Run full Master Data Model (L0-LA) multi-layer extraction and synthesis."""
+    from .mdm_synthesis import generate_full_mdm_report
+    return generate_full_mdm_report(root)
+
+def mdm_report(root=None, fmt="dict"):
+    """Get formatted Master Data Model report (dict or markdown)."""
+    from .mdm_synthesis import generate_full_mdm_report, format_report_markdown
+    report = generate_full_mdm_report(root)
+    if fmt == "markdown":
+        return format_report_markdown(report)
+    return report
```

---

## 3. `lib/cipkg/cli.py`

```diff
--- a/lib/cipkg/cli.py
+++ b/lib/cipkg/cli.py
@@ -248,2 +248,38 @@
     from .server import serve
     serve(root, getattr(args, 'port', None))
+
+def handle_mdm_scan_command(root, args):
+    """Run full Master Data Model (L0-LA) multi-layer extraction and synthesis."""
+    from .mdm_engine import run_mdm_extraction
+    from .mdm_synthesis import synthesize_la_findings
+    from .store import connect
+    con = connect(root)
+    ext_res = run_mdm_extraction(root)
+    la_res = synthesize_la_findings(con, root)
+    _out({"extraction": ext_res, "synthesized_findings_count": len(la_res)})
+
+def handle_mdm_report_command(root, args):
+    """Generate and display complete Master Data Model executive report."""
+    from .mdm_synthesis import generate_full_mdm_report, format_report_markdown
+    report = generate_full_mdm_report(root)
+    if getattr(args, "markdown", False):
+        print(format_report_markdown(report))
+    else:
+        _out(report)
+
+def handle_mdm_trace_command(root, args):
+    """Display step-by-step explainability trace for a specific finding."""
+    from .mdm_schema import get_explainability_trace
+    from .store import connect
+    con = connect(root)
+    fid = getattr(args, "finding_id", "")
+    trace = get_explainability_trace(con, fid)
+    _out({"finding_id": fid, "trace_steps": trace})
+
+def handle_mdm_gaps_command(root, args):
+    """Scan and list all detected L4 wiring gaps (IPC, events, routes)."""
+    from .mdm_engine import scan_l4_flow_and_wiring
+    from .store import connect
+    con = connect(root)
+    gaps = scan_l4_flow_and_wiring(con, root)
+    _out(gaps)
@@ -770,2 +806,10 @@
     vc = sub.add_parser("vacuum", help="compact DB, prune old events"); vc.add_argument("--days", type=int)
+
+    # Master Data Model (L0-LA) CLI surface
+    sub.add_parser("mdm-scan", help="run complete L0-LA extraction and synthesis")
+    mr = sub.add_parser("mdm-report", help="generate comprehensive MDM executive report")
+    mr.add_argument("--markdown", "-m", action="store_true", help="output report in markdown format")
+    mt = sub.add_parser("mdm-trace", help="display explainability trace for a finding")
+    mt.add_argument("finding_id", help="the finding ID to trace (e.g. LA-GAP-...)")
+    sub.add_parser("mdm-gaps", help="list detected L4 silent wiring gaps and traps")
@@ -838,2 +882,6 @@
         "embed-ping": handle_embed_ping_command,
+        # Master Data Model (L0-LA) commands
+        "mdm-scan": handle_mdm_scan_command,
+        "mdm-report": handle_mdm_report_command,
+        "mdm-trace": handle_mdm_trace_command,
+        "mdm-gaps": handle_mdm_gaps_command,
     }
```

---

## 4. `lib/cipkg/command_registry.py`

```diff
--- a/lib/cipkg/command_registry.py
+++ b/lib/cipkg/command_registry.py
@@ -107,2 +107,5 @@
         self._register_system_commands()
+
+        # Master Data Model Commands
+        self._register_mdm_commands()
@@ -1393,2 +1396,96 @@
             return {'error': f'Failed to handle selftest: {str(e)}'}
+
+    def _register_mdm_commands(self):
+        """Register Master Data Model (L0-LA) commands."""
+        self.register(CommandCard(
+            command="mdm_scan",
+            icon="🧬",
+            label="MDM Full Scan (L0-LA)",
+            description="Run complete L0-LA extraction and synthesis",
+            category=CommandCategory.QUALITY,
+            priority=CommandPriority.HIGH,
+            handler=self._handle_mdm_scan,
+            has_form=False
+        ))
+
+        self.register(CommandCard(
+            command="mdm_report",
+            icon="📊",
+            label="MDM Executive Report",
+            description="Generate comprehensive forensic scorecard and dossier",
+            category=CommandCategory.QUALITY,
+            priority=CommandPriority.HIGH,
+            handler=self._handle_mdm_report,
+            parameters=[
+                CommandParameter("markdown", "bool", "Output in markdown", False, False, flag=True)
+            ],
+            has_form=True
+        ))
+
+        self.register(CommandCard(
+            command="mdm_gaps",
+            icon="🗺️",
+            label="MDM Wiring Gaps",
+            description="Scan silent IPC and event wiring gaps",
+            category=CommandCategory.QUALITY,
+            priority=CommandPriority.HIGH,
+            handler=self._handle_mdm_gaps,
+            has_form=False
+        ))
+
+        self.register(CommandCard(
+            command="mdm_trace",
+            icon="🔍",
+            label="MDM Explainability Trace",
+            description="View step-by-step evidence chain for a finding",
+            category=CommandCategory.QUALITY,
+            priority=CommandPriority.MEDIUM,
+            handler=self._handle_mdm_trace,
+            parameters=[
+                CommandParameter("finding_id", "str", "Finding ID (e.g. LA-GAP-...)", True)
+            ],
+            has_form=True
+        ))
+
+    def _handle_mdm_scan(self, root: str, args: dict) -> dict:
+        """Handle MDM scan."""
+        try:
+            from .mdm_engine import run_mdm_extraction
+            from .mdm_synthesis import synthesize_la_findings
+            from .store import connect
+            con = connect(root)
+            ext = run_mdm_extraction(root)
+            syn = synthesize_la_findings(con, root)
+            return {"extraction": ext, "findings_count": len(syn)}
+        except Exception as e:
+            return {"error": f"Failed to run MDM scan: {str(e)}"}
+
+    def _handle_mdm_report(self, root: str, args: dict) -> dict:
+        """Handle MDM report."""
+        try:
+            from .mdm_synthesis import generate_full_mdm_report
+            return generate_full_mdm_report(root)
+        except Exception as e:
+            return {"error": f"Failed to generate MDM report: {str(e)}"}
+
+    def _handle_mdm_gaps(self, root: str, args: dict) -> dict:
+        """Handle MDM gaps."""
+        try:
+            from .mdm_engine import scan_l4_flow_and_wiring
+            from .store import connect
+            con = connect(root)
+            return scan_l4_flow_and_wiring(con, root)
+        except Exception as e:
+            return {"error": f"Failed to scan MDM gaps: {str(e)}"}
+
+    def _handle_mdm_trace(self, root: str, args: dict) -> dict:
+        """Handle MDM trace."""
+        try:
+            from .mdm_schema import get_explainability_trace
+            from .store import connect
+            con = connect(root)
+            fid = args.get("finding_id", "")
+            return {"finding_id": fid, "trace": get_explainability_trace(con, fid)}
+        except Exception as e:
+            return {"error": f"Failed to fetch MDM trace: {str(e)}"}
```

---

## 5. `lib/cipkg/server.py`

```diff
--- a/lib/cipkg/server.py
+++ b/lib/cipkg/server.py
@@ -48,2 +48,10 @@
     {"name": "models", "description": "Prisma model usage report incl. orphan detection.",
      "inputSchema": {"type": "object", "properties": {}}},
+    {"name": "mdm_scan", "description": "Execute complete Master Data Model (L0-LA) multi-layer scan.",
+     "inputSchema": {"type": "object", "properties": {}}},
+    {"name": "mdm_report", "description": "Generate comprehensive MDM executive dossier and scorecard.",
+     "inputSchema": {"type": "object", "properties": {"markdown": {"type": "boolean"}}}},
+    {"name": "mdm_gaps", "description": "Scan silent IPC command and event wiring gaps.",
+     "inputSchema": {"type": "object", "properties": {}}},
+    {"name": "mdm_trace", "description": "Fetch step-by-step explainability trace for an MDM finding.",
+     "inputSchema": {"type": "object", "properties": {"finding_id": {"type": "string"}}, "required": ["finding_id"]}},
 ]
@@ -158,2 +166,17 @@
         elif name == "models":
             res = stack_prisma.models_report(root)
+        elif name == "mdm_scan":
+            from .mdm_engine import run_mdm_extraction
+            from .mdm_synthesis import synthesize_la_findings
+            con = connect(root)
+            ext = run_mdm_extraction(root)
+            syn = synthesize_la_findings(con, root)
+            res = {"extraction": ext, "findings_count": len(syn)}
+        elif name == "mdm_report":
+            from .mdm_synthesis import generate_full_mdm_report, format_report_markdown
+            rep = generate_full_mdm_report(root)
+            res = {"report": rep, "markdown": format_report_markdown(rep) if args.get("markdown") else None}
+        elif name == "mdm_gaps":
+            from .mdm_engine import scan_l4_flow_and_wiring
+            res = scan_l4_flow_and_wiring(connect(root), root)
+        elif name == "mdm_trace":
+            from .mdm_schema import get_explainability_trace
+            res = {"finding_id": args.get("finding_id"), "trace": get_explainability_trace(connect(root), args.get("finding_id", ""))}
         elif name == "index_status":
```

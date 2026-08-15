# CIP Documentation System Integration Plan

**Purpose:** Integrate the new documentation system blueprint with the CIP (Code Intelligence Protocol) system to create automated documentation enforcement and maintenance.

**Status:** Planning Phase - Ready for Implementation

---

## Overview

This plan details how to extend the CIP system to support the documentation blueprint's requirements. The integration leverages CIP's existing indexing, audit, and hook capabilities while adding new documentation-specific features.

## Current CIP Capabilities Analysis

### Existing Relevant Features
- **Indexing System:** Files, symbols, chunks, edges, summaries tables
- **Audit System:** Rules engine with findings, severity levels, auto-fix
- **Hook System:** Pre/post-edit hooks for agent integration
- **Storage Schema:** Extensible SQLite with schema versioning
- **CLI Interface:** Extensible command structure via `cli.py`
- **Impact Analysis:** Call graph analysis for ripple effects
- **Stack Packs:** Next.js, Prisma, Tauri-specific indexing

### Database Schema (Current v4)
- `files` - file metadata and indexing info
- `symbols` - symbol definitions and signatures
- `chunks` - code chunks with tokenization
- `edges` - import/extends relationships
- `summaries` - repo/dir/file/symbol summaries
- `commits`/`commit_files` - git history
- `signals` - test/type signals
- `findings` - audit rule violations

---

## Integration Build Order (Per Blueprint)

### Phase 1: Immediate Critical Items (Items #0, #3)

#### Item #0: `cip docs audit --existing` (One-time)
**Priority:** CRITICAL - Must run before any new docs are created
**Purpose:** Detect dangling doc references already in the repo

**Implementation:**
```python
# New file: lib/cipkg/docs/audit.py
def audit_existing_refs(root):
    """Check all doc references in repo against actual files on disk."""
    findings = []
    
    # Scan README.md for doc table references
    readme_path = os.path.join(root, "README.md")
    if os.path.exists(readme_path):
        content = open(readme_path).read()
        # Extract markdown links to .md files
        doc_links = re.findall(r'\[([^\]]+)\]\(([^)]+\.md)\)', content)
        for title, path in doc_links:
            full_path = os.path.join(root, path)
            if not os.path.exists(full_path):
                findings.append({
                    "rule": "DOCS-DANGLING-REF",
                    "severity": "high",
                    "path": "README.md",
                    "line": 0,  # Would need line number extraction
                    "title": f"Dangling doc reference: {path}",
                    "detail": f"Referenced as '{title}' but file does not exist",
                    "suggestion": f"Create {path} or remove reference from README",
                    "effort": "medium"
                })
    
    # Scan CHANGELOG.md for tracker references
    changelog_path = os.path.join(root, "CHANGELOG.md")
    if os.path.exists(changelog_path):
        content = open(changelog_path).read()
        # Look for references to docs/ paths
        doc_refs = re.findall(r'docs/[^\s\)]+', content)
        for ref in doc_refs:
            full_path = os.path.join(root, ref)
            if not os.path.exists(full_path):
                findings.append({
                    "rule": "DOCS-DANGLING-REF",
                    "severity": "medium",
                    "path": "CHANGELOG.md",
                    "title": f"Dangling doc reference: {ref}",
                    "detail": f"Referenced in changelog but file does not exist",
                    "suggestion": f"Create {ref} or remove reference",
                    "effort": "small"
                })
    
    return findings
```

**CLI Integration:**
```python
# Add to cli.py
def handle_docs_audit_command(root, args):
    """Handle docs audit commands."""
    from .docs import audit as docs_audit
    
    if args.existing:
        result = docs_audit.audit_existing_refs(root)
        _out({"findings": result, "total": len(result)})
```

**Schema Additions:**
None required initially - uses existing `findings` table.

---

#### Item #3: ADR Enforcement (Highest Blueprint Priority)
**Priority:** CRITICAL - Enforces blueprint's single most important rule
**Purpose:** Prevent editing of Accepted ADRs and detect missing ADRs

**3a: Pre-commit Hook for ADR Protection**
```python
# Extend hooks.py
def pre_adr_edit_hook(file_path, diff_content, root=None):
    """Block edits to Accepted ADRs unless superseding."""
    if not file_path.startswith("docs/decisions/"):
        return {"ok": True, "proceed": True}
    
    # Check if file is an ADR
    if not file_path.startswith("docs/decisions/ADR-"):
        return {"ok": True, "proceed": True}
    
    # Parse current file status
    adr_path = os.path.join(root, file_path)
    if not os.path.exists(adr_path):
        return {"ok": True, "proceed": True}
    
    content = open(adr_path).read()
    status_match = re.search(r'Status:\s*(Accepted|Proposed|Deprecated|Superseded)', content)
    
    if status_match and status_match.group(1) == "Accepted":
        # Check if diff contains "Superseded-by:" or status change
        if "Superseded-by:" not in diff_content and "Status: Superseded" not in diff_content:
            return {
                "ok": False,
                "proceed": False,
                "block_reason": "Cannot edit Accepted ADR directly. Create new ADR with Superseded-by field instead.",
                "suggestion": f"Create new ADR in docs/decisions/ with 'Superseded-by: {os.path.basename(file_path)}'"
            }
    
    return {"ok": True, "proceed": True}
```

**3b: Missing ADR Detection**
```python
# New file: lib/cipkg/docs/decisions.py
def detect_missing_adrs(root, since_commit=None):
    """Detect commits that should have ADRs but don't."""
    findings = []
    
    # Get recent commits
    import subprocess
    if since_commit:
        result = subprocess.run(
            ["git", "log", "--oneline", f"{since_commit}..HEAD"],
            capture_output=True, text=True, cwd=root
        )
    else:
        result = subprocess.run(
            ["git", "log", "--oneline", "-20"],
            capture_output=True, text=True, cwd=root
        )
    
    commits = result.stdout.strip().split('\n') if result.stdout.strip() else []
    
    for commit_line in commits:
        sha, *message_parts = commit_line.split(' ', 1)
        message = ' '.join(message_parts)
        
        # Check for ADR-triggering patterns
        adr_triggers = [
            (r'dependency.*swap|remove.*add.*package', "dependency change"),
            (r'schema.*migration|alter.*table', "schema migration"),
            (r'config.*flag.*enable.*disable', "config behavior change"),
            (r'architecture.*decision|choose.*between', "architectural decision")
        ]
        
        triggered = False
        trigger_reason = None
        for pattern, reason in adr_triggers:
            if re.search(pattern, message, re.IGNORECASE):
                triggered = True
                trigger_reason = reason
                break
        
        if triggered:
            # Check if ADR was created in this commit
            file_result = subprocess.run(
                ["git", "diff-tree", "--name-only", "-r", sha],
                capture_output=True, text=True, cwd=root
            )
            files = file_result.stdout.strip().split('\n') if file_result.stdout.strip() else []
            
            has_adr = any(f.startswith("docs/decisions/ADR-") for f in files)
            
            if not has_adr:
                findings.append({
                    "rule": "DOCS-MISSING-ADR",
                    "severity": "high",
                    "path": f"commit:{sha}",
                    "title": f"Missing ADR for {trigger_reason}",
                    "detail": f"Commit {sha[:7]}: {message}",
                    "suggestion": f"Create ADR in docs/decisions/ documenting this decision",
                    "effort": "medium"
                })
    
    return findings
```

**3c: ADR Graph and History**
```python
# Extend decisions.py
def build_adr_graph(root):
    """Build supersession graph from ADR frontmatter."""
    adr_files = glob.glob(os.path.join(root, "docs/decisions", "ADR-*.md"))
    graph = {"nodes": [], "edges": []}
    
    for adr_file in adr_files:
        content = open(adr_file).read()
        adr_id = os.path.basename(adr_file)
        
        # Parse frontmatter
        status_match = re.search(r'Status:\s*(\w+)', content)
        superseded_match = re.search(r'Superseded-by:\s*([^\n]+)', content)
        
        status = status_match.group(1) if status_match else "Unknown"
        superseded_by = superseded_match.group(1).strip() if superseded_match else None
        
        graph["nodes"].append({
            "id": adr_id,
            "status": status,
            "file": adr_file
        })
        
        if superseded_by:
            graph["edges"].append({
                "from": adr_id,
                "to": superseded_by,
                "type": "supersedes"
            })
    
    return graph

def get_adr_history(root, topic):
    """Get full ADR chain for a topic."""
    graph = build_adr_graph(root)
    
    # Find ADRs related to topic (by title or content)
    related = []
    for node in graph["nodes"]:
        adr_file = os.path.join(root, "docs/decisions", node["id"])
        content = open(adr_file).read()
        if topic.lower() in content.lower():
            related.append(node)
    
    # Build chains
    chains = []
    for adr in related:
        chain = [adr]
        current = adr
        while True:
            # Find what this ADR supersedes
            superseded_by = [e["from"] for e in graph["edges"] if e["to"] == current["id"]]
            if not superseded_by:
                break
            prev_adr = next((n for n in graph["nodes"] if n["id"] in superseded_by), None)
            if prev_adr:
                chain.insert(0, prev_adr)
                current = prev_adr
            else:
                break
        chains.append(chain)
    
    return {"topic": topic, "chains": chains}
```

**Schema Additions:**
```sql
-- Add to CORE_SCHEMA in store.py
CREATE TABLE IF NOT EXISTS doc_refs(
  doc_path TEXT,
  doc_line INTEGER,
  ref_kind TEXT,           -- 'module', 'schema', 'route', 'folder'
  ref_target TEXT,         -- symbol name, model name, etc.
  hash_at_link_time TEXT,
  last_check REAL,
  staleness TEXT,         -- 'fresh', 'stale', 'missing'
  PRIMARY KEY(doc_path, doc_line, ref_target)
);
CREATE INDEX IF NOT EXISTS idx_doc_refs_target ON doc_refs(ref_target);
CREATE INDEX IF NOT EXISTS idx_doc_refs_kind ON doc_refs(ref_kind);

CREATE TABLE IF NOT EXISTS adrs(
  id TEXT PRIMARY KEY,     -- ADR-XXX
  status TEXT,
  superseded_by TEXT,
  created_at REAL,
  last_modified REAL
);
```

---

### Phase 2: Core Documentation Linking (Item #1)

#### Item #1: `doc_refs` Linking System
**Priority:** HIGH - Foundation for all other features
**Purpose:** Link documentation to code/schema/routes per blueprint taxonomy

**Implementation:**
```python
# New file: lib/cipkg/docs/links.py
def extract_doc_refs(root):
    """Extract doc references from blueprint-compliant docs."""
    refs = []
    
    # 1. Module docs -> directories
    modules_dir = os.path.join(root, "docs/modules")
    if os.path.exists(modules_dir):
        for module_file in glob.glob(os.path.join(modules_dir, "*.md")):
            module_name = os.path.basename(module_file).replace(".md", "")
            # Map module name to likely directory
            possible_dirs = [
                module_name,
                module_name.replace("-", "_"),
                module_name.replace("_", "-"),
                f"src/{module_name}",
                f"src/{module_name}s"
            ]
            
            for line_num, line in enumerate(open(module_file), 1):
                # Look for symbol mentions
                symbols = re.findall(r'\b[A-Z][a-zA-Z0-9_]*\b', line)
                for symbol in symbols:
                    refs.append({
                        "doc_path": f"docs/modules/{module_name}.md",
                        "doc_line": line_num,
                        "ref_kind": "module",
                        "ref_target": symbol,
                        "hash_at_link_time": sha(line),
                        "last_check": time.time(),
                        "staleness": "fresh"
                    })
    
    # 2. Architecture docs -> specific targets
    # data-model.md -> Prisma models
    data_model_path = os.path.join(root, "docs/architecture/data-model.md")
    if os.path.exists(data_model_path):
        # Extract model references
        for line_num, line in enumerate(open(data_model_path), 1):
            models = re.findall(r'\b[A-Z][a-z]*\b', line)
            for model in models:
                refs.append({
                    "doc_path": "docs/architecture/data-model.md",
                    "doc_line": line_num,
                    "ref_kind": "schema",
                    "ref_target": model,
                    "hash_at_link_time": sha(line),
                    "last_check": time.time(),
                    "staleness": "fresh"
                })
    
    # 3. Per-folder README.md -> folder contents
    for readme_path in glob.glob(os.path.join(root, "*/README.md")):
        if readme_path.startswith("docs/"):
            continue  # Skip docs folder itself
        
        rel_path = os.path.relpath(readme_path, root).replace(os.sep, "/")
        folder = os.path.dirname(rel_path)
        
        for line_num, line in enumerate(open(readme_path), 1):
            symbols = re.findall(r'\b[A-Z][a-zA-Z0-9_]*\b', line)
            for symbol in symbols:
                refs.append({
                    "doc_path": rel_path,
                    "doc_line": line_num,
                    "ref_kind": "folder",
                    "ref_target": symbol,
                    "hash_at_link_time": sha(line),
                    "last_check": time.time(),
                    "staleness": "fresh"
                })
    
    return refs

def check_doc_staleness(root):
    """Check if doc references are stale based on code changes."""
    con = connect(root)
    
    # Get all doc refs
    refs = [dict(r) for r in con.execute("SELECT * FROM doc_refs").fetchall()]
    
    for ref in refs:
        doc_path = ref["doc_path"]
        full_doc_path = os.path.join(root, doc_path)
        
        if not os.path.exists(full_doc_path):
            ref["staleness"] = "missing"
            continue
        
        # Check if doc content changed
        current_hash = None
        for line_num, line in enumerate(open(full_doc_path), 1):
            if line_num == ref["doc_line"]:
                current_hash = sha(line)
                break
        
        if current_hash and current_hash != ref["hash_at_link_time"]:
            ref["staleness"] = "changed"
        else:
            # Check if referenced target changed
            target_changed = False
            if ref["ref_kind"] == "schema":
                # Check if Prisma model changed
                target_files = con.execute(
                    "SELECT path, mtime FROM files WHERE path LIKE '%schema.prisma'"
                ).fetchall()
                if target_files:
                    latest_mtime = max(f["mtime"] for f in target_files)
                    if latest_mtime > ref["last_check"]:
                        target_changed = True
            
            if target_changed:
                ref["staleness"] = "stale"
            else:
                ref["staleness"] = "fresh"
    
    # Update database
    for ref in refs:
        con.execute(
            "UPDATE doc_refs SET staleness=?, last_check=? WHERE doc_path=? AND doc_line=? AND ref_target=?",
            (ref["staleness"], time.time(), ref["doc_path"], ref["doc_line"], ref["ref_target"])
        )
    
    con.commit()
    return refs
```

**CLI Integration:**
```python
def handle_docs_check_command(root, args):
    """Handle docs staleness check."""
    from .docs import links as docs_links
    
    if args.refresh:
        refs = docs_links.extract_doc_refs(root)
        # Upsert to database
        con = connect(root)
        for ref in refs:
            con.execute(
                "INSERT INTO doc_refs(doc_path, doc_line, ref_kind, ref_target, hash_at_link_time, last_check, staleness) "
                "VALUES(?,?,?,?,?,?,?) "
                "ON CONFLICT(doc_path, doc_line, ref_target) DO UPDATE SET "
                "hash_at_link_time=excluded.hash_at_link_time, last_check=excluded.last_check",
                (ref["doc_path"], ref["doc_line"], ref["ref_kind"], ref["ref_target"],
                 ref["hash_at_link_time"], ref["last_check"], ref["staleness"])
            )
        con.commit()
    
    refs = docs_links.check_doc_staleness(root)
    stale = [r for r in refs if r["staleness"] in ("stale", "changed", "missing")]
    
    _out({
        "total_refs": len(refs),
        "stale": len(stale),
        "stale_refs": stale
    })
```

---

### Phase 3: Staleness Check with Severity (Item #2)

#### Item #2: Enhanced Staleness with Public/Private Severity
**Priority:** HIGH - Enables prioritized doc maintenance
**Purpose:** Weight staleness findings by blueprint update triggers

**Implementation:**
```python
# Extend links.py
def check_doc_staleness_with_severity(root):
    """Check staleness with public/private symbol distinction."""
    con = connect(root)
    
    refs = [dict(r) for r in con.execute("SELECT * FROM doc_refs").fetchall()]
    
    for ref in refs:
        # Check if referenced symbol is public (exported)
        if ref["ref_kind"] in ("module", "folder"):
            # Check if symbol is exported
            symbol_rows = con.execute(
                "SELECT * FROM symbols WHERE name=? AND kind='export'",
                (ref["ref_target"],)
            ).fetchall()
            
            is_public = len(symbol_rows) > 0
        else:
            is_public = True  # Schema/route refs are always public-facing
        
        # Determine severity based on blueprint triggers
        if ref["staleness"] == "missing":
            severity = "critical"
        elif ref["staleness"] == "changed":
            severity = "high" if is_public else "medium"
        elif ref["staleness"] == "stale":
            severity = "medium" if is_public else "low"
        else:
            severity = None
        
        ref["severity"] = severity
    
    return refs

def generate_staleness_report(root):
    """Generate prioritized staleness report."""
    refs = check_doc_staleness_with_severity(root)
    
    # Group by severity
    by_severity = {"critical": [], "high": [], "medium": [], "low": []}
    for ref in refs:
        if ref.get("severity"):
            by_severity[ref["severity"]].append(ref)
    
    return {
        "summary": {k: len(v) for k, v in by_severity.items()},
        "findings": by_severity
    }
```

---

### Phase 4: Generated Sections Automation (Item #6)

#### Item #6: Auto-Generate API Docs, ER Diagrams, Dependency Graphs
**Priority:** MEDIUM - Automates blueprint §5 requirements
**Purpose:** Generate content blueprint explicitly marks as "generated, not hand-written"

**Implementation:**
```python
# New file: lib/cipkg/docs/generate.py
def generate_api_docs(root):
    """Generate API documentation from routes table."""
    con = connect(root)
    
    # Get routes from Next.js stack pack
    routes = con.execute("SELECT * FROM routes").fetchall()
    
    api_docs = []
    for route in routes:
        api_docs.append(f"## {route['method']} {route['path']}")
        api_docs.append(f"**Handler:** {route.get('handler', 'Unknown')}")
        api_docs.append(f"**Middleware:** {route.get('middleware', 'None')}")
        api_docs.append("")
    
    # Write to docs/api/endpoints.md
    api_dir = os.path.join(root, "docs/api")
    os.makedirs(api_dir, exist_ok=True)
    
    with open(os.path.join(api_dir, "endpoints.md"), "w") as f:
        f.write("# API Endpoints\n\n")
        f.write("<!-- AUTO-GENERATED BY CIP - DO NOT EDIT -->\n\n")
        f.write("\n".join(api_docs))
    
    return {"generated": len(routes), "file": "docs/api/endpoints.md"}

def generate_er_diagram(root):
    """Generate ER diagram from Prisma schema."""
    con = connect(root)
    
    # Get models from Prisma stack pack
    models = con.execute("SELECT * FROM prisma_models").fetchall()
    
    mermaid = "```mermaid\nerDiagram\n"
    
    for model in models:
        model_name = model["name"]
        mermaid += f"  {model_name} {{\n"
        
        # Get fields
        fields = con.execute(
            "SELECT * FROM prisma_fields WHERE model=?",
            (model_name,)
        ).fetchall()
        
        for field in fields:
            field_type = field["type"]
            if field.get("is_id"):
                mermaid += f"    {field['name']} {field_type} PK\n"
            elif field.get("is_unique"):
                mermaid += f"    {field['name']} {field_type} UK\n"
            else:
                mermaid += f"    {field['name']} {field_type}\n"
        
        mermaid += "  }\n"
    
    mermaid += "```\n"
    
    # Inject into data-model.md
    data_model_path = os.path.join(root, "docs/architecture/data-model.md")
    if os.path.exists(data_model_path):
        content = open(data_model_path).read()
        
        # Find or create auto-generated section
        auto_marker = "<!-- AUTO-GENERATED ER DIAGRAM -->"
        if auto_marker in content:
            # Replace existing
            content = re.sub(
                r'<!-- AUTO-GENERATED ER DIAGRAM -->.*<!-- END AUTO-GENERATED -->',
                f'<!-- AUTO-GENERATED ER DIAGRAM -->\n{mermaid}\n<!-- END AUTO-GENERATED -->',
                content,
                flags=re.DOTALL
            )
        else:
            # Append
            content += f"\n\n<!-- AUTO-GENERATED ER DIAGRAM -->\n{mermaid}\n<!-- END AUTO-GENERATED -->\n"
        
        with open(data_model_path, "w") as f:
            f.write(content)
    
    return {"models": len(models), "file": "docs/architecture/data-model.md"}

def generate_dependency_graph(root):
    """Generate dependency graph from edges table."""
    con = connect(root)
    
    # Get import edges
    edges = con.execute("SELECT * FROM edges WHERE kind='import' LIMIT 100").fetchall()
    
    mermaid = "```mermaid\ngraph TD\n"
    
    # Group by file to reduce nodes
    files = {}
    for edge in edges:
        src_file = edge["src_path"]
        dst_file = edge["dst_path"]
        
        if src_file not in files:
            files[src_file] = f"F{len(files)}"
        if dst_file not in files:
            files[dst_file] = f"F{len(files)}"
        
        mermaid += f"  {files[src_file]} --> {files[dst_file]}\n"
    
    # Add legend
    mermaid += "\n  classDef files fill:#f9f,stroke:#333,stroke-width:2px\n"
    for file_path, node_id in files.items():
        short_name = os.path.basename(file_path)
        mermaid += f"  class {node_id} files\n"
    
    mermaid += "```\n"
    
    # Inject into overview.md
    overview_path = os.path.join(root, "docs/architecture/overview.md")
    if os.path.exists(overview_path):
        content = open(overview_path).read()
        
        auto_marker = "<!-- AUTO-GENERATED DEPENDENCY GRAPH -->"
        if auto_marker in content:
            content = re.sub(
                r'<!-- AUTO-GENERATED DEPENDENCY GRAPH -->.*<!-- END AUTO-GENERATED -->',
                f'<!-- AUTO-GENERATED DEPENDENCY GRAPH -->\n{mermaid}\n<!-- END AUTO-GENERATED -->',
                content,
                flags=re.DOTALL
            )
        else:
            content += f"\n\n<!-- AUTO-GENERATED DEPENDENCY GRAPH -->\n{mermaid}\n<!-- END AUTO-GENERATED -->\n"
        
        with open(overview_path, "w") as f:
            f.write(content)
    
    return {"edges": len(edges), "file": "docs/architecture/overview.md"}
```

**CLI Integration:**
```python
def handle_docs_generate_command(root, args):
    """Handle docs generation commands."""
    from .docs import generate as docs_generate
    
    results = {}
    
    if args.api or args.all:
        results["api"] = docs_generate.generate_api_docs(root)
    
    if args.er or args.all:
        results["er"] = docs_generate.generate_er_diagram(root)
    
    if args.deps or args.all:
        results["deps"] = docs_generate.generate_dependency_graph(root)
    
    _out(results)
```

---

### Phase 5: Coverage Checks (Item #5)

#### Item #5: CHANGELOG Coverage Verification
**Priority:** MEDIUM - Ensures user/API visible changes are documented
**Purpose:** Cross-check CHANGELOG entries against API surface changes

**Implementation:**
```python
# New file: lib/cipkg/docs/changelog.py
def check_changelog_coverage(root):
    """Check if API changes have corresponding CHANGELOG entries."""
    con = connect(root)
    
    # Get recent API changes from routes
    # This would require tracking route changes over time
    # For now, check if routes changed since last CHANGELOG entry
    
    changelog_path = os.path.join(root, "CHANGELOG.md")
    if not os.path.exists(changelog_path):
        return {"error": "CHANGELOG.md not found"}
    
    # Get last CHANGELOG entry date
    with open(changelog_path) as f:
        content = f.read()
        # Extract most recent date
        date_match = re.search(r'## \d{4}-\d{2}-\d{2}', content)
        last_changelog_date = date_match.group(0) if date_match else None
    
    if not last_changelog_date:
        return {"error": "Could not find last CHANGELOG date"}
    
    # Check for API changes since that date
    # This would require comparing current routes against historical snapshot
    # For now, return placeholder
    return {
        "last_changelog_date": last_changelog_date,
        "api_changes_since": "Not implemented - requires route history tracking",
        "coverage": "manual"
    }
```

---

### Phase 6: Monthly Sweep Automation (Item #7)

#### Item #7: Monthly Sweep as Scheduled CIP Check
**Priority:** LOW - Can be deferred, builds on existing features
**Purpose:** Automated monthly docs maintenance

**Implementation:**
```python
# Extend audit.py rules
def add_todo_docs_rule():
    """Add rule to find TODO: update docs comments."""
    return {
        "id": "DOCS-TODO-UPDATE",
        "pattern": r"TODO.*update.*docs",
        "severity": "low",
        "title": "TODO comment about updating docs",
        "suggestion": "Either update the docs or remove the TODO",
        "effort": "small"
    }

def check_last_reviewed_staleness(root):
    """Check for docs with stale last-reviewed dates."""
    con = connect(root)
    
    # Get module docs with last-reviewed field
    module_docs = glob.glob(os.path.join(root, "docs/modules", "*.md"))
    
    stale_docs = []
    ninety_days_ago = time.time() - (90 * 24 * 60 * 60)
    
    for doc_path in module_docs:
        content = open(doc_path).read()
        review_match = re.search(r'Last Reviewed:\s*(\d{4}-\d{2}-\d{2})', content)
        
        if review_match:
            review_date_str = review_match.group(1)
            try:
                review_date = time.mktime(time.strptime(review_date_str, "%Y-%m-%d"))
                
                if review_date < ninety_days_ago:
                    # Check if linked code changed more recently
                    # This would require checking git history for the linked module
                    # For now, flag as potentially stale
                    stale_docs.append({
                        "doc": os.path.basename(doc_path),
                        "last_reviewed": review_date_str,
                        "days_since_review": int((time.time() - review_date) / (24 * 60 * 60))
                    })
            except ValueError:
                pass
    
    return stale_docs
```

---

### Phase 7: Glossary Suggestions (Item #4)

#### Item #4: Glossary Entry Suggestions
**Priority:** LOW - Nice-to-have, lowest urgency
**Purpose:** Auto-suggest domain terms for GLOSSARY.md

**Implementation:**
```python
# New file: lib/cipkg/docs/glossary.py
def suggest_glossary_entries(root):
    """Suggest domain terms that should be in GLOSSARY.md."""
    con = connect(root)
    
    # Get all symbols from the codebase
    symbols = con.execute("SELECT DISTINCT name FROM symbols").fetchall()
    symbol_names = set(s["name"] for s in symbols)
    
    # Read existing GLOSSARY.md
    glossary_path = os.path.join(root, "docs/GLOSSARY.md")
    defined_terms = set()
    
    if os.path.exists(glossary_path):
        content = open(glossary_path).read()
        # Extract defined terms (headers)
        defined_terms = set(re.findall(r'^##\s+([A-Z][a-zA-Z0-9_]+)', content, re.MULTILINE))
    
    # Filter out standard library/framework terms
    stdlib_terms = {
        "String", "Number", "Boolean", "Array", "Object", "Promise",
        "Error", "Date", "Math", "JSON", "RegExp", "Map", "Set"
    }
    
    # Find terms that appear frequently but aren't defined
    term_frequency = {}
    for symbol in symbol_names:
        if symbol in defined_terms or symbol in stdlib_terms:
            continue
        
        # Count occurrences across files
        file_count = len(con.execute(
            "SELECT DISTINCT path FROM symbols WHERE name=?",
            (symbol,)
        ).fetchall())
        
        if file_count >= 3:  # Appears in 3+ files
            term_frequency[symbol] = file_count
    
    # Sort by frequency
    suggestions = sorted(term_frequency.items(), key=lambda x: x[1], reverse=True)
    
    return {
        "suggestions": [{"term": term, "file_count": count} for term, count in suggestions[:20]],
        "total_defined": len(defined_terms),
        "total_candidates": len(term_frequency)
    }
```

---

## CLI Command Extensions

Add these commands to `cli.py`:

```python
# Add to argument parser
subparsers = parser.add_subparsers(dest='command', help='CIP commands')

# Docs commands
docs_parser = subparsers.add_parser('docs', help='Documentation operations')
docs_subparsers = docs_parser.add_subparsers(dest='docs_command')

docs_audit_parser = docs_subparsers.add_parser('audit', help='Audit documentation')
docs_audit_parser.add_argument('--existing', action='store_true', help='Check existing dangling references')
docs_audit_parser.add_argument('--refresh', action='store_true', help='Refresh doc links')

docs_check_parser = docs_subparsers.add_parser('check', help='Check documentation staleness')
docs_check_parser.add_argument('--refresh', action='store_true', help='Refresh doc links before checking')

docs_generate_parser = docs_subparsers.add_parser('generate', help='Generate documentation sections')
docs_generate_parser.add_argument('--api', action='store_true', help='Generate API docs')
docs_generate_parser.add_argument('--er', action='store_true', help='Generate ER diagram')
docs_generate_parser.add_argument('--deps', action='store_true', help='Generate dependency graph')
docs_generate_parser.add_argument('--all', action='store_true', help='Generate all sections')

docs_decisions_parser = docs_subparsers.add_parser('decisions', help='ADR operations')
docs_decisions_parser.add_argument('--missing', action='store_true', help='Detect missing ADRs')
docs_decisions_parser.add_argument('--graph', action='store_true', help='Build ADR supersession graph')
docs_decisions_parser.add_argument('--history', help='Get ADR history for topic')

docs_glossary_parser = docs_subparsers.add_parser('glossary', help='Glossary operations')
docs_glossary_parser.add_argument('--suggest', action='store_true', help='Suggest glossary entries')
```

---

## Database Schema Migration

```sql
-- Migration from v4 to v5
-- Run this in store.py migrate() function

-- Add doc-related tables
CREATE TABLE IF NOT EXISTS doc_refs(
  doc_path TEXT,
  doc_line INTEGER,
  ref_kind TEXT,
  ref_target TEXT,
  hash_at_link_time TEXT,
  last_check REAL,
  staleness TEXT,
  PRIMARY KEY(doc_path, doc_line, ref_target)
);
CREATE INDEX IF NOT EXISTS idx_doc_refs_target ON doc_refs(ref_target);
CREATE INDEX IF NOT EXISTS idx_doc_refs_kind ON doc_refs(ref_kind);

CREATE TABLE IF NOT EXISTS adrs(
  id TEXT PRIMARY KEY,
  status TEXT,
  superseded_by TEXT,
  created_at REAL,
  last_modified REAL
);

-- Update schema version
UPDATE meta SET value='5' WHERE key='schema_version';
```

---

## Hook Configuration Updates

Update `.cip/hooks/claude-code.json` to include ADR protection:

```json
{
  "version": "1.0",
  "hooks": {
    "PostToolUse": {
      "Edit": {
        "command": "cip",
        "args": ["hook", "post-edit", "{file}"],
        "inject_result": true
      },
      "Write": {
        "command": "cip",
        "args": ["hook", "post-edit", "{file}"],
        "inject_result": true
      }
    },
    "PreToolUse": {
      "Edit": {
        "command": "cip",
        "args": ["hook", "pre-edit", "{file}", "{diff}"],
        "inject_result": true,
        "blocking": false
      },
      "Write": {
        "command": "cip",
        "args": ["hook", "pre-adr-edit", "{file}", "{diff}"],
        "inject_result": true,
        "blocking": true
      }
    }
  }
}
```

---

## Implementation Timeline

### Sprint 1: Critical Foundation (Week 1)
1. **Item #0:** Implement `cip docs audit --existing`
2. **Item #3a:** Implement ADR pre-edit hook protection
3. **Schema migration:** Add doc_refs and adrs tables

### Sprint 2: Core Linking (Week 2)
1. **Item #1:** Implement doc_refs extraction and linking
2. **Item #2:** Implement staleness check with severity
3. **CLI integration:** Add docs commands

### Sprint 3: Generation & Coverage (Week 3)
1. **Item #6:** Implement generated sections (API, ER, deps)
2. **Item #5:** Implement CHANGELOG coverage check
3. **Item #3b:** Implement missing ADR detection

### Sprint 4: Advanced Features (Week 4)
1. **Item #3c:** Implement ADR graph and history
2. **Item #7:** Implement monthly sweep automation
3. **Item #4:** Implement glossary suggestions

---

## Testing Strategy

### Unit Tests
- Test doc reference extraction with sample docs
- Test ADR status parsing and validation
- Test staleness detection logic
- Test glossary suggestion algorithms

### Integration Tests
- Test end-to-end `cip docs audit --existing` on vivim-final
- Test ADR hook protection with sample edits
- Test generated sections output format

### Validation Tests
- Run on vivim-final to verify no dangling refs remain
- Verify ADR protection blocks incorrect edits
- Validate generated sections render correctly

---

## Success Criteria

### Phase 1 Success
- [ ] `cip docs audit --existing` runs without errors
- [ ] ADR pre-edit hook blocks edits to Accepted ADRs
- [ ] Schema migration completes successfully

### Phase 2 Success
- [ ] Doc references are extracted and stored
- [ ] Staleness check prioritizes public interface changes
- [ ] CLI docs commands work as expected

### Phase 3 Success
- [ ] API docs generate automatically
- [ ] ER diagram renders in data-model.md
- [ ] Dependency graph renders in overview.md

### Phase 4 Success
- [ ] Missing ADRs are detected
- [ ] ADR graph and history queries work
- [ ] Monthly sweep identifies stale docs
- [ ] Glossary suggestions are useful

---

## Notes and Considerations

### Vivim-Specific Customizations
- The CIP config already has a "vivim" profile with excludes - update this to include new docs folders
- Vivim's dense vocabulary (ChromeGovernor, capability resolution, etc.) makes glossary suggestions particularly valuable
- Existing dangling refs in README.md provide immediate test data for Item #0

### Performance Considerations
- Doc reference extraction should be cached and only refreshed on changes
- ADR graph building is O(n) and can be cached
- Generated sections should only run when underlying data changes

### Future Enhancements
- Add `cip docs sync` to automatically update docs based on detected changes
- Integrate with CI/CD pipeline for pre-commit docs validation
- Add web UI for browsing doc relationships and staleness

---

## Next Steps

1. **Review and approve** this integration plan
2. **Begin Sprint 1** implementation starting with Item #0
3. **Test on vivim-final** after each phase
4. **Update documentation** as features are implemented
5. **Create ADR** documenting this integration decision per blueprint rules
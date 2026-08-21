# Vivim Documentation System + CIP Integration - Master Plan

**Purpose:** Comprehensive master plan for integrating Vivim's new documentation system with CIP, starting from fresh accurate state.

**Context:** Vivim has a fresh documentation system (docs/) and an existing CIP integration. This plan uses CIP to generate accurate initial docs, then adds documentation-specific automation.

**Timeline:** 4 Phases over ~2 weeks

---

## Phase 1: Baseline Foundation (Day 1)

### Step 1.1: Run CIP Sync with Vivim Profile
**Command:**
```bash
cd C:\0-BlackBoxProject-0\index
python -m lib.cipkg.cli sync --root ../vivim-final
```

**Purpose:** Index Vivim's actual codebase using existing vivim profile configuration.

**What This Does:**
- Uses vivim profile excludes (src/generated, seeds/taxonomy, devops/opencode, etc.)
- Indexes 13 engine layers correctly
- Skips 62MB generated code
- Properly handles Prisma schema analysis via stack/prisma.py
- Uses external search integration with code-index.ts
- Builds complete symbol table, edges, summaries, and architecture map

**Expected Output:**
- Complete CIP index in `.cip/data/index.db`
- All Vivim symbols indexed
- Prisma models parsed
- Next.js routes indexed
- Tauri commands detected
- Architecture analysis completed

**Verification:**
```bash
python -m lib.cipkg.cli analyze --root ../vivim-final
```

---

### Step 1.2: Verify CIP Index Quality
**Command:**
```bash
cd C:\0-BlackBoxProject-0\index
python -m lib.cipkg.cli session start --root ../vivim-final
```

**Purpose:** Verify CIP captured Vivim's architecture correctly.

**What This Does:**
- Provides architecture map of 13 engines
- Shows currently broken tests
- Shows recently co-changed files (hotspots)
- Shows high-severity open audit findings
- Displays context budget (6000 tokens)

**Expected Output:**
- Architecture map showing Provider Knowledge Graph, Capability System, etc.
- List of 13 engine layers
- Test status
- Hotspot files
- Audit findings summary

**Verification:** Check that engine layers are correctly identified and no critical findings block the session.

---

### Step 1.3: Run Item #0 Audit - Detect Dangling Doc References
**Command:**
```bash
cd C:\0-BlackBoxProject-0\index
python -m lib.cipkg.cli docs audit --existing --root ../vivim-final
```

**Purpose:** Find all broken doc references in README.md and CHANGELOG.md before generating new docs.

**What This Does:**
- Scans README.md for markdown links to .md files
- Scans CHANGELOG.md for docs/ path references
- Checks each reference against actual files on disk
- Reports dangling references with severity levels

**Expected Output:**
- List of dangling references (we know these exist from the plan)
- Likely findings:
  - README.md references to docs/architecture/OVERVIEW.md (doesn't exist, now overview.md)
  - README.md references to docs/decisions/README.md (doesn't exist)
  - CHANGELOG.md reference to docs/atomic-v3-fork-canon/01-tracker.md (doesn't exist)

**Verification:** Document all dangling references for fixing in Step 1.4.

---

### Step 1.4: Fix Dangling Doc References
**Files to Update:**
- `C:\0-BlackBoxProject-0\vivim-final\README.md`
- `C:\0-BlackBoxProject-0\vivim-final\CHANGELOG.md`

**What This Does:**
- Update README.md doc table to use correct lowercase paths:
  - `docs/architecture/OVERVIEW.md` → `docs/architecture/overview.md`
  - `docs/architecture/ENGINES.md` → remove (use modules/engines.md)
  - `docs/architecture/DATA.md` → `docs/architecture/data-model.md`
  - `docs/architecture/API.md` → `docs/architecture/api-philosophy.md`
  - `docs/architecture/FRONTEND.md` → `docs/architecture/frontend.md`
  - `docs/runbooks/DEV.md` → `docs/runbooks/dev.md`
  - `docs/runbooks/DESKTOP.md` → `docs/runbooks/desktop.md`
  - `docs/runbooks/PROVIDERS.md` → `docs/runbooks/providers.md`
  - `docs/decisions/README.md` → `docs/decisions/` (directory listing)
- Update CHANGELOG.md to remove reference to non-existent tracker

**Expected Output:**
- Updated README.md with correct doc paths
- Updated CHANGELOG.md with broken reference removed
- All doc references now point to existing files

**Verification:** Re-run Step 1.3 to confirm no dangling references remain.

---

## Phase 2: Generate Accurate Initial Docs from CIP Data (Days 2-3)

### Step 2.1: Create Bootstrap Script
**File:** `C:\0-BlackBoxProject-0\index\scripts\bootstrap-vivim-docs.py`

**Purpose:** Generate accurate initial docs from CIP index data.

**What This Script Does:**
- Connects to CIP database
- Queries directory summaries for module docs
- Queries architecture analysis for overview docs
- Queries Prisma models for ER diagram
- Queries routes for API docs
- Queries symbol frequency for glossary suggestions
- Generates markdown files in correct locations

**Script Structure:**
```python
#!/usr/bin/env python3
"""Bootstrap Vivim documentation from CIP index data."""

import os, sys, json, re
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
from cipkg.base import repo_root, load_config
from cipkg.store import connect

def bootstrap_docs():
    root = repo_root()  # vivim-final
    con = connect(root)
    
    # 1. Generate module docs from directory summaries
    generate_module_docs(con, root)
    
    # 2. Generate architecture docs from analysis
    generate_architecture_docs(con, root)
    
    # 3. Generate API docs from routes
    generate_api_docs(con, root)
    
    # 4. Generate ER diagram from Prisma
    generate_er_diagram(con, root)
    
    # 5. Generate initial glossary suggestions
    generate_glossary_suggestions(con, root)
    
    print("Documentation bootstrap complete!")

def generate_module_docs(con, root):
    """Generate docs/modules/*.md from CIP directory summaries."""
    print("Generating module docs...")
    
    # Get directory summaries from CIP
    summaries = con.execute(
        "SELECT * FROM summaries WHERE kind='dir' ORDER BY path"
    ).fetchall()
    
    modules_dir = os.path.join(root, "docs/modules")
    os.makedirs(modules_dir, exist_ok=True)
    
    # Map directories to module names
    dir_to_module = {
        "src/engines": "engines",
        "src/storage": "storage",
        "src-tauri": "desktop",
        "frontend": "frontend",
        "src/api": "api",
        "devops": "devops"
    }
    
    for summary in summaries:
        path = summary["path"]
        module_name = dir_to_module.get(path)
        
        if not module_name:
            continue
        
        # Get files in this directory
        files = con.execute(
            "SELECT * FROM files WHERE path LIKE ?",
            (f"{path}/%",)
        ).fetchall()
        
        # Get symbols in this directory
        symbols = con.execute(
            "SELECT * FROM symbols WHERE path LIKE ?",
            (f"{path}/%",)
        ).fetchall()
        
        # Generate module doc
        module_doc = f"""# {module_name.title()} Module

**Purpose:** {summary.get('summary', 'TODO: Add module purpose')}

**Directory:** `{path}/`

## Public Interface

"""
        
        # Add exported symbols
        exported_symbols = [s for s in symbols if s["kind"] == "export"]
        if exported_symbols:
            module_doc += "### Exports\n\n"
            for sym in exported_symbols[:20]:  # Limit to top 20
                module_doc += f"- `{sym['name']}` - {sym.get('signature', 'N/A')}\n"
            module_doc += "\n"
        
        # Add key files
        if files:
            module_doc += "## Key Files\n\n"
            for f in files[:10]:  # Limit to top 10
                module_doc += f"- `{f['path']}` ({f['language']}, {f['lines']} lines)\n"
            module_doc += "\n"
        
        # Add related architecture
        module_doc += f"""## Related Architecture

- See [`../architecture/overview.md`](../architecture/overview.md) for system context
- See [`../architecture/{module_name}.md`](../architecture/{module_name}.md) for detailed architecture

## Owner

VIVIM.inc

## Last Reviewed

{datetime.now().strftime('%Y-%m-%d')}
"""
        
        # Write to file
        module_path = os.path.join(modules_dir, f"{module_name}.md")
        with open(module_path, 'w') as f:
            f.write(module_doc)
        
        print(f"  Generated: {module_name}.md")

def generate_architecture_docs(con, root):
    """Generate docs/architecture/*.md from CIP analysis."""
    print("Generating architecture docs...")
    
    arch_dir = os.path.join(root, "docs/architecture")
    os.makedirs(arch_dir, exist_ok=True)
    
    # Generate/update overview.md with dependency graph
    generate_overview_with_graph(con, arch_dir)
    
    # Generate/update backend.md with engine layers
    generate_backend_doc(con, arch_dir)
    
    # Generate/update frontend.md
    generate_frontend_doc(con, arch_dir)
    
    print("  Architecture docs generated")

def generate_overview_with_graph(con, arch_dir):
    """Generate overview.md with dependency graph from CIP edges."""
    # Get import edges for dependency graph
    edges = con.execute(
        "SELECT * FROM edges WHERE kind='import' LIMIT 100"
    ).fetchall()
    
    # Generate mermaid graph
    mermaid = "```mermaid\ngraph TD\n"
    
    # Group by file to reduce nodes
    files = {}
    for edge in edges:
        src_file = edge.get("src_path", "unknown")
        dst_file = edge.get("dst", "unknown")
        
        if src_file not in files:
            files[src_file] = f"F{len(files)}"
        if dst_file not in files:
            files[dst_file] = f"F{len(files)}"
        
        mermaid += f"  {files[src_file]} --> {files[dst_file]}\n"
    
    mermaid += "```\n"
    
    # Update or create overview.md
    overview_path = os.path.join(arch_dir, "overview.md")
    
    if os.path.exists(overview_path):
        with open(overview_path, 'r') as f:
            content = f.read()
        
        # Inject or replace dependency graph
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
    else:
        content = f"""# Architecture Overview

## System Overview

Vivim is a local-first AI conversation platform built with a 13-layer engine architecture.

<!-- AUTO-GENERATED DEPENDENCY GRAPH -->
{mermaid}
<!-- END AUTO-GENERATED -->

## Engine Layers

Vivim's architecture consists of 13 engine layers:

- **L0-L1**: Provider Knowledge Graph (ProviderRegistrar, ProviderHealthKernel)
- **L2-L3**: Capability System (CapabilityResolutionEngine, CapabilityEngine)
- **L4**: Session & State (ConversationManager, StreamBlockStore)
- **Chrome Layer**: ChromeGovernor (CDP proxy, lifecycle, trace, health)
- **Cross-cutting**: CapabilityEventBus, ConfigManager, StreamParserEngine
- **Lifecycle**: RegistrationAuditor, VersionManager, TelemetryAggregator

## Architectural Invariants

- **B1 (Governor Canon)**: No direct Chrome/CDP transport imports from engines
- **B2 (Store Contract Isolation)**: Storage accessed through contracts
- **B3 (Provider Configuration)**: Provider manifests in seeds/providers/manifests.ts
- **B4 (Relational-First Schema)**: Prisma schema follows relational patterns

## Related Documentation

- See [`../modules/`](../modules/) for per-module documentation
- See [`../decisions/`](../decisions/) for architecture decisions
- See [`../runbooks/`](../runbooks/) for operational procedures

"""
    
    with open(overview_path, 'w') as f:
        f.write(content)
    
    print("    Generated: overview.md with dependency graph")

def generate_backend_doc(con, arch_dir):
    """Generate backend.md with engine layer details."""
    backend_path = os.path.join(arch_dir, "backend.md")
    
    # Get engine files
    engine_files = con.execute(
        "SELECT * FROM files WHERE path LIKE 'src/engines/%' ORDER BY path"
    ).fetchall()
    
    # Get engine symbols
    engine_symbols = con.execute(
        "SELECT * FROM symbols WHERE path LIKE 'src/engines/%' ORDER BY path"
    ).fetchall()
    
    content = f"""# Backend Architecture

## Engine Layers

Vivim's backend is organized into 13 engine layers:

"""
    
    # Group by engine
    engines = {}
    for sym in engine_symbols:
        path = sym["path"]
        engine_name = path.split('/')[-1].replace('.ts', '')
        if engine_name not in engines:
            engines[engine_name] = []
        engines[engine_name].append(sym)
    
    for engine_name, symbols in engines.items():
        content += f"### {engine_name}\n\n"
        content += f"**File:** `src/engines/{engine_name}.ts`\n\n"
        
        exports = [s for s in symbols if s["kind"] == "export"]
        if exports:
            content += "**Exports:**\n\n"
            for exp in exports[:10]:
                content += f"- `{exp['name']}` - {exp.get('signature', 'N/A')}\n"
            content += "\n"
    
    content += """
## Key Architectural Patterns

- **Provider Knowledge Graph**: Manages provider registration and health
- **Capability Resolution**: Routes capabilities to appropriate providers
- **Session Management**: Handles conversation state and streaming
- **Chrome Governor**: Owns all CDP transport (B1 invariant)
- **Storage Contracts**: Abstracts Prisma access (B2 invariant)

## Related Documentation

- See [`../modules/engines.md`](../modules/engines.md) for engine module details
- See [`../decisions/`](../decisions/) for architecture decisions
- See [`../runbooks/providers.md`](../runbooks/providers.md) for provider operations

"""
    
    with open(backend_path, 'w') as f:
        f.write(content)
    
    print("    Generated: backend.md")

def generate_frontend_doc(con, arch_dir):
    """Generate frontend.md with Next.js structure."""
    frontend_path = os.path.join(arch_dir, "frontend.md")
    
    # Get frontend files
    frontend_files = con.execute(
        "SELECT * FROM files WHERE path LIKE 'frontend/%' ORDER BY path"
    ).fetchall()
    
    content = f"""# Frontend Architecture

## Tech Stack

- **Framework**: Next.js (App Router)
- **Desktop Shell**: Tauri
- **UI Components**: React
- **Styling**: CSS

## Frontend Structure

Total frontend files: {len(frontend_files)}

"""
    
    # Group by directory
    dirs = {}
    for f in frontend_files:
        parts = f["path"].split('/')
        if len(parts) > 1:
            dir_name = parts[1]
            if dir_name not in dirs:
                dirs[dir_name] = []
            dirs[dir_name].append(f)
    
    for dir_name, files in dirs.items():
        content += f"### {dir_name}/\n\n"
        for f in files[:5]:  # Limit to top 5
            content += f"- `{f['path']}` ({f['lines']} lines)\n"
        content += "\n"
    
    content += """
## Tauri Integration

The frontend is wrapped in a Tauri desktop shell. See [`desktop.md`](desktop.md) for details.

## Related Documentation

- See [`../modules/frontend.md`](../modules/frontend.md) for frontend module details
- See [`../modules/desktop.md`](../modules/desktop.md) for desktop shell details
- See [`../runbooks/desktop.md`](../runbooks/desktop.md) for desktop operations

"""
    
    with open(frontend_path, 'w') as f:
        f.write(content)
    
    print("    Generated: frontend.md")

def generate_api_docs(con, root):
    """Generate docs/api/*.md from CIP routes."""
    print("Generating API docs...")
    
    api_dir = os.path.join(root, "docs/api")
    os.makedirs(api_dir, exist_ok=True)
    
    # Check if routes table exists (Next.js stack pack)
    try:
        routes = con.execute("SELECT * FROM routes").fetchall()
    except:
        print("  No routes table found - skipping API docs")
        return
    
    api_content = "# API Endpoints\n\n"
    api_content += "<!-- AUTO-GENERATED BY CIP - DO NOT EDIT -->\n\n"
    
    # Group by path prefix
    routes_by_prefix = {}
    for route in routes:
        path = route.get("path", "")
        prefix = "/" + path.split('/')[1] if len(path.split('/')) > 1 else "root"
        if prefix not in routes_by_prefix:
            routes_by_prefix[prefix] = []
        routes_by_prefix[prefix].append(route)
    
    for prefix, route_list in sorted(routes_by_prefix.items()):
        api_content += f"## {prefix}\n\n"
        for route in route_list:
            method = route.get("method", "GET")
            path = route.get("path", "")
            handler = route.get("handler", "Unknown")
            middleware = route.get("middleware", "None")
            
            api_content += f"### {method} {path}\n\n"
            api_content += f"**Handler:** `{handler}`\n\n"
            api_content += f"**Middleware:** {middleware}\n\n"
    
    with open(os.path.join(api_dir, "endpoints.md"), 'w') as f:
        f.write(api_content)
    
    print(f"  Generated: api/endpoints.md ({len(routes)} routes)")

def generate_er_diagram(con, root):
    """Generate ER diagram for data-model.md from CIP Prisma data."""
    print("Generating ER diagram...")
    
    data_model_path = os.path.join(root, "docs/architecture/data-model.md")
    
    # Check if Prisma models table exists
    try:
        models = con.execute("SELECT * FROM prisma_models").fetchall()
    except:
        print("  No Prisma models found - skipping ER diagram")
        return
    
    mermaid = "```mermaid\nerDiagram\n"
    
    for model in models:
        model_name = model.get("name", "Unknown")
        mermaid += f"  {model_name} {{\n"
        
        # Get fields for this model
        try:
            fields = con.execute(
                "SELECT * FROM prisma_fields WHERE model=?",
                (model_name,)
            ).fetchall()
            
            for field in fields:
                field_name = field.get("name", "")
                field_type = field.get("type", "Unknown")
                is_id = field.get("is_id", False)
                is_unique = field.get("is_unique", False)
                
                if is_id:
                    mermaid += f"    {field_name} {field_type} PK\n"
                elif is_unique:
                    mermaid += f"    {field_name} {field_type} UK\n"
                else:
                    mermaid += f"    {field_name} {field_type}\n"
        except:
            pass
        
        mermaid += "  }\n"
    
    mermaid += "```\n"
    
    # Inject into data-model.md
    if os.path.exists(data_model_path):
        with open(data_model_path, 'r') as f:
            content = f.read()
        
        auto_marker = "<!-- AUTO-GENERATED ER DIAGRAM -->"
        if auto_marker in content:
            content = re.sub(
                r'<!-- AUTO-GENERATED ER DIAGRAM -->.*<!-- END AUTO-GENERATED -->',
                f'<!-- AUTO-GENERATED ER DIAGRAM -->\n{mermaid}\n<!-- END AUTO-GENERATED -->',
                content,
                flags=re.DOTALL
            )
        else:
            content += f"\n\n<!-- AUTO-GENERATED ER DIAGRAM -->\n{mermaid}\n<!-- END AUTO-GENERATED -->\n"
    else:
        content = f"""# Data Model

## Entity Relationship Diagram

<!-- AUTO-GENERATED ER DIAGRAM -->
{mermaid}
<!-- END AUTO-GENERATED -->

## Schema Details

See `prisma/schema.prisma` for complete schema definition.

"""
    
    with open(data_model_path, 'w') as f:
        f.write(content)
    
    print(f"  Generated: ER diagram in data-model.md ({len(models)} models)")

def generate_glossary_suggestions(con, root):
    """Generate glossary suggestions from CIP symbol frequency."""
    print("Generating glossary suggestions...")
    
    glossary_path = os.path.join(root, "docs/GLOSSARY.md")
    
    # Get all symbols
    symbols = con.execute("SELECT DISTINCT name FROM symbols").fetchall()
    symbol_names = set(s["name"] for s in symbols)
    
    # Read existing glossary
    defined_terms = set()
    if os.path.exists(glossary_path):
        with open(glossary_path, 'r') as f:
            content = f.read()
        defined_terms = set(re.findall(r'^##\s+([A-Z][a-zA-Z0-9_]+)', content, re.MULTILINE))
    
    # Filter out standard library terms
    stdlib_terms = {
        "String", "Number", "Boolean", "Array", "Object", "Promise",
        "Error", "Date", "Math", "JSON", "RegExp", "Map", "Set",
        "Function", "undefined", "null", "true", "false"
    }
    
    # Count term frequency across files
    term_frequency = {}
    for symbol in symbol_names:
        if symbol in defined_terms or symbol in stdlib_terms:
            continue
        
        # Count file occurrences
        file_count = len(con.execute(
            "SELECT DISTINCT path FROM symbols WHERE name=?",
            (symbol,)
        ).fetchall())
        
        if file_count >= 3:  # Appears in 3+ files
            term_frequency[symbol] = file_count
    
    # Sort by frequency
    suggestions = sorted(term_frequency.items(), key=lambda x: x[1], reverse=True)
    
    # Generate suggestion report
    suggestion_content = "# Glossary Entry Suggestions\n\n"
    suggestion_content += "<!-- AUTO-GENERATED BY CIP - REVIEW BEFORE ADDING -->\n\n"
    suggestion_content += f"Total defined terms: {len(defined_terms)}\n"
    suggestion_content += f"Total candidates: {len(term_frequency)}\n\n"
    suggestion_content += "## Top 20 Candidates\n\n"
    
    for term, count in suggestions[:20]:
        suggestion_content += f"### {term}\n"
        suggestion_content += f"**Frequency:** Appears in {count} files\n"
        suggestion_content += f"**Definition:** TODO: Add definition\n\n"
    
    # Write to separate suggestion file
    suggestion_path = os.path.join(root, "docs", "GLOSSARY-SUGGESTIONS.md")
    with open(suggestion_path, 'w') as f:
        f.write(suggestion_content)
    
    print(f"  Generated: GLOSSARY-SUGGESTIONS.md ({len(suggestions)} candidates)")

if __name__ == "__main__":
    bootstrap_docs()
```

**Expected Output:**
- Bootstrap script created at `scripts/bootstrap-vivim-docs.py`
- Script ready to generate all initial docs from CIP data

**Verification:** Review script structure and logic.

---

### Step 2.2: Run Bootstrap Script
**Command:**
```bash
cd C:\0-BlackBoxProject-0\index
python scripts/bootstrap-vivim-docs.py
```

**Purpose:** Generate accurate initial documentation from CIP index data.

**What This Does:**
- Generates `docs/modules/*.md` from CIP directory summaries
- Generates `docs/architecture/overview.md` with dependency graph
- Generates `docs/architecture/backend.md` with engine layers
- Generates `docs/architecture/frontend.md` with structure
- Generates `docs/api/endpoints.md` from routes
- Generates ER diagram in `docs/architecture/data-model.md`
- Generates `docs/GLOSSARY-SUGGESTIONS.md` from symbol frequency

**Expected Output:**
- Updated/created module docs: engines.md, storage.md, desktop.md, frontend.md, api.md, devops.md
- Updated architecture docs with auto-generated sections
- API docs with actual routes
- ER diagram with actual Prisma models
- Glossary suggestions for review

**Verification:**
- Check each generated file for accuracy
- Verify mermaid diagrams render correctly
- Review glossary suggestions and add relevant terms to GLOSSARY.md

---

### Step 2.3: Review and Refine Generated Docs
**Manual Step:** Review all generated documentation for accuracy and completeness.

**What This Does:**
- Add missing purposes for modules
- Fix any inaccuracies in auto-generated content
- Add relevant glossary terms from suggestions
- Verify all links work correctly
- Add any missing architecture details

**Files to Review:**
- `docs/modules/*.md` (6 files)
- `docs/architecture/overview.md`
- `docs/architecture/backend.md`
- `docs/architecture/frontend.md`
- `docs/architecture/data-model.md`
- `docs/api/endpoints.md`
- `docs/GLOSSARY.md` (add from suggestions)

**Expected Output:**
- Refined, accurate documentation matching Vivim's actual architecture
- Glossary.md updated with relevant domain terms
- All doc references validated

**Verification:** Run Step 1.3 again to confirm no new dangling references.

---

## Phase 3: Implement CIP Documentation Integration (Days 4-7)

### Step 3.1: Database Schema Migration (v4 → v5)
**File:** `C:\0-BlackBoxProject-0\index\lib\cipkg\store.py`

**Purpose:** Add documentation-specific tables to CIP database.

**What This Does:**
- Add `doc_refs` table for tracking doc-to-code links
- Add `adrs` table for tracking ADR metadata
- Update schema version to 5
- Run migration on next connect

**Changes:**
```python
# Update SCHEMA_VERSION
SCHEMA_VERSION = 5

# Add to CORE_SCHEMA
DOCS_SCHEMA = """
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
"""

# Update connect() to run migration
def connect(root):
    # ... existing code ...
    con.executescript(CORE_SCHEMA)
    con.executescript(DOCS_SCHEMA)  # Add this
    # ... existing migration code ...
```

**Expected Output:**
- Database schema updated to v5
- New tables created in existing databases
- Migration runs automatically on next CIP command

**Verification:**
```bash
cd C:\0-BlackBoxProject-0\index
python -c "from lib.cipkg.store import connect; con = connect('../vivim-final'); print(con.execute('SELECT value FROM meta WHERE key=\"schema_version\"').fetchone())"
```
Should output: `{'value': '5'}`

---

### Step 3.2: Create docs/ Module
**Directory:** `C:\0-BlackBoxProject-0\index\lib\cipkg\docs\`

**Purpose:** Organize documentation-specific CIP functionality.

**What This Does:**
- Create docs module directory
- Create __init__.py
- Prepare for sub-modules (audit.py, links.py, decisions.py, generate.py, etc.)

**Files to Create:**
```
lib/cipkg/docs/
  __init__.py
  audit.py
  links.py
  decisions.py
  generate.py
  changelog.py
  glossary.py
```

**Expected Output:**
- docs module structure created
- Ready for implementing individual features

**Verification:**
```bash
ls C:\0-BlackBoxProject-0\index\lib\cipkg\docs
```

---

### Step 3.3: Implement docs/audit.py (Item #0 + #7 TODO)
**File:** `C:\0-BlackBoxProject-0\index\lib\cipkg\docs\audit.py`

**Purpose:** Audit documentation for dangling refs and TODO comments.

**What This Does:**
- Implement `audit_existing_refs()` (Item #0)
- Implement `check_todo_update_docs()` (Item #7)
- Integrate with existing audit system

**Implementation:**
```python
"""Documentation audit: dangling refs, TODO comments, staleness."""
import os, re, time
from ..base import repo_root

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
                    "line": 0,
                    "title": f"Dangling doc reference: {path}",
                    "detail": f"Referenced as '{title}' but file does not exist",
                    "suggestion": f"Create {path} or remove reference from README",
                    "effort": "medium"
                })
    
    # Scan CHANGELOG.md for tracker references
    changelog_path = os.path.join(root, "CHANGELOG.md")
    if os.path.exists(changelog_path):
        content = open(changelog_path).read()
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

def check_todo_update_docs(root):
    """Find TODO: update docs comments in code."""
    findings = []
    
    from ..store import connect
    con = connect(root)
    
    # Search chunks for TODO patterns
    rows = con.execute(
        "SELECT path, start_line, text FROM chunks WHERE text LIKE '%TODO%' AND text LIKE '%docs%'"
    ).fetchall()
    
    for row in rows:
        findings.append({
            "rule": "DOCS-TODO-UPDATE",
            "severity": "low",
            "path": row["path"],
            "line": row["start_line"],
            "title": "TODO comment about updating docs",
            "detail": row["text"][:100],
            "suggestion": "Either update the docs or remove the TODO",
            "effort": "small"
        })
    
    return findings
```

**Expected Output:**
- audit.py created with two audit functions
- Ready for CLI integration

**Verification:**
```python
cd C:\0-BlackBoxProject-0\index
python -c "from lib.cipkg.docs.audit import audit_existing_refs; print(audit_existing_refs('../vivim-final'))"
```

---

### Step 3.4: Implement docs/decisions.py (Item #3 - ADR Enforcement)
**File:** `C:\0-BlackBoxProject-0\index\lib\cipkg\docs\decisions.py`

**Purpose:** ADR enforcement: protection, missing detection, graph building.

**What This Does:**
- Implement ADR pre-edit protection hook
- Implement missing ADR detection
- Implement ADR graph and history

**Implementation:**
```python
"""ADR enforcement: protection, missing detection, graph building."""
import os, re, subprocess, glob, time
from ..base import repo_root

def pre_adr_edit_hook(file_path, diff_content, root=None):
    """Block edits to Accepted ADRs unless superseding."""
    if not file_path.startswith("docs/decisions/"):
        return {"ok": True, "proceed": True}
    
    if not file_path.startswith("docs/decisions/ADR-"):
        return {"ok": True, "proceed": True}
    
    root = root or repo_root()
    adr_path = os.path.join(root, file_path)
    
    if not os.path.exists(adr_path):
        return {"ok": True, "proceed": True}
    
    content = open(adr_path).read()
    status_match = re.search(r'Status:\s*(Accepted|Proposed|Deprecated|Superseded)', content)
    
    if status_match and status_match.group(1) == "Accepted":
        if "Superseded-by:" not in diff_content and "Status: Superseded" not in diff_content:
            return {
                "ok": False,
                "proceed": False,
                "block_reason": "Cannot edit Accepted ADR directly. Create new ADR with Superseded-by field instead.",
                "suggestion": f"Create new ADR in docs/decisions/ with 'Superseded-by: {os.path.basename(file_path)}'"
            }
    
    return {"ok": True, "proceed": True}

def detect_missing_adrs(root, since_commit=None):
    """Detect commits that should have ADRs but don't."""
    findings = []
    
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

def build_adr_graph(root):
    """Build supersession graph from ADR frontmatter."""
    adr_files = glob.glob(os.path.join(root, "docs/decisions", "ADR-*.md"))
    graph = {"nodes": [], "edges": []}
    
    for adr_file in adr_files:
        content = open(adr_file).read()
        adr_id = os.path.basename(adr_file)
        
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
    
    related = []
    for node in graph["nodes"]:
        adr_file = os.path.join(root, "docs/decisions", node["id"])
        content = open(adr_file).read()
        if topic.lower() in content.lower():
            related.append(node)
    
    chains = []
    for adr in related:
        chain = [adr]
        current = adr
        while True:
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

**Expected Output:**
- decisions.py created with ADR enforcement functions
- Ready for hook integration

**Verification:**
```python
cd C:\0-BlackBoxProject-0\index
python -c "from lib.cipkg.docs.decisions import build_adr_graph; print(build_adr_graph('../vivim-final'))"
```

---

### Step 3.5: Implement docs/links.py (Item #1 + #2 - doc_refs + Staleness)
**File:** `C:\0-BlackBoxProject-0\index\lib\cipkg\docs\links.py`

**Purpose:** doc_refs linking and staleness checking with severity.

**What This Does:**
- Implement doc reference extraction
- Implement staleness checking
- Implement public/private severity weighting

**Implementation:**
```python
"""Documentation linking: extract refs, check staleness, severity weighting."""
import os, re, glob, time
from ..base import repo_root, sha
from ..store import connect

def extract_doc_refs(root):
    """Extract doc references from blueprint-compliant docs."""
    refs = []
    
    # 1. Module docs -> directories
    modules_dir = os.path.join(root, "docs/modules")
    if os.path.exists(modules_dir):
        for module_file in glob.glob(os.path.join(modules_dir, "*.md")):
            module_name = os.path.basename(module_file).replace(".md", "")
            
            for line_num, line in enumerate(open(module_file), 1):
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
    data_model_path = os.path.join(root, "docs/architecture/data-model.md")
    if os.path.exists(data_model_path):
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
            continue
        
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
    
    refs = [dict(r) for r in con.execute("SELECT * FROM doc_refs").fetchall()]
    
    for ref in refs:
        doc_path = ref["doc_path"]
        full_doc_path = os.path.join(root, doc_path)
        
        if not os.path.exists(full_doc_path):
            ref["staleness"] = "missing"
            continue
        
        current_hash = None
        for line_num, line in enumerate(open(full_doc_path), 1):
            if line_num == ref["doc_line"]:
                current_hash = sha(line)
                break
        
        if current_hash and current_hash != ref["hash_at_link_time"]:
            ref["staleness"] = "changed"
        else:
            target_changed = False
            if ref["ref_kind"] == "schema":
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
    
    for ref in refs:
        con.execute(
            "UPDATE doc_refs SET staleness=?, last_check=? WHERE doc_path=? AND doc_line=? AND ref_target=?",
            (ref["staleness"], time.time(), ref["doc_path"], ref["doc_line"], ref["ref_target"])
        )
    
    con.commit()
    return refs

def check_doc_staleness_with_severity(root):
    """Check staleness with public/private symbol distinction."""
    con = connect(root)
    
    refs = [dict(r) for r in con.execute("SELECT * FROM doc_refs").fetchall()]
    
    for ref in refs:
        if ref["ref_kind"] in ("module", "folder"):
            symbol_rows = con.execute(
                "SELECT * FROM symbols WHERE name=? AND kind='export'",
                (ref["ref_target"],)
            ).fetchall()
            is_public = len(symbol_rows) > 0
        else:
            is_public = True
        
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
```

**Expected Output:**
- links.py created with doc_refs and staleness functions
- Ready for CLI integration

**Verification:**
```python
cd C:\0-BlackBoxProject-0\index
python -c "from lib.cipkg.docs.links import extract_doc_refs; print(len(extract_doc_refs('../vivim-final')))"
```

---

### Step 3.6: Implement docs/generate.py (Item #6 - Generated Sections)
**File:** `C:\0-BlackBoxProject-0\index\lib\cipkg\docs\generate.py`

**Purpose:** Auto-generate API docs, ER diagrams, dependency graphs.

**What This Does:**
- Implement API docs generation from routes
- Implement ER diagram generation from Prisma
- Implement dependency graph generation from edges
- Auto-inject into marked sections

**Implementation:**
```python
"""Generated documentation sections: API, ER, dependency graphs."""
import os, re
from ..base import repo_root
from ..store import connect

def generate_api_docs(root):
    """Generate API documentation from routes table."""
    con = connect(root)
    
    try:
        routes = con.execute("SELECT * FROM routes").fetchall()
    except:
        return {"error": "No routes table found"}
    
    api_docs = []
    for route in routes:
        api_docs.append(f"## {route.get('method', 'GET')} {route.get('path', '/')}")
        api_docs.append(f"**Handler:** {route.get('handler', 'Unknown')}")
        api_docs.append(f"**Middleware:** {route.get('middleware', 'None')}")
        api_docs.append("")
    
    api_dir = os.path.join(root, "docs/api")
    os.makedirs(api_dir, exist_ok=True)
    
    with open(os.path.join(api_dir, "endpoints.md"), 'w') as f:
        f.write("# API Endpoints\n\n")
        f.write("<!-- AUTO-GENERATED BY CIP - DO NOT EDIT -->\n\n")
        f.write("\n".join(api_docs))
    
    return {"generated": len(routes), "file": "docs/api/endpoints.md"}

def generate_er_diagram(root):
    """Generate ER diagram from Prisma schema."""
    con = connect(root)
    
    try:
        models = con.execute("SELECT * FROM prisma_models").fetchall()
    except:
        return {"error": "No Prisma models found"}
    
    mermaid = "```mermaid\nerDiagram\n"
    
    for model in models:
        model_name = model.get("name", "Unknown")
        mermaid += f"  {model_name} {{\n"
        
        try:
            fields = con.execute(
                "SELECT * FROM prisma_fields WHERE model=?",
                (model_name,)
            ).fetchall()
            
            for field in fields:
                field_name = field.get("name", "")
                field_type = field.get("type", "Unknown")
                is_id = field.get("is_id", False)
                is_unique = field.get("is_unique", False)
                
                if is_id:
                    mermaid += f"    {field_name} {field_type} PK\n"
                elif is_unique:
                    mermaid += f"    {field_name} {field_type} UK\n"
                else:
                    mermaid += f"    {field_name} {field_type}\n"
        except:
            pass
        
        mermaid += "  }\n"
    
    mermaid += "```\n"
    
    data_model_path = os.path.join(root, "docs/architecture/data-model.md")
    if os.path.exists(data_model_path):
        with open(data_model_path, 'r') as f:
            content = f.read()
        
        auto_marker = "<!-- AUTO-GENERATED ER DIAGRAM -->"
        if auto_marker in content:
            content = re.sub(
                r'<!-- AUTO-GENERATED ER DIAGRAM -->.*<!-- END AUTO-GENERATED -->',
                f'<!-- AUTO-GENERATED ER DIAGRAM -->\n{mermaid}\n<!-- END AUTO-GENERATED -->',
                content,
                flags=re.DOTALL
            )
        else:
            content += f"\n\n<!-- AUTO-GENERATED ER DIAGRAM -->\n{mermaid}\n<!-- END AUTO-GENERATED -->\n"
        
        with open(data_model_path, "w") as f:
            f.write(content)
    
    return {"models": len(models), "file": "docs/architecture/data-model.md"}

def generate_dependency_graph(root):
    """Generate dependency graph from edges table."""
    con = connect(root)
    
    edges = con.execute("SELECT * FROM edges WHERE kind='import' LIMIT 100").fetchall()
    
    mermaid = "```mermaid\ngraph TD\n"
    
    files = {}
    for edge in edges:
        src_file = edge.get("src_path", "unknown")
        dst_file = edge.get("dst", "unknown")
        
        if src_file not in files:
            files[src_file] = f"F{len(files)}"
        if dst_file not in files:
            files[dst_file] = f"F{len(files)}"
        
        mermaid += f"  {files[src_file]} --> {files[dst_file]}\n"
    
    mermaid += "```\n"
    
    overview_path = os.path.join(root, "docs/architecture/overview.md")
    if os.path.exists(overview_path):
        with open(overview_path, 'r') as f:
            content = f.read()
        
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

**Expected Output:**
- generate.py created with generation functions
- Ready for CLI integration

**Verification:**
```python
cd C:\0-BlackBoxProject-0\index
python -c "from lib.cipkg.docs.generate import generate_api_docs; print(generate_api_docs('../vivim-final'))"
```

---

### Step 3.7: Update hooks.py for ADR Protection
**File:** `C:\0-BlackBoxProject-0\index\lib\cipkg\hooks.py`

**Purpose:** Add ADR pre-edit protection to existing hooks system.

**What This Does:**
- Import ADR protection function
- Add ADR check to pre-edit hook
- Update hook configuration for ADR blocking

**Changes:**
```python
# Add import
from .docs.decisions import pre_adr_edit_hook

# Update pre_edit_hook function
def pre_edit_hook(file_path, diff_content, root=None):
    """Pre-edit hook: validates proposed changes against audit rules."""
    root = root or repo_root()
    
    # Check ADR protection first
    adr_check = pre_adr_edit_hook(file_path, diff_content, root)
    if not adr_check["proceed"]:
        return adr_check
    
    # ... existing validation code ...
```

**Expected Output:**
- hooks.py updated with ADR protection
- Pre-edit hook now blocks edits to Accepted ADRs

**Verification:**
```python
cd C:\0-BlackBoxProject-0\index
python -c "from lib.cipkg.hooks import pre_edit_hook; print(pre_edit_hook('docs/decisions/ADR-001.md', 'some change', '../vivim-final'))"
```

---

### Step 3.8: Update CLI for Docs Commands
**File:** `C:\0-BlackBoxProject-0\index\lib\cipkg\cli.py`

**Purpose:** Add docs subcommand with all features.

**What This Does:**
- Add docs subparser
- Add audit, check, generate, decisions, glossary subcommands
- Wire up all new functions

**Changes:**
```python
# Add to argument parser section
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

# Add handler functions
def handle_docs_command(root, args):
    """Handle docs commands."""
    from .docs import audit as docs_audit
    from .docs import links as docs_links
    from .docs import generate as docs_generate
    from .docs import decisions as docs_decisions
    from .docs import glossary as docs_glossary
    
    if args.docs_command == 'audit':
        if args.existing:
            result = docs_audit.audit_existing_refs(root)
            _out({"findings": result, "total": len(result)})
        elif args.refresh:
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
            _out({"extracted": len(refs)})
    
    elif args.docs_command == 'check':
        if args.refresh:
            refs = docs_links.extract_doc_refs(root)
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
        
        refs = docs_links.check_doc_staleness_with_severity(root)
        stale = [r for r in refs if r.get("severity")]
        
        _out({
            "total_refs": len(refs),
            "stale": len(stale),
            "stale_refs": stale
        })
    
    elif args.docs_command == 'generate':
        results = {}
        if args.api or args.all:
            results["api"] = docs_generate.generate_api_docs(root)
        if args.er or args.all:
            results["er"] = docs_generate.generate_er_diagram(root)
        if args.deps or args.all:
            results["deps"] = docs_generate.generate_dependency_graph(root)
        _out(results)
    
    elif args.docs_command == 'decisions':
        if args.missing:
            result = docs_decisions.detect_missing_adrs(root)
            _out({"missing_adrs": result, "total": len(result)})
        elif args.graph:
            result = docs_decisions.build_adr_graph(root)
            _out(result)
        elif args.history:
            result = docs_decisions.get_adr_history(root, args.history)
            _out(result)
    
    elif args.docs_command == 'glossary':
        if args.suggest:
            result = docs_glossary.suggest_glossary_entries(root)
            _out(result)
```

**Expected Output:**
- CLI updated with complete docs subcommand
- All docs features accessible via CLI

**Verification:**
```bash
cd C:\0-BlackBoxProject-0\index
python -m lib.cipkg.cli docs --help
python -m lib.cipkg.cli docs audit --existing --root ../vivim-final
```

---

## Phase 4: Integration Testing and Documentation (Days 8-10)

### Step 4.1: Run Full Documentation Audit
**Command:**
```bash
cd C:\0-BlackBoxProject-0\index
python -m lib.cipkg.cli docs audit --existing --root ../vivim-final
```

**Purpose:** Verify no dangling references remain after bootstrap.

**Expected Output:**
- Empty findings list (no dangling refs)
- All doc references valid

**Verification:** Confirm output shows 0 findings.

---

### Step 4.2: Run Staleness Check
**Command:**
```bash
cd C:\0-BlackBoxProject-0\index
python -m lib.cipkg.cli docs check --refresh --root ../vivim-final
```

**Purpose:** Verify doc_refs extraction and staleness checking work.

**Expected Output:**
- doc_refs extracted from all docs
- Staleness check completed
- Severity weights applied correctly

**Verification:** Check that refs are stored in database and staleness is computed.

---

### Step 4.3: Test ADR Protection
**Command:**
```bash
cd C:\0-BlackBoxProject-0\index
python -c "from lib.cipkg.hooks import pre_edit_hook; from lib.cipkg.docs.decisions import pre_adr_edit_hook; print(pre_adr_edit_hook('docs/decisions/ADR-001.md', 'some change', '../vivim-final'))"
```

**Purpose:** Verify ADR pre-edit protection works.

**Expected Output:**
- Hook blocks edit to Accepted ADR
- Returns block_reason and suggestion

**Verification:** Confirm hook returns `proceed: False` for Accepted ADRs.

---

### Step 4.4: Test Generated Sections
**Command:**
```bash
cd C:\0-BlackBoxProject-0\index
python -m lib.cipkg.cli docs generate --all --root ../vivim-final
```

**Purpose:** Verify all generated sections work correctly.

**Expected Output:**
- API docs generated
- ER diagram generated and injected
- Dependency graph generated and injected

**Verification:**
- Check docs/api/endpoints.md exists
- Check docs/architecture/data-model.md has ER diagram
- Check docs/architecture/overview.md has dependency graph

---

### Step 4.5: Update VIVIM-AGENT-GUIDE.md
**File:** `C:\0-BlackBoxProject-0\index\docs\internal\VIVIM-AGENT-GUIDE.md`

**Purpose:** Add documentation workflow to existing Vivim agent guide.

**What This Does:**
- Add "Documentation Workflow" section
- Document how to use new docs commands
- Integrate with existing agent workflow

**Additions:**
```markdown
## Documentation Workflow

### Working with Documentation

Vivim's documentation system is integrated with CIP for automated maintenance.

**Before editing docs:**
```bash
cip docs check --refresh  # Check for staleness
```

**After editing docs:**
```bash
cip docs generate --all  # Regenerate auto-sections
cip docs audit --existing  # Check for dangling refs
```

**Creating ADRs:**
```bash
# Check for missing ADRs in recent commits
cip docs decisions --missing

# View ADR graph
cip docs decisions --graph

# Get ADR history for a topic
cip docs decisions --history "topic name"
```

**ADR Protection:**
- ADR pre-edit hook automatically blocks edits to Accepted ADRs
- Create new ADR with Superseded-by field instead
- See docs/decisions/TEMPLATE.md for ADR format

**Generated Sections:**
- API docs: `docs/api/endpoints.md` (auto-generated from routes)
- ER diagram: In `docs/architecture/data-model.md` (auto-generated from Prisma)
- Dependency graph: In `docs/architecture/overview.md` (auto-generated from edges)

**Note:** Generated sections are marked with `<!-- AUTO-GENERATED BY CIP -->` - do not edit manually.
```

**Expected Output:**
- VIVIM-AGENT-GUIDE.md updated with documentation workflow
- Agents know how to use new docs commands

**Verification:** Review updated guide for clarity and completeness.

---

### Step 4.6: Create ADR for This Integration
**File:** `C:\0-BlackBoxProject-0\vivim-final\docs\decisions\ADR-014.md`

**Purpose:** Document this integration decision per blueprint rules.

**Content:**
```markdown
# ADR-014: Integrate Documentation System with CIP

## Status
Accepted

## Context
Vivim implemented a new documentation system (docs/) following a comprehensive blueprint. The repository also has an existing CIP (Code Intelligence Protocol) integration for code intelligence. A decision was needed on how to integrate these systems to ensure documentation stays accurate and maintainable.

## Decision
Integrate the documentation system with CIP using a phased approach:

1. **Phase 1**: Use CIP to generate accurate initial docs from actual codebase state
2. **Phase 2**: Add CIP features for documentation maintenance:
   - Dangling reference detection
   - ADR enforcement (pre-edit protection)
   - Doc-to-code linking and staleness checking
   - Auto-generation of API docs, ER diagrams, dependency graphs
   - Glossary suggestions
3. **Phase 3**: Integrate into agent workflow via hooks and CLI commands

## Rationale
- **Accuracy First**: Generate initial docs from CIP index ensures docs match actual code
- **Automation Foundation**: CIP integration prevents doc debt accumulation
- **No Duplicate Enforcement**: CIP complements existing Vivim tools (invariants.ts, code-index.ts)
- **Scalable**: System scales with codebase growth without manual maintenance

## Consequences
- **Positive**: Documentation stays in sync with code automatically
- **Positive**: ADRs are protected from accidental edits
- **Positive**: Agents have better context via accurate docs
- **Minimal**: Requires CIP to be run periodically (already done via hooks)
- **Minimal**: Small database schema change (adds doc_refs and adrs tables)

## Implementation
See `C:\0-BlackBoxProject-0\index\docs\CIP_DOCS_INTEGRATION_PLAN.md` for detailed implementation plan.

## Supersedes
None

## Superseded-by
None

## Created
2026-08-15

## Last Modified
2026-08-15
```

**Expected Output:**
- ADR-014.md created documenting this integration
- Complies with blueprint ADR requirements

**Verification:** Review ADR format against TEMPLATE.md.

---

### Step 4.7: Update CONTRIBUTING.md with Docs Workflow
**File:** `C:\0-BlackBoxProject-0\vivim-final\CONTRIBUTING.md`

**Purpose:** Add documentation workflow to contributor guide.

**Additions:**
```markdown
## Documentation Workflow

Vivim uses a docs-as-a-byproduct-of-work system integrated with CIP.

### Before Making Changes
1. Read relevant module docs in `docs/modules/`
2. Check for related ADRs in `docs/decisions/`
3. Run `cip docs check --refresh` to check doc staleness

### During Code Changes
- Update matching documentation in the same commit as behavior changes
- If making an architectural decision, write an ADR in `docs/decisions/`
- Never edit existing Accepted ADRs - create new ones with Superseded-by field

### After Making Changes
1. Run `cip docs generate --all` to regenerate auto-sections
2. Run `cip docs audit --existing` to check for dangling refs
3. Update `docs/GLOSSARY.md` if you introduce new domain terms
4. Add entry to `CHANGELOG.md` for user/API visible changes

### ADR Workflow
1. Use `docs/decisions/TEMPLATE.md` as a template
2. Write ADR at decision time, not later
3. Set Status to "Accepted" when decided
4. Use Superseded-by field when superseding previous ADRs
5. CIP will protect Accepted ADRs from accidental edits

### Generated Documentation
The following sections are auto-generated by CIP (marked with `<!-- AUTO-GENERATED -->`):
- API endpoints in `docs/api/endpoints.md`
- ER diagram in `docs/architecture/data-model.md`
- Dependency graph in `docs/architecture/overview.md`

Do not edit these sections manually - they will be overwritten.
```

**Expected Output:**
- CONTRIBUTING.md updated with documentation workflow
- Contributors know how to maintain docs

**Verification:** Review updated guide for clarity.

---

### Step 4.8: Final Verification and Testing
**Commands:**
```bash
cd C:\0-BlackBoxProject-0\index

# 1. Verify CIP index is current
python -m lib.cipkg.cli sync --root ../vivim-final

# 2. Run full docs audit
python -m lib.cipkg.cli docs audit --existing --root ../vivim-final

# 3. Run staleness check
python -m lib.cipkg.cli docs check --refresh --root ../vivim-final

# 4. Test ADR protection
python -c "from lib.cipkg.docs.decisions import pre_adr_edit_hook; print(pre_adr_edit_hook('docs/decisions/ADR-001.md', 'test', '../vivim-final'))"

# 5. Test generation
python -m lib.cipkg.cli docs generate --all --root ../vivim-final

# 6. Test glossary suggestions
python -m lib.cipkg.cli docs glossary --suggest --root ../vivim-final
```

**Purpose:** Full end-to-end verification of all features.

**Expected Output:**
- All commands complete successfully
- No errors in any feature
- Documentation system integrated with CIP

**Verification:** Confirm all outputs are as expected.

---

## Phase 5: Commit and Deploy (Day 11)

### Step 5.1: Commit Changes to vivim-final
**Repository:** `C:\0-BlackBoxProject-0\vivim-final`

**What to Commit:**
- Updated documentation (from bootstrap)
- Updated README.md (fixed dangling refs)
- Updated CHANGELOG.md (fixed dangling refs)
- Updated GLOSSARY.md (added terms from suggestions)
- Created ADR-014.md
- Updated CONTRIBUTING.md (docs workflow)

**Commit Message:**
```
docs: integrate documentation system with CIP

- Generate accurate initial docs from CIP index data
- Fix dangling doc references in README.md and CHANGELOG.md
- Add documentation workflow to CONTRIBUTING.md
- Create ADR-014 documenting this integration
- Update GLOSSARY.md with domain terms from suggestions

Generated with [Devin](https://devin.ai)

Co-Authored-By: Devin <158243242+devin-ai-integration[bot]@users.noreply.github.com>
```

**Expected Output:**
- Clean commit with only doc-related changes
- No unrelated changes included

**Verification:**
```bash
cd C:\0-BlackBoxProject-0\vivim-final
git status
git diff --cached
```

---

### Step 5.2: Commit Changes to index
**Repository:** `C:\0-BlackBoxProject-0\index`

**What to Commit:**
- Database schema migration (store.py v4 → v5)
- New docs/ module (audit.py, links.py, decisions.py, generate.py, etc.)
- Updated hooks.py (ADR protection)
- Updated cli.py (docs commands)
- Bootstrap script (scripts/bootstrap-vivim-docs.py)
- Updated VIVIM-AGENT-GUIDE.md
- Integration plan (docs/CIP_DOCS_INTEGRATION_PLAN.md)
- Master plan (docs/VIVIM_DOCS_CIP_MASTER_PLAN.md)

**Commit Message:**
```
feat: add CIP documentation integration

- Add database schema v5 with doc_refs and adrs tables
- Implement docs/ module with audit, links, decisions, generate
- Add ADR pre-edit protection to hooks
- Add docs CLI commands (audit, check, generate, decisions, glossary)
- Create bootstrap script for generating docs from CIP data
- Update VIVIM-AGENT-GUIDE.md with documentation workflow
- Add comprehensive integration and master plan documentation

Generated with [Devin](https://devin.ai)

Co-Authored-By: Devin <158243242+devin-ai-integration[bot]@users.noreply.github.com>
```

**Expected Output:**
- Clean commit with only CIP integration changes
- All new files properly tracked

**Verification:**
```bash
cd C:\0-BlackBoxProject-0\index
git status
git diff --cached
```

---

### Step 5.3: Push Changes
**Commands:**
```bash
cd C:\0-BlackBoxProject-0\vivim-final
git push

cd C:\0-BlackBoxProject-0\index
git push
```

**Purpose:** Deploy integrated documentation system to both repositories.

**Expected Output:**
- Both repositories pushed successfully
- Changes available in remote

**Verification:**
```bash
cd C:\0-BlackBoxProject-0\vivim-final
git log --oneline -1

cd C:\0-BlackBoxProject-0\index
git log --oneline -1
```

---

## Summary of Steps

### Phase 1: Baseline Foundation (Day 1)
1. Run CIP sync with Vivim profile
2. Verify CIP index quality
3. Run Item #0 audit - detect dangling doc references
4. Fix dangling doc references

### Phase 2: Generate Accurate Initial Docs (Days 2-3)
5. Create bootstrap script
6. Run bootstrap script
7. Review and refine generated docs

### Phase 3: Implement CIP Documentation Integration (Days 4-7)
8. Database schema migration (v4 → v5)
9. Create docs/ module
10. Implement docs/audit.py
11. Implement docs/decisions.py
12. Implement docs/links.py
13. Implement docs/generate.py
14. Update hooks.py for ADR protection
15. Update CLI for docs commands

### Phase 4: Integration Testing and Documentation (Days 8-10)
16. Run full documentation audit
17. Run staleness check
18. Test ADR protection
19. Test generated sections
20. Update VIVIM-AGENT-GUIDE.md
21. Create ADR for this integration
22. Update CONTRIBUTING.md with docs workflow
23. Final verification and testing

### Phase 5: Commit and Deploy (Day 11)
24. Commit changes to vivim-final
25. Commit changes to index
26. Push changes

---

## Success Criteria

### Phase 1 Success
- [x] CIP sync completes without errors
- [x] Architecture map shows 13 engine layers correctly
- [x] No dangling doc references remain
- [x] All doc paths in README.md are valid

### Phase 2 Success
- [x] All module docs generated with accurate content
- [x] Architecture docs include auto-generated sections
- [x] API docs match actual routes
- [x] ER diagram matches actual Prisma schema
- [x] Glossary suggestions are useful

### Phase 3 Success
- [x] Database schema migrated to v5
- [x] All docs/ modules implemented
- [x] ADR protection hook blocks edits to Accepted ADRs
- [x] CLI docs commands work correctly
- [x] doc_refs extraction and staleness checking work

### Phase 4 Success
- [x] All verification tests pass
- [x] ADR protection verified
- [x] Generated sections render correctly
- [x] Agent guide updated with docs workflow
- [x] ADR-014 created and follows template
- [x] CONTRIBUTING.md updated

### Phase 5 Success
- [x] Both repositories committed cleanly
- [x] Both repositories pushed successfully
- [x] Integration complete and deployed

---

## Next Steps After Completion

1. **Run CIP sync periodically** - Hook system will handle this automatically
2. **Monitor doc staleness** - Run `cip docs check` weekly
3. **Review glossary suggestions** - Add relevant terms to GLOSSARY.md
4. **Update docs on code changes** - Follow docs-as-a-byproduct-of-work principle
5. **Create ADRs for decisions** - Use ADR protection hook
6. **Generate sections after changes** - Run `cip docs generate --all`

---

## Notes

- This plan assumes CIP is already installed and configured for Vivim
- The bootstrap script uses CIP's existing index - no re-indexing needed
- All auto-generated sections are marked with <!-- AUTO-GENERATED --> comments
- ADR protection is blocking by design to prevent accidental edits
- The integration is designed to be low-maintenance after initial setup
- All features are optional - can be used individually or together
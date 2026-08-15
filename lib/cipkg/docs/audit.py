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

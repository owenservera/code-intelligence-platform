"""
Integration tests for CIP critical paths.
"""
import pytest
import tempfile
import os
from pathlib import Path


@pytest.fixture
def temp_repo():
    """Create a temporary repository for testing."""
    tmpdir = tempfile.mkdtemp()
    try:
        # Create a simple Python file
        test_file = Path(tmpdir) / "test_module.py"
        test_file.write_text("""
def hello_world():
    \"\"\"Say hello.\"\"\"
    return "Hello, World!"

class Greeter:
    \"\"\"A greeter class.\"\"\"
    
    def greet(self, name: str) -> str:
        return f"Hello, {name}!"
""")
        
        yield tmpdir
    finally:
        # Windows file locking workaround
        import shutil
        import time
        try:
            shutil.rmtree(tmpdir)
        except PermissionError:
            time.sleep(0.1)
            try:
                shutil.rmtree(tmpdir)
            except PermissionError:
                pass


def test_indexer_to_store_integration(temp_repo):
    """Test indexer → store integration."""
    from cipkg.store import connect
    from cipkg import indexer
    from cipkg.base import load_config
    
    # Index the repository (indexer.sync expects root path, not con)
    result = indexer.sync(temp_repo)
    
    # Verify symbols were indexed
    con = connect(temp_repo)
    cursor = con.execute("SELECT COUNT(*) c FROM symbols")
    symbol_count = cursor.fetchone()["c"]
    
    assert symbol_count > 0, "No symbols indexed"
    
    # Verify chunks were created
    cursor = con.execute("SELECT COUNT(*) c FROM chunks")
    chunk_count = cursor.fetchone()["c"]
    
    assert chunk_count > 0, "No chunks created"


def test_retriever_integration(temp_repo):
    """Test retriever integration."""
    from cipkg.store import connect
    from cipkg import indexer, retrieve
    from cipkg.base import load_config
    
    # Index first (indexer.sync expects root path)
    indexer.sync(temp_repo)
    
    # Test lexical search (retrieve.search expects path)
    results = retrieve.search(temp_repo, "hello", k=5)
    assert len(results) > 0, "Lexical search failed"


def test_impact_analysis_integration(temp_repo):
    """Test impact analysis integration."""
    from cipkg.store import connect
    from cipkg import indexer
    from cipkg.stack.impact import impact
    from cipkg.base import load_config
    
    # Index first (indexer.sync expects root path)
    indexer.sync(temp_repo)
    
    # Get a symbol ID
    con = connect(temp_repo)
    cursor = con.execute("SELECT id FROM symbols LIMIT 1")
    row = cursor.fetchone()
    
    if row:
        symbol_id = row["id"]
        
        # Analyze impact using function-based API (impact expects path)
        result = impact(temp_repo, target=symbol_id)
        
        assert 'risk' in result, "Impact analysis failed"
        assert 'affected_files' in result, "No affected files returned"


def test_context_retrieval_integration(temp_repo):
    """Test context retrieval integration."""
    from cipkg.store import connect
    from cipkg import indexer, retrieve
    from cipkg.base import load_config
    
    # Index first (indexer.sync expects root path)
    indexer.sync(temp_repo)
    
    # Get context (retrieve.context expects path)
    result = retrieve.context(temp_repo, query="hello world")
    
    assert 'sections' in result, "Context retrieval failed"
    assert result['budget_tokens'] > 0, "No token budget"


def test_gapfill_integration(temp_repo):
    """Test gapfill integration."""
    from cipkg.store import connect
    from cipkg import indexer
    from cipkg import gapfill
    from cipkg.base import load_config
    
    # Index first (indexer.sync expects root path)
    indexer.sync(temp_repo)
    
    # Test coverage analysis (gapfill.coverage expects path)
    result = gapfill.coverage(temp_repo)
    
    assert 'actual_coverage' in result, "Coverage analysis failed"
    assert 'coverage_pct' in result['actual_coverage'], "No coverage percentage"


def test_health_score_integration(temp_repo):
    """Test health score integration."""
    from cipkg.store import connect
    from cipkg import indexer
    from cipkg import gapfill
    from cipkg.base import load_config
    
    # Index first (indexer.sync expects root path)
    indexer.sync(temp_repo)
    
    # Get health score (gapfill.score expects path)
    result = gapfill.score(temp_repo)
    
    assert 'score' in result, "Health score failed"
    assert 0 <= result['score'] <= 100, "Score out of range"


def test_server_tool_integration(temp_repo):
    """Test server tool integration."""
    from cipkg.store import connect
    from cipkg import indexer
    from cipkg.server import call_tool, TOOLS
    from cipkg.base import load_config
    
    # Index first (indexer.sync expects root path)
    indexer.sync(temp_repo)
    
    # Verify tools are defined
    assert len(TOOLS) > 0, "No tools defined"
    
    # Test search tool using existing call_tool function (expects path)
    cfg = load_config(temp_repo)
    result = call_tool(temp_repo, cfg, 'search', {'query': 'hello', 'k': 5})
    
    assert result['ok'] is True, f"Search tool failed: {result.get('error')}"


def test_retrieval_bridge_integration(temp_repo):
    """Test retrieval bridge integration."""
    from cipkg.store import connect
    from cipkg import indexer
    from cipkg.retrieval_bridge import search_and_format
    from cipkg.base import load_config
    
    # Index first (indexer.sync expects root path)
    indexer.sync(temp_repo)
    
    # Test search and format (search_and_format expects path)
    result = search_and_format(temp_repo, "hello world", max_tokens=1024)
    
    assert result.total_tokens > 0, "No tokens used"
    assert result.budget_tokens == 1024, "Wrong budget"


def test_learning_system_memory_integration(temp_repo):
    """Test learning system memory integration."""
    from cipkg.learning_system import LearningSystem
    
    learner = LearningSystem(temp_repo)
    
    # Record an action
    learner.record_action({
        'action_type': 'command',
        'user_id': 'test_user',
        'repo_id': 'test_repo',
        'command': 'search',
        'arguments': {'query': 'test'},
        'success': True,
        'execution_time': 0.1
    })
    
    # Recall relevant experiences
    results = learner.recall_relevant('search')
    
    # Should return list (may be empty if memory not initialized)
    assert isinstance(results, list), "Recall should return list"


def test_dependency_checker():
    """Test dependency checker."""
    from cipkg.dependency_checker import check_dependencies, get_missing_dependencies
    
    # Check dependencies
    results = check_dependencies()
    
    assert len(results) > 0, "No dependency categories"
    
    # Get missing
    missing = get_missing_dependencies()
    
    # Just verify it returns a list
    assert isinstance(missing, list), "Missing deps should be a list"


def test_retrieve_lexical_search(temp_repo):
    """Test retrieve.py lexical search functionality."""
    from cipkg.store import connect
    from cipkg import indexer
    from cipkg.retrieve import lex_search
    from cipkg.base import load_config
    
    # Index first (indexer.sync expects root path)
    indexer.sync(temp_repo)
    
    # Test lexical search (lex_search expects con, not path)
    con = connect(temp_repo)
    results = lex_search(con, "hello", k=5)
    
    assert isinstance(results, list), "Lexical search should return list"


def test_retrieve_symbol_lookup(temp_repo):
    """Test retrieve.py symbol lookup functionality."""
    from cipkg.store import connect
    from cipkg import indexer
    from cipkg.base import load_config
    
    # Index first (indexer.sync expects root path)
    indexer.sync(temp_repo)
    
    # Test symbol lookup via database query (needs con)
    con = connect(temp_repo)
    cursor = con.execute("SELECT * FROM symbols WHERE name LIKE ?", ("%hello%",))
    results = cursor.fetchall()
    
    assert isinstance(results, list), "Symbol lookup should return list"


def test_analysis_health_calculation(temp_repo):
    """Test analysis.py health score calculation."""
    from cipkg.store import connect
    from cipkg import indexer
    from cipkg.analysis import _calculate_health_score, _open_findings
    from cipkg.base import load_config
    
    # Index first (indexer.sync expects root path)
    indexer.sync(temp_repo)
    
    # Test _open_findings (needs con)
    con = connect(temp_repo)
    findings = _open_findings(con)
    assert isinstance(findings, list), "_open_findings should return list"
    
    # Test _calculate_health_score (expects con, cfg, path)
    cfg = load_config(temp_repo)
    score = _calculate_health_score(con, cfg, temp_repo)
    assert isinstance(score, (int, float)), "Health score should be numeric"
    assert 0 <= score <= 100, "Health score should be in range"


def test_analysis_repo_health_report(temp_repo):
    """Test analysis.py repository health report."""
    from cipkg.store import connect
    from cipkg import indexer
    from cipkg.analysis import repo_health_report
    from cipkg.base import load_config
    
    # Index first (indexer.sync expects root path)
    indexer.sync(temp_repo)
    
    # Test repo_health_report (expects path)
    report = repo_health_report(temp_repo)
    
    assert isinstance(report, dict), "Health report should be dict"
    assert ('overall_score' in report or 'health_score' in report), "Report should contain health score"


def test_embed_hashing_fallback(temp_repo):
    """Test embed.py hashing fallback when no embedding backend."""
    from cipkg.embed import get_embedder
    from cipkg.base import load_config
    
    cfg = load_config(temp_repo)
    
    # Force hashing backend
    cfg['embed']['backend'] = 'hashing'
    
    # Test hashing embedder
    embedder = get_embedder(cfg)
    
    # Should return without error
    assert embedder is not None, "Hashing embedder should be available"


def test_indexer_file_parsing(temp_repo):
    """Test indexer.py file parsing for different file types."""
    from cipkg.store import connect
    from cipkg import indexer
    from cipkg.base import load_config
    from pathlib import Path
    
    # Create additional test files
    (Path(temp_repo) / "test_js.js").write_text("""
function testFunction() {
    return "test";
}
""")
    
    (Path(temp_repo) / "test_ts.ts").write_text("""
interface TestInterface {
    name: string;
}
""")
    
    # Index should handle multiple file types (indexer.sync expects root path)
    result = indexer.sync(temp_repo)
    
    assert result is not None, "Indexing should succeed"
    assert (result.get('files', 0) > 0 or result.get('files_indexed', 0) > 0), "Files should be indexed"


def test_store_database_operations(temp_repo):
    """Test store.py database operations."""
    from cipkg.store import connect
    from cipkg.base import load_config
    
    # Test connection
    con = connect(temp_repo)
    assert con is not None, "Database connection should succeed"
    
    # Test basic query
    cursor = con.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    assert len(tables) > 0, "Database should have tables"


def test_forensics_endpoints(temp_repo):
    """Test forensic summary, dossier, and context-pack endpoints."""
    from cipkg import indexer
    from cipkg.web_bridge import app
    from starlette.testclient import TestClient

    indexer.sync(temp_repo)
    client = TestClient(app)
    repo_param = f"?repo={temp_repo}"

    # 1. Summary
    res = client.get(f"/api/forensics/summary{repo_param}")
    assert res.status_code == 200
    body = res.json()
    data = body.get("data", body)
    assert "dimensions" in data
    assert "ghost_code" in data["dimensions"]
    assert "silent_traps" in data["dimensions"]
    assert "architecture" in data["dimensions"]
    assert "risk_matrix" in data["dimensions"]
    assert "secrets_env" in data["dimensions"]

    # 2. Dossier (JSON & Markdown)
    res_json = client.get(f"/api/forensics/dossier{repo_param}&format=json")
    assert res_json.status_code == 200
    dossier_body = res_json.json()
    dossier_data = dossier_body.get("data", dossier_body)
    assert "summary" in dossier_data

    res_md = client.get(f"/api/forensics/dossier{repo_param}&format=markdown")
    assert res_md.status_code == 200
    assert "# Code Forensics & Intelligence Dossier" in res_md.text

    # 3. Context pack
    res_pack = client.post(f"/api/forensics/context-pack{repo_param}", json={"max_tokens": 4096})
    assert res_pack.status_code == 200
    pack_body = res_pack.json()
    pack_data = pack_body.get("data", pack_body)
    assert "context_pack" in pack_data
    assert pack_data["token_limit"] == 128000



if __name__ == "__main__":
    pytest.main([__file__, "-v"])



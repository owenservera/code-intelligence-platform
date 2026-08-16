"""
Enhanced Web Server with WebSocket support for real-time dashboard.
"""

import json
import asyncio
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Dict, Any, Optional, Set
import os
import time
from urllib.parse import urlparse, parse_qs


class WebSocketConnection:
    """Represents a single WebSocket connection."""
    
    def __init__(self, conn_id: str, socket):
        self.conn_id = conn_id
        self.socket = socket
        self.subscribed_topics: Set[str] = set()
        self.connected_at = time.time()
    
    async def send(self, message: Dict[str, Any]):
        """Send message to this connection."""
        try:
            await self.socket.send(json.dumps(message))
        except Exception as e:
            print(f"WebSocket send error: {e}")
    
    def subscribe(self, topic: str):
        """Subscribe to a topic."""
        self.subscribed_topics.add(topic)
    
    def unsubscribe(self, topic: str):
        """Unsubscribe from a topic."""
        self.subscribed_topics.discard(topic)


class WebSocketManager:
    """Manages all WebSocket connections."""
    
    def __init__(self):
        self.connections: Dict[str, WebSocketConnection] = {}
        self._lock = threading.Lock()
    
    def add_connection(self, conn_id: str, socket) -> WebSocketConnection:
        """Add a new connection."""
        with self._lock:
            conn = WebSocketConnection(conn_id, socket)
            self.connections[conn_id] = conn
            return conn
    
    def remove_connection(self, conn_id: str):
        """Remove a connection."""
        with self._lock:
            if conn_id in self.connections:
                del self.connections[conn_id]
    
    async def broadcast(self, topic: str, message: Dict[str, Any]):
        """Broadcast message to all connections subscribed to topic."""
        with self._lock:
            connections = list(self.connections.values())
        
        for conn in connections:
            if topic in conn.subscribed_topics or topic == "*":
                await conn.send(message)
    
    async def send_to(self, conn_id: str, message: Dict[str, Any]):
        """Send message to specific connection."""
        with self._lock:
            conn = self.connections.get(conn_id)
        
        if conn:
            await conn.send(message)


class DashboardAPIHandler(SimpleHTTPRequestHandler):
    """HTTP handler for dashboard API endpoints."""
    
    # Class-level references set by server
    root = None
    ws_manager = None
    
    def __init__(self, *args, **kwargs):
        self.static_path = Path(__file__).parent / "static"
        super().__init__(*args, directory=str(self.static_path), **kwargs)
    
    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        
        # API endpoints
        if path.startswith('/api/'):
            self._handle_api_get(path, parsed)
        # Static files
        elif path == '/' or path == '/dashboard':
            self.path = '/dashboard.html'
            super().do_GET()
        else:
            super().do_GET()
    
    def do_POST(self):
        """Handle POST requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path.startswith('/api/'):
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            
            try:
                data = json.loads(body) if body else {}
                self._handle_api_post(path, data)
            except json.JSONDecodeError:
                self._send_json({'error': 'Invalid JSON'}, 400)
    
    def _handle_api_get(self, path: str, parsed):
        """Handle API GET requests."""
        params = parse_qs(parsed.query)
        
        if path == '/api/ping':
            self._send_json({'status': 'ok', 'timestamp': time.time()})
        elif path == '/api/health':
            self._api_health()
        elif path == '/api/search':
            query = params.get('q', [''])[0]
            limit = int(params.get('limit', [10])[0])
            self._api_search(query, limit)
        elif path == '/api/symbols':
            self._api_symbols()
        elif path == '/api/impact':
            symbol_id = params.get('symbol', [''])[0]
            self._api_impact(symbol_id)
        elif path == '/api/gaps':
            self._api_gaps()
        elif path == '/api/memory':
            self._api_memory()
        elif path == '/api/graph':
            self._api_graph()
        elif path == '/api/stats':
            self._api_stats()
        elif path == '/api/config':
            self._api_config()
        else:
            self._send_json({'error': 'Not found'}, 404)
    
    def _handle_api_post(self, path: str, data: Dict):
        """Handle API POST requests."""
        if path == '/api/sync':
            self._api_sync()
        elif path == '/api/analyze':
            self._api_analyze()
        elif path == '/api/audit':
            self._api_audit()
        elif path == '/api/memory/store':
            self._api_memory_store(data)
        elif path == '/api/memory/recall':
            self._api_memory_recall(data)
        else:
            self._send_json({'error': 'Not found'}, 404)
    
    # === API Implementations ===
    
    def _api_health(self):
        """Get repository health."""
        try:
            from cipkg import analysis
            from cipkg.base import repo_root
            
            root = self.root or repo_root()
            report = analysis.repo_health_report(root)
            self._send_json(report)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _api_search(self, query: str, limit: int):
        """Search codebase."""
        try:
            from cipkg import retrieve
            from cipkg.base import repo_root
            
            root = self.root or repo_root()
            results = retrieve.hybrid_search(root, query, limit=limit)
            self._send_json({'results': results, 'query': query})
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _api_symbols(self):
        """Get all symbols."""
        try:
            from cipkg.store import connect
            from cipkg.base import repo_root
            
            root = self.root or repo_root()
            con = connect(root)
            
            cursor = con.execute("""
                SELECT id, name, kind, path, start_line, end_line
                FROM symbols
                ORDER BY path, start_line
                LIMIT 1000
            """)
            
            symbols = []
            for row in cursor.fetchall():
                symbols.append({
                    'id': row[0],
                    'name': row[1],
                    'kind': row[2],
                    'path': row[3],
                    'start_line': row[4],
                    'end_line': row[5]
                })
            
            self._send_json({'symbols': symbols})
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _api_impact(self, symbol_id: str):
        """Get impact analysis."""
        try:
            from cipkg.store import connect
            from cipkg.stack.impact import ImpactAnalyzer
            from cipkg.base import repo_root
            
            root = self.root or repo_root()
            con = connect(root)
            
            analyzer = ImpactAnalyzer(con)
            result = analyzer.analyze_impact(symbol_id)
            self._send_json(result)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _api_gaps(self):
        """Get knowledge gaps."""
        try:
            from cipkg.gapfill import GapFiller
            from cipkg.store import connect
            from cipkg.base import repo_root
            
            root = self.root or repo_root()
            con = connect(root)
            
            filler = GapFiller(con)
            gaps = filler.find_gaps()
            
            self._send_json({
                'gaps': [
                    {
                        'type': g.gap_type,
                        'path': g.path,
                        'symbol_id': g.symbol_id,
                        'severity': g.severity,
                        'description': g.description,
                        'suggested_fix': g.suggested_fix
                    }
                    for g in gaps
                ]
            })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _api_memory(self):
        """Get memory dashboard data."""
        try:
            from cipkg.memory.temporal_graph import TemporalKnowledgeGraph
            from cipkg.memory.episodic import EpisodicMemory
            from cipkg.base import repo_root
            
            root = self.root or repo_root()
            
            # Get temporal facts
            graph = TemporalKnowledgeGraph(f"{root}/.cip/memory.db")
            facts = graph.query_facts(at_time=time.time())
            
            # Get recent episodes
            episodic = EpisodicMemory(f"{root}/.cip/episodes.db")
            episodes = episodic.query_episodes(limit=50)
            
            self._send_json({
                'facts': [
                    {
                        'subject': f.subject,
                        'predicate': f.predicate,
                        'object_value': f.object_value,
                        'valid_from': f.valid_from,
                        'confidence': f.confidence
                    }
                    for f in facts[:100]
                ],
                'episodes': [
                    {
                        'id': e.id,
                        'timestamp': e.timestamp,
                        'type': e.episode_type,
                        'context': e.context,
                        'outcome': e.outcome
                    }
                    for e in episodes
                ]
            })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _api_graph(self):
        """Get code graph data for visualization."""
        try:
            from cipkg.store import connect
            from cipkg.base import repo_root
            
            root = self.root or repo_root()
            con = connect(root)
            
            # Get nodes (symbols)
            cursor = con.execute("""
                SELECT id, name, kind, path FROM symbols LIMIT 500
            """)
            
            nodes = []
            for row in cursor.fetchall():
                nodes.append({
                    'id': row[0],
                    'name': row[1],
                    'kind': row[2],
                    'path': row[3]
                })
            
            # Get edges (relationships)
            cursor = con.execute("""
                SELECT src, dst, kind FROM edges LIMIT 1000
            """)
            
            edges = []
            for row in cursor.fetchall():
                edges.append({
                    'source': row[0],
                    'target': row[1],
                    'type': row[2]
                })
            
            self._send_json({
                'nodes': nodes,
                'edges': edges
            })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _api_stats(self):
        """Get dashboard statistics."""
        try:
            from cipkg.store import connect, get_meta
            from cipkg.base import repo_root
            
            root = self.root or repo_root()
            con = connect(root)
            
            # Get counts
            cursor = con.execute("SELECT COUNT(*) FROM files")
            file_count = cursor.fetchone()[0]
            
            cursor = con.execute("SELECT COUNT(*) FROM symbols")
            symbol_count = cursor.fetchone()[0]
            
            cursor = con.execute("SELECT COUNT(*) FROM chunks")
            chunk_count = cursor.fetchone()[0]
            
            cursor = con.execute("SELECT COUNT(*) FROM edges")
            edge_count = cursor.fetchone()[0]
            
            # Get last sync time
            last_sync = get_meta(con, "last_sync", "Never")
            
            self._send_json({
                'files': file_count,
                'symbols': symbol_count,
                'chunks': chunk_count,
                'edges': edge_count,
                'last_sync': last_sync
            })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _api_config(self):
        """Get current configuration."""
        try:
            from cipkg.base import load_config
            from cipkg.base import repo_root
            
            root = self.root or repo_root()
            cfg = load_config(root)
            
            # Convert to serializable format
            self._send_json({
                'index': dict(cfg.get('index', {})),
                'embed': dict(cfg.get('embed', {})),
                'retrieval': dict(cfg.get('retrieval', {})),
                'memory': dict(cfg.get('memory', {}))
            })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _api_sync(self):
        """Trigger index sync."""
        try:
            from cipkg import indexer
            from cipkg.store import connect
            from cipkg.base import load_config, repo_root
            
            root = self.root or repo_root()
            con = connect(root)
            cfg = load_config(root)
            
            result = indexer.sync(con, cfg)
            self._send_json({'status': 'success', 'result': result})
            
            # Broadcast sync event
            if self.ws_manager:
                asyncio.create_task(
                    self.ws_manager.broadcast('sync', {
                        'type': 'sync_complete',
                        'data': result
                    })
                )
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _api_analyze(self):
        """Trigger analysis."""
        try:
            from cipkg import analysis
            from cipkg.base import repo_root
            
            root = self.root or repo_root()
            report = analysis.repo_health_report(root)
            self._send_json(report)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _api_audit(self):
        """Trigger audit."""
        try:
            from cipkg.stack import audit as stack_audit
            from cipkg.base import repo_root
            
            root = self.root or repo_root()
            results = stack_audit.audit(root, refresh=True)
            self._send_json(results)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _api_memory_store(self, data: Dict):
        """Store memory."""
        try:
            from cipkg.memory.temporal_graph import AgentMemory
            from cipkg.base import repo_root
            
            root = self.root or repo_root()
            memory = AgentMemory(f"{root}/.cip/memory.db")
            
            key = data.get('key')
            value = data.get('value')
            source = data.get('source', 'dashboard')
            
            if key and value is not None:
                memory.remember(key, value, source)
                self._send_json({'status': 'success'})
            else:
                self._send_json({'error': 'key and value required'}, 400)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _api_memory_recall(self, data: Dict):
        """Recall memories."""
        try:
            from cipkg.memory.temporal_graph import TemporalKnowledgeGraph
            from cipkg.base import repo_root
            
            root = self.root or repo_root()
            graph = TemporalKnowledgeGraph(f"{root}/.cip/memory.db")
            
            query = data.get('query', '')
            subject = data.get('subject')
            predicate = data.get('predicate')
            
            facts = graph.query_facts(
                subject=subject,
                predicate=predicate,
                at_time=time.time()
            )
            
            self._send_json({
                'facts': [
                    {
                        'subject': f.subject,
                        'predicate': f.predicate,
                        'object_value': f.object_value,
                        'valid_from': f.valid_from,
                        'confidence': f.confidence
                    }
                    for f in facts
                ]
            })
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _send_json(self, data: Dict, status: int = 200):
        """Send JSON response."""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def log_message(self, format, *args):
        """Log requests for debugging."""
        print(f"[HTTP] {args[0]}")


def start_web_server(root: str, port: int = 8090, host: str = "localhost"):
    """Start the web dashboard server."""
    import socket
    from cipkg.base import repo_root
    from .websocket_handler import DashboardWebSocketServer
    
    root = root or repo_root()
    
    # Set class-level root
    DashboardAPIHandler.root = root
    
    # Create WebSocket manager
    ws_manager = WebSocketManager()
    DashboardAPIHandler.ws_manager = ws_manager
    
    # Try ports if default is blocked
    max_attempts = 5
    server = None
    for attempt in range(max_attempts):
        try:
            server = HTTPServer((host, port), DashboardAPIHandler)
            server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            break
        except PermissionError:
            print(f"⚠️  Port {port} blocked, trying {port + 1}...")
            port += 1
            server = None
        except OSError as e:
            print(f"⚠️  Port {port} unavailable ({e}), trying {port + 1}...")
            port += 1
            server = None
    
    if server is None:
        print(f"❌ Could not find available port after {max_attempts} attempts")
        return
    
    # Start WebSocket server on port+1
    ws_port = port + 1
    ws_server = DashboardWebSocketServer(host=host, port=ws_port)
    try:
        ws_server.start_in_thread()
        print(f"🔌 WebSocket server: ws://{host}:{ws_port}")
    except Exception as e:
        print(f"⚠️  WebSocket server failed to start: {e}")
        print(f"   Dashboard will work without real-time updates")
    
    print(f"🌐 Web Dashboard: http://{host}:{port}")
    print(f"📊 API Endpoint: http://{host}:{port}/api/")
    print(f"Press Ctrl+C to stop")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        print("\n🛑 Shutting down...")
        server.shutdown()
        server.server_close()


# CLI integration
def handle_dashboard_web_command(root, args):
    """Handle 'cip dashboard-web' command."""
    port = getattr(args, 'port', 8090)
    host = getattr(args, 'host', 'localhost')
    start_web_server(root, port, host)
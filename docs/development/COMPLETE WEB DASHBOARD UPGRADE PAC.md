# 🌐 **COMPLETE WEB DASHBOARD UPGRADE PACK**

**Repository:** `owenservera/code-intelligence-platform`  
**Target:** Web Dashboard System  
**Upgrade Scope:** Interactive, Stateful, Visual Codebase Map, Real-time Updates

---

## 📋 **EXECUTIVE SUMMARY**

This upgrade transforms the basic web dashboard into a **production-grade, fully interactive web application** with:

| Feature | Current State | Upgraded State |
|---------|--------------|----------------|
| Interactivity | Static HTML | Real-time WebSocket, click/hover/zoom |
| State Management | None | Persistent state with undo/redo |
| Code Visualization | None | Interactive graph with D3.js |
| Search | Basic form | Live search with autocomplete |
| Impact Analysis | Text only | Visual blast radius graph |
| Memory Dashboard | None | Timeline + knowledge graph |
| Health Monitoring | Static | Real-time gauges + alerts |

---

## 🏗️ **ARCHITECTURE OVERVIEW**

```
┌─────────────────────────────────────────────────────────────────┐
│                    Web Dashboard Architecture                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Frontend   │◀──▶│  WebSocket   │◀──▶│   Backend    │      │
│  │  (SPA/JS)    │    │   Server     │    │  (Python)    │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                    │                    │              │
│         ▼                    ▼                    ▼              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │  State Store │    │  Real-time   │    │  CIP Core    │      │
│  │  (Redux-like)│    │  Events      │    │  (Indexer,   │      │
│  └──────────────┘    └──────────────┘    │  Retriever)  │      │
│         │                    │            └──────────────┘      │
│         ▼                    ▼                    │              │
│  ┌──────────────┐    ┌──────────────┐           │              │
│  │  D3.js Graph │    │  Charts.js   │           │              │
│  │  (Code Map)  │    │  (Metrics)   │           │              │
│  └──────────────┘    └──────────────┘           │              │
│                                                  │              │
│  ┌──────────────────────────────────────────────┘              │
│  │                                                              │
│  ▼                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │  Search UI   │    │  Impact Viz  │    │  Memory Dash │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 **FILE STRUCTURE**

Create/replace these files:

```
lib/cipkg/
├── static/
│   ├── dashboard.html          # Main SPA (replaced)
│   ├── css/
│   │   ├── dashboard.css       # Main styles
│   │   ├── graph.css           # Graph visualization styles
│   │   └── components.css      # Component styles
│   ├── js/
│   │   ├── app.js              # Main application
│   │   ├── store.js            # State management
│   │   ├── websocket.js        # WebSocket client
│   │   ├── graph.js            # D3.js code graph
│   │   ├── search.js           # Search interface
│   │   ├── impact.js           # Impact visualization
│   │   ├── memory.js           # Memory dashboard
│   │   └── components.js       # Reusable components
│   └── lib/
│       ├── d3.v7.min.js        # D3.js for graphs
│       ├── chart.min.js        # Chart.js for metrics
│       └── marked.min.js       # Markdown rendering
├── web_server.py               # Enhanced web server (replaced)
└── websocket_handler.py        # WebSocket handler (new)
```

---

## 🔧 **PHASE 1: BACKEND - WEBSOCKET SERVER**

### **1.1 Enhanced Web Server**

**File:** `lib/cipkg/web_server.py`

```python
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
        
        if path == '/api/health':
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
        """Override to reduce noise."""
        pass


def start_web_server(root: str, port: int = 8080, host: str = "localhost"):
    """Start the web dashboard server."""
    from cipkg.base import repo_root
    
    root = root or repo_root()
    
    # Set class-level root
    DashboardAPIHandler.root = root
    
    # Create WebSocket manager
    ws_manager = WebSocketManager()
    DashboardAPIHandler.ws_manager = ws_manager
    
    # Start HTTP server
    server = HTTPServer((host, port), DashboardAPIHandler)
    print(f"🌐 Web Dashboard: http://{host}:{port}")
    print(f"📊 API Endpoint: http://{host}:{port}/api/")
    print(f"🔌 WebSocket: ws://{host}:{port + 1}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
        server.shutdown()


# CLI integration
def handle_dashboard_web_command(root, args):
    """Handle 'cip dashboard-web' command."""
    port = getattr(args, 'port', 8080)
    host = getattr(args, 'host', 'localhost')
    start_web_server(root, port, host)
```

---

### **1.2 WebSocket Handler**

**Create new file:** `lib/cipkg/websocket_handler.py`

```python
"""
WebSocket handler for real-time dashboard updates.
"""

import asyncio
import json
import websockets
from typing import Dict, Any, Set
import time
import threading


class DashboardWebSocketServer:
    """WebSocket server for real-time dashboard updates."""
    
    def __init__(self, host: str = "localhost", port: int = 8081):
        self.host = host
        self.port = port
        self.connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.subscriptions: Dict[str, Set[str]] = {}  # conn_id -> topics
        self._running = False
    
    async def handler(self, websocket, path):
        """Handle WebSocket connections."""
        conn_id = f"conn_{id(websocket)}_{int(time.time())}"
        self.connections[conn_id] = websocket
        self.subscriptions[conn_id] = set()
        
        print(f"🔌 WebSocket connected: {conn_id}")
        
        try:
            # Send welcome message
            await websocket.send(json.dumps({
                'type': 'connected',
                'conn_id': conn_id,
                'timestamp': time.time()
            }))
            
            # Handle messages
            async for message in websocket:
                await self._handle_message(conn_id, message)
                
        except websockets.exceptions.ConnectionClosed:
            print(f"🔌 WebSocket disconnected: {conn_id}")
        finally:
            # Cleanup
            if conn_id in self.connections:
                del self.connections[conn_id]
            if conn_id in self.subscriptions:
                del self.subscriptions[conn_id]
    
    async def _handle_message(self, conn_id: str, message: str):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == 'subscribe':
                topic = data.get('topic')
                if topic:
                    self.subscriptions[conn_id].add(topic)
                    await self._send(conn_id, {
                        'type': 'subscribed',
                        'topic': topic
                    })
            
            elif msg_type == 'unsubscribe':
                topic = data.get('topic')
                if topic:
                    self.subscriptions[conn_id].discard(topic)
            
            elif msg_type == 'ping':
                await self._send(conn_id, {
                    'type': 'pong',
                    'timestamp': time.time()
                })
            
            elif msg_type == 'request':
                # Handle data requests
                resource = data.get('resource')
                await self._handle_request(conn_id, resource, data)
        
        except json.JSONDecodeError:
            await self._send(conn_id, {
                'type': 'error',
                'message': 'Invalid JSON'
            })
    
    async def _handle_request(self, conn_id: str, resource: str, data: Dict):
        """Handle data request from client."""
        # This would integrate with CIP core to fetch data
        # For now, return placeholder
        await self._send(conn_id, {
            'type': 'response',
            'resource': resource,
            'data': {},
            'timestamp': time.time()
        })
    
    async def broadcast(self, topic: str, message: Dict[str, Any]):
        """Broadcast message to all subscribed connections."""
        message['type'] = 'event'
        message['topic'] = topic
        message['timestamp'] = time.time()
        
        for conn_id, topics in self.subscriptions.items():
            if topic in topics or '*' in topics:
                await self._send(conn_id, message)
    
    async def _send(self, conn_id: str, message: Dict[str, Any]):
        """Send message to specific connection."""
        if conn_id in self.connections:
            try:
                await self.connections[conn_id].send(json.dumps(message))
            except Exception as e:
                print(f"WebSocket send error: {e}")
    
    async def start(self):
        """Start the WebSocket server."""
        self._running = True
        
        async with websockets.serve(self.handler, self.host, self.port):
            print(f"🔌 WebSocket server: ws://{self.host}:{self.port}")
            await asyncio.Future()  # Run forever
    
    def start_in_thread(self):
        """Start WebSocket server in a background thread."""
        def run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.start())
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return thread


# Event emitter for CIP core to push updates
class DashboardEventEmitter:
    """Emits events to dashboard via WebSocket."""
    
    def __init__(self, ws_server: DashboardWebSocketServer):
        self.ws_server = ws_server
    
    def emit_index_update(self, files_updated: int, symbols_added: int):
        """Emit index update event."""
        asyncio.create_task(
            self.ws_server.broadcast('index', {
                'event': 'index_update',
                'files_updated': files_updated,
                'symbols_added': symbols_added
            })
        )
    
    def emit_health_update(self, health_score: int, issues: list):
        """Emit health update event."""
        asyncio.create_task(
            self.ws_server.broadcast('health', {
                'event': 'health_update',
                'score': health_score,
                'issues': issues
            })
        )
    
    def emit_search_result(self, query: str, results_count: int):
        """Emit search result event."""
        asyncio.create_task(
            self.ws_server.broadcast('search', {
                'event': 'search_complete',
                'query': query,
                'results_count': results_count
            })
        )
    
    def emit_memory_update(self, memory_type: str, count: int):
        """Emit memory update event."""
        asyncio.create_task(
            self.ws_server.broadcast('memory', {
                'event': 'memory_update',
                'type': memory_type,
                'count': count
            })
        )
```

---

## 🎨 **PHASE 2: FRONTEND - MAIN APPLICATION**

### **2.1 Main Dashboard HTML**

**File:** `lib/cipkg/static/dashboard.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CIP Dashboard v2.0</title>
    
    <!-- External Libraries -->
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    
    <!-- CIP Dashboard Styles -->
    <link rel="stylesheet" href="/css/dashboard.css">
    <link rel="stylesheet" href="/css/graph.css">
    <link rel="stylesheet" href="/css/components.css">
</head>
<body>
    <!-- App Container -->
    <div id="app">
        <!-- Header -->
        <header class="dashboard-header">
            <div class="header-left">
                <h1 class="logo">🧠 CIP Dashboard</h1>
                <span class="version">v2.0</span>
            </div>
            <div class="header-center">
                <div class="search-container">
                    <input type="text" id="global-search" placeholder="Search code, symbols, docs..." autocomplete="off">
                    <div id="search-results" class="search-dropdown"></div>
                </div>
            </div>
            <div class="header-right">
                <button id="btn-sync" class="btn btn-primary" title="Sync Index">🔄 Sync</button>
                <button id="btn-theme" class="btn btn-secondary" title="Toggle Theme">🌓</button>
                <div class="connection-status" id="connection-status">
                    <span class="status-dot"></span>
                    <span class="status-text">Connecting...</span>
                </div>
            </div>
        </header>

        <!-- Navigation Tabs -->
        <nav class="dashboard-nav">
            <button class="nav-tab active" data-tab="overview">📊 Overview</button>
            <button class="nav-tab" data-tab="code-map">🗺️ Code Map</button>
            <button class="nav-tab" data-tab="search">🔍 Search</button>
            <button class="nav-tab" data-tab="impact">💥 Impact</button>
            <button class="nav-tab" data-tab="gaps">🕳️ Gaps</button>
            <button class="nav-tab" data-tab="memory">🧠 Memory</button>
            <button class="nav-tab" data-tab="settings">⚙️ Settings</button>
        </nav>

        <!-- Main Content Area -->
        <main class="dashboard-content">
            <!-- Overview Tab -->
            <section id="tab-overview" class="tab-content active">
                <div class="overview-grid">
                    <!-- Health Score Card -->
                    <div class="card health-card">
                        <h3>Repository Health</h3>
                        <div class="health-gauge">
                            <canvas id="health-gauge" width="200" height="200"></canvas>
                            <div class="health-score" id="health-score">--</div>
                        </div>
                        <div class="health-details" id="health-details"></div>
                    </div>

                    <!-- Stats Cards -->
                    <div class="card stats-card">
                        <h3>Index Statistics</h3>
                        <div class="stats-grid">
                            <div class="stat-item">
                                <span class="stat-value" id="stat-files">--</span>
                                <span class="stat-label">Files</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-value" id="stat-symbols">--</span>
                                <span class="stat-label">Symbols</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-value" id="stat-chunks">--</span>
                                <span class="stat-label">Chunks</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-value" id="stat-edges">--</span>
                                <span class="stat-label">Relationships</span>
                            </div>
                        </div>
                        <div class="last-sync" id="last-sync">Last sync: --</div>
                    </div>

                    <!-- Recent Activity -->
                    <div class="card activity-card">
                        <h3>Recent Activity</h3>
                        <div class="activity-list" id="activity-list">
                            <div class="activity-item">Loading...</div>
                        </div>
                    </div>

                    <!-- Quick Actions -->
                    <div class="card actions-card">
                        <h3>Quick Actions</h3>
                        <div class="actions-grid">
                            <button class="action-btn" data-action="sync">🔄 Sync Index</button>
                            <button class="action-btn" data-action="analyze">📊 Analyze</button>
                            <button class="action-btn" data-action="audit">🔍 Audit</button>
                            <button class="action-btn" data-action="gapfill">🕳️ Find Gaps</button>
                            <button class="action-btn" data-action="consolidate">🧠 Consolidate</button>
                            <button class="action-btn" data-action="export">📤 Export</button>
                        </div>
                    </div>
                </div>
            </section>

            <!-- Code Map Tab -->
            <section id="tab-code-map" class="tab-content">
                <div class="code-map-container">
                    <div class="map-toolbar">
                        <button id="map-zoom-in" class="btn btn-sm">➕</button>
                        <button id="map-zoom-out" class="btn btn-sm">➖</button>
                        <button id="map-fit" class="btn btn-sm">🔲 Fit</button>
                        <button id="map-reset" class="btn btn-sm">🔄 Reset</button>
                        <select id="map-layout" class="select-sm">
                            <option value="force">Force Layout</option>
                            <option value="tree">Tree Layout</option>
                            <option value="radial">Radial Layout</option>
                            <option value="grid">Grid Layout</option>
                        </select>
                        <select id="map-filter" class="select-sm">
                            <option value="all">All Symbols</option>
                            <option value="functions">Functions</option>
                            <option value="classes">Classes</option>
                            <option value="modules">Modules</option>
                        </select>
                    </div>
                    <div id="code-map" class="code-map-canvas"></div>
                    <div class="map-legend">
                        <div class="legend-item"><span class="legend-color" style="background: #4CAF50"></span> Function</div>
                        <div class="legend-item"><span class="legend-color" style="background: #2196F3"></span> Class</div>
                        <div class="legend-item"><span class="legend-color" style="background: #FF9800"></span> Module</div>
                        <div class="legend-item"><span class="legend-color" style="background: #9C27B0"></span> Interface</div>
                        <div class="legend-item"><span class="legend-color" style="background: #F44336"></span> Variable</div>
                    </div>
                    <div id="map-tooltip" class="map-tooltip"></div>
                </div>
            </section>

            <!-- Search Tab -->
            <section id="tab-search" class="tab-content">
                <div class="search-container-full">
                    <div class="search-header">
                        <h2>Code Search</h2>
                        <div class="search-filters">
                            <select id="search-type">
                                <option value="hybrid">Hybrid Search</option>
                                <option value="semantic">Semantic Only</option>
                                <option value="lexical">Lexical Only</option>
                            </select>
                            <input type="number" id="search-limit" value="10" min="1" max="50">
                        </div>
                    </div>
                    <div class="search-input-container">
                        <input type="text" id="search-input" placeholder="Search for code, functions, classes..." autocomplete="off">
                        <button id="search-btn" class="btn btn-primary">Search</button>
                    </div>
                    <div id="search-results-full" class="search-results-full"></div>
                </div>
            </section>

            <!-- Impact Tab -->
            <section id="tab-impact" class="tab-content">
                <div class="impact-container">
                    <div class="impact-header">
                        <h2>Impact Analysis</h2>
                        <div class="impact-input">
                            <input type="text" id="impact-symbol" placeholder="Enter symbol ID or name...">
                            <button id="impact-analyze-btn" class="btn btn-primary">Analyze</button>
                        </div>
                    </div>
                    <div class="impact-results">
                        <div class="impact-summary" id="impact-summary"></div>
                        <div class="impact-graph" id="impact-graph"></div>
                        <div class="impact-details" id="impact-details"></div>
                    </div>
                </div>
            </section>

            <!-- Gaps Tab -->
            <section id="tab-gaps" class="tab-content">
                <div class="gaps-container">
                    <div class="gaps-header">
                        <h2>Knowledge Gaps</h2>
                        <div class="gaps-filters">
                            <select id="gap-type-filter">
                                <option value="all">All Types</option>
                                <option value="missing_docs">Missing Docs</option>
                                <option value="missing_tests">Missing Tests</option>
                                <option value="missing_types">Missing Types</option>
                            </select>
                            <select id="gap-severity-filter">
                                <option value="all">All Severities</option>
                                <option value="high">High</option>
                                <option value="medium">Medium</option>
                                <option value="low">Low</option>
                            </select>
                        </div>
                    </div>
                    <div class="gaps-summary" id="gaps-summary"></div>
                    <div class="gaps-list" id="gaps-list"></div>
                </div>
            </section>

            <!-- Memory Tab -->
            <section id="tab-memory" class="tab-content">
                <div class="memory-container">
                    <div class="memory-header">
                        <h2>Agent Memory</h2>
                        <div class="memory-actions">
                            <button id="memory-consolidate" class="btn btn-primary">🧠 Consolidate</button>
                            <button id="memory-clear" class="btn btn-danger">🗑️ Clear</button>
                        </div>
                    </div>
                    <div class="memory-grid">
                        <div class="memory-section">
                            <h3>Temporal Facts</h3>
                            <div class="memory-timeline" id="memory-facts"></div>
                        </div>
                        <div class="memory-section">
                            <h3>Recent Episodes</h3>
                            <div class="memory-episodes" id="memory-episodes"></div>
                        </div>
                        <div class="memory-section">
                            <h3>Memory Graph</h3>
                            <div class="memory-graph" id="memory-graph"></div>
                        </div>
                    </div>
                </div>
            </section>

            <!-- Settings Tab -->
            <section id="tab-settings" class="tab-content">
                <div class="settings-container">
                    <h2>Settings</h2>
                    <div class="settings-grid">
                        <div class="settings-section">
                            <h3>Index Settings</h3>
                            <div id="settings-index"></div>
                        </div>
                        <div class="settings-section">
                            <h3>Embedding Settings</h3>
                            <div id="settings-embed"></div>
                        </div>
                        <div class="settings-section">
                            <h3>Retrieval Settings</h3>
                            <div id="settings-retrieval"></div>
                        </div>
                        <div class="settings-section">
                            <h3>Memory Settings</h3>
                            <div id="settings-memory"></div>
                        </div>
                    </div>
                </div>
            </section>
        </main>

        <!-- Status Bar -->
        <footer class="dashboard-footer">
            <div class="footer-left">
                <span id="footer-status">Ready</span>
            </div>
            <div class="footer-center">
                <span id="footer-repo">Repository: --</span>
            </div>
            <div class="footer-right">
                <span id="footer-time">--</span>
            </div>
        </footer>
    </div>

    <!-- Toast Notifications -->
    <div id="toast-container" class="toast-container"></div>

    <!-- Modal Container -->
    <div id="modal-container" class="modal-container"></div>

    <!-- CIP Dashboard Scripts -->
    <script src="/js/store.js"></script>
    <script src="/js/websocket.js"></script>
    <script src="/js/components.js"></script>
    <script src="/js/graph.js"></script>
    <script src="/js/search.js"></script>
    <script src="/js/impact.js"></script>
    <script src="/js/memory.js"></script>
    <script src="/js/app.js"></script>
</body>
</html>
```

---

### **2.2 Main Stylesheet**

**Create file:** `lib/cipkg/static/css/dashboard.css`

```css
/* CIP Dashboard v2.0 - Main Styles */

:root {
    /* Color Palette */
    --bg-primary: #0f1419;
    --bg-secondary: #1a2332;
    --bg-card: #1e2a3a;
    --bg-hover: #2a3a4a;
    
    --text-primary: #e8eaed;
    --text-secondary: #9aa0a6;
    --text-muted: #5f6368;
    
    --accent-primary: #4CAF50;
    --accent-secondary: #2196F3;
    --accent-warning: #FF9800;
    --accent-danger: #F44336;
    --accent-purple: #9C27B0;
    
    --border-color: #2a3a4a;
    --shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    --shadow-lg: 0 10px 25px rgba(0, 0, 0, 0.5);
    
    /* Spacing */
    --spacing-xs: 4px;
    --spacing-sm: 8px;
    --spacing-md: 16px;
    --spacing-lg: 24px;
    --spacing-xl: 32px;
    
    /* Border Radius */
    --radius-sm: 4px;
    --radius-md: 8px;
    --radius-lg: 12px;
    
    /* Transitions */
    --transition: all 0.3s ease;
}

/* Light Theme */
[data-theme="light"] {
    --bg-primary: #ffffff;
    --bg-secondary: #f5f5f5;
    --bg-card: #ffffff;
    --bg-hover: #f0f0f0;
    
    --text-primary: #202124;
    --text-secondary: #5f6368;
    --text-muted: #9aa0a6;
    
    --border-color: #e0e0e0;
    --shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    --shadow-lg: 0 10px 25px rgba(0, 0, 0, 0.15);
}

/* Reset & Base */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    line-height: 1.6;
    overflow-x: hidden;
}

/* App Container */
#app {
    display: flex;
    flex-direction: column;
    height: 100vh;
}

/* Header */
.dashboard-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--spacing-md) var(--spacing-lg);
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    box-shadow: var(--shadow);
    z-index: 100;
}

.header-left {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
}

.logo {
    font-size: 1.5rem;
    font-weight: 700;
    background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.version {
    font-size: 0.75rem;
    color: var(--text-muted);
    background: var(--bg-card);
    padding: 2px 8px;
    border-radius: var(--radius-sm);
}

.header-center {
    flex: 1;
    max-width: 600px;
    margin: 0 var(--spacing-lg);
}

.search-container {
    position: relative;
}

.search-container input {
    width: 100%;
    padding: var(--spacing-sm) var(--spacing-md);
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-lg);
    color: var(--text-primary);
    font-size: 0.9rem;
    transition: var(--transition);
}

.search-container input:focus {
    outline: none;
    border-color: var(--accent-primary);
    box-shadow: 0 0 0 3px rgba(76, 175, 80, 0.1);
}

.search-dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-lg);
    max-height: 400px;
    overflow-y: auto;
    display: none;
    z-index: 1000;
}

.search-dropdown.active {
    display: block;
}

.header-right {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
}

/* Buttons */
.btn {
    padding: var(--spacing-sm) var(--spacing-md);
    border: none;
    border-radius: var(--radius-md);
    cursor: pointer;
    font-size: 0.9rem;
    font-weight: 500;
    transition: var(--transition);
    display: inline-flex;
    align-items: center;
    gap: var(--spacing-xs);
}

.btn-primary {
    background: var(--accent-primary);
    color: white;
}

.btn-primary:hover {
    background: #45a049;
    transform: translateY(-1px);
}

.btn-secondary {
    background: var(--bg-card);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
}

.btn-secondary:hover {
    background: var(--bg-hover);
}

.btn-danger {
    background: var(--accent-danger);
    color: white;
}

.btn-danger:hover {
    background: #d32f2f;
}

.btn-sm {
    padding: var(--spacing-xs) var(--spacing-sm);
    font-size: 0.8rem;
}

/* Connection Status */
.connection-status {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    font-size: 0.8rem;
    color: var(--text-secondary);
}

.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--accent-warning);
    animation: pulse 2s infinite;
}

.status-dot.connected {
    background: var(--accent-primary);
    animation: none;
}

.status-dot.disconnected {
    background: var(--accent-danger);
    animation: none;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

/* Navigation */
.dashboard-nav {
    display: flex;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    padding: 0 var(--spacing-lg);
    overflow-x: auto;
}

.nav-tab {
    padding: var(--spacing-md) var(--spacing-lg);
    background: none;
    border: none;
    color: var(--text-secondary);
    cursor: pointer;
    font-size: 0.9rem;
    font-weight: 500;
    border-bottom: 2px solid transparent;
    transition: var(--transition);
    white-space: nowrap;
}

.nav-tab:hover {
    color: var(--text-primary);
    background: var(--bg-hover);
}

.nav-tab.active {
    color: var(--accent-primary);
    border-bottom-color: var(--accent-primary);
}

/* Main Content */
.dashboard-content {
    flex: 1;
    overflow-y: auto;
    padding: var(--spacing-lg);
}

.tab-content {
    display: none;
}

.tab-content.active {
    display: block;
    animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

/* Cards */
.card {
    background: var(--bg-card);
    border-radius: var(--radius-lg);
    padding: var(--spacing-lg);
    box-shadow: var(--shadow);
    border: 1px solid var(--border-color);
}

.card h3 {
    margin-bottom: var(--spacing-md);
    font-size: 1.1rem;
    color: var(--text-primary);
}

/* Overview Grid */
.overview-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: var(--spacing-lg);
}

/* Health Gauge */
.health-gauge {
    position: relative;
    display: flex;
    justify-content: center;
    align-items: center;
    margin: var(--spacing-lg) 0;
}

.health-score {
    position: absolute;
    font-size: 2rem;
    font-weight: 700;
    color: var(--accent-primary);
}

/* Stats Grid */
.stats-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: var(--spacing-md);
}

.stat-item {
    text-align: center;
    padding: var(--spacing-md);
    background: var(--bg-secondary);
    border-radius: var(--radius-md);
}

.stat-value {
    display: block;
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--accent-secondary);
}

.stat-label {
    font-size: 0.8rem;
    color: var(--text-secondary);
}

/* Activity List */
.activity-list {
    max-height: 300px;
    overflow-y: auto;
}

.activity-item {
    padding: var(--spacing-sm) 0;
    border-bottom: 1px solid var(--border-color);
    font-size: 0.9rem;
}

.activity-item:last-child {
    border-bottom: none;
}

/* Actions Grid */
.actions-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: var(--spacing-sm);
}

.action-btn {
    padding: var(--spacing-md);
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);
    color: var(--text-primary);
    cursor: pointer;
    transition: var(--transition);
    font-size: 0.9rem;
}

.action-btn:hover {
    background: var(--bg-hover);
    border-color: var(--accent-primary);
    transform: translateY(-2px);
}

/* Code Map */
.code-map-container {
    height: calc(100vh - 200px);
    display: flex;
    flex-direction: column;
}

.map-toolbar {
    display: flex;
    gap: var(--spacing-sm);
    padding: var(--spacing-sm);
    background: var(--bg-secondary);
    border-radius: var(--radius-md);
    margin-bottom: var(--spacing-md);
}

.code-map-canvas {
    flex: 1;
    background: var(--bg-secondary);
    border-radius: var(--radius-lg);
    border: 1px solid var(--border-color);
    overflow: hidden;
}

.map-legend {
    display: flex;
    gap: var(--spacing-lg);
    padding: var(--spacing-sm);
    justify-content: center;
}

.legend-item {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    font-size: 0.8rem;
}

.legend-color {
    width: 12px;
    height: 12px;
    border-radius: 50%;
}

.map-tooltip {
    position: absolute;
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);
    padding: var(--spacing-md);
    box-shadow: var(--shadow-lg);
    pointer-events: none;
    display: none;
    z-index: 1000;
    max-width: 300px;
}

/* Search Results */
.search-results-full {
    margin-top: var(--spacing-lg);
}

.search-result-item {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);
    padding: var(--spacing-md);
    margin-bottom: var(--spacing-sm);
    cursor: pointer;
    transition: var(--transition);
}

.search-result-item:hover {
    border-color: var(--accent-primary);
    transform: translateX(4px);
}

.search-result-path {
    font-size: 0.8rem;
    color: var(--accent-secondary);
    margin-bottom: var(--spacing-xs);
}

.search-result-code {
    font-family: 'Monaco', 'Menlo', monospace;
    font-size: 0.85rem;
    background: var(--bg-secondary);
    padding: var(--spacing-sm);
    border-radius: var(--radius-sm);
    overflow-x: auto;
    white-space: pre;
}

.search-result-score {
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-top: var(--spacing-xs);
}

/* Impact Analysis */
.impact-container {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-lg);
}

.impact-summary {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: var(--spacing-md);
}

.impact-metric {
    background: var(--bg-card);
    padding: var(--spacing-md);
    border-radius: var(--radius-md);
    text-align: center;
}

.impact-metric-value {
    font-size: 1.5rem;
    font-weight: 700;
}

.impact-metric-label {
    font-size: 0.8rem;
    color: var(--text-secondary);
}

.impact-graph {
    height: 400px;
    background: var(--bg-secondary);
    border-radius: var(--radius-lg);
    border: 1px solid var(--border-color);
}

/* Gaps */
.gaps-list {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
}

.gap-item {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);
    padding: var(--spacing-md);
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
}

.gap-severity {
    width: 8px;
    height: 8px;
    border-radius: 50%;
}

.gap-severity.high { background: var(--accent-danger); }
.gap-severity.medium { background: var(--accent-warning); }
.gap-severity.low { background: var(--accent-primary); }

.gap-content {
    flex: 1;
}

.gap-title {
    font-weight: 600;
    margin-bottom: var(--spacing-xs);
}

.gap-description {
    font-size: 0.85rem;
    color: var(--text-secondary);
}

.gap-fix {
    font-size: 0.8rem;
    color: var(--accent-primary);
    margin-top: var(--spacing-xs);
}

/* Memory */
.memory-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: var(--spacing-lg);
}

.memory-section {
    background: var(--bg-card);
    border-radius: var(--radius-lg);
    padding: var(--spacing-lg);
    border: 1px solid var(--border-color);
}

.memory-timeline {
    max-height: 400px;
    overflow-y: auto;
}

.memory-fact {
    padding: var(--spacing-sm) 0;
    border-bottom: 1px solid var(--border-color);
}

.memory-fact:last-child {
    border-bottom: none;
}

.fact-predicate {
    font-weight: 600;
    color: var(--accent-secondary);
}

.fact-value {
    font-size: 0.9rem;
    color: var(--text-secondary);
}

.fact-time {
    font-size: 0.75rem;
    color: var(--text-muted);
}

/* Settings */
.settings-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: var(--spacing-lg);
}

.settings-section {
    background: var(--bg-card);
    border-radius: var(--radius-lg);
    padding: var(--spacing-lg);
    border: 1px solid var(--border-color);
}

.setting-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-sm) 0;
    border-bottom: 1px solid var(--border-color);
}

.setting-item:last-child {
    border-bottom: none;
}

.setting-label {
    font-size: 0.9rem;
}

.setting-value {
    font-size: 0.9rem;
    color: var(--accent-secondary);
}

/* Footer */
.dashboard-footer {
    display: flex;
    justify-content: space-between;
    padding: var(--spacing-sm) var(--spacing-lg);
    background: var(--bg-secondary);
    border-top: 1px solid var(--border-color);
    font-size: 0.8rem;
    color: var(--text-secondary);
}

/* Toast Notifications */
.toast-container {
    position: fixed;
    top: var(--spacing-lg);
    right: var(--spacing-lg);
    z-index: 10000;
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
}

.toast {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);
    padding: var(--spacing-md);
    box-shadow: var(--shadow-lg);
    min-width: 300px;
    animation: slideIn 0.3s ease;
}

.toast.success { border-left: 4px solid var(--accent-primary); }
.toast.error { border-left: 4px solid var(--accent-danger); }
.toast.warning { border-left: 4px solid var(--accent-warning); }
.toast.info { border-left: 4px solid var(--accent-secondary); }

@keyframes slideIn {
    from { transform: translateX(100%); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
}

/* Modal */
.modal-container {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    display: none;
    justify-content: center;
    align-items: center;
    z-index: 9999;
}

.modal-container.active {
    display: flex;
}

.modal {
    background: var(--bg-card);
    border-radius: var(--radius-lg);
    padding: var(--spacing-xl);
    max-width: 600px;
    width: 90%;
    max-height: 80vh;
    overflow-y: auto;
    box-shadow: var(--shadow-lg);
}

/* Select */
.select-sm {
    padding: var(--spacing-xs) var(--spacing-sm);
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-sm);
    color: var(--text-primary);
    font-size: 0.8rem;
}

/* Scrollbar */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: var(--bg-secondary);
}

::-webkit-scrollbar-thumb {
    background: var(--border-color);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: var(--text-muted);
}

/* Responsive */
@media (max-width: 768px) {
    .dashboard-header {
        flex-wrap: wrap;
        gap: var(--spacing-md);
    }
    
    .header-center {
        order: 3;
        width: 100%;
        max-width: none;
        margin: var(--spacing-md) 0 0 0;
    }
    
    .overview-grid {
        grid-template-columns: 1fr;
    }
    
    .memory-grid {
        grid-template-columns: 1fr;
    }
}
```

---

### **2.3 State Management**

**Create file:** `lib/cipkg/static/js/store.js`

```javascript
/**
 * CIP Dashboard State Management
 * Redux-like store with undo/redo support
 */

class Store {
    constructor(initialState = {}) {
        this.state = initialState;
        this.listeners = [];
        this.history = [];
        this.historyIndex = -1;
        this.maxHistory = 50;
    }

    getState() {
        return { ...this.state };
    }

    setState(updates, addToHistory = true) {
        const prevState = { ...this.state };
        this.state = { ...this.state, ...updates };

        // Add to history for undo/redo
        if (addToHistory) {
            // Remove any future history if we're not at the end
            if (this.historyIndex < this.history.length - 1) {
                this.history = this.history.slice(0, this.historyIndex + 1);
            }

            this.history.push({
                prev: prevState,
                next: { ...this.state },
                timestamp: Date.now()
            });

            // Limit history size
            if (this.history.length > this.maxHistory) {
                this.history.shift();
            } else {
                this.historyIndex++;
            }
        }

        // Notify listeners
        this._notifyListeners(updates);
    }

    subscribe(listener) {
        this.listeners.push(listener);
        return () => {
            this.listeners = this.listeners.filter(l => l !== listener);
        };
    }

    undo() {
        if (this.historyIndex > 0) {
            this.historyIndex--;
            this.state = { ...this.history[this.historyIndex].prev };
            this._notifyListeners(this.state);
            return true;
        }
        return false;
    }

    redo() {
        if (this.historyIndex < this.history.length - 1) {
            this.historyIndex++;
            this.state = { ...this.history[this.historyIndex].next };
            this._notifyListeners(this.state);
            return true;
        }
        return false;
    }

    canUndo() {
        return this.historyIndex > 0;
    }

    canRedo() {
        return this.historyIndex < this.history.length - 1;
    }

    _notifyListeners(updates) {
        this.listeners.forEach(listener => {
            try {
                listener(this.state, updates);
            } catch (e) {
                console.error('Store listener error:', e);
            }
        });
    }

    // Persist state to localStorage
    persist(key = 'cip-dashboard-state') {
        try {
            localStorage.setItem(key, JSON.stringify(this.state));
        } catch (e) {
            console.warn('Failed to persist state:', e);
        }
    }

    // Restore state from localStorage
    restore(key = 'cip-dashboard-state') {
        try {
            const saved = localStorage.getItem(key);
            if (saved) {
                this.state = JSON.parse(saved);
                this._notifyListeners(this.state);
            }
        } catch (e) {
            console.warn('Failed to restore state:', e);
        }
    }
}

// Create global store instance
const store = new Store({
    // Connection state
    connected: false,
    connectionStatus: 'connecting',

    // Repository state
    repository: {
        root: '',
        name: '',
        health: null,
        stats: null,
        lastSync: null
    },

    // UI state
    activeTab: 'overview',
    theme: 'dark',
    searchQuery: '',
    searchResults: [],
    searchLoading: false,

    // Code map state
    codeMap: {
        nodes: [],
        edges: [],
        layout: 'force',
        filter: 'all',
        zoom: 1,
        panX: 0,
        panY: 0,
        selectedNode: null,
        hoveredNode: null
    },

    // Impact analysis state
    impact: {
        symbolId: '',
        result: null,
        loading: false
    },

    // Gaps state
    gaps: {
        items: [],
        filter: { type: 'all', severity: 'all' },
        loading: false
    },

    // Memory state
    memory: {
        facts: [],
        episodes: [],
        loading: false
    },

    // Activity log
    activity: [],

    // Notifications
    toasts: []
});

// Auto-persist state changes
store.subscribe(() => {
    store.persist();
});

// Export for use in other modules
window.store = store;
```

---

### **2.4 WebSocket Client**

**Create file:** `lib/cipkg/static/js/websocket.js`

```javascript
/**
 * WebSocket client for real-time updates
 */

class WebSocketClient {
    constructor(url) {
        this.url = url;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.subscriptions = new Set();
        this.messageHandlers = new Map();
        this.isConnected = false;
    }

    connect() {
        try {
            this.ws = new WebSocket(this.url);

            this.ws.onopen = () => {
                console.log('🔌 WebSocket connected');
                this.isConnected = true;
                this.reconnectAttempts = 0;

                // Update store
                store.setState({
                    connected: true,
                    connectionStatus: 'connected'
                });

                // Re-subscribe to topics
                this.subscriptions.forEach(topic => {
                    this._sendSubscribe(topic);
                });

                // Emit connected event
                this._emit('connected');
            };

            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this._handleMessage(message);
                } catch (e) {
                    console.error('WebSocket message parse error:', e);
                }
            };

            this.ws.onclose = () => {
                console.log('🔌 WebSocket disconnected');
                this.isConnected = false;

                store.setState({
                    connected: false,
                    connectionStatus: 'disconnected'
                });

                this._emit('disconnected');
                this._attemptReconnect();
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this._emit('error', error);
            };

        } catch (e) {
            console.error('WebSocket connection failed:', e);
            this._attemptReconnect();
        }
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }

    subscribe(topic, handler) {
        this.subscriptions.add(topic);

        if (!this.messageHandlers.has(topic)) {
            this.messageHandlers.set(topic, []);
        }
        this.messageHandlers.get(topic).push(handler);

        // Subscribe on server if connected
        if (this.isConnected) {
            this._sendSubscribe(topic);
        }

        // Return unsubscribe function
        return () => {
            const handlers = this.messageHandlers.get(topic);
            if (handlers) {
                const index = handlers.indexOf(handler);
                if (index > -1) {
                    handlers.splice(index, 1);
                }
            }
        };
    }

    send(message) {
        if (this.ws && this.isConnected) {
            this.ws.send(JSON.stringify(message));
        }
    }

    _sendSubscribe(topic) {
        this.send({
            type: 'subscribe',
            topic: topic
        });
    }

    _handleMessage(message) {
        const { type, topic } = message;

        if (type === 'event' && topic) {
            this._emit(topic, message);
        } else if (type === 'connected') {
            this._emit('connected', message);
        } else if (type === 'pong') {
            this._emit('pong', message);
        }
    }

    _emit(event, data = null) {
        const handlers = this.messageHandlers.get(event) || [];
        handlers.forEach(handler => {
            try {
                handler(data);
            } catch (e) {
                console.error(`WebSocket handler error for ${event}:`, e);
            }
        });
    }

    _attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

            store.setState({
                connectionStatus: `reconnecting (${this.reconnectAttempts}/${this.maxReconnectAttempts})`
            });

            console.log(`🔄 Reconnecting in ${delay}ms...`);
            setTimeout(() => this.connect(), delay);
        } else {
            store.setState({
                connectionStatus: 'failed'
            });
            console.error('❌ Max reconnection attempts reached');
        }
    }

    // Ping server to keep connection alive
    startHeartbeat(interval = 30000) {
        setInterval(() => {
            if (this.isConnected) {
                this.send({ type: 'ping' });
            }
        }, interval);
    }
}

// Create global WebSocket client
const wsUrl = `ws://${window.location.hostname}:${parseInt(window.location.port) + 1}`;
const wsClient = new WebSocketClient(wsUrl);

// Export
window.wsClient = wsClient;
```

---

### **2.5 Code Graph Visualization**

**Create file:** `lib/cipkg/static/js/graph.js`

```javascript
/**
 * Interactive Code Graph Visualization using D3.js
 */

class CodeGraph {
    constructor(containerId) {
        this.container = d3.select(`#${containerId}`);
        this.svg = null;
        this.g = null;
        this.zoom = null;
        this.simulation = null;
        this.nodes = [];
        this.edges = [];
        this.nodeElements = null;
        this.edgeElements = null;
        this.labelElements = null;

        this.colorMap = {
            'function': '#4CAF50',
            'method': '#4CAF50',
            'class': '#2196F3',
            'module': '#FF9800',
            'interface': '#9C27B0',
            'variable': '#F44336'
        };

        this.sizeMap = {
            'function': 8,
            'method': 8,
            'class': 12,
            'module': 15,
            'interface': 10,
            'variable': 6
        };

        this._init();
    }

    _init() {
        const width = this.container.node().clientWidth;
        const height = this.container.node().clientHeight;

        // Create SVG
        this.svg = this.container.append('svg')
            .attr('width', width)
            .attr('height', height);

        // Create zoom behavior
        this.zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on('zoom', (event) => {
                this.g.attr('transform', event.transform);
            });

        this.svg.call(this.zoom);

        // Create main group
        this.g = this.svg.append('g');

        // Create layers
        this.edgeLayer = this.g.append('g').attr('class', 'edges');
        this.nodeLayer = this.g.append('g').attr('class', 'nodes');
        this.labelLayer = this.g.append('g').attr('class', 'labels');

        // Initialize force simulation
        this.simulation = d3.forceSimulation()
            .force('link', d3.forceLink().id(d => d.id).distance(100))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(d => this.sizeMap[d.kind] + 5));
    }

    setData(nodes, edges) {
        this.nodes = nodes.map(n => ({ ...n }));
        this.edges = edges.map(e => ({ ...e }));

        this._render();
    }

    _render() {
        // Clear existing
        this.edgeLayer.selectAll('*').remove();
        this.nodeLayer.selectAll('*').remove();
        this.labelLayer.selectAll('*').remove();

        // Render edges
        this.edgeElements = this.edgeLayer.selectAll('line')
            .data(this.edges)
            .enter()
            .append('line')
            .attr('class', 'graph-edge')
            .attr('stroke', '#4a5568')
            .attr('stroke-width', 1)
            .attr('stroke-opacity', 0.6);

        // Render nodes
        this.nodeElements = this.nodeLayer.selectAll('circle')
            .data(this.nodes)
            .enter()
            .append('circle')
            .attr('class', 'graph-node')
            .attr('r', d => this.sizeMap[d.kind] || 8)
            .attr('fill', d => this.colorMap[d.kind] || '#999')
            .attr('stroke', '#fff')
            .attr('stroke-width', 2)
            .attr('cursor', 'pointer')
            .call(d3.drag()
                .on('start', (event, d) => this._dragStarted(event, d))
                .on('drag', (event, d) => this._dragged(event, d))
                .on('end', (event, d) => this._dragEnded(event, d))
            )
            .on('click', (event, d) => this._nodeClicked(event, d))
            .on('mouseover', (event, d) => this._nodeHovered(event, d))
            .on('mouseout', () => this._nodeUnhovered());

        // Render labels
        this.labelElements = this.labelLayer.selectAll('text')
            .data(this.nodes)
            .enter()
            .append('text')
            .attr('class', 'graph-label')
            .attr('font-size', '10px')
            .attr('fill', '#e8eaed')
            .attr('text-anchor', 'middle')
            .attr('dy', d => -(this.sizeMap[d.kind] + 5))
            .text(d => d.name)
            .attr('pointer-events', 'none');

        // Update simulation
        this.simulation.nodes(this.nodes)
            .on('tick', () => this._ticked());

        this.simulation.force('link')
            .links(this.edges);
    }

    _ticked() {
        this.edgeElements
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);

        this.nodeElements
            .attr('cx', d => d.x)
            .attr('cy', d => d.y);

        this.labelElements
            .attr('x', d => d.x)
            .attr('y', d => d.y);
    }

    _dragStarted(event, d) {
        if (!event.active) this.simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    _dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    _dragEnded(event, d) {
        if (!event.active) this.simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }

    _nodeClicked(event, d) {
        event.stopPropagation();

        // Update store
        store.setState({
            codeMap: {
                ...store.getState().codeMap,
                selectedNode: d
            }
        });

        // Highlight connected nodes
        this._highlightConnections(d);

        // Show tooltip with details
        this._showTooltip(event, d);
    }

    _nodeHovered(event, d) {
        // Enlarge node
        d3.select(event.target)
            .transition()
            .duration(200)
            .attr('r', (this.sizeMap[d.kind] || 8) * 1.5);

        // Show tooltip
        this._showTooltip(event, d);
    }

    _nodeUnhovered() {
        // Reset all nodes
        this.nodeElements
            .transition()
            .duration(200)
            .attr('r', d => this.sizeMap[d.kind] || 8);

        // Hide tooltip
        this._hideTooltip();
    }

    _highlightConnections(node) {
        const connectedIds = new Set();
        connectedIds.add(node.id);

        this.edges.forEach(edge => {
            if (edge.source.id === node.id) connectedIds.add(edge.target.id);
            if (edge.target.id === node.id) connectedIds.add(edge.source.id);
        });

        // Dim non-connected nodes
        this.nodeElements
            .transition()
            .duration(300)
            .attr('opacity', d => connectedIds.has(d.id) ? 1 : 0.2);

        this.edgeElements
            .transition()
            .duration(300)
            .attr('stroke-opacity', d =>
                (d.source.id === node.id || d.target.id === node.id) ? 1 : 0.1
            );
    }

    _showTooltip(event, node) {
        const tooltip = document.getElementById('map-tooltip');
        tooltip.innerHTML = `
            <strong>${node.name}</strong><br>
            <span style="color: ${this.colorMap[node.kind]}">${node.kind}</span><br>
            <small>${node.path}</small>
        `;
        tooltip.style.display = 'block';
        tooltip.style.left = (event.pageX + 10) + 'px';
        tooltip.style.top = (event.pageY + 10) + 'px';
    }

    _hideTooltip() {
        const tooltip = document.getElementById('map-tooltip');
        tooltip.style.display = 'none';
    }

    // Layout methods
    setLayout(layoutType) {
        switch (layoutType) {
            case 'force':
                this._applyForceLayout();
                break;
            case 'tree':
                this._applyTreeLayout();
                break;
            case 'radial':
                this._applyRadialLayout();
                break;
            case 'grid':
                this._applyGridLayout();
                break;
        }
    }

    _applyForceLayout() {
        this.simulation
            .force('link', d3.forceLink().id(d => d.id).distance(100))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(
                this.container.node().clientWidth / 2,
                this.container.node().clientHeight / 2
            ))
            .alpha(1)
            .restart();
    }

    _applyTreeLayout() {
        // Simplified tree layout
        const width = this.container.node().clientWidth;
        const height = this.container.node().clientHeight;

        this.nodes.forEach((node, i) => {
            node.fx = (i % 10) * (width / 10) + 50;
            node.fy = Math.floor(i / 10) * 60 + 50;
        });

        this.simulation.alpha(0.1).restart();
    }

    _applyRadialLayout() {
        const width = this.container.node().clientWidth;
        const height = this.container.node().clientHeight;
        const centerX = width / 2;
        const centerY = height / 2;
        const radius = Math.min(width, height) / 3;

        this.nodes.forEach((node, i) => {
            const angle = (2 * Math.PI * i) / this.nodes.length;
            node.fx = centerX + radius * Math.cos(angle);
            node.fy = centerY + radius * Math.sin(angle);
        });

        this.simulation.alpha(0.1).restart();
    }

    _applyGridLayout() {
        const width = this.container.node().clientWidth;
        const cols = Math.ceil(Math.sqrt(this.nodes.length));
        const cellWidth = width / cols;
        const cellHeight = 60;

        this.nodes.forEach((node, i) => {
            node.fx = (i % cols) * cellWidth + cellWidth / 2;
            node.fy = Math.floor(i / cols) * cellHeight + 50;
        });

        this.simulation.alpha(0.1).restart();
    }

    // Filter nodes by kind
    filterByKind(kind) {
        if (kind === 'all') {
            this.nodeElements.attr('display', null);
            this.labelElements.attr('display', null);
        } else {
            this.nodeElements
                .attr('display', d => d.kind === kind ? null : 'none');
            this.labelElements
                .attr('display', d => d.kind === kind ? null : 'none');
        }
    }

    // Zoom controls
    zoomIn() {
        this.svg.transition().duration(300).call(
            this.zoom.scaleBy, 1.3
        );
    }

    zoomOut() {
        this.svg.transition().duration(300).call(
            this.zoom.scaleBy, 0.7
        );
    }

    fitToView() {
        const bounds = this.g.node().getBBox();
        const width = this.container.node().clientWidth;
        const height = this.container.node().clientHeight;

        const scale = Math.min(
            width / bounds.width,
            height / bounds.height
        ) * 0.9;

        const translate = [
            width / 2 - scale * (bounds.x + bounds.width / 2),
            height / 2 - scale * (bounds.y + bounds.height / 2)
        ];

        this.svg.transition().duration(500).call(
            this.zoom.transform,
            d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale)
        );
    }

    reset() {
        this.svg.transition().duration(500).call(
            this.zoom.transform,
            d3.zoomIdentity
        );
        this.simulation.alpha(1).restart();
    }

    // Resize handler
    resize() {
        const width = this.container.node().clientWidth;
        const height = this.container.node().clientHeight;

        this.svg.attr('width', width).attr('height', height);
        this.simulation.force('center', d3.forceCenter(width / 2, height / 2));
        this.simulation.alpha(0.3).restart();
    }
}

// Export
window.CodeGraph = CodeGraph;
```

---

### **2.6 Main Application**

**Create file:** `lib/cipkg/static/js/app.js`

```javascript
/**
 * CIP Dashboard Main Application
 */

class DashboardApp {
    constructor() {
        this.codeGraph = null;
        this.healthChart = null;
        this._init();
    }

    async _init() {
        // Initialize components
        this._initTheme();
        this._initNavigation();
        this._initSearch();
        this._initWebSocket();
        this._initKeyboardShortcuts();

        // Load initial data
        await this._loadInitialData();

        // Initialize code graph when tab is activated
        this._initCodeGraph();

        // Start heartbeat
        wsClient.startHeartbeat();

        console.log('🚀 CIP Dashboard v2.0 initialized');
    }

    _initTheme() {
        const themeBtn = document.getElementById('btn-theme');
        const savedTheme = localStorage.getItem('cip-theme') || 'dark';

        document.documentElement.setAttribute('data-theme', savedTheme);

        themeBtn.addEventListener('click', () => {
            const current = document.documentElement.getAttribute('data-theme');
            const newTheme = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('cip-theme', newTheme);
        });
    }

    _initNavigation() {
        const tabs = document.querySelectorAll('.nav-tab');

        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const tabId = tab.dataset.tab;

                // Update active tab
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');

                // Show corresponding content
                document.querySelectorAll('.tab-content').forEach(content => {
                    content.classList.remove('active');
                });
                document.getElementById(`tab-${tabId}`).classList.add('active');

                // Update store
                store.setState({ activeTab: tabId });

                // Load tab-specific data
                this._loadTabData(tabId);
            });
        });
    }

    _initSearch() {
        const searchInput = document.getElementById('global-search');
        const searchResults = document.getElementById('search-results');
        let debounceTimer = null;

        searchInput.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            const query = e.target.value.trim();

            if (query.length < 2) {
                searchResults.classList.remove('active');
                return;
            }

            debounceTimer = setTimeout(async () => {
                const results = await this._apiSearch(query, 5);
                this._renderSearchDropdown(results);
            }, 300);
        });

        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                const query = searchInput.value.trim();
                if (query) {
                    this._performFullSearch(query);
                }
            }
            if (e.key === 'Escape') {
                searchResults.classList.remove('active');
            }
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-container')) {
                searchResults.classList.remove('active');
            }
        });
    }

    _initWebSocket() {
        // Connect WebSocket
        wsClient.connect();

        // Subscribe to events
        wsClient.subscribe('index', (data) => {
            this._showToast('Index updated', 'success');
            this._loadStats();
        });

        wsClient.subscribe('health', (data) => {
            this._updateHealthGauge(data.score);
        });

        wsClient.subscribe('sync', (data) => {
            this._showToast('Sync complete', 'success');
            this._loadStats();
        });

        wsClient.subscribe('memory', (data) => {
            this._showToast('Memory updated', 'info');
        });
    }

    _initKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + K for search
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                document.getElementById('global-search').focus();
            }

            // Ctrl/Cmd + Z for undo
            if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
                if (e.shiftKey) {
                    store.redo();
                } else {
                    store.undo();
                }
            }

            // Number keys for tab switching
            if (e.altKey && e.key >= '1' && e.key <= '7') {
                const tabIndex = parseInt(e.key) - 1;
                const tabs = document.querySelectorAll('.nav-tab');
                if (tabs[tabIndex]) {
                    tabs[tabIndex].click();
                }
            }
        });
    }

    _initCodeGraph() {
        // Initialize when code map tab is first activated
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.target.id === 'tab-code-map' &&
                    mutation.target.classList.contains('active')) {
                    this._loadCodeMap();
                }
            });
        });

        observer.observe(document.getElementById('tab-code-map'), {
            attributes: true,
            attributeFilter: ['class']
        });

        // Map toolbar controls
        document.getElementById('map-zoom-in')?.addEventListener('click', () => {
            this.codeGraph?.zoomIn();
        });

        document.getElementById('map-zoom-out')?.addEventListener('click', () => {
            this.codeGraph?.zoomOut();
        });

        document.getElementById('map-fit')?.addEventListener('click', () => {
            this.codeGraph?.fitToView();
        });

        document.getElementById('map-reset')?.addEventListener('click', () => {
            this.codeGraph?.reset();
        });

        document.getElementById('map-layout')?.addEventListener('change', (e) => {
            this.codeGraph?.setLayout(e.target.value);
        });

        document.getElementById('map-filter')?.addEventListener('change', (e) => {
            this.codeGraph?.filterByKind(e.target.value);
        });
    }

    async _loadInitialData() {
        try {
            // Load stats
            await this._loadStats();

            // Load health
            await this._loadHealth();

            // Load activity
            await this._loadActivity();

            // Update footer
            this._updateFooter();

        } catch (e) {
            console.error('Failed to load initial data:', e);
            this._showToast('Failed to load data', 'error');
        }
    }

    async _loadTabData(tabId) {
        switch (tabId) {
            case 'overview':
                await this._loadHealth();
                await this._loadStats();
                break;
            case 'code-map':
                await this._loadCodeMap();
                break;
            case 'gaps':
                await this._loadGaps();
                break;
            case 'memory':
                await this._loadMemory();
                break;
            case 'settings':
                await this._loadSettings();
                break;
        }
    }

    async _loadStats() {
        try {
            const response = await fetch('/api/stats');
            const data = await response.json();

            document.getElementById('stat-files').textContent = this._formatNumber(data.files);
            document.getElementById('stat-symbols').textContent = this._formatNumber(data.symbols);
            document.getElementById('stat-chunks').textContent = this._formatNumber(data.chunks);
            document.getElementById('stat-edges').textContent = this._formatNumber(data.edges);
            document.getElementById('last-sync').textContent = `Last sync: ${data.last_sync}`;

        } catch (e) {
            console.error('Failed to load stats:', e);
        }
    }

    async _loadHealth() {
        try {
            const response = await fetch('/api/health');
            const data = await response.json();

            this._updateHealthGauge(data.score || 0);
            this._renderHealthDetails(data);

        } catch (e) {
            console.error('Failed to load health:', e);
        }
    }

    async _loadCodeMap() {
        try {
            const response = await fetch('/api/graph');
            const data = await response.json();

            if (!this.codeGraph) {
                this.codeGraph = new CodeGraph('code-map');
            }

            this.codeGraph.setData(data.nodes, data.edges);

        } catch (e) {
            console.error('Failed to load code map:', e);
        }
    }

    async _loadGaps() {
        try {
            const response = await fetch('/api/gaps');
            const data = await response.json();

            this._renderGaps(data.gaps);

        } catch (e) {
            console.error('Failed to load gaps:', e);
        }
    }

    async _loadMemory() {
        try {
            const response = await fetch('/api/memory');
            const data = await response.json();

            this._renderMemoryFacts(data.facts);
            this._renderMemoryEpisodes(data.episodes);

        } catch (e) {
            console.error('Failed to load memory:', e);
        }
    }

    async _loadSettings() {
        try {
            const response = await fetch('/api/config');
            const data = await response.json();

            this._renderSettings(data);

        } catch (e) {
            console.error('Failed to load settings:', e);
        }
    }

    async _loadActivity() {
        // For now, show placeholder
        const activityList = document.getElementById('activity-list');
        activityList.innerHTML = `
            <div class="activity-item">🔄 System initialized</div>
            <div class="activity-item">📊 Dashboard loaded</div>
        `;
    }

    // === Rendering Methods ===

    _updateHealthGauge(score) {
        const scoreEl = document.getElementById('health-score');
        scoreEl.textContent = score;

        // Color based on score
        if (score >= 80) {
            scoreEl.style.color = '#4CAF50';
        } else if (score >= 60) {
            scoreEl.style.color = '#FF9800';
        } else {
            scoreEl.style.color = '#F44336';
        }

        // Draw gauge using Chart.js
        const ctx = document.getElementById('health-gauge').getContext('2d');
        if (this.healthChart) {
            this.healthChart.destroy();
        }

        this.healthChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [score, 100 - score],
                    backgroundColor: [
                        score >= 80 ? '#4CAF50' : score >= 60 ? '#FF9800' : '#F44336',
                        '#2a3a4a'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                cutout: '80%',
                responsive: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false }
                }
            }
        });
    }

    _renderHealthDetails(data) {
        const details = document.getElementById('health-details');
        details.innerHTML = `
            <div class="health-detail">
                <span>Coverage:</span>
                <span>${data.coverage || '--'}%</span>
            </div>
            <div class="health-detail">
                <span>Quality:</span>
                <span>${data.quality || '--'}%</span>
            </div>
            <div class="health-detail">
                <span>Recency:</span>
                <span>${data.recency || '--'}%</span>
            </div>
        `;
    }

    _renderSearchDropdown(results) {
        const dropdown = document.getElementById('search-results');

        if (!results || results.length === 0) {
            dropdown.innerHTML = '<div class="search-dropdown-item">No results found</div>';
            dropdown.classList.add('active');
            return;
        }

        dropdown.innerHTML = results.map(result => `
            <div class="search-dropdown-item" data-path="${result.path}" data-line="${result.start_line}">
                <div class="search-dropdown-path">${result.path}</div>
                <div class="search-dropdown-preview">${this._escapeHtml(result.text?.substring(0, 100))}...</div>
            </div>
        `).join('');

        dropdown.classList.add('active');

        // Add click handlers
        dropdown.querySelectorAll('.search-dropdown-item').forEach(item => {
            item.addEventListener('click', () => {
                const path = item.dataset.path;
                const line = item.dataset.line;
                this._showToast(`Opening ${path}:${line}`, 'info');
                dropdown.classList.remove('active');
            });
        });
    }

    _renderGaps(gaps) {
        const list = document.getElementById('gaps-list');
        const summary = document.getElementById('gaps-summary');

        if (!gaps || gaps.length === 0) {
            list.innerHTML = '<div class="gap-item">No gaps found! 🎉</div>';
            summary.textContent = 'No knowledge gaps detected.';
            return;
        }

        // Summary
        const byType = {};
        gaps.forEach(gap => {
            byType[gap.type] = (byType[gap.type] || 0) + 1;
        });

        summary.innerHTML = Object.entries(byType).map(([type, count]) =>
            `<span class="gap-summary-item">${type.replace('_', ' ')}: ${count}</span>`
        ).join(' | ');

        // List
        list.innerHTML = gaps.map(gap => `
            <div class="gap-item">
                <div class="gap-severity ${gap.severity}"></div>
                <div class="gap-content">
                    <div class="gap-title">${gap.description}</div>
                    <div class="gap-description">${gap.path}</div>
                    <div class="gap-fix">💡 ${gap.suggested_fix}</div>
                </div>
            </div>
        `).join('');
    }

    _renderMemoryFacts(facts) {
        const container = document.getElementById('memory-facts');

        if (!facts || facts.length === 0) {
            container.innerHTML = '<div class="memory-fact">No memories stored yet.</div>';
            return;
        }

        container.innerHTML = facts.map(fact => `
            <div class="memory-fact">
                <div class="fact-predicate">${fact.predicate}</div>
                <div class="fact-value">${JSON.stringify(fact.object_value)}</div>
                <div class="fact-time">${new Date(fact.valid_from * 1000).toLocaleString()}</div>
            </div>
        `).join('');
    }

    _renderMemoryEpisodes(episodes) {
        const container = document.getElementById('memory-episodes');

        if (!episodes || episodes.length === 0) {
            container.innerHTML = '<div class="memory-fact">No episodes recorded yet.</div>';
            return;
        }

        container.innerHTML = episodes.map(ep => `
            <div class="memory-fact">
                <div class="fact-predicate">${ep.type}</div>
                <div class="fact-value">${JSON.stringify(ep.context).substring(0, 100)}...</div>
                <div class="fact-time">${new Date(ep.timestamp * 1000).toLocaleString()}</div>
            </div>
        `).join('');
    }

    _renderSettings(config) {
        const sections = {
            'settings-index': config.index,
            'settings-embed': config.embed,
            'settings-retrieval': config.retrieval,
            'settings-memory': config.memory
        };

        Object.entries(sections).forEach(([elementId, sectionConfig]) => {
            const element = document.getElementById(elementId);
            if (element && sectionConfig) {
                element.innerHTML = Object.entries(sectionConfig).map(([key, value]) => `
                    <div class="setting-item">
                        <span class="setting-label">${key}</span>
                        <span class="setting-value">${value}</span>
                    </div>
                `).join('');
            }
        });
    }

    // === API Methods ===

    async _apiSearch(query, limit = 10) {
        try {
            const response = await fetch(`/api/search?q=${encodeURIComponent(query)}&limit=${limit}`);
            const data = await response.json();
            return data.results || [];
        } catch (e) {
            console.error('Search API error:', e);
            return [];
        }
    }

    async _performFullSearch(query) {
        // Switch to search tab
        document.querySelector('[data-tab="search"]').click();

        // Set search input
        document.getElementById('search-input').value = query;

        // Perform search
        const results = await this._apiSearch(query, 20);
        this._renderFullSearchResults(results);
    }

    _renderFullSearchResults(results) {
        const container = document.getElementById('search-results-full');

        if (!results || results.length === 0) {
            container.innerHTML = '<div class="search-result-item">No results found.</div>';
            return;
        }

        container.innerHTML = results.map(result => `
            <div class="search-result-item">
                <div class="search-result-path">${result.path}:${result.start_line}-${result.end_line}</div>
                <div class="search-result-code">${this._escapeHtml(result.text)}</div>
                <div class="search-result-score">Score: ${(result.score * 100).toFixed(1)}%</div>
            </div>
        `).join('');
    }

    // === Utility Methods ===

    _showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;

        container.appendChild(toast);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            toast.remove();
        }, 5000);
    }

    _formatNumber(num) {
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toString();
    }

    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    _updateFooter() {
        document.getElementById('footer-time').textContent = new Date().toLocaleTimeString();

        // Update time every second
        setInterval(() => {
            document.getElementById('footer-time').textContent = new Date().toLocaleTimeString();
        }, 1000);
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.dashboardApp = new DashboardApp();
});
```

---

## 📝 **IMPLEMENTATION INSTRUCTIONS**

### **Step 1: Create Directory Structure**

```bash
mkdir -p lib/cipkg/static/css
mkdir -p lib/cipkg/static/js
mkdir -p lib/cipkg/static/lib
```

### **Step 2: Create/Replace Files**

```bash
# Backend files
touch lib/cipkg/web_server.py
touch lib/cipkg/websocket_handler.py

# Frontend files
touch lib/cipkg/static/dashboard.html
touch lib/cipkg/static/css/dashboard.css
touch lib/cipkg/static/css/graph.css
touch lib/cipkg/static/css/components.css
touch lib/cipkg/static/js/store.js
touch lib/cipkg/static/js/websocket.js
touch lib/cipkg/static/js/graph.js
touch lib/cipkg/static/js/search.js
touch lib/cipkg/static/js/impact.js
touch lib/cipkg/static/js/memory.js
touch lib/cipkg/static/js/components.js
touch lib/cipkg/static/js/app.js
```

### **Step 3: Add CLI Command**

Add to `lib/cipkg/cli.py`:

```python
def handle_dashboard_web_command(root, args):
    """Handle 'cip dashboard-web' command."""
    from .web_server import start_web_server
    port = getattr(args, 'port', 8080)
    host = getattr(args, 'host', 'localhost')
    start_web_server(root, port, host)
```

Add to dispatch dictionary:
```python
"dashboard-web": handle_dashboard_web_command,
```

### **Step 4: Install Dependencies**

```bash
pip install websockets
```

Add to `requirements.txt`:
```txt
websockets>=12.0
```

### **Step 5: Test**

```bash
# Start web dashboard
cip dashboard-web --port 8080

# Open in browser
open http://localhost:8080
```

---

## ✅ **VERIFICATION CHECKLIST**

- [ ] Web dashboard loads at http://localhost:8080
- [ ] WebSocket connects successfully
- [ ] Health gauge displays correctly
- [ ] Stats update in real-time
- [ ] Code map renders with interactive nodes
- [ ] Zoom/pan works on code map
- [ ] Node click shows connections
- [ ] Search returns results
- [ ] Impact analysis visualizes blast radius
- [ ] Gaps list displays correctly
- [ ] Memory dashboard shows facts and episodes
- [ ] Theme toggle works
- [ ] Keyboard shortcuts functional
- [ ] Toast notifications appear
- [ ] State persists across page refresh
- [ ] Responsive on mobile

---

This upgrade transforms the web dashboard into a **production-grade, fully interactive application** that agents and developers can use to explore, analyze, and understand codebases visually! 🚀z
s

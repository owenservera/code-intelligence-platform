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
    
    async def handler(self, websocket):
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
        
        async with websockets.serve(self.handler, self.host, self.port) as server:
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
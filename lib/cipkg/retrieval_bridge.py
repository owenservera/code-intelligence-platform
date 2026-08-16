"""
Bridge between retrieval system and context manager.
Formats search results for agent consumption.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ContextItem:
    """A single item of context for agent consumption."""
    type: str  # 'code_snippet', 'file_reference', 'test_reference', 'summary'
    path: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UnifiedContext:
    """Unified context package for agent consumption."""
    items: List[ContextItem]
    total_tokens: int
    budget_tokens: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContextManager:
    """Manage and format context for agent consumption."""
    
    def __init__(self, root: str):
        self.root = root
    
    def build_context(
        self,
        items: List[Dict[str, Any]],
        max_tokens: int = 4096,
        priority: str = 'relevance'
    ) -> UnifiedContext:
        """Build unified context from items.
        
        Args:
            items: List of context items with type, path, content, metadata
            max_tokens: Maximum token budget
            priority: Priority for item selection ('relevance', 'impact', 'recency')
        
        Returns:
            UnifiedContext with selected items within token budget
        """
        context_items = []
        used_tokens = 0
        
        # Sort items by priority
        if priority == 'relevance':
            items.sort(key=lambda x: x.get('metadata', {}).get('score', 0), reverse=True)
        elif priority == 'impact':
            items.sort(key=lambda x: x.get('metadata', {}).get('impact_level', 'low'))
        elif priority == 'recency':
            items.sort(key=lambda x: x.get('metadata', {}).get('timestamp', 0), reverse=True)
        
        for item in items:
            # Estimate tokens (rough: 4 chars per token)
            content = item.get('content', '')
            item_tokens = len(content) // 4
            
            if used_tokens + item_tokens > max_tokens and context_items:
                break
            
            context_items.append(ContextItem(
                type=item.get('type', 'unknown'),
                path=item.get('path', ''),
                content=content,
                metadata=item.get('metadata', {})
            ))
            used_tokens += item_tokens
        
        return UnifiedContext(
            items=context_items,
            total_tokens=used_tokens,
            budget_tokens=max_tokens,
            metadata={'priority': priority, 'item_count': len(context_items)}
        )


def search_and_format(root: str, query: str, max_tokens: int = 4096) -> UnifiedContext:
    """Search and format results for agent context.
    
    Args:
        root: Repository root path
        query: Search query string
        max_tokens: Maximum token budget for context
    
    Returns:
        UnifiedContext with formatted search results
    """
    from . import retrieve
    
    # Perform hybrid search
    results = retrieve.search(root, query, k=20)
    
    # Format for agent
    context_manager = ContextManager(root)
    
    # Build context from search results
    context_items = []
    for result in results:
        context_items.append({
            'type': 'code_snippet',
            'path': result.get('path', ''),
            'content': result.get('snippet', ''),
            'metadata': {
                'symbol_id': result.get('symbol'),
                'start_line': result.get('lines', [0, 0])[0],
                'end_line': result.get('lines', [0, 0])[1],
                'score': result.get('score', 0),
                'matched': result.get('matched', []),
                'tier': result.get('tier', 'code')
            }
        })
    
    # Create unified context with token budget
    unified = context_manager.build_context(
        items=context_items,
        max_tokens=max_tokens,
        priority='relevance'
    )
    
    return unified


def get_impact_context(root: str, target: str, max_tokens: int = 2048) -> UnifiedContext:
    """Get context for impact analysis.
    
    Args:
        root: Repository root path
        target: File or symbol to analyze impact for
        max_tokens: Maximum token budget for context
    
    Returns:
        UnifiedContext with impact analysis results
    """
    from .stack import impact
    
    # Get impact analysis
    impact_data = impact.impact(root, target)
    
    # Format for agent
    context_manager = ContextManager(root)
    
    context_items = []
    
    # Add affected files
    for affected_path in impact_data.get('affected_files', []):
        context_items.append({
            'type': 'file_reference',
            'path': affected_path,
            'content': f"Affected by change to {target}",
            'metadata': {
                'impact_level': impact_data.get('risk', 'low'),
                'distance': 1
            }
        })
    
    # Add test files
    for test_file in impact_data.get('tests_to_run', []):
        context_items.append({
            'type': 'test_reference',
            'path': test_file,
            'content': f"Tests affected by change to {target}",
            'metadata': {'impact_level': 'high'}
        })
    
    # Add routes affected
    for route in impact_data.get('routes_affected', []):
        context_items.append({
            'type': 'route_reference',
            'path': route.get('path', ''),
            'content': f"Route affected: {route.get('kind', 'unknown')}",
            'metadata': {'impact_level': 'high'}
        })
    
    # Add advice
    advice = impact_data.get('advice', [])
    if advice:
        context_items.append({
            'type': 'summary',
            'path': '',
            'content': '\n'.join(advice),
            'metadata': {'impact_level': impact_data.get('risk', 'low')}
        })
    
    return context_manager.build_context(
        items=context_items,
        max_tokens=max_tokens,
        priority='impact'
    )


def get_symbol_context(root: str, symbol_id: str, max_tokens: int = 3072) -> UnifiedContext:
    """Get comprehensive context for a symbol.
    
    Args:
        root: Repository root path
        symbol_id: Symbol ID or name
        max_tokens: Maximum token budget for context
    
    Returns:
        UnifiedContext with symbol context
    """
    from . import retrieve
    
    # Get symbol details
    symbols = retrieve.find_symbol(root, symbol_id, limit=1)
    if not symbols:
        return UnifiedContext(items=[], total_tokens=0, budget_tokens=max_tokens)
    
    symbol = symbols[0]
    context_manager = ContextManager(root)
    context_items = []
    
    # Add symbol source
    context_items.append({
        'type': 'code_snippet',
        'path': symbol.get('path', ''),
        'content': f"Symbol: {symbol.get('name', '')}\nKind: {symbol.get('kind', '')}\nSignature: {symbol.get('signature', '')}",
        'metadata': {
            'symbol_id': symbol.get('id'),
            'start_line': symbol.get('start_line'),
            'end_line': symbol.get('end_line'),
            'score': 1.0
        }
    })
    
    # Get graph relationships
    graph_data = retrieve.graph(root, symbol.get('id'), direction='both', depth=1)
    
    # Add callers
    for edge in graph_data.get('edges', [])[:10]:
        if edge.get('dst') == symbol.get('id'):
            caller_id = edge.get('src')
            caller = con.execute("SELECT name, path FROM symbols WHERE id=?", (caller_id,)).fetchone()
            if caller:
                context_items.append({
                    'type': 'code_snippet',
                    'path': caller['path'],
                    'content': f"Caller: {caller['name']}",
                    'metadata': {'relationship': 'caller', 'score': 0.8}
                })
    
    # Add callees
    for edge in graph_data.get('edges', [])[:10]:
        if edge.get('src') == symbol.get('id'):
            callee_id = edge.get('dst')
            callee = con.execute("SELECT name, path FROM symbols WHERE id=?", (callee_id,)).fetchone()
            if callee:
                context_items.append({
                    'type': 'code_snippet',
                    'path': callee['path'],
                    'content': f"Callee: {callee['name']}",
                    'metadata': {'relationship': 'callee', 'score': 0.8}
                })
    
    # Add test files
    tests = [r['dst'] for r in con.execute(
        "SELECT dst FROM edges WHERE src=? AND kind='tested_by'", (symbol['id'],)).fetchall()]
    for test_id in tests[:3]:
        test = con.execute("SELECT path FROM symbols WHERE id=?", (test_id,)).fetchone()
        if test:
            context_items.append({
                'type': 'test_reference',
                'path': test['path'],
                'content': f"Test for {symbol['name']}",
                'metadata': {'impact_level': 'high', 'score': 0.9}
            })
    
    return context_manager.build_context(
        items=context_items,
        max_tokens=max_tokens,
        priority='relevance'
    )

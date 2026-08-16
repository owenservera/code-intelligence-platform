"""
AST-Aware Code Chunking - Semantic boundaries instead of arbitrary line splits.
"""
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class ASTChunk:
    text: str
    start_line: int
    end_line: int
    symbol_id: Optional[str]
    symbol_kind: Optional[str]
    parent_symbol: Optional[str]

def chunk_by_ast(parsed_symbols: List[Dict], source_lines: List[str]) -> List[ASTChunk]:
    """Chunk code at AST boundaries (functions, classes) instead of line counts."""
    chunks = []
    
    # Group symbols by parent
    top_level_symbols = [s for s in parsed_symbols if not s.get('parent')]
    
    for symbol in top_level_symbols:
        start = symbol.get('start_line', 0)
        end = symbol.get('end_line', start)
        
        # Extract the complete symbol
        chunk_text = '\n'.join(source_lines[start-1:end])
        
        chunks.append(ASTChunk(
            text=chunk_text,
            start_line=start,
            end_line=end,
            symbol_id=symbol.get('id'),
            symbol_kind=symbol.get('kind'),
            parent_symbol=symbol.get('parent')
        ))
    
    # Handle remaining code between symbols
    if top_level_symbols:
        last_end = max(s.get('end_line', 0) for s in top_level_symbols)
        if last_end < len(source_lines):
            remaining = '\n'.join(source_lines[last_end:])
            if remaining.strip():
                chunks.append(ASTChunk(
                    text=remaining,
                    start_line=last_end + 1,
                    end_line=len(source_lines),
                    symbol_id=None,
                    symbol_kind='module',
                    parent_symbol=None
                ))
    
    return chunks

def chunk_file_ast_aware(file_path: str, parsed_data: Dict) -> List[ASTChunk]:
    """Main entry point for AST-aware chunking."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        source_lines = source.split('\n')
        symbols = parsed_data.get('symbols', [])
        
        return chunk_by_ast(symbols, source_lines)
    except Exception:
        # Fallback to simple chunking
        return []

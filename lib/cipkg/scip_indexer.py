"""
SCIP (Source Code Intelligence Protocol) Integration
Provides precise cross-file symbol resolution.
"""
import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class SCIPSymbol:
    id: str
    name: str
    kind: str
    definition_path: str
    definition_line: int
    references: List[Dict]

class SCIPIndexer:
    """Index codebase using SCIP for precise symbol resolution."""
    
    def __init__(self, root: str):
        self.root = root
        self.symbols: Dict[str, SCIPSymbol] = {}
        self.scip_data: Optional[Dict] = None
    
    def index(self) -> Dict[str, SCIPSymbol]:
        """Generate SCIP index for the repository."""
        # Check if scip-cli is available
        if not self._scip_available():
            print("Warning: scip-cli not found. Install with: pip install scip-python")
            return {}
        
        # Run scip indexer
        scip_output = self._run_scip_index()
        if not scip_output:
            return {}
        
        # Parse SCIP JSON
        self.scip_data = json.loads(scip_output)
        self._extract_symbols()
        
        return self.symbols
    
    def _scip_available(self) -> bool:
        """Check if scip-cli is installed."""
        import shutil
        return shutil.which('scip') is not None
    
    def _run_scip_index(self) -> Optional[str]:
        """Run scip index command."""
        import subprocess
        try:
            result = subprocess.run(
                ['scip', 'index', '--output', 'json'],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=300
            )
            return result.stdout if result.returncode == 0 else None
        except Exception:
            return None
    
    def _extract_symbols(self):
        """Extract symbols from SCIP data."""
        if not self.scip_data:
            return
        
        for occurrence in self.scip_data.get('occurrences', []):
            symbol_id = occurrence.get('symbol')
            if not symbol_id:
                continue
            
            # Parse SCIP symbol format
            # Format: language manager package version descriptor
            parts = symbol_id.split(' ')
            if len(parts) >= 5:
                name = parts[-1].rstrip('.')
                kind = self._infer_kind(parts)
                
                if occurrence.get('isDefinition'):
                    self.symbols[symbol_id] = SCIPSymbol(
                        id=symbol_id,
                        name=name,
                        kind=kind,
                        definition_path=occurrence.get('path', ''),
                        definition_line=occurrence.get('range', {}).get('start', {}).get('line', 0),
                        references=[]
                    )
                elif symbol_id in self.symbols:
                    # This is a reference
                    self.symbols[symbol_id].references.append({
                        'path': occurrence.get('path', ''),
                        'line': occurrence.get('range', {}).get('start', {}).get('line', 0)
                    })
    
    def _infer_kind(self, parts: List[str]) -> str:
        """Infer symbol kind from SCIP descriptor."""
        descriptor = parts[-2] if len(parts) >= 2 else ''
        
        if descriptor.endswith('('):
            return 'function'
        elif descriptor.endswith('.'):
            return 'class'
        elif descriptor.endswith('/'):
            return 'module'
        else:
            return 'variable'
    
    def find_references(self, symbol_name: str) -> List[Dict]:
        """Find all references to a symbol."""
        results = []
        for symbol in self.symbols.values():
            if symbol.name == symbol_name:
                results.extend(symbol.references)
        return results
    
    def find_definition(self, symbol_name: str) -> Optional[Dict]:
        """Find definition of a symbol."""
        for symbol in self.symbols.values():
            if symbol.name == symbol_name:
                return {
                    'path': symbol.definition_path,
                    'line': symbol.definition_line,
                    'kind': symbol.kind
                }
        return None

# CLI integration
def handle_scip_command(root, args):
    """Index repository with SCIP."""
    indexer = SCIPIndexer(root)
    symbols = indexer.index()
    
    print(f"Indexed {len(symbols)} symbols with SCIP")
    
    # Save to database
    from .store import connect
    con = connect(root)
    
    for symbol_id, symbol in symbols.items():
        con.execute("""
            INSERT OR REPLACE INTO symbols (id, name, kind, path, start_line, signature)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            symbol_id,
            symbol.name,
            symbol.kind,
            symbol.definition_path,
            symbol.definition_line,
            f"SCIP:{symbol_id}"
        ))
        
        # Add references as edges
        for ref in symbol.references:
            con.execute("""
                INSERT OR IGNORE INTO edges (src, dst, kind, src_path)
                VALUES (?, ?, 'references', ?)
            """, (ref['path'], symbol_id, ref['path']))
    
    con.commit()

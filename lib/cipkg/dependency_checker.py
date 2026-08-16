"""
Dependency checker - Verify required dependencies are installed.
"""
import importlib
from typing import Dict, List, Tuple


REQUIRED_DEPS = {
    'core': ['numpy', 'tomli'],
    'embeddings': ['sentence_transformers', 'torch'],
    'parsing': ['tree_sitter', 'tree_sitter_languages'],
    'tui': ['textual'],
    'graph': ['networkx'],
    'vector_db': ['lancedb', 'pyarrow'],
    'watcher': ['watchdog'],
    'http': ['httpx']
}

OPTIONAL_DEPS = {
    'ml': ['scikit-learn', 'pandas'],
    'visualization': ['matplotlib', 'plotly'],
    'testing': ['pytest', 'pytest-cov']
}


def check_dependencies() -> Dict[str, List[Tuple[str, bool]]]:
    """Check all dependencies and return status.
    
    Returns:
        Dictionary mapping category to list of (dependency_name, installed) tuples
    """
    results = {}
    
    for category, deps in REQUIRED_DEPS.items():
        results[category] = []
        
        for dep in deps:
            try:
                importlib.import_module(dep)
                results[category].append((dep, True))
            except ImportError:
                results[category].append((dep, False))
    
    return results


def check_optional_dependencies() -> Dict[str, List[Tuple[str, bool]]]:
    """Check optional dependencies and return status.
    
    Returns:
        Dictionary mapping category to list of (dependency_name, installed) tuples
    """
    results = {}
    
    for category, deps in OPTIONAL_DEPS.items():
        results[category] = []
        
        for dep in deps:
            try:
                importlib.import_module(dep)
                results[category].append((dep, True))
            except ImportError:
                results[category].append((dep, False))
    
    return results


def get_missing_dependencies() -> List[str]:
    """Get list of missing required dependencies.
    
    Returns:
        List of missing dependencies in format 'category: dependency'
    """
    missing = []
    
    for category, deps in check_dependencies().items():
        for dep, installed in deps:
            if not installed:
                missing.append(f"{category}: {dep}")
    
    return missing


def get_missing_optional_dependencies() -> List[str]:
    """Get list of missing optional dependencies.
    
    Returns:
        List of missing optional dependencies in format 'category: dependency'
    """
    missing = []
    
    for category, deps in check_optional_dependencies().items():
        for dep, installed in deps:
            if not installed:
                missing.append(f"{category}: {dep}")
    
    return missing


def print_dependency_report():
    """Print dependency status report."""
    results = check_dependencies()
    optional_results = check_optional_dependencies()
    
    print("\n📦 Dependency Status Report")
    print("=" * 50)
    
    for category, deps in results.items():
        print(f"\n{category.upper()}:")
        for dep, installed in deps:
            status = "✅" if installed else "❌"
            print(f"  {status} {dep}")
    
    print("\n\nOptional Dependencies:")
    for category, deps in optional_results.items():
        print(f"\n{category.upper()}:")
        for dep, installed in deps:
            status = "✅" if installed else "⚠️"
            print(f"  {status} {dep}")
    
    missing = get_missing_dependencies()
    if missing:
        print(f"\n⚠️  Missing required dependencies: {len(missing)}")
        for dep in missing:
            print(f"  • {dep}")
        print("\nInstall with: pip install " + " ".join([d.split(": ")[1] for d in missing]))
    else:
        print("\n✅ All required dependencies installed!")
    
    missing_optional = get_missing_optional_dependencies()
    if missing_optional:
        print(f"\nℹ️  Missing optional dependencies: {len(missing_optional)}")
        for dep in missing_optional:
            print(f"  • {dep}")


def handle_deps_command(root, args):
    """Handle 'cip deps' command."""
    print_dependency_report()


if __name__ == "__main__":
    print_dependency_report()

"""
Initialization Status Detection for CIP CLI v2.0

This module provides detection of repository initialization status and
guidance for the initialization process.
"""

import os
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


class InitStatus(Enum):
    """Repository initialization status."""
    NOT_INITIALIZED = "not_initialized"
    INITIALIZED_NO_INDEX = "initialized_no_index"
    INITIALIZED_STALE_INDEX = "initialized_stale_index"
    FULLY_INITIALIZED = "fully_initialized"
    ERROR = "error"


@dataclass
class RepoDetection:
    """Repository detection results."""
    repo_type: str
    languages: List[str]
    frameworks: List[str]
    has_git: bool
    git_branch: Optional[str]
    git_uncommitted: int
    file_count: int


@dataclass
class InitState:
    """Complete initialization state."""
    status: InitStatus
    cip_dir_exists: bool
    config_exists: bool
    index_exists: bool
    index_fresh: bool
    git_hooks_installed: bool
    agents_md_exists: bool
    detection: Optional[RepoDetection] = None
    error_message: Optional[str] = None
    recommendations: List[str] = None


class InitDetector:
    """Detect repository initialization status."""
    
    def __init__(self, root: str):
        self.root = root
        self.cip_dir = os.path.join(root, ".cip")
        self.data_dir = os.path.join(self.cip_dir, "data")
        self.config_file = os.path.join(self.cip_dir, "config.toml")
        self.index_file = os.path.join(self.data_dir, "index.db")
        self.agents_file = os.path.join(root, "AGENTS.md")
    
    def detect(self) -> InitState:
        """Detect complete initialization state."""
        try:
            # Check basic CIP directory structure
            cip_dir_exists = os.path.isdir(self.cip_dir)
            config_exists = os.path.isfile(self.config_file)
            index_exists = os.path.isfile(self.index_file)
            agents_md_exists = os.path.isfile(self.agents_file)
            
            # Check git hooks
            git_hooks_installed = self._check_git_hooks()
            
            # Check index freshness
            index_fresh = self._check_index_freshness() if index_exists else False
            
            # Detect repository characteristics
            detection = self._detect_repo()
            
            # Determine overall status
            if not cip_dir_exists:
                status = InitStatus.NOT_INITIALIZED
                recommendations = self._get_init_recommendations(detection)
            elif not index_exists:
                status = InitStatus.INITIALIZED_NO_INDEX
                recommendations = self._get_index_recommendations(detection)
            elif not index_fresh:
                status = InitStatus.INITIALIZED_STALE_INDEX
                recommendations = self._get_sync_recommendations(detection)
            else:
                status = InitStatus.FULLY_INITIALIZED
                recommendations = self._get_ready_recommendations(detection)
            
            return InitState(
                status=status,
                cip_dir_exists=cip_dir_exists,
                config_exists=config_exists,
                index_exists=index_exists,
                index_fresh=index_fresh,
                git_hooks_installed=git_hooks_installed,
                agents_md_exists=agents_md_exists,
                detection=detection,
                recommendations=recommendations
            )
            
        except Exception as e:
            # Return error state with actual file status
            return InitState(
                status=InitStatus.ERROR,
                cip_dir_exists=os.path.isdir(self.cip_dir),
                config_exists=os.path.isfile(self.config_file),
                index_exists=os.path.isfile(self.index_file),
                index_fresh=False,
                git_hooks_installed=False,
                agents_md_exists=os.path.isfile(self.agents_file),
                error_message=str(e),
                recommendations=["Check repository permissions", "Verify CIP installation"]
            )
    
    def _check_git_hooks(self) -> bool:
        """Check if git hooks are installed."""
        git_dir = os.path.join(self.root, ".git", "hooks")
        if not os.path.isdir(git_dir):
            return False
        
        # Check for CIP markers in hooks
        hook_files = ["post-commit", "post-merge", "post-checkout"]
        cip_marker = "# >>> cip >>>"
        
        for hook_file in hook_files:
            hook_path = os.path.join(git_dir, hook_file)
            if os.path.exists(hook_path):
                try:
                    with open(hook_path, 'r') as f:
                        content = f.read()
                    if cip_marker in content:
                        return True
                except Exception:
                    pass
        
        return False
    
    def _check_index_freshness(self) -> bool:
        """Check if index is fresh (updated within last hour)."""
        import time
        
        if not os.path.exists(self.index_file):
            return False
        
        try:
            index_mtime = os.path.getmtime(self.index_file)
            current_time = time.time()
            age_hours = (current_time - index_mtime) / 3600
            
            # Consider index fresh if less than 1 hour old
            return age_hours < 1
        except Exception:
            return False
    
    def _detect_repo(self) -> RepoDetection:
        """Detect repository characteristics."""
        repo_type = "generic"
        languages = []
        frameworks = []
        has_git = False
        git_branch = None
        git_uncommitted = 0
        file_count = 0
        
        # Check for git
        git_dir = os.path.join(self.root, ".git")
        has_git = os.path.isdir(git_dir)
        
        if has_git:
            try:
                import subprocess
                # Get current branch
                result = subprocess.run(
                    ['git', 'branch', '--show-current'],
                    cwd=self.root,
                    capture_output=True,
                    text=True
                )
                git_branch = result.stdout.strip() if result.returncode == 0 else None
                
                # Get uncommitted files
                result = subprocess.run(
                    ['git', 'diff', '--name-only'],
                    cwd=self.root,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    git_uncommitted = len([f for f in result.stdout.split('\n') if f.strip()])
            except Exception:
                pass
        
        # Count files
        try:
            file_count = sum(1 for root_dir, dirs, files in os.walk(self.root) for file in files if os.path.isfile(os.path.join(root_dir, file)))
        except Exception:
            file_count = 0
        
        # Detect languages and frameworks
        try:
            languages, frameworks = self._detect_languages_and_frameworks()
        except Exception:
            languages, frameworks = [], []
        
        # Determine repo type
        if "nextjs" in frameworks or "react" in frameworks:
            repo_type = "nextjs-app"
        elif "python" in languages:
            repo_type = "python-lib"
        elif "typescript" in languages or "javascript" in languages:
            repo_type = "typescript-lib"
        
        return RepoDetection(
            repo_type=repo_type,
            languages=languages,
            frameworks=frameworks,
            has_git=has_git,
            git_branch=git_branch,
            git_uncommitted=git_uncommitted,
            file_count=file_count
        )
    
    def _detect_languages_and_frameworks(self) -> tuple[List[str], List[str]]:
        """Detect programming languages and frameworks."""
        languages = []
        frameworks = []
        
        # Language indicators
        language_files = {
            'python': ['requirements.txt', 'setup.py', 'setup.cfg', 'pyproject.toml', '*.py'],
            'typescript': ['tsconfig.json', '*.ts', '*.tsx'],
            'javascript': ['package.json', '*.js', '*.jsx'],
            'go': ['go.mod', '*.go'],
            'rust': ['Cargo.toml', '*.rs'],
            'java': ['pom.xml', '*.java'],
            'ruby': ['Gemfile', '*.rb']
        }
        
        # Framework indicators
        framework_files = {
            'nextjs': ['next.config.js', 'next.config.mjs'],
            'react': ['package.json'],  # Would check dependencies
            'django': ['settings.py'],
            'flask': ['app.py'],
            'pytest': ['pytest.ini', 'setup.cfg'],
            'jest': ['jest.config.js'],
            'vitest': ['vitest.config.ts']
        }
        
        # Check for language indicators
        for lang, indicators in language_files.items():
            for indicator in indicators:
                if indicator.startswith('*.'):
                    # Check file extensions
                    ext = indicator[2:]
                    if self._has_files_with_extension(ext):
                        languages.append(lang)
                        break
                else:
                    if os.path.exists(os.path.join(self.root, indicator)):
                        languages.append(lang)
                        break
        
        # Check for framework indicators
        for framework, indicators in framework_files:
            for indicator in indicators:
                if os.path.exists(os.path.join(self.root, indicator)):
                    frameworks.append(framework)
                    break
        
        # Check package.json for frameworks
        if os.path.exists(os.path.join(self.root, 'package.json')):
            try:
                import json
                with open(os.path.join(self.root, 'package.json'), 'r') as f:
                    package_data = json.load(f)
                    deps = package_data.get('dependencies', {})
                    dev_deps = package_data.get('devDependencies', {})
                    all_deps = {**deps, **dev_deps}
                    
                    if 'next' in all_deps:
                        frameworks.append('nextjs')
                    if 'react' in all_deps:
                        frameworks.append('react')
                    if 'jest' in all_deps:
                        frameworks.append('jest')
                    if 'vitest' in all_deps:
                        frameworks.append('vitest')
            except Exception:
                pass
        
        return list(set(languages)), list(set(frameworks))
    
    def _has_files_with_extension(self, extension: str) -> bool:
        """Check if repository has files with given extension."""
        try:
            for root_dir, dirs, files in os.walk(self.root):
                # Skip .cip and .git directories
                if '.cip' in root_dir or '.git' in root_dir:
                    continue
                for file in files:
                    if file.endswith(extension):
                        return True
        except Exception:
            pass
        return False
    
    def _get_init_recommendations(self, detection: RepoDetection) -> List[str]:
        """Get recommendations for uninitialized repository."""
        recommendations = [
            "Initialize CIP to enable intelligent code analysis",
            "Scan all files to build code map",
            "Index git history for change tracking",
            "Install git hooks for automatic updates"
        ]
        
        if detection.has_git:
            recommendations.append("Git repository detected - hooks will be installed automatically")
        
        if detection.languages:
            recommendations.append(f"Detected languages: {', '.join(detection.languages)}")
        
        return recommendations
    
    def _get_index_recommendations(self, detection: RepoDetection) -> List[str]:
        """Get recommendations for repository without index."""
        recommendations = [
            "Build code index to enable search and analysis",
            "Index symbols, imports, and relationships",
            "Enable semantic search capabilities"
        ]
        
        if detection.file_count > 1000:
            recommendations.append("Large repository - indexing may take several minutes")
        
        return recommendations
    
    def _get_sync_recommendations(self, detection: RepoDetection) -> List[str]:
        """Get recommendations for repository with stale index."""
        recommendations = [
            "Sync index to include recent changes",
            "Update code map with new files",
            "Refresh git history index"
        ]
        
        if detection.git_uncommitted > 0:
            recommendations.append(f"You have {detection.git_uncommitted} uncommitted files")
        
        return recommendations
    
    def _get_ready_recommendations(self, detection: RepoDetection) -> List[str]:
        """Get recommendations for fully initialized repository."""
        recommendations = [
            "Repository is ready for intelligent operations",
            "Use search to find code patterns",
            "Run workflows for guided operations",
            "Check health score for repository status"
        ]
        
        if detection.git_uncommitted > 0:
            recommendations.append(f"Consider reviewing {detection.git_uncommitted} uncommitted files")
        
        return recommendations


def detect_init_status(root: str) -> InitState:
    """Convenience function to detect initialization status."""
    detector = InitDetector(root)
    return detector.detect()


def get_init_ui_text(state: InitState) -> str:
    """Get UI text for initialization state."""
    if state.status == InitStatus.NOT_INITIALIZED:
        return "Repository Not Initialized"
    elif state.status == InitStatus.INITIALIZED_NO_INDEX:
        return "Repository Ready - Index Needed"
    elif state.status == InitStatus.INITIALIZED_STALE_INDEX:
        return "Repository Ready - Index Stale"
    elif state.status == InitStatus.FULLY_INITIALIZED:
        return "Repository Ready"
    else:
        return "Error Detecting Status"


def should_launch_dashboard(state: InitState) -> bool:
    """Determine if dashboard should be launched."""
    return state.status in [
        InitStatus.FULLY_INITIALIZED,
        InitStatus.INITIALIZED_STALE_INDEX
    ]


def should_show_init_ui(state: InitState) -> bool:
    """Determine if initialization UI should be shown."""
    return state.status == InitStatus.NOT_INITIALIZED


def should_show_index_ui(state: InitState) -> bool:
    """Determine if index building UI should be shown."""
    return state.status == InitStatus.INITIALIZED_NO_INDEX

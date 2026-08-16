"""Token estimation utility for CLI agent context management.

Provides token counting for proactive context budgeting across any agent framework.
Compatible with CIP Code Intelligence Platform and works on Windows PowerShell 7+.
"""

import os
import sys
from typing import Dict, Optional


# Model-specific token limits - adapt to your agent's model
# These are defaults; override via environment or configuration
DEFAULT_TOKEN_LIMIT = int(os.environ.get("TOKEN_LIMIT", "128000"))
EMERGENCY_THRESHOLD = 0.90   # >90% triggers Tier 3
PRECOMPACTION_THRESHOLD = 0.80  # 80% triggers Tier 2
CAUTION_THRESHOLD = 0.60       # 60% triggers Tier 1


class TokenEstimator:
    """Estimates token count for conversation context management."""
    
    def __init__(self, limit: int = DEFAULT_TOKEN_LIMIT, encoding_name: str = "gpt-4o"):
        """Initialize token estimator.
        
        Args:
            limit: Hard token limit for the model/context window
            encoding_name: Tiktoken encoding name for accurate counting
        """
        self.limit = limit
        self.encoding_name = encoding_name
        self._cache: Dict[str, int] = {}
        
        # Try to import tiktoken for accurate counting
        try:
            import tiktoken
            self.encoding = tiktoken.encoding_for_model(encoding_name)
            self.use_tiktoken = True
        except ImportError:
            self.use_tiktoken = False
            self._warn_tiktoken_missing()
        except KeyError:
            # Model not found in tiktoken, use fallback
            self.use_tiktoken = False
            self._warn_tiktoken_fallback()
    
    def _warn_tiktoken_missing(self):
        """Warn that tiktoken is not available."""
        pass  # Silent fallback
    
    def _warn_tiktoken_fallback(self):
        """Wik that tiktoken couldn't find the specified encoding."""
        pass  # Silent fallback
    
    def estimate(self, text: str) -> int:
        """Estimate token count for the given text.
        
        Args:
            text: Input text to estimate tokens for
            
        Returns:
            Estimated token count (integer)
        """
        if not text:
            return 0
        
        if self.use_tiktoken:
            try:
                return len(self.encoding.encode(text))
            except Exception:
                # Fall back to character estimate if tiktoken fails
                pass
        
        # Fallback: character-based estimate (rough: 1 char ≈ 0.25-0.33 tokens)
        # This approximates gpt-4o encoding behavior
        return max(1, len(text) // 4)
    
    def estimate_history(self, conversation_history: str) -> Dict[str, int]:
        """Estimate tokens used in conversation history.
        
        Args:
            conversation_history: Full conversation text
            
        Returns:
            Dictionary with token metrics
        """
        tokens = self.estimate(conversation_history)
        return {
            "tokens": tokens,
            "remaining": self.limit - tokens,
            "percent": round((tokens / self.limit) * 100, 1) if self.limit > 0 else 0,
            "limit": self.limit
        }
    
    def get_tier(self, conversation_history: str) -> str:
        """Determine current compaction tier.
        
        Args:
            conversation_history: Full conversation text
            
        Returns:
            Tier string: "TIER_0", "TIER_1", "TIER_2", or "TIER_3"
        """
        metrics = self.estimate_history(conversation_history)
        pct = metrics["percent"]
        
        if pct >= EMERGENCY_THRESHOLD * 100:
            return "TIER_3"
        elif pct >= PRECOMPACTION_THRESHOLD * 100:
            return "TIER_2"
        elif pct >= CAUTION_THRESHOLD * 100:
            return "TIER_1"
        else:
            return "TIER_0"
    
    def get_status(self, conversation_history: str) -> Dict[str, object]:
        """Get comprehensive status for the current conversation.
        
        Args:
            conversation_history: Full conversation text
            
        Returns:
            Dictionary with all status metrics including tier
        """
        metrics = self.estimate_history(conversation_history)
        tier = self.get_tier(conversation_history)
        
        return {
            **metrics,
            "tier": tier,
            "in_safe_zone": tier == "TIER_0",
            "in_caution_zone": tier == "TIER_1",
            "in_precompaction": tier == "TIER_2",
            "in_emergency": tier == "TIER_3"
        }
    
    def remaining_tokens(self, conversation_history: str) -> int:
        """Get remaining tokens before hard limit.
        
        Args:
            conversation_history: Full conversation text
            
        Returns:
            Number of tokens remaining
        """
        metrics = self.estimate_history(conversation_history)
        return max(0, metrics["remaining"])


# Global instance for agent use
_estimator: Optional[TokenEstimator] = None


def get_estimator() -> TokenEstimator:
    """Get or create the global token estimator instance.
    
    Returns:
        TokenEstimator instance
    """
    global _estimator
    if _estimator is None:
        _estimator = TokenEstimator()
    return _estimator


def estimate_tokens(text: str) -> int:
    """Quick function to estimate token count.
    
    Args:
        text: Input text to estimate
        
    Returns:
        Estimated token count
    """
    return get_estimator().estimate(text)


def estimate_history(conversation_history: str) -> Dict[str, int]:
    """Quick function to estimate conversation history tokens.
    
    Args:
        conversation_history: Full conversation text
        
    Returns:
        Dictionary with token metrics
    """
    return get_estimator().estimate_history(conversation_history)


def get_tier(conversation_history: str) -> str:
    """Quick function to determine current compaction tier.
    
    Args:
        conversation_history: Full conversation text
        
    Returns:
        Tier string: "TIER_0", "TIER_1", "TIER_2", or "TIER_3"
    """
    return get_estimator().get_tier(conversation_history)


def get_status(conversation_history: str) -> Dict[str, object]:
    """Quick function to get comprehensive conversation status.
    
    Args:
        conversation_history: Full conversation text
        
    Returns:
        Dictionary with all status metrics including tier
    """
    return get_estimator().get_status(conversation_history)


def remaining_tokens(conversation_history: str) -> int:
    """Quick function to get remaining tokens before hard limit.
    
    Args:
        conversation_history: Full conversation text
        
    Returns:
        Number of tokens remaining
    """
    return get_estimator().remaining_tokens(conversation_history)


# PowerShell-compatible path utilities
def data_dir(root: str) -> str:
    """Get CIP data directory path (PowerShell-compatible).
    
    Args:
        root: Repository root directory
        
    Returns:
        Path to .cip/data directory
    """
    return os.path.join(root, ".cip", "data")


def compaction_summary_path(root: str, filename: str = "compaction_summary.md") -> str:
    """Get path for compaction summary file.
    
    Args:
        root: Repository root directory
        filename: Summary file name
        
    Returns:
        Full path to compaction summary file
    """
    return os.path.join(data_dir(root), filename)


def emergency_save_path(root: str, filename: str = "emergency_save.md") -> str:
    """Get path for emergency save file.
    
    Args:
        root: Repository root directory
        filename: Save file name
        
    Returns:
        Full path to emergency save file
    """
    return os.path.join(data_dir(root), filename)
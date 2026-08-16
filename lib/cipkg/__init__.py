"""CIP — Code Intelligence Protocol: drop-in repository intelligence for AI agents."""
__version__ = "1.0.0"

# Expose key classes and enums for easy import
from cipkg.command_registry import CommandCategory, CommandPriority, CommandCard, CommandRegistry

__all__ = ["CommandCategory", "CommandPriority", "CommandCard", "CommandRegistry"]

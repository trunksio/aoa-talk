"""
Agents Common Package
----------------------
Shared utilities for Agentic Units (AUs).

This package provides:
- Lifecycle management for agents
- Manifest and registration utilities
"""

from .manifest import AgentManifest, Capability, Agent, Embedding
from .register_on_start import register_agent_from_manifest

# Re-export all shared utilities from cavia_common
# This allows agents to import everything from agents_common
# Note: cavia_common is installed via pip, no sys.path manipulation needed


__version__ = "1.0.0"

__all__ = [
    # Manifest and registration
    "AgentManifest",
    "Capability",
    "Agent",
    "Embedding",
    "register_agent_from_manifest",
    # Lifecycle management
    "AgentContext",
    "register_agent",
    "start_heartbeat",
    "stop_heartbeat",
    "setup_signal_handlers",
    "start_worker",
    "validate_intent",
    "check_intent_drift",
    "update_intent_context",
    "discover_next_agent",
    "enqueue_to_next_agent",
    "register_agent_context",
    "process_agent_task",
]

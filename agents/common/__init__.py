"""
Agents Common Package
----------------------
Shared utilities and models for Agentic Units (AUs).
"""

from .manifest import AgentManifest, Capability, Agent, Embedding
from .register_on_start import register_agent_from_manifest

__version__ = "1.0.0"

__all__ = [
    "AgentManifest",
    "Capability",
    "Agent",
    "Embedding",
    "register_agent_from_manifest",
]

"""
Agents Common Package
----------------------
Shared utilities for Agentic Units (AUs).

This package provides:
- Lifecycle management for agents
- Manifest and registration utilities
- Re-exported models and clients from cavia_common for agent convenience
"""

# Import lifecycle management from local module
from .lifecycle import (
    AgentContext,
    register_agent,
    start_heartbeat,
    stop_heartbeat,
    setup_signal_handlers,
    start_worker,
    validate_intent,
    check_intent_drift,
    update_intent_context,
    discover_next_agent,
    enqueue_to_next_agent,
    register_agent_context,
    process_agent_task,
)

# Manifest and registration utilities
from .manifest import AgentManifest, Capability, Agent, Embedding
from .register_on_start import register_agent_from_manifest

# Re-export commonly used models and clients from cavia_common for agent convenience
from cavia_common import (
    # Configuration and logging
    get_settings,
    setup_logging,
    get_logger,
    # Models
    AgentTask,
    AgentTaskV2,
    AgentTaskResult,
    AgentStatus,
    ParsedCV,
    EvaluationResult,
    StructuredEvaluation,
    CVEvaluationReport,
    IntentValidation,
    # Clients
    get_db_manager,
    get_redis_connection,
    get_minio_client,
    get_ollama_client,
)

__version__ = "1.0.0"

__all__ = [
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
    # Manifest and registration
    "AgentManifest",
    "Capability",
    "Agent",
    "Embedding",
    "register_agent_from_manifest",
    # Re-exported from cavia_common (for convenience)
    "get_settings",
    "setup_logging",
    "get_logger",
    "AgentTask",
    "AgentTaskV2",
    "AgentTaskResult",
    "AgentStatus",
    "ParsedCV",
    "EvaluationResult",
    "StructuredEvaluation",
    "CVEvaluationReport",
    "IntentValidation",
    "get_db_manager",
    "get_redis_connection",
    "get_minio_client",
    "get_ollama_client",
]

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

# Re-export all shared utilities from cavia_common
# This allows agents to import everything from agents_common
from cavia_common import (
    Settings,
    get_settings,
    setup_logging,
    get_logger,
    AgentRegistration,
    AgentStatus,
    JobStatus,
    CVJob,
    EvaluationResult,
    ParsedCV,
    EvaluationCriterion,
    CVEvaluationReport,
    AgentTask,
    AgentTaskV2,
    AgentTaskResult,
    IntentConstraint,
    IntentSuccessCriteria,
    StructuredIntent,
    IntentValidation,
    ReasoningStep,
    SubCriterion,
    StructuredEvaluation,
    DatabaseManager,
    get_db_manager,
    get_redis_connection,
    MinIOClient,
    get_minio_client,
    OllamaClient,
    get_ollama_client,
    BaseAgent,
    WorkflowTemplate,
    get_workflow_template,
    list_workflow_templates,
    get_workflows_by_category,
    WORKFLOW_TEMPLATES,
)

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
    # Re-exported from cavia_common
    "Settings",
    "get_settings",
    "setup_logging",
    "get_logger",
    "AgentRegistration",
    "AgentStatus",
    "JobStatus",
    "CVJob",
    "EvaluationResult",
    "ParsedCV",
    "EvaluationCriterion",
    "CVEvaluationReport",
    "AgentTask",
    "AgentTaskV2",
    "AgentTaskResult",
    "IntentConstraint",
    "IntentSuccessCriteria",
    "StructuredIntent",
    "IntentValidation",
    "ReasoningStep",
    "SubCriterion",
    "StructuredEvaluation",
    "DatabaseManager",
    "get_db_manager",
    "get_redis_connection",
    "MinIOClient",
    "get_minio_client",
    "OllamaClient",
    "get_ollama_client",
    "BaseAgent",
    "WorkflowTemplate",
    "get_workflow_template",
    "list_workflow_templates",
    "get_workflows_by_category",
    "WORKFLOW_TEMPLATES",
]

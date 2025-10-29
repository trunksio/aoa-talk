"""
Agents Common Package
----------------------
Shared utilities and models for Agentic Units (AUs).

This package consolidates all common utilities needed by agents,
including base classes, models, clients, and manifest management.
"""

# Manifest and registration utilities (agents_common specific)
from .manifest import AgentManifest, Capability, Agent, Embedding
from .register_on_start import register_agent_from_manifest

# Re-export all shared utilities from cavia_common
# This allows agents to import everything from agents_common
import sys
sys.path.insert(0, "/shared")

from cavia_common import (
    # Configuration
    Settings,
    get_settings,
    # Logging
    setup_logging,
    get_logger,
    # Agent models
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
    # Intent models
    IntentConstraint,
    IntentSuccessCriteria,
    StructuredIntent,
    IntentValidation,
    # Evaluation models
    ReasoningStep,
    SubCriterion,
    StructuredEvaluation,
    # Clients
    DatabaseManager,
    get_db_manager,
    get_redis_connection,
    MinIOClient,
    get_minio_client,
    OllamaClient,
    get_ollama_client,
    # Base agent (DEPRECATED)
    BaseAgent,
    # Workflows
    WorkflowTemplate,
    get_workflow_template,
    list_workflow_templates,
    get_workflows_by_category,
    WORKFLOW_TEMPLATES,
)

# Import explicit lifecycle management (NEW PATTERN)
from cavia_common.agent_lifecycle import (
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

__version__ = "1.0.0"

__all__ = [
    # Manifest and registration (agents_common specific)
    "AgentManifest",
    "Capability",
    "Agent",
    "Embedding",
    "register_agent_from_manifest",
    # Configuration
    "Settings",
    "get_settings",
    # Logging
    "setup_logging",
    "get_logger",
    # Agent models
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
    # Intent models
    "IntentConstraint",
    "IntentSuccessCriteria",
    "StructuredIntent",
    "IntentValidation",
    # Evaluation models
    "ReasoningStep",
    "SubCriterion",
    "StructuredEvaluation",
    # Clients
    "DatabaseManager",
    "get_db_manager",
    "get_redis_connection",
    "MinIOClient",
    "get_minio_client",
    "OllamaClient",
    "get_ollama_client",
    # Base agent (DEPRECATED - use explicit lifecycle instead)
    "BaseAgent",
    # Explicit lifecycle management (NEW PATTERN)
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
    # Workflows
    "WorkflowTemplate",
    "get_workflow_template",
    "list_workflow_templates",
    "get_workflows_by_category",
    "WORKFLOW_TEMPLATES",
]

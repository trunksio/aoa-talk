"""
Agents Common Package
----------------------
Shared utilities and models for Agentic Units (AUs).

This package consolidates all common utilities needed by agents,
including lifecycle management, models, and clients.
"""

import sys

# Add shared path for cavia_common dependencies
sys.path.insert(0, "/shared")

# Import from cavia_common (shared models and clients only)
from cavia_common import (
    # Configuration
    Settings,
    get_settings,
    # Logging
    setup_logging,
    get_logger,
    # Models
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
    # Clients
    DatabaseManager,
    get_db_manager,
    get_redis_connection,
    MinIOClient,
    get_minio_client,
    OllamaClient,
    get_ollama_client,
    # Workflows
    WorkflowTemplate,
    get_workflow_template,
    list_workflow_templates,
    get_workflows_by_category,
    WORKFLOW_TEMPLATES,
)

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

# Manifest and registration utilities (agents_common specific)
from .manifest import AgentManifest, Capability, Agent, Embedding
from .register_on_start import register_agent_from_manifest

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
    # Lifecycle management (NEW PATTERN)
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

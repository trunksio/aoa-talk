"""
CAVIA Common - Shared utilities for Agent Oriented Architecture
"""

from .config import Settings, get_settings
from .logging import setup_logging, get_logger
from .models import (
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
    # Intent management models
    IntentConstraint,
    IntentSuccessCriteria,
    StructuredIntent,
    IntentValidation,
    # Structured evaluation models for Instructor
    ReasoningStep,
    SubCriterion,
    StructuredEvaluation,
)
from .database import DatabaseManager, get_db_manager
from .redis_client import get_redis_connection
from .minio_client import MinIOClient, get_minio_client
from .ollama_client import OllamaClient, get_ollama_client
from .base_agent import BaseAgent
from .workflows import (
    WorkflowTemplate,
    get_workflow_template,
    list_workflow_templates,
    get_workflows_by_category,
    WORKFLOW_TEMPLATES,
)

__version__ = "0.2.0"

__all__ = [
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
    # Base agent
    "BaseAgent",
    # Workflows
    "WorkflowTemplate",
    "get_workflow_template",
    "list_workflow_templates",
    "get_workflows_by_category",
    "WORKFLOW_TEMPLATES",
]

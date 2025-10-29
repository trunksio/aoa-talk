"""
Agent Lifecycle Management - Explicit helper functions for agent startup and operation.

This module provides explicit functions for agent lifecycle management without
requiring inheritance from a base class. Each agent can call these functions
directly to manage its lifecycle.
"""

import os
import sys
import time
import signal
from typing import Any, Dict, Optional, Callable
from threading import Thread
from datetime import datetime, UTC

from rq import Queue, Worker

# Import from cavia_common (installed via pip)
from cavia_common import (
    get_settings,
    get_logger,
    setup_logging,
    AgentStatus,
    AgentTask,
    AgentTaskV2,
    AgentTaskResult,
    IntentValidation,
    get_db_manager,
    get_redis_connection,
)


class AgentContext:
    """
    Context object that holds agent state and clients.

    This replaces the BaseAgent's instance variables with an explicit context
    that agents manage themselves.
    """

    def __init__(
        self,
        agent_id: str,
        agent_type: str,
        agent_info_provider: Callable[[], Dict[str, Any]],
        task_processor: Callable[[Any], AgentTaskResult],
    ):
        """
        Initialize agent context.

        Args:
            agent_id: Unique agent identifier
            agent_type: Agent type (e.g., 'parser', 'evaluator')
            agent_info_provider: Function that returns agent metadata
            task_processor: Function that processes tasks
        """
        # Setup logging
        setup_logging()
        self.logger = get_logger(f"{agent_type.capitalize()}Agent")

        # Configuration
        self.settings = get_settings()
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.agent_info_provider = agent_info_provider
        self.task_processor = task_processor

        # Clients
        self.db = get_db_manager()
        self.redis_conn = get_redis_connection()

        # State
        self.status = AgentStatus.STARTING
        self.heartbeat_thread: Optional[Thread] = None
        self.running = False

        self.logger.info(
            "Agent context initialized",
            agent_id=self.agent_id,
            agent_type=self.agent_type,
        )

    def get_queue_name(self) -> str:
        """Get the queue name for this agent type"""
        queue_mapping = {
            "parser": self.settings.queue_parsing,
            "evaluator": self.settings.queue_evaluation,
            "orchestrator": self.settings.queue_orchestration,
            "reporter": self.settings.queue_reporting,
            "ocr": getattr(self.settings, "queue_ocr", "queue-ocr"),
        }
        return queue_mapping.get(self.agent_type, f"queue-{self.agent_type}")


def register_agent(ctx: AgentContext) -> bool:
    """
    Register agent with the agent-registry service.

    Args:
        ctx: Agent context

    Returns:
        True if registration successful, False otherwise
    """
    try:
        import requests

        info = ctx.agent_info_provider()

        # Transform capabilities dict into List[Capability] format expected by registry
        # Agent info providers return capabilities as a dict, but registry expects list of Capability objects
        capabilities_dict = info.get("capabilities", {})
        capabilities_list = []

        # Create a single capability entry that encompasses all agent capabilities
        if capabilities_dict:
            capabilities_list.append(
                {
                    "name": f"{ctx.agent_type}_capabilities",
                    "description": info["description"],
                    "input_types": capabilities_dict.get("supported_formats", []),
                    "output_types": capabilities_dict.get(
                        "extraction_features",
                        capabilities_dict.get("evaluation_types", []),
                    ),
                    "parameters": {
                        k: v
                        for k, v in capabilities_dict.items()
                        if k
                        not in [
                            "supported_formats",
                            "extraction_features",
                            "evaluation_types",
                        ]
                    },
                    "metadata": {},
                }
            )

        # Call registry HTTP API using correct payload structure
        registry_url = os.getenv("REGISTRY_URL", "http://registry:8001")
        payload = {
            "agent": {
                "agent_id": ctx.agent_id,
                "name": info["name"],
                "description": info["description"],
                "agent_type": ctx.agent_type,
                "capabilities": capabilities_list,
                "version": "1.0.0",
                "status": "active",
                "metadata": {"queue_name": ctx.get_queue_name()},
            }
        }
        response = requests.post(
            f"{registry_url}/register",
            json=payload,
            timeout=30,
        )

        response.raise_for_status()
        success = response.json().get("status") == "success"

        if success:
            ctx.status = AgentStatus.ACTIVE
            ctx.logger.info("Agent registered successfully", agent_id=ctx.agent_id)
        else:
            ctx.logger.error("Agent registration failed", agent_id=ctx.agent_id)

        return success

    except Exception as e:
        ctx.logger.error("Registration error", agent_id=ctx.agent_id, error=str(e))
        ctx.status = AgentStatus.ERROR
        return False


def start_heartbeat(ctx: AgentContext) -> None:
    """
    Start heartbeat thread to signal agent is alive.

    Args:
        ctx: Agent context
    """

    def heartbeat_loop():
        while ctx.running:
            try:
                ctx.db.update_heartbeat(ctx.agent_id)
                ctx.logger.debug("Heartbeat sent", agent_id=ctx.agent_id)
            except Exception as e:
                ctx.logger.error("Heartbeat error", error=str(e))

            time.sleep(ctx.settings.agent_heartbeat_interval)

    ctx.running = True
    ctx.heartbeat_thread = Thread(target=heartbeat_loop, daemon=True)
    ctx.heartbeat_thread.start()
    ctx.logger.info("Heartbeat started", agent_id=ctx.agent_id)


def stop_heartbeat(ctx: AgentContext) -> None:
    """
    Stop heartbeat thread.

    Args:
        ctx: Agent context
    """
    ctx.running = False
    if ctx.heartbeat_thread:
        ctx.heartbeat_thread.join(timeout=5)
    ctx.logger.info("Heartbeat stopped", agent_id=ctx.agent_id)


def setup_signal_handlers(ctx: AgentContext) -> None:
    """
    Setup signal handlers for graceful shutdown.

    Args:
        ctx: Agent context
    """

    def signal_handler(signum, frame):
        ctx.logger.info("Shutdown signal received", signal=signum)
        stop_heartbeat(ctx)
        ctx.status = AgentStatus.STOPPING
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    ctx.logger.info("Signal handlers registered")


def start_worker(ctx: AgentContext) -> None:
    """
    Start RQ worker to process tasks.

    This is the main blocking call that runs the agent worker loop.

    Args:
        ctx: Agent context
    """
    try:
        # Setup signal handlers
        setup_signal_handlers(ctx)

        # Register agent
        if not register_agent(ctx):
            raise Exception("Failed to register agent")

        # Start heartbeat
        start_heartbeat(ctx)

        # Register this agent context for RQ job processing
        register_agent_context(ctx)

        # Start RQ worker
        queue_name = ctx.get_queue_name()
        ctx.logger.info("Starting worker", queue=queue_name, agent_id=ctx.agent_id)

        # Create queue and worker using RQ directly
        queue = Queue(queue_name, connection=ctx.redis_conn)
        worker = Worker([queue], connection=ctx.redis_conn, name=ctx.agent_id)

        # Work loop (blocking)
        worker.work()

    except Exception as e:
        ctx.logger.error("Worker error", error=str(e))
        ctx.status = AgentStatus.ERROR
        raise
    finally:
        stop_heartbeat(ctx)
        ctx.status = AgentStatus.INACTIVE


# Intent validation functions


def validate_intent(ctx: AgentContext, task: AgentTaskV2) -> IntentValidation:
    """
    Validate that the agent's work aligns with the intent.

    Uses keyword-based alignment scoring.

    Args:
        ctx: Agent context
        task: AgentTaskV2 with structured intent

    Returns:
        IntentValidation with alignment and drift scores
    """
    try:
        # Simple heuristic validation (can be enhanced with LLM)
        intent = task.intent
        goal_lower = intent.goal.lower()
        workflow_lower = intent.workflow_type.lower()
        agent_type = ctx.agent_type

        # Calculate alignment score based on keyword matching
        alignment_keywords = {
            "parser": ["parse", "extract", "analyze", "document"],
            "ocr": ["ocr", "scan", "image", "picture", "photo"],
            "evaluator": ["evaluate", "assess", "score", "judge", "criteria"],
            "reporter": ["report", "summary", "decision", "output"],
            "expense_evaluator": [
                "expense",
                "receipt",
                "invoice",
                "reimburse",
                "policy",
            ],
        }

        relevant_keywords = alignment_keywords.get(agent_type, [])
        keyword_matches = sum(
            1 for kw in relevant_keywords if kw in goal_lower or kw in workflow_lower
        )
        alignment_score = min(1.0, keyword_matches / max(len(relevant_keywords), 1))

        # Drift score = 1 - alignment (higher drift = lower alignment)
        drift_score = 1.0 - alignment_score

        # Check if previous agents have high drift
        avg_previous_drift = 0.0
        if task.intent_validations:
            avg_previous_drift = sum(
                v.drift_score for v in task.intent_validations
            ) / len(task.intent_validations)

        # Cumulative drift
        cumulative_drift = (avg_previous_drift + drift_score) / 2

        is_aligned = alignment_score >= 0.5

        reasoning = (
            f"Agent '{agent_type}' processing '{intent.workflow_type}' workflow. "
        )
        reasoning += f"Keyword alignment: {alignment_score:.2f}. "
        if not is_aligned:
            reasoning += "WARNING: Low alignment detected. Agent may not be suited for this intent."

        suggestions = []
        if drift_score > 0.5:
            suggestions.append(
                f"Consider routing to agent better suited for '{intent.goal}'"
            )
        if cumulative_drift > 0.4:
            suggestions.append(
                "Significant cumulative drift detected across agent chain"
            )

        return IntentValidation(
            agent_id=ctx.agent_id,
            agent_type=agent_type,
            is_aligned=is_aligned,
            alignment_score=alignment_score,
            drift_score=cumulative_drift,
            reasoning=reasoning,
            suggestions=suggestions,
        )

    except Exception as e:
        ctx.logger.error("Intent validation failed", error=str(e))
        # Return default validation if error occurs
        return IntentValidation(
            agent_id=ctx.agent_id,
            agent_type=ctx.agent_type,
            is_aligned=True,  # Default to aligned to not block workflow
            alignment_score=0.5,
            drift_score=0.5,
            reasoning=f"Validation error: {str(e)}",
            suggestions=["Manual review recommended due to validation error"],
        )


def check_intent_drift(task: AgentTaskV2, threshold: float = 0.4) -> bool:
    """
    Check if intent has drifted too far from original goal.

    Args:
        task: AgentTaskV2 with intent validations
        threshold: Drift threshold (0-1), default 0.4

    Returns:
        True if drift exceeds threshold (should stop workflow)
    """
    if not task.intent_validations:
        return False

    # Calculate average drift across all validations
    total_drift = sum(v.drift_score for v in task.intent_validations)
    avg_drift = total_drift / len(task.intent_validations)

    # Check if any individual validation has very high drift
    max_drift = max(v.drift_score for v in task.intent_validations)

    # Drift detected if average exceeds threshold OR any single agent has >0.7 drift
    return avg_drift > threshold or max_drift > 0.7


def update_intent_context(
    task: AgentTaskV2, ctx: AgentContext, updates: Dict[str, Any]
) -> None:
    """
    Update the intent context with information from agent's processing.

    Args:
        task: AgentTaskV2 to update
        ctx: Agent context
        updates: Dictionary of context updates
    """
    task.intent.context.update(updates)
    task.intent.current_stage = f"{ctx.agent_type}_completed"
    task.intent.updated_at = datetime.now(UTC)


# Agent discovery and chaining functions


def discover_next_agent(
    ctx: AgentContext, capability_query: str
) -> Optional[Dict[str, str]]:
    """
    Discover the next agent via HTTP call to agent-registry service.

    Args:
        ctx: Agent context
        capability_query: Natural language description of needed capability

    Returns:
        Dict with 'agent_type' and 'queue_name', or None if not found
    """
    try:
        import requests

        # Call registry's /search endpoint with correct query format
        registry_url = os.getenv("REGISTRY_URL", "http://registry:8001")
        response = requests.post(
            f"{registry_url}/search",
            json={
                "query": capability_query,
                "mode": "semantic",
                "limit": 5,
            },
            timeout=10,
        )

        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])

        if not results:
            ctx.logger.warning(
                "No agent found for capability", capability=capability_query
            )
            return None

        # Filter out the calling agent to prevent self-enqueueing
        current_agent_type = ctx.agent_type
        filtered_agents = [
            res for res in results if res.get("agent_type") != current_agent_type
        ]

        if not filtered_agents:
            ctx.logger.warning(
                "No suitable agent found (all matches were self)",
                capability=capability_query,
                current_agent=current_agent_type,
            )
            return None

        # Get top result
        top = filtered_agents[0]
        agent_type = top.get("agent_type")
        queue_name = (top.get("metadata") or {}).get(
            "queue_name", f"queue-{agent_type}"
        )

        ctx.logger.info(
            "Discovered next agent",
            capability=capability_query,
            agent_type=agent_type,
            queue=queue_name,
            similarity=top.get("similarity_score"),
        )

        return {"agent_type": agent_type, "queue_name": queue_name}

    except Exception as e:
        ctx.logger.error(
            "Failed to discover next agent", capability=capability_query, error=str(e)
        )
        return None


def enqueue_to_next_agent(
    ctx: AgentContext,
    capability_query: str,
    task_type: str,
    payload: Dict[str, Any],
    intent: Any,
    steps_completed: list[str],
    intent_validations: Optional[list] = None,
) -> Optional[str]:
    """
    Discover and enqueue task to the next agent in the chain.

    Args:
        ctx: Agent context
        capability_query: What capability is needed next
        task_type: Type of task for the next agent
        payload: Task payload data
        intent: Original intent being fulfilled (str or StructuredIntent)
        steps_completed: List of agent types that have already processed this
        intent_validations: Optional list of intent validations (for V2 tasks)

    Returns:
        RQ job ID if successful, None otherwise
    """
    try:
        import uuid
        from rq import Queue

        ctx.logger.debug("Starting agent discovery", capability=capability_query)

        # Discover next agent
        next_agent = discover_next_agent(ctx, capability_query)
        if not next_agent:
            raise Exception(f"No agent found for capability: {capability_query}")

        # Update steps_completed with current agent type
        updated_steps = steps_completed + [ctx.agent_type]

        # Create task dict (supports both legacy and V2 formats)
        task_dict = {
            "task_id": str(uuid.uuid4()),
            "task_type": task_type,
            "payload": payload,
            "intent": intent,
            "steps_completed": updated_steps,
        }

        # Add intent_validations for V2 tasks
        if intent_validations is not None:
            task_dict["intent_validations"] = intent_validations

        # Enqueue to discovered agent's queue
        queue = Queue(next_agent["queue_name"], connection=ctx.redis_conn)
        job = queue.enqueue(
            "agents_common.lifecycle.process_agent_task",
            task_dict,
            job_timeout="15m",
            result_ttl=3600,
        )

        ctx.logger.info(
            "Enqueued to next agent",
            next_agent_type=next_agent["agent_type"],
            queue=next_agent["queue_name"],
            job_id=job.id,
        )

        return job.id

    except Exception as e:
        ctx.logger.error("Failed to enqueue to next agent", error=str(e))
        return None


# Global agent context registry for RQ workers
_agent_context: Optional[AgentContext] = None


def register_agent_context(ctx: AgentContext) -> None:
    """
    Register the agent context for this worker process.

    Args:
        ctx: Agent context to register
    """
    global _agent_context
    _agent_context = ctx


def process_agent_task(task_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    RQ job function that processes agent tasks.

    This is the entry point called by RQ workers. It delegates to the
    registered agent context's task processor.

    Supports both AgentTask (legacy) and AgentTaskV2 (with structured intent).

    Args:
        task_dict: Dictionary representation of AgentTask or AgentTaskV2

    Returns:
        Dictionary representation of AgentTaskResult
    """
    if _agent_context is None:
        raise RuntimeError(
            "No agent context registered. "
            "Agent must call register_agent_context() before starting worker."
        )

    # Determine task type and deserialize appropriately
    try:
        # Try AgentTaskV2 first (has 'intent' as dict with 'intent_id')
        if (
            isinstance(task_dict.get("intent"), dict)
            and "intent_id" in task_dict["intent"]
        ):
            task = AgentTaskV2(**task_dict)
        else:
            # Fall back to legacy AgentTask (intent is string)
            task = AgentTask(**task_dict)
    except Exception:
        # If deserialization fails, try legacy format
        task = AgentTask(**task_dict)

    # Process task using the agent context's task processor
    result = _agent_context.task_processor(task)

    # Return result as dict
    return result.dict() if hasattr(result, "dict") else result

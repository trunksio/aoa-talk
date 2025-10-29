"""
Template for Agentic Unit main entry point.

This file demonstrates how to create a custom agent using explicit lifecycle management
without inheriting from BaseAgent. This approach makes the agent lifecycle transparent
and easier to understand.
"""

import os
import sys
import time
from typing import Any, Dict

from agents_common import (
    AgentContext,
    start_worker,
)
from cavia_common import (
    AgentTask,
    AgentTaskResult,
    get_logger,
    setup_logging,
)

# Setup logging
setup_logging()
logger = get_logger(__name__)


class TemplateAgent:
    """
    Template Agentic Unit.

    Customize this class to implement your specific agent logic.

    No longer inherits from BaseAgent - uses explicit lifecycle management.
    """

    def __init__(self, agent_id: str = None):
        """
        Initialize TemplateAgent with explicit setup.

        Args:
            agent_id: Optional agent identifier (auto-generated if not provided)
        """
        # Create agent context with explicit lifecycle management
        self.ctx = AgentContext(
            agent_id=agent_id or f"template-{os.urandom(4).hex()}",
            agent_type="template",  # Change this for your agent
            agent_info_provider=self.get_agent_info,
            task_processor=self.process_task
        )

        # Setup logging from context
        self.logger = self.ctx.logger

        # Add any agent-specific initialization here
        # For example: Initialize clients, models, etc.

        self.logger.info("TemplateAgent initialized with explicit lifecycle", agent_id=self.ctx.agent_id)

    def get_agent_info(self) -> Dict[str, Any]:
        """Return agent metadata for registration"""
        return {
            "name": "Template Agent",  # Change this
            "description": "A template agent for demonstration purposes",  # Change this
            "capabilities": {
                "tasks": ["example_task"],  # List supported task types
                "version": "1.0.0",
            },
        }

    def process_task(self, task: AgentTask) -> AgentTaskResult:
        """
        Process a task and return the result.

        Args:
            task: AgentTask containing task_type and payload

        Returns:
            AgentTaskResult with status and result or error
        """
        start_time = time.time()

        try:
            self.logger.info(
                "Processing task",
                task_id=task.task_id,
                task_type=task.task_type,
            )

            # TODO: Implement your task processing logic here
            if task.task_type == "example_task":
                result = self._process_example_task(task.payload)
            else:
                raise ValueError(f"Unknown task type: {task.task_type}")

            execution_time = time.time() - start_time

            return AgentTaskResult(
                task_id=task.task_id,
                agent_id=self.ctx.agent_id,
                status="success",
                result=result,
                execution_time=execution_time,
            )

        except Exception as e:
            self.logger.error(
                "Task processing failed",
                task_id=task.task_id,
                error=str(e),
            )

            execution_time = time.time() - start_time

            return AgentTaskResult(
                task_id=task.task_id,
                agent_id=self.ctx.agent_id,
                status="error",
                error=str(e),
                execution_time=execution_time,
            )

    def _process_example_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Example task processing method.

        Replace this with your actual task logic.
        """
        # Example: Echo back the payload with some processing
        return {
            "message": "Task processed successfully",
            "input": payload,
            "agent_id": self.ctx.agent_id,
        }


def main():
    """
    Main entry point for the agent.

    Demonstrates explicit startup lifecycle:
    1. Create agent instance
    2. Start worker (registers, starts heartbeat, runs RQ loop)

    This explicit approach makes it clear what happens during agent startup:
    - Agent registration with agent-registry
    - Heartbeat thread startup
    - Signal handler setup
    - RQ worker loop
    """
    # Get agent ID from environment or let it auto-generate
    agent_id = os.getenv("AGENT_ID")

    # Create agent with explicit initialization
    agent = TemplateAgent(agent_id=agent_id)

    logger.info(
        "Starting agent worker with explicit lifecycle",
        agent_id=agent.ctx.agent_id,
        agent_type=agent.ctx.agent_type,
    )

    # Start the worker (explicit lifecycle management)
    # This will:
    # 1. Register agent with agent-registry
    # 2. Start heartbeat thread
    # 3. Setup signal handlers for graceful shutdown
    # 4. Start RQ worker loop (blocking)
    start_worker(agent.ctx)


if __name__ == "__main__":
    main()

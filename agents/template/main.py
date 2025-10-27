"""
Template for Agentic Unit main entry point.

This file demonstrates how to create a custom agent using the BaseAgent class.
"""

import sys
from typing import Any, Dict

# Add shared package to path
sys.path.insert(0, "/shared")

from cavia_common import (
    BaseAgent,
    AgentTask,
    AgentTaskResult,
    get_logger,
    setup_logging,
)

# Setup logging
setup_logging()
logger = get_logger(__name__)


class TemplateAgent(BaseAgent):
    """
    Template Agentic Unit.

    Customize this class to implement your specific agent logic.
    """

    def __init__(self, agent_id: str = None):
        super().__init__(agent_id)
        # Add any agent-specific initialization here
        self.logger.info("TemplateAgent initialized")

    def get_agent_type(self) -> str:
        """Return the agent type identifier"""
        return "template"  # Change this for your agent

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
        import time
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
                agent_id=self.agent_id,
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
                agent_id=self.agent_id,
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
            "agent_id": self.agent_id,
        }


def main():
    """Main entry point for the agent"""
    import os

    # Get agent ID from environment or generate
    agent_id = os.getenv("AGENT_ID")

    # Create and start agent
    agent = TemplateAgent(agent_id=agent_id)

    logger.info(
        "Starting agent worker",
        agent_id=agent.agent_id,
        agent_type=agent.get_agent_type(),
    )

    # Start the RQ worker (blocking call)
    agent.start_worker()


if __name__ == "__main__":
    main()

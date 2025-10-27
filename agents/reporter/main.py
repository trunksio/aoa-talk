"""
Reporter Agent - Generates comprehensive CV evaluation reports
"""

import sys
import time
import json
import re
from typing import Any, Dict, List
from io import BytesIO

# Add shared package to path
sys.path.insert(0, "/shared")

from cavia_common import (
    BaseAgent,
    AgentTask,
    AgentTaskResult,
    CVEvaluationReport,
    get_logger,
    setup_logging,
    get_ollama_client,
    get_db_manager,
    get_minio_client,
)

from report_templates import (
    SYSTEM_PROMPT,
    build_report_prompt,
    format_markdown_report,
)

# Setup logging
setup_logging()
logger = get_logger(__name__)


class ReporterAgent(BaseAgent):
    """
    Agentic Unit for generating CV evaluation reports.

    Responsibilities:
    - Fetch evaluation results from database
    - Generate comprehensive report using LLM
    - Determine SUITABLE/REJECTED recommendation
    - Store report in database and MinIO
    - Format report as Markdown
    """

    def __init__(self, agent_id: str = None):
        super().__init__(agent_id)

        # Initialize clients
        self.ollama = get_ollama_client()
        self.db = get_db_manager()
        self.minio = get_minio_client()

        self.logger.info("ReporterAgent initialized", agent_id=self.agent_id)

    def get_agent_type(self) -> str:
        """Return the agent type"""
        return "reporter"

    def get_agent_info(self) -> Dict[str, Any]:
        """Return agent metadata for registration"""
        return {
            "name": "CV Reporter Agent",
            "description": "Generates comprehensive evaluation reports with LLM-based synthesis",
            "capabilities": {
                "report_formats": ["json", "markdown"],
                "llm_model": self.settings.ollama_model,
                "recommendation_types": ["suitable", "rejected"],
                "version": "1.0.0",
            },
        }

    def process_task(self, task: AgentTask) -> AgentTaskResult:
        """
        Process a report generation task.

        Expected task payload:
        {
            "task_type": "generate_report",
            "payload": {
                "job_id": "uuid",
                "parsed_cv": ParsedCV.dict(),
                "storage_path": "path/to/parsed_cv.json",
                "evaluations": [EvaluationResult.dict(), ...]
            }
        }
        """
        start_time = time.time()

        try:
            # Extract task parameters from payload (event-driven, no DB fetch)
            job_id = task.payload["job_id"]
            parsed_cv = task.payload["parsed_cv"]
            storage_path = task.payload.get("storage_path")
            evaluations = task.payload["evaluations"]

            self.logger.info(
                "Starting report generation",
                task_id=task.task_id,
                job_id=job_id,
                evaluations_count=len(evaluations),
            )

            if not evaluations:
                raise ValueError("No evaluations provided in task payload")

            # Load criteria for report context
            criteria = self._load_active_criteria()

            # Generate report using LLM
            report_data = self._generate_report_with_llm(parsed_cv, evaluations, criteria)

            # Calculate weighted overall score
            overall_score = self._calculate_weighted_score(evaluations, criteria)

            # Generate markdown report
            candidate_name = parsed_cv.get("contact_info", {}).get("name", "Unknown")
            markdown_report = format_markdown_report(
                candidate_name=candidate_name,
                report_data=report_data,
                evaluations=evaluations,
                criteria=criteria,
            )

            # Store markdown in MinIO
            markdown_path = self._store_markdown_report(job_id, markdown_report)

            # Prepare final report data for db-writer
            final_report = {
                "job_id": job_id,
                "overall_score": overall_score,
                "recommendation": report_data["recommendation"],
                "decision_reasoning": report_data["rationale"],
                "summary": report_data["summary"],
                "strengths": report_data.get("strengths", []),
                "concerns": report_data.get("concerns", []),
                "markdown_path": markdown_path,
                "storage_path": markdown_path,
            }

            execution_time = time.time() - start_time

            self.logger.info(
                "Report generation completed successfully",
                task_id=task.task_id,
                job_id=job_id,
                decision=report_data["recommendation"],
                overall_score=overall_score,
                execution_time=execution_time,
            )

            # Enqueue to db-writer for final persistence
            self._enqueue_to_db_writer(job_id, final_report, task)

            return AgentTaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="success",
                result={
                    "job_id": job_id,
                    "overall_score": overall_score,
                    "decision": report_data["recommendation"],
                    "markdown_path": markdown_path,
                },
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = time.time() - start_time

            self.logger.error(
                "Report generation failed",
                task_id=task.task_id,
                job_id=task.payload.get("job_id"),
                error=str(e),
                execution_time=execution_time,
            )

            return AgentTaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="error",
                error=str(e),
                execution_time=execution_time,
            )

    def _load_active_criteria(self) -> List[Dict[str, Any]]:
        """Load all active evaluation criteria from database"""
        try:
            with self.db.get_session() as session:
                from sqlalchemy import text

                query = text("""
                    SELECT criterion_id, name, description, evaluation_prompt, weight
                    FROM evaluation_criteria
                    WHERE is_active = true
                    ORDER BY weight DESC
                """)

                result = session.execute(query)
                criteria = []

                for row in result:
                    criteria.append({
                        "criterion_id": row[0],
                        "name": row[1],
                        "description": row[2],
                        "evaluation_prompt": row[3],
                        "weight": row[4],
                    })

                return criteria

        except Exception as e:
            self.logger.error("Failed to load evaluation criteria", error=str(e))
            raise

    def _calculate_weighted_score(
        self,
        evaluations: List[Dict[str, Any]],
        criteria: List[Dict[str, Any]]
    ) -> float:
        """Calculate weighted overall score from evaluations"""
        # Create criterion_id -> weight mapping
        weights = {c["criterion_id"]: c["weight"] for c in criteria}

        # Calculate weighted score
        total_weighted_score = 0.0
        total_weight = 0.0

        for eval in evaluations:
            criterion_id = eval["criterion_id"]
            score = eval["score"]
            weight = weights.get(criterion_id, 1.0)

            total_weighted_score += score * weight
            total_weight += weight

        # Avoid division by zero
        if total_weight == 0:
            return 0.0

        overall_score = total_weighted_score / total_weight
        return round(overall_score, 2)

    def _generate_report_with_llm(
        self,
        parsed_cv: dict,
        evaluations: List[Dict[str, Any]],
        criteria: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate report using LLM.

        Args:
            parsed_cv: ParsedCV as dict
            evaluations: List of EvaluationResult dicts
            criteria: List of EvaluationCriterion dicts

        Returns:
            Dict with recommendation, overall_score, summary, strengths, concerns, rationale
        """
        self.logger.debug("Calling LLM for report generation")

        try:
            # Build report prompt
            prompt = build_report_prompt(parsed_cv, evaluations, criteria)

            # Call Ollama
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]

            response = self.ollama.chat(
                messages=messages,
                temperature=0.4,  # Slightly higher for more natural language
            )

            if not response:
                raise ValueError("LLM returned empty response")

            # Parse JSON response
            report_data = self._parse_llm_response(response)

            # Validate report
            self._validate_report(report_data)

            return report_data

        except Exception as e:
            self.logger.error("LLM report generation error", error=str(e))
            raise

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """
        Parse JSON response from LLM.

        Handles cases where LLM wraps JSON in markdown code blocks.
        """
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find raw JSON
            json_match = re.search(r'(\{.*\})', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response

        try:
            report_data = json.loads(json_str)
            return report_data
        except json.JSONDecodeError as e:
            self.logger.error("Failed to parse LLM JSON response", response=response[:500])
            raise ValueError(f"Invalid JSON in LLM response: {e}")

    def _validate_report(self, report_data: Dict[str, Any]):
        """Validate report dict has required fields"""
        required_fields = [
            "recommendation",
            "overall_score",
            "summary",
            "strengths",
            "concerns",
            "rationale"
        ]

        for field in required_fields:
            if field not in report_data:
                raise ValueError(f"Missing required field in report: {field}")

        # Validate recommendation
        if report_data["recommendation"] not in ["SUITABLE", "REJECTED"]:
            raise ValueError(f"Invalid recommendation: {report_data['recommendation']}")

        # Validate overall_score
        score = report_data["overall_score"]
        if not isinstance(score, (int, float)) or not (0 <= score <= 100):
            raise ValueError(f"Overall score must be between 0-100, got: {score}")

    def _enqueue_to_db_writer(
        self,
        job_id: str,
        final_report: Dict[str, Any],
        task: AgentTask
    ):
        """Enqueue to db-writer worker for final database persistence"""
        try:
            import uuid
            from rq import Queue

            # Create db-writer queue
            db_queue = Queue("db-writer", connection=self.redis_conn)

            # Create update_job_result task
            task_dict = {
                "task_id": str(uuid.uuid4()),
                "task_type": "update_job_result",
                "payload": {
                    "job_id": job_id,
                    "status": "completed",
                    "result": final_report,
                },
                "intent": task.intent,
                "steps_completed": task.steps_completed + [self.get_agent_type()],
            }

            # Enqueue to db-writer (non-agentic worker)
            job = db_queue.enqueue(
                "main.process_db_task",
                task_dict,
                job_timeout='5m',
                result_ttl=3600,
            )

            self.logger.info("Enqueued to db-writer", job_id=job_id, rq_job_id=job.id)

        except Exception as e:
            self.logger.error("Failed to enqueue to db-writer", job_id=job_id, error=str(e))
            # Don't raise - report generation was successful

    def _store_markdown_report(self, job_id: str, markdown: str) -> str:
        """Store markdown report in MinIO"""
        try:
            storage_path = f"reports/{job_id}/report.md"

            # Upload to MinIO
            self.minio.upload_file(
                bucket_name="cvs-processed",
                object_name=storage_path,
                file_data=BytesIO(markdown.encode('utf-8')),
                content_type="text/markdown",
            )

            self.logger.debug("Markdown report stored in MinIO", storage_path=storage_path)
            return storage_path

        except Exception as e:
            self.logger.error("Failed to store markdown report in MinIO", error=str(e))
            raise


def main():
    """Main entry point for the Reporter Agent"""
    import os

    # Get agent ID from environment
    agent_id = os.getenv("AGENT_ID", "reporter-001")

    # Create and start agent
    agent = ReporterAgent(agent_id=agent_id)

    logger.info(
        "Starting Reporter Agent worker",
        agent_id=agent.agent_id,
        agent_type=agent.get_agent_type(),
    )

    # Start the RQ worker (blocking call)
    agent.start_worker()


if __name__ == "__main__":
    main()

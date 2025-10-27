"""
Evaluator Agent - LLM-based CV evaluation with Chain-of-Thought reasoning
"""

import sys
import time
import json
from typing import Any, Dict

# Add shared package to path
sys.path.insert(0, "/shared")

import instructor
from openai import OpenAI

from cavia_common import (
    BaseAgent,
    AgentTask,
    AgentTaskResult,
    EvaluationResult,
    StructuredEvaluation,  # New Instructor-compatible model
    get_logger,
    setup_logging,
    get_ollama_client,
    get_db_manager,
)

from prompts import SYSTEM_PROMPT, build_evaluation_prompt

# Setup logging
setup_logging()
logger = get_logger(__name__)


class EvaluatorAgent(BaseAgent):
    """
    Agentic Unit for evaluating CVs using LLM.

    Responsibilities:
    - Receive ParsedCV and EvaluationCriterion
    - Build evaluation prompt
    - Call Ollama LLM for evaluation
    - Parse and validate response
    - Store EvaluationResult in database
    """

    def __init__(self, agent_id: str = None):
        super().__init__(agent_id)

        # Initialize Ollama client
        self.ollama = get_ollama_client()
        self.db = get_db_manager()

        # Initialize Instructor client for structured outputs
        # Ollama provides an OpenAI-compatible API endpoint
        openai_client = OpenAI(
            base_url=f"{self.settings.ollama_host}/v1",
            api_key="ollama"  # Ollama doesn't require a real API key
        )
        self.instructor_client = instructor.from_openai(openai_client)

        self.logger.info(
            "EvaluatorAgent initialized with Instructor",
            agent_id=self.agent_id,
            ollama_model=self.settings.ollama_model
        )

    def get_agent_type(self) -> str:
        """Return the agent type"""
        return "evaluator"

    def get_agent_info(self) -> Dict[str, Any]:
        """Return agent metadata for registration"""
        return {
            "name": "CV Evaluator Agent",
            "description": "LLM-based evaluation of CVs against configurable criteria",
            "capabilities": {
                "evaluation_types": ["criterion-based"],
                "llm_model": self.settings.ollama_model,
                "scoring_range": "0-100",
                "output_format": "structured_json",
                "version": "1.0.0",
            },
        }

    def process_task(self, task: AgentTask) -> AgentTaskResult:
        """
        Process a CV evaluation task.

        Expected task payload:
        {
            "task_type": "evaluate_cv",
            "payload": {
                "job_id": "uuid",
                "parsed_cv": ParsedCV.dict(),
                "storage_path": "path/to/parsed_cv.json"
            }
        }

        Evaluates CV against ALL active criteria, then enqueues to reporter.
        """
        start_time = time.time()

        try:
            # Extract task parameters
            job_id = task.payload["job_id"]
            parsed_cv = task.payload["parsed_cv"]
            storage_path = task.payload.get("storage_path")

            self.logger.info(
                "Starting CV evaluation for all criteria",
                task_id=task.task_id,
                job_id=job_id,
            )

            # Load all active criteria from database
            criteria = self._load_active_criteria()

            if not criteria:
                raise ValueError("No active evaluation criteria found in database")

            self.logger.info(
                "Loaded evaluation criteria",
                count=len(criteria),
                criteria_names=[c["name"] for c in criteria]
            )

            # Evaluate against each criterion
            evaluation_results = []
            for criterion in criteria:
                self.logger.info(
                    "Evaluating criterion",
                    job_id=job_id,
                    criterion=criterion["name"]
                )

                # Build evaluation prompt with CoT instructions
                prompt = build_evaluation_prompt(parsed_cv, criterion)

                # Call LLM for structured evaluation with Chain-of-Thought
                structured_eval = self._evaluate_with_llm(prompt, criterion["name"])

                # Convert StructuredEvaluation to legacy EvaluationResult format
                # Combine sub-criteria evidence into single evidence string
                evidence_parts = [
                    f"{sub.name}: {sub.evidence}"
                    for sub in structured_eval.sub_criteria
                ]
                combined_evidence = "\n".join(evidence_parts)

                # Combine reasoning steps and summary
                reasoning_parts = [
                    f"Step {step.step_number}: {step.observation} - {step.analysis}"
                    for step in structured_eval.reasoning_steps
                ]
                reasoning_parts.append(f"\nSummary: {structured_eval.summary}")
                combined_reasoning = "\n".join(reasoning_parts)

                # Create EvaluationResult for database storage
                eval_result = EvaluationResult(
                    criterion_id=criterion["criterion_id"],
                    agent_id=self.agent_id,
                    score=float(structured_eval.overall_score),
                    confidence=structured_eval.confidence,
                    evidence=combined_evidence,
                    reasoning=combined_reasoning,
                    metadata={
                        "structured_evaluation": structured_eval.model_dump(),
                        "sub_criteria_scores": [
                            {"name": sub.name, "score": sub.score}
                            for sub in structured_eval.sub_criteria
                        ],
                        "key_strengths": structured_eval.key_strengths,
                        "key_weaknesses": structured_eval.key_weaknesses,
                    }
                )

                # Store in database
                self._store_evaluation(job_id, eval_result)

                evaluation_results.append(eval_result)

                self.logger.info(
                    "Criterion evaluation completed with CoT",
                    criterion=criterion["name"],
                    score=eval_result.score,
                    confidence=eval_result.confidence,
                    reasoning_steps=len(structured_eval.reasoning_steps),
                    sub_criteria_count=len(structured_eval.sub_criteria)
                )

            execution_time = time.time() - start_time

            self.logger.info(
                "All CV evaluations completed successfully",
                task_id=task.task_id,
                job_id=job_id,
                criteria_count=len(evaluation_results),
                execution_time=execution_time,
            )

            # Enqueue to reporter using semantic discovery
            self._enqueue_to_reporter(job_id, parsed_cv, storage_path, evaluation_results, task)

            return AgentTaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="success",
                result={
                    "job_id": job_id,
                    "evaluations_completed": len(evaluation_results),
                    "evaluation_results": [e.model_dump() for e in evaluation_results],
                },
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = time.time() - start_time

            self.logger.error(
                "CV evaluation failed",
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

    def _evaluate_with_llm(self, prompt: str, criterion_name: str) -> StructuredEvaluation:
        """
        Call Ollama LLM to evaluate CV with Chain-of-Thought reasoning.

        Uses Instructor library for automatic structured output extraction
        and Pydantic validation.

        Args:
            prompt: Evaluation prompt with CoT instructions
            criterion_name: Name of criterion (for logging)

        Returns:
            StructuredEvaluation with reasoning steps, sub-criteria, and final scores
        """
        self.logger.debug("Calling LLM for evaluation with Instructor", criterion=criterion_name)

        try:
            # Call Instructor-patched Ollama with StructuredEvaluation response model
            evaluation: StructuredEvaluation = self.instructor_client.chat.completions.create(
                model=self.settings.ollama_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                response_model=StructuredEvaluation,
                temperature=0.3,  # Low temperature for consistency
                max_retries=3,  # Instructor will retry on validation failures
            )

            self.logger.debug(
                "Structured evaluation received",
                criterion=criterion_name,
                reasoning_steps=len(evaluation.reasoning_steps),
                sub_criteria=len(evaluation.sub_criteria),
                overall_score=evaluation.overall_score,
                confidence=evaluation.confidence
            )

            return evaluation

        except Exception as e:
            self.logger.error(
                "LLM evaluation error",
                criterion=criterion_name,
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    def _load_active_criteria(self) -> list[Dict[str, Any]]:
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

    def _store_evaluation(self, job_id: str, evaluation: EvaluationResult):
        """Store EvaluationResult in database"""
        try:
            with self.db.get_session() as session:
                from sqlalchemy import text

                query = text("""
                    INSERT INTO cv_evaluations (
                        job_id,
                        criterion_id,
                        agent_id,
                        score,
                        confidence,
                        evidence,
                        reasoning,
                        metadata
                    ) VALUES (
                        :job_id,
                        :criterion_id,
                        :agent_id,
                        :score,
                        :confidence,
                        :evidence,
                        :reasoning,
                        CAST(:metadata AS jsonb)
                    )
                """)

                session.execute(
                    query,
                    {
                        "job_id": job_id,
                        "criterion_id": evaluation.criterion_id,
                        "agent_id": evaluation.agent_id,
                        "score": evaluation.score,
                        "confidence": evaluation.confidence,
                        "evidence": evaluation.evidence,
                        "reasoning": evaluation.reasoning,
                        "metadata": json.dumps(evaluation.metadata),
                    }
                )
                session.commit()

            self.logger.debug("Evaluation stored in database", job_id=job_id)

        except Exception as e:
            self.logger.error("Failed to store evaluation in database", error=str(e))
            raise

    def _enqueue_to_reporter(
        self,
        job_id: str,
        parsed_cv: dict,
        storage_path: str,
        evaluation_results: list,
        task: AgentTask
    ):
        """Discover and enqueue to reporter agent using semantic discovery"""
        try:
            # Convert evaluation results to dicts
            evaluations_data = [e.model_dump() for e in evaluation_results]

            # Use semantic discovery to find reporter agent
            job_id_result = self.enqueue_to_next_agent(
                capability_query="generate comprehensive CV evaluation report with acceptance decision",
                task_type="generate_report",
                payload={
                    "job_id": job_id,
                    "parsed_cv": parsed_cv,
                    "storage_path": storage_path,
                    "evaluations": evaluations_data,
                },
                intent=task.intent or "Process CV and determine acceptance",
                steps_completed=task.steps_completed
            )

            if job_id_result:
                self.logger.info("Enqueued to reporter via semantic discovery", job_id=job_id, rq_job_id=job_id_result)
            else:
                self.logger.warning("Failed to enqueue to reporter", job_id=job_id)

        except Exception as e:
            self.logger.error("Failed to enqueue to reporter", job_id=job_id, error=str(e))
            # Don't raise - evaluation was successful even if enqueueing failed


def main():
    """Main entry point for the Evaluator Agent"""
    import os

    # Get agent ID from environment
    agent_id = os.getenv("AGENT_ID", "evaluator-001")

    # Create and start agent
    agent = EvaluatorAgent(agent_id=agent_id)

    logger.info(
        "Starting Evaluator Agent worker",
        agent_id=agent.agent_id,
        agent_type=agent.get_agent_type(),
    )

    # Start the RQ worker (blocking call)
    agent.start_worker()


if __name__ == "__main__":
    main()

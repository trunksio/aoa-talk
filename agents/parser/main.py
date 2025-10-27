"""
Parser Agent - Extracts structured data from CV files (PDF/DOCX)
"""

import sys
import os
import time
import tempfile
from typing import Any, Dict
from pathlib import Path

# Add shared package to path
sys.path.insert(0, "/shared")

from cavia_common import (
    BaseAgent,
    AgentTask,
    AgentTaskV2,
    AgentTaskResult,
    ParsedCV,
    get_logger,
    setup_logging,
    get_minio_client,
    get_db_manager,
)

from parsers import PDFParser, DOCXParser, LLMCVExtractor

# Setup logging
setup_logging()
logger = get_logger(__name__)


class ParserAgent(BaseAgent):
    """
    Agentic Unit for parsing CV files.

    Responsibilities:
    - Download CV from MinIO
    - Detect file format (PDF/DOCX)
    - Extract text content
    - Extract structured data using LLM (contact, education, experience, skills, etc.)
    - Store ParsedCV in database and MinIO
    """

    def __init__(self, agent_id: str = None):
        super().__init__(agent_id)

        # Initialize parsers
        self.pdf_parser = PDFParser()
        self.docx_parser = DOCXParser()

        # Initialize LLM-based extractor (much more reliable than regex)
        from cavia_common import get_ollama_client
        ollama_client = get_ollama_client()
        self.extractor = LLMCVExtractor(ollama_client)

        # Initialize clients
        self.minio = get_minio_client()
        self.db = get_db_manager()

        self.logger.info("ParserAgent initialized with LLM extractor", agent_id=self.agent_id)

    def get_agent_type(self) -> str:
        """Return the agent type"""
        return "parser"

    def get_agent_info(self) -> Dict[str, Any]:
        """Return agent metadata for registration"""
        return {
            "name": "CV Parser Agent",
            "description": "Extracts structured data from CV files in PDF and DOCX formats",
            "capabilities": {
                "supported_formats": ["pdf", "docx"],
                "extraction_features": [
                    "contact_information",
                    "education",
                    "work_experience",
                    "skills",
                    "certifications"
                ],
                "version": "1.0.0",
            },
        }

    def process_task(self, task) -> AgentTaskResult:
        """
        Process a CV parsing task.

        Supports both AgentTask (legacy) and AgentTaskV2 (with intent validation).

        Expected task payload:
        {
            "task_type": "parse_cv",
            "payload": {
                "job_id": "uuid",
                "filename": "cv.pdf",
                "minio_bucket": "cvs-raw",
                "minio_path": "path/to/cv.pdf"
            }
        }
        """
        start_time = time.time()

        # Detect task version
        is_v2_task = isinstance(task, AgentTaskV2) or hasattr(task, 'intent_validations')

        try:
            # INTENT VALIDATION - Step 1: Validate intent alignment
            if is_v2_task:
                self.logger.info(
                    "Starting CV parsing with intent validation (AgentTaskV2)",
                    task_id=task.task_id,
                    job_id=task.payload.get("job_id"),
                    filename=task.payload.get("filename"),
                    intent_goal=task.intent.goal if hasattr(task.intent, 'goal') else "N/A",
                )

                # Validate intent alignment
                validation = self.validate_intent(task)
                task.intent_validations.append(validation)

                self.logger.info(
                    f"Intent validation completed: aligned={validation.is_aligned}, "
                    f"alignment={validation.alignment_score:.2f}, drift={validation.drift_score:.2f}",
                    task_id=task.task_id,
                    is_aligned=validation.is_aligned,
                    alignment_score=validation.alignment_score,
                    drift_score=validation.drift_score,
                )

                # DRIFT CHECK - Step 2: Check if we've drifted too far
                if self.check_intent_drift(task, threshold=0.4):
                    self.logger.warning(
                        "Intent drift detected! Stopping workflow to prevent busy work.",
                        task_id=task.task_id,
                        avg_drift=sum(v.drift_score for v in task.intent_validations) / len(task.intent_validations),
                    )
                    # Store drift detection in job metadata
                    self._store_drift_detection(task.payload["job_id"], task.intent_validations)

                    return AgentTaskResult(
                        task_id=task.task_id,
                        agent_id=self.agent_id,
                        status="drift_detected",
                        error="Intent drift detected - workflow stopped to prevent misaligned work",
                        execution_time=time.time() - start_time,
                    )
            else:
                self.logger.info(
                    "Starting CV parsing (legacy AgentTask)",
                    task_id=task.task_id,
                    job_id=task.payload.get("job_id"),
                    filename=task.payload.get("filename"),
                )

            # Extract task parameters
            job_id = task.payload["job_id"]
            filename = task.payload["filename"]
            bucket = task.payload.get("minio_bucket", "cvs-raw")
            minio_path = task.payload["minio_path"]

            # Download file from MinIO
            temp_file = self._download_file(bucket, minio_path, filename)

            try:
                # Detect file type and parse
                file_ext = Path(filename).suffix.lower()

                if file_ext == '.pdf':
                    raw_text = self.pdf_parser.parse(temp_file)
                    metadata = self.pdf_parser.get_metadata(temp_file)
                elif file_ext in ['.docx', '.doc']:
                    raw_text = self.docx_parser.parse(temp_file)
                    metadata = self.docx_parser.get_metadata(temp_file)
                else:
                    raise ValueError(f"Unsupported file format: {file_ext}")

                if not raw_text:
                    raise ValueError("Failed to extract text from file")

                # Extract structured data
                parsed_cv = self._extract_structured_data(raw_text, filename, metadata)

                # Store ParsedCV in database
                self._store_parsed_cv(job_id, parsed_cv)

                # Store in MinIO
                storage_path = self._store_in_minio(job_id, parsed_cv)

                execution_time = time.time() - start_time

                # INTENT UPDATE - Step 3: Update intent context with results
                if is_v2_task:
                    self.update_intent_context(task, {
                        "parsing_completed": True,
                        "contact_extracted": len(parsed_cv.contact_info) > 0,
                        "education_count": len(parsed_cv.education),
                        "experience_count": len(parsed_cv.experience),
                        "skills_count": len(parsed_cv.skills),
                        "parser_agent": self.agent_id,
                    })

                    # Store updated validations in job metadata
                    self._store_intent_validations(job_id, task.intent_validations)

                    self.logger.info(
                        "Intent context updated with parsing results",
                        current_stage=task.intent.current_stage,
                    )

                self.logger.info(
                    "CV parsing completed successfully",
                    task_id=task.task_id,
                    job_id=job_id,
                    execution_time=execution_time,
                )

                # Discover and enqueue to next agent (evaluator)
                self._enqueue_to_evaluator(job_id, parsed_cv, storage_path, task)

                return AgentTaskResult(
                    task_id=task.task_id,
                    agent_id=self.agent_id,
                    status="success",
                    result={
                        "job_id": job_id,
                        "parsed_cv": parsed_cv.dict(),
                        "storage_path": storage_path,
                    },
                    execution_time=execution_time,
                )

            finally:
                # Cleanup temp file
                if os.path.exists(temp_file):
                    os.unlink(temp_file)

        except Exception as e:
            execution_time = time.time() - start_time

            self.logger.error(
                "CV parsing failed",
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

    def _download_file(self, bucket: str, object_name: str, filename: str) -> str:
        """Download file from MinIO to temp file"""
        self.logger.debug(f"Downloading file from MinIO: {bucket}/{object_name}")

        # Download file data
        file_data = self.minio.download_file(bucket, object_name)
        if not file_data:
            raise ValueError(f"Failed to download file from MinIO: {bucket}/{object_name}")

        # Save to temp file
        suffix = Path(filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_data)
            temp_path = tmp.name

        self.logger.debug(f"File downloaded to temp: {temp_path}")
        return temp_path

    def _extract_structured_data(
        self, raw_text: str, filename: str, file_metadata: dict
    ) -> ParsedCV:
        """Extract structured data from raw text using LLM"""
        self.logger.debug("Extracting structured data using LLM")

        # Use LLM to extract all sections in one call (more efficient and accurate)
        extracted_data = self.extractor.extract_all_sections(raw_text)

        # Build ParsedCV object from LLM-extracted data
        parsed_cv = ParsedCV(
            contact_info=extracted_data.get("contact_info", {}),
            education=extracted_data.get("education", []),
            experience=extracted_data.get("experience", []),
            skills=extracted_data.get("skills", []),
            certifications=extracted_data.get("certifications", []),
            raw_text=raw_text[:10000],  # Truncate for storage (keep first 10k chars)
            metadata={
                "filename": filename,
                "file_metadata": file_metadata,
                "parser_version": "2.0.0-llm",
                "extraction_method": "ollama_llm",
            }
        )

        self.logger.debug(
            "Structured data extracted via LLM",
            contact_count=len(parsed_cv.contact_info),
            education_count=len(parsed_cv.education),
            experience_count=len(parsed_cv.experience),
            skills_count=len(parsed_cv.skills),
            certifications_count=len(parsed_cv.certifications),
        )

        return parsed_cv

    def _store_parsed_cv(self, job_id: str, parsed_cv: ParsedCV):
        """Store ParsedCV in database"""
        try:
            with self.db.get_session() as session:
                # Update cv_jobs table with parsed data
                from sqlalchemy import text

                query = text("""
                    UPDATE cv_jobs
                    SET metadata = jsonb_set(
                        COALESCE(metadata, '{}'),
                        '{parsed_cv}',
                        CAST(:parsed_cv AS jsonb)
                    )
                    WHERE job_id = :job_id
                """)

                session.execute(
                    query,
                    {
                        "job_id": job_id,
                        "parsed_cv": parsed_cv.model_dump_json(),
                    }
                )
                session.commit()

            self.logger.debug("ParsedCV stored in database", job_id=job_id)

        except Exception as e:
            self.logger.error("Failed to store ParsedCV in database", error=str(e))
            raise

    def _store_in_minio(self, job_id: str, parsed_cv: ParsedCV) -> str:
        """Store ParsedCV JSON in MinIO"""
        import json
        from io import BytesIO

        try:
            storage_path = f"cvs-processed/parsed/{job_id}/parsed_cv.json"

            # Convert to JSON
            json_data = parsed_cv.model_dump_json(indent=2)

            # Upload to MinIO
            self.minio.upload_file(
                bucket_name="cvs-processed",
                object_name=storage_path,
                file_data=BytesIO(json_data.encode('utf-8')),
                content_type="application/json",
            )

            self.logger.debug("ParsedCV stored in MinIO", storage_path=storage_path)
            return storage_path

        except Exception as e:
            self.logger.error("Failed to store ParsedCV in MinIO", error=str(e))
            raise

    def _store_intent_validations(self, job_id: str, validations: list):
        """Store intent validations in job metadata"""
        try:
            import json

            with self.db.get_session() as session:
                from sqlalchemy import text

                query = text("""
                    UPDATE cv_jobs
                    SET metadata = jsonb_set(
                        COALESCE(metadata, '{}'),
                        '{intent_validations}',
                        CAST(:validations AS jsonb)
                    )
                    WHERE job_id = :job_id
                """)

                validations_json = json.dumps([v.model_dump() if hasattr(v, 'model_dump') else v for v in validations])

                session.execute(
                    query,
                    {
                        "job_id": job_id,
                        "validations": validations_json,
                    }
                )
                session.commit()

            self.logger.debug("Intent validations stored in database", job_id=job_id, count=len(validations))

        except Exception as e:
            self.logger.error("Failed to store intent validations", error=str(e))
            # Don't raise - validation storage failure shouldn't stop workflow

    def _store_drift_detection(self, job_id: str, validations: list):
        """Store drift detection info in job metadata and update status"""
        try:
            import json

            with self.db.get_session() as session:
                from sqlalchemy import text

                # Calculate drift metrics
                avg_drift = sum(v.drift_score for v in validations) / len(validations) if validations else 0
                max_drift = max(v.drift_score for v in validations) if validations else 0

                # Store drift info and update status
                query = text("""
                    UPDATE cv_jobs
                    SET
                        status = 'failed',
                        metadata = jsonb_set(
                            jsonb_set(
                                COALESCE(metadata, '{}'),
                                '{intent_validations}',
                                CAST(:validations AS jsonb)
                            ),
                            '{drift_detected}',
                            CAST(:drift_info AS jsonb)
                        )
                    WHERE job_id = :job_id
                """)

                validations_json = json.dumps([v.model_dump() if hasattr(v, 'model_dump') else v for v in validations])
                drift_info = json.dumps({
                    "detected": True,
                    "avg_drift": avg_drift,
                    "max_drift": max_drift,
                    "threshold": 0.4,
                    "message": "Workflow stopped due to intent drift - agents not aligned with original goal"
                })

                session.execute(
                    query,
                    {
                        "job_id": job_id,
                        "validations": validations_json,
                        "drift_info": drift_info,
                    }
                )
                session.commit()

            self.logger.info("Drift detection info stored", job_id=job_id, avg_drift=avg_drift, max_drift=max_drift)

        except Exception as e:
            self.logger.error("Failed to store drift detection", error=str(e))

    def _enqueue_to_evaluator(self, job_id: str, parsed_cv: ParsedCV, storage_path: str, task):
        """Discover and enqueue to evaluator agent using semantic discovery"""
        try:
            import json
            import sys

            print(f"DEBUG: _enqueue_to_evaluator called for job {job_id}", file=sys.stderr, flush=True)

            # Detect task version
            is_v2_task = isinstance(task, AgentTaskV2) or hasattr(task, 'intent_validations')

            # Build task parameters
            if is_v2_task:
                # For V2 tasks, pass the entire task forward (with intent and validations)
                intent_param = task.intent
                validations_param = task.intent_validations
            else:
                # For legacy tasks, use string intent
                intent_param = task.intent or "Process CV and determine acceptance"
                validations_param = None

            # Use semantic discovery to find evaluator agent
            print(f"DEBUG: About to call enqueue_to_next_agent", file=sys.stderr, flush=True)
            job_id_result = self.enqueue_to_next_agent(
                capability_query="evaluate CV against job criteria and acceptance standards",
                task_type="evaluate_cv",
                payload={
                    "job_id": job_id,
                    "parsed_cv": json.loads(parsed_cv.model_dump_json()),
                    "storage_path": storage_path,
                },
                intent=intent_param,
                steps_completed=task.steps_completed,
                intent_validations=validations_param  # Pass validations forward
            )

            print(f"DEBUG: enqueue_to_next_agent returned: {job_id_result}", file=sys.stderr, flush=True)

            if job_id_result:
                self.logger.info("Enqueued to evaluator via semantic discovery", job_id=job_id, rq_job_id=job_id_result)
            else:
                self.logger.warning("Failed to enqueue to evaluator", job_id=job_id)

        except Exception as e:
            print(f"DEBUG: Exception in _enqueue_to_evaluator: {e}", file=sys.stderr, flush=True)
            self.logger.error("Failed to enqueue to evaluator", job_id=job_id, error=str(e))
            # Don't raise - parsing was successful even if enqueueing failed


def main():
    """Main entry point for the Parser Agent"""
    import os

    # Get agent ID from environment
    agent_id = os.getenv("AGENT_ID", "parser-001")

    # Create and start agent
    agent = ParserAgent(agent_id=agent_id)

    logger.info(
        "Starting Parser Agent worker",
        agent_id=agent.agent_id,
        agent_type=agent.get_agent_type(),
    )

    # Start the RQ worker (blocking call)
    agent.start_worker()


if __name__ == "__main__":
    main()

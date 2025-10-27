"""
OCR Agent - Extracts structured data from scanned/image-based CV files using DeepSeek-OCR

This agent handles CVs that are scanned images or contain charts/graphs that require
advanced OCR processing. It uses DeepSeek-OCR for text extraction and Ollama LLM
for structured data extraction.
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
    AgentTaskResult,
    ParsedCV,
    get_logger,
    setup_logging,
    get_minio_client,
    get_db_manager,
)

from ocr_processor import DeepSeekOCRProcessor

# Setup logging
setup_logging()
logger = get_logger(__name__)


class OCRAgent(BaseAgent):
    """
    Agentic Unit for OCR-based CV parsing.

    Responsibilities:
    - Download CV/image from MinIO
    - Run DeepSeek-OCR to extract text from scanned documents
    - Handle documents with charts, graphs, and complex layouts
    - Extract structured data using LLM (contact, education, experience, skills, etc.)
    - Store ParsedCV in database and MinIO
    - Discover and enqueue to EvaluatorAgent
    """

    def __init__(self, agent_id: str = None):
        super().__init__(agent_id)

        # Initialize DeepSeek-OCR processor (lazy loading for model)
        self.ocr_processor = DeepSeekOCRProcessor()

        # Initialize LLM-based extractor (reuse from parser agent pattern)
        # Import here to avoid circular dependencies
        sys.path.insert(0, "/app/../parser")
        try:
            from parsers.llm_extractor import LLMCVExtractor
            from cavia_common import get_ollama_client

            ollama_client = get_ollama_client()
            self.llm_extractor = LLMCVExtractor(ollama_client)
            logger.info("LLM extractor initialized")
        except ImportError as e:
            logger.warning(f"Could not import LLMCVExtractor, will create inline: {e}")
            self.llm_extractor = None

        # Initialize clients
        self.minio = get_minio_client()
        self.db = get_db_manager()

        self.logger.info(
            "OCRAgent initialized",
            agent_id=self.agent_id,
            model_info=self.ocr_processor.get_model_info()
        )

    def get_agent_type(self) -> str:
        """Return the agent type"""
        return "ocr"

    def get_agent_info(self) -> Dict[str, Any]:
        """Return agent metadata for registration"""
        return {
            "name": "DeepSeek-OCR CV Agent",
            "description": "Extracts structured data from scanned image-based CVs, documents with charts and graphs using advanced OCR technology",
            "capabilities": {
                "supported_formats": ["pdf", "png", "jpg", "jpeg", "tiff"],
                "ocr_model": "deepseek-ocr",
                "extraction_features": [
                    "scanned_documents",
                    "image_based_cvs",
                    "charts_and_graphs",
                    "complex_layouts",
                    "contact_information",
                    "education",
                    "work_experience",
                    "skills",
                    "certifications"
                ],
                "version": "1.0.0",
            },
        }

    def process_task(self, task: AgentTask) -> AgentTaskResult:
        """
        Process an OCR-based CV extraction task.

        Expected task payload:
        {
            "task_type": "extract_from_image_cv",
            "payload": {
                "job_id": "uuid",
                "filename": "scanned_cv.pdf",
                "minio_bucket": "cvs-raw",
                "minio_path": "path/to/cv.pdf"
            }
        }
        """
        start_time = time.time()

        try:
            self.logger.info(
                "Starting OCR-based CV extraction",
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
                # Detect file type and run OCR
                file_ext = Path(filename).suffix.lower()

                if file_ext == '.pdf':
                    raw_text, num_pages = self._process_pdf_with_ocr(temp_file)
                    metadata = {"num_pages": num_pages, "file_type": "pdf"}
                elif file_ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
                    raw_text = self._process_image_with_ocr(temp_file)
                    metadata = {"file_type": file_ext.replace('.', '')}
                else:
                    raise ValueError(f"Unsupported file format for OCR: {file_ext}")

                if not raw_text or len(raw_text.strip()) < 50:
                    raise ValueError("OCR failed to extract meaningful text from file")

                # Extract structured data using LLM
                parsed_cv = self._extract_structured_data(raw_text, filename, metadata)

                # Store ParsedCV in database
                self._store_parsed_cv(job_id, parsed_cv)

                # Store in MinIO
                storage_path = self._store_in_minio(job_id, parsed_cv)

                execution_time = time.time() - start_time

                self.logger.info(
                    "OCR-based CV extraction completed successfully",
                    task_id=task.task_id,
                    job_id=job_id,
                    execution_time=execution_time,
                    text_length=len(raw_text),
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
                        "ocr_metadata": metadata,
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
                "OCR-based CV extraction failed",
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

    def _process_pdf_with_ocr(self, pdf_path: str) -> tuple:
        """
        Process PDF with OCR extraction.

        Returns:
            Tuple of (extracted_text, num_pages)
        """
        self.logger.info("Processing PDF with DeepSeek-OCR")

        try:
            # Try primary PDF processing method (pypdfium2)
            text, num_pages = self.ocr_processor.process_pdf(
                pdf_path,
                prompt_mode="markdown"  # Use markdown for better structure
            )
            return text, num_pages

        except Exception as e:
            self.logger.warning(f"Primary PDF OCR failed, trying fallback: {e}")

            # Try fallback method (pdf2image)
            try:
                text, num_pages = self.ocr_processor.process_pdf_fallback(
                    pdf_path,
                    prompt_mode="markdown"
                )
                return text, num_pages

            except Exception as fallback_error:
                self.logger.error(f"Fallback PDF OCR also failed: {fallback_error}")
                raise ValueError(f"All PDF OCR methods failed: {e}, {fallback_error}")

    def _process_image_with_ocr(self, image_path: str) -> str:
        """
        Process image with OCR extraction.

        Returns:
            Extracted text
        """
        self.logger.info("Processing image with DeepSeek-OCR")

        text = self.ocr_processor.process_image(
            image_path,
            prompt_mode="markdown"  # Use markdown for better structure
        )

        return text

    def _extract_structured_data(
        self, raw_text: str, filename: str, ocr_metadata: dict
    ) -> ParsedCV:
        """Extract structured data from OCR text using LLM"""
        self.logger.debug("Extracting structured data using LLM")

        if self.llm_extractor:
            # Use imported LLMCVExtractor
            extracted_data = self.llm_extractor.extract_all_sections(raw_text)
        else:
            # Inline extraction logic (fallback)
            from cavia_common import get_ollama_client
            extracted_data = self._extract_with_ollama_inline(raw_text)

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
                "ocr_metadata": ocr_metadata,
                "parser_version": "1.0.0-deepseek-ocr",
                "extraction_method": "deepseek_ocr_plus_llm",
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

    def _extract_with_ollama_inline(self, raw_text: str) -> dict:
        """Inline LLM extraction (fallback if LLMCVExtractor not available)"""
        import json
        from cavia_common import get_ollama_client

        ollama = get_ollama_client()

        prompt = f"""Extract structured information from the following CV text.
Return ONLY a valid JSON object with this exact structure:
{{
  "contact_info": {{"name": "", "email": "", "phone": "", "location": "", "linkedin": "", "github": ""}},
  "education": [{{"degree": "", "institution": "", "field": "", "start_date": "", "end_date": "", "gpa": ""}}],
  "experience": [{{"title": "", "company": "", "start_date": "", "end_date": "", "location": "", "description": ""}}],
  "skills": ["skill1", "skill2"],
  "certifications": [{{"name": "", "issuer": "", "date": ""}}]
}}

CV Text:
{raw_text[:8000]}

JSON:"""

        response = ollama.chat(
            messages=[
                {"role": "system", "content": "You are a CV parsing assistant. Extract information accurately and return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
        )

        try:
            result_text = response.get("message", {}).get("content", "{}")
            # Try to find JSON in the response
            if "{" in result_text:
                json_start = result_text.index("{")
                json_end = result_text.rindex("}") + 1
                json_str = result_text[json_start:json_end]
                return json.loads(json_str)
            return {}
        except Exception as e:
            self.logger.warning(f"Failed to parse LLM response: {e}")
            return {}

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
            storage_path = f"cvs-processed/ocr/{job_id}/parsed_cv.json"

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

    def _enqueue_to_evaluator(self, job_id: str, parsed_cv: ParsedCV, storage_path: str, task: AgentTask):
        """Discover and enqueue to evaluator agent using semantic discovery"""
        try:
            import json

            self.logger.debug(f"Enqueueing to evaluator for job {job_id}")

            # Use semantic discovery to find evaluator agent
            job_id_result = self.enqueue_to_next_agent(
                capability_query="evaluate CV against job criteria and acceptance standards",
                task_type="evaluate_cv",
                payload={
                    "job_id": job_id,
                    "parsed_cv": json.loads(parsed_cv.model_dump_json()),
                    "storage_path": storage_path,
                },
                intent=task.intent or "Process scanned CV and determine acceptance",
                steps_completed=task.steps_completed
            )

            if job_id_result:
                self.logger.info("Enqueued to evaluator via semantic discovery", job_id=job_id, rq_job_id=job_id_result)
            else:
                self.logger.warning("Failed to enqueue to evaluator", job_id=job_id)

        except Exception as e:
            self.logger.error("Failed to enqueue to evaluator", job_id=job_id, error=str(e))
            # Don't raise - OCR extraction was successful even if enqueueing failed


def main():
    """Main entry point for the OCR Agent"""
    import os

    # Get agent ID from environment
    agent_id = os.getenv("AGENT_ID", "ocr-001")

    # Create and start agent
    agent = OCRAgent(agent_id=agent_id)

    logger.info(
        "Starting OCR Agent worker",
        agent_id=agent.agent_id,
        agent_type=agent.get_agent_type(),
        model_info=agent.ocr_processor.get_model_info(),
    )

    # Start the RQ worker (blocking call)
    agent.start_worker()


if __name__ == "__main__":
    main()

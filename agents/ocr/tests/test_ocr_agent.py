"""
Tests for OCR Agent

This test suite validates the OCR agent's ability to extract
structured data from scanned/image-based CVs.
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add shared package to path
sys.path.insert(0, "/shared")
sys.path.insert(0, str(Path(__file__).parent.parent))

from cavia_common import AgentTask


class TestOCRAgent:
    """Test suite for OCR Agent"""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock external dependencies"""
        with patch('main.get_minio_client') as mock_minio, \
             patch('main.get_db_manager') as mock_db, \
             patch('main.get_ollama_client') as mock_ollama, \
             patch('main.DeepSeekOCRProcessor') as mock_ocr_processor:

            # Setup mock MinIO
            mock_minio_instance = Mock()
            mock_minio_instance.download_file.return_value = b"fake pdf content"
            mock_minio.return_value = mock_minio_instance

            # Setup mock DB
            mock_db_instance = Mock()
            mock_db.return_value = mock_db_instance

            # Setup mock Ollama
            mock_ollama_instance = Mock()
            mock_ollama.return_value = mock_ollama_instance

            # Setup mock OCR processor
            mock_processor_instance = Mock()
            mock_processor_instance.get_model_info.return_value = {
                "model_name": "deepseek-ai/deepseek-ocr",
                "device": "cpu",
                "model_loaded": False,
            }
            mock_ocr_processor.return_value = mock_processor_instance

            yield {
                'minio': mock_minio_instance,
                'db': mock_db_instance,
                'ollama': mock_ollama_instance,
                'ocr_processor': mock_processor_instance,
            }

    def test_agent_initialization(self, mock_dependencies):
        """Test that OCR agent initializes correctly"""
        from main import OCRAgent

        agent = OCRAgent(agent_id="test-ocr-001")

        assert agent.agent_id == "test-ocr-001"
        assert agent.get_agent_type() == "ocr"

    def test_agent_info(self, mock_dependencies):
        """Test that agent info is correctly structured"""
        from main import OCRAgent

        agent = OCRAgent(agent_id="test-ocr-001")
        info = agent.get_agent_info()

        assert info["name"] == "DeepSeek-OCR CV Agent"
        assert "scanned_documents" in info["capabilities"]["extraction_features"]
        assert "charts_and_graphs" in info["capabilities"]["extraction_features"]
        assert "deepseek-ocr" == info["capabilities"]["ocr_model"]

    @patch('main.os.path.exists', return_value=True)
    @patch('main.os.unlink')
    @patch('main.tempfile.NamedTemporaryFile')
    def test_process_pdf_task(self, mock_tempfile, mock_unlink, mock_exists, mock_dependencies):
        """Test processing a PDF OCR task"""
        from main import OCRAgent

        # Setup temp file mock
        mock_temp = Mock()
        mock_temp.name = "/tmp/test.pdf"
        mock_tempfile.return_value.__enter__.return_value = mock_temp

        # Setup OCR processor mock
        mock_dependencies['ocr_processor'].process_pdf.return_value = (
            "Test CV Content\nName: John Doe\nEmail: john@example.com",
            1
        )

        # Create agent
        agent = OCRAgent(agent_id="test-ocr-001")

        # Mock the LLM extractor
        agent.llm_extractor = Mock()
        agent.llm_extractor.extract_all_sections.return_value = {
            "contact_info": {"name": "John Doe", "email": "john@example.com"},
            "education": [],
            "experience": [],
            "skills": [],
            "certifications": [],
        }

        # Mock DB session
        mock_session = MagicMock()
        mock_session.__enter__.return_value = mock_session
        mock_session.__exit__.return_value = False
        mock_dependencies['db'].get_session.return_value = mock_session

        # Mock enqueue method
        agent.enqueue_to_next_agent = Mock(return_value="job-123")

        # Create task
        task = AgentTask(
            task_id="task-123",
            task_type="extract_from_image_cv",
            payload={
                "job_id": "job-123",
                "filename": "scanned_cv.pdf",
                "minio_bucket": "cvs-raw",
                "minio_path": "uploads/job-123/scanned_cv.pdf",
            },
            intent="Extract from scanned CV",
            steps_completed=[],
        )

        # Process task
        result = agent.process_task(task)

        # Assertions
        assert result.status == "success"
        assert result.task_id == "task-123"
        assert "parsed_cv" in result.result
        assert result.result["parsed_cv"]["contact_info"]["name"] == "John Doe"

        # Verify OCR was called
        mock_dependencies['ocr_processor'].process_pdf.assert_called_once()

    def test_ocr_processor_model_info(self, mock_dependencies):
        """Test that OCR processor provides model info"""
        from main import OCRAgent

        agent = OCRAgent(agent_id="test-ocr-001")
        model_info = agent.ocr_processor.get_model_info()

        assert "model_name" in model_info
        assert "device" in model_info
        assert model_info["model_name"] == "deepseek-ai/deepseek-ocr"


class TestDeepSeekOCRProcessor:
    """Test suite for DeepSeek-OCR Processor"""

    @patch('ocr_processor.torch.cuda.is_available', return_value=False)
    def test_processor_initialization_cpu(self, mock_cuda):
        """Test processor initializes on CPU when CUDA not available"""
        from ocr_processor import DeepSeekOCRProcessor

        processor = DeepSeekOCRProcessor()

        assert processor.device == "cpu"
        assert processor._model_loaded == False

    @patch('ocr_processor.torch.cuda.is_available', return_value=True)
    def test_processor_initialization_cuda(self, mock_cuda):
        """Test processor initializes on CUDA when available"""
        from ocr_processor import DeepSeekOCRProcessor

        processor = DeepSeekOCRProcessor()

        assert processor.device == "cuda"
        assert processor._model_loaded == False

    @patch('ocr_processor.torch.cuda.is_available', return_value=True)
    @patch('ocr_processor.torch.cuda.device_count', return_value=1)
    @patch('ocr_processor.torch.cuda.get_device_name', return_value="NVIDIA GB10")
    def test_model_info(self, mock_device_name, mock_device_count, mock_cuda_available):
        """Test getting model information"""
        from ocr_processor import DeepSeekOCRProcessor

        processor = DeepSeekOCRProcessor()
        info = processor.get_model_info()

        assert info["model_name"] == "deepseek-ai/deepseek-ocr"
        assert info["device"] == "cuda"
        assert info["cuda_available"] == True
        assert info["cuda_device_count"] == 1
        assert info["cuda_device_name"] == "NVIDIA GB10"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Unit tests for lifecycle module

Tests cover:
- register_agent with mocked HTTP responses
- discover_next_agent with mocked HTTP responses
- Offline functionality validation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, UTC

# Import lifecycle functions
from agents_common.lifecycle import (
    AgentContext,
    register_agent,
    discover_next_agent,
    enqueue_to_next_agent,
    validate_intent,
    check_intent_drift,
)


@pytest.fixture
def mock_agent_context():
    """Create a mock agent context for testing"""

    def mock_info_provider():
        return {
            "name": "Test Agent",
            "description": "A test agent for unit testing",
            "capabilities": {
                "supported_formats": ["pdf", "docx"],
                "extraction_features": ["contact", "education", "experience"],
                "version": "1.0.0",
            },
        }

    def mock_task_processor(task):
        return {"status": "success", "result": {}}

    # Mock the dependencies
    with patch("agents_common.lifecycle.get_logger") as mock_logger, patch(
        "agents_common.lifecycle.setup_logging"
    ), patch("agents_common.lifecycle.get_settings") as mock_settings, patch(
        "agents_common.lifecycle.get_db_manager"
    ) as mock_db, patch(
        "agents_common.lifecycle.get_redis_connection"
    ) as mock_redis:

        mock_logger.return_value = MagicMock()
        mock_settings.return_value = MagicMock(
            queue_parsing="queue-parsing",
            queue_evaluation="queue-evaluation",
            agent_heartbeat_interval=30,
        )
        mock_db.return_value = MagicMock()
        mock_redis.return_value = MagicMock()

        ctx = AgentContext(
            agent_id="test-agent-001",
            agent_type="parser",
            agent_info_provider=mock_info_provider,
            task_processor=mock_task_processor,
        )

        yield ctx


class TestRegisterAgent:
    """Test cases for register_agent function"""

    def test_register_agent_success(self, mock_agent_context):
        """Test successful agent registration with correct payload format"""

        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "success",
            "agent_id": "test-agent-001",
        }
        mock_response.raise_for_status = Mock()

        with patch(
            "agents_common.lifecycle.requests.post", return_value=mock_response
        ) as mock_post:
            result = register_agent(mock_agent_context)

            # Assert registration succeeded
            assert result is True

            # Verify HTTP call was made
            assert mock_post.called
            call_args = mock_post.call_args

            # Verify URL
            assert "register" in call_args[0][0]

            # Verify payload structure
            payload = call_args[1]["json"]
            assert "agent" in payload
            assert payload["agent"]["agent_id"] == "test-agent-001"
            assert payload["agent"]["name"] == "Test Agent"
            assert payload["agent"]["agent_type"] == "parser"

            # Verify capabilities is a list (not dict)
            assert isinstance(payload["agent"]["capabilities"], list)
            if payload["agent"]["capabilities"]:
                cap = payload["agent"]["capabilities"][0]
                assert "name" in cap
                assert "description" in cap
                assert "input_types" in cap
                assert "output_types" in cap

    def test_register_agent_failure(self, mock_agent_context):
        """Test agent registration failure handling"""

        # Mock failed HTTP response
        mock_response = Mock()
        mock_response.json.return_value = {"status": "error"}
        mock_response.raise_for_status = Mock()

        with patch("agents_common.lifecycle.requests.post", return_value=mock_response):
            result = register_agent(mock_agent_context)

            # Assert registration failed
            assert result is False

    def test_register_agent_http_error(self, mock_agent_context):
        """Test agent registration with HTTP error"""

        # Mock HTTP error
        with patch("agents_common.lifecycle.requests.post") as mock_post:
            mock_post.side_effect = Exception("Connection refused")

            result = register_agent(mock_agent_context)

            # Assert registration failed gracefully
            assert result is False


class TestDiscoverNextAgent:
    """Test cases for discover_next_agent function"""

    def test_discover_next_agent_success(self, mock_agent_context):
        """Test successful agent discovery with correct query format"""

        # Mock successful search response
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {
                    "agent_type": "evaluator",
                    "metadata": {"queue_name": "queue-evaluation"},
                    "similarity_score": 0.95,
                }
            ]
        }
        mock_response.raise_for_status = Mock()

        with patch(
            "agents_common.lifecycle.requests.post", return_value=mock_response
        ) as mock_post:
            result = discover_next_agent(
                mock_agent_context, "evaluate CV against criteria"
            )

            # Assert discovery succeeded
            assert result is not None
            assert result["agent_type"] == "evaluator"
            assert result["queue_name"] == "queue-evaluation"

            # Verify HTTP call was made with correct format
            assert mock_post.called
            call_args = mock_post.call_args

            # Verify URL
            assert "search" in call_args[0][0]

            # Verify query structure matches SearchQuery model
            query_payload = call_args[1]["json"]
            assert "query" in query_payload
            assert "mode" in query_payload
            assert "limit" in query_payload
            assert query_payload["mode"] == "semantic"
            assert query_payload["limit"] == 5

    def test_discover_next_agent_no_results(self, mock_agent_context):
        """Test agent discovery with no matching agents"""

        # Mock empty search response
        mock_response = Mock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = Mock()

        with patch("agents_common.lifecycle.requests.post", return_value=mock_response):
            result = discover_next_agent(mock_agent_context, "nonexistent capability")

            # Assert no agent found
            assert result is None

    def test_discover_next_agent_filters_self(self, mock_agent_context):
        """Test that discovery filters out the calling agent"""

        # Mock search response that includes the calling agent
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {
                    "agent_type": "parser",  # Same as mock_agent_context
                    "metadata": {"queue_name": "queue-parsing"},
                },
                {
                    "agent_type": "evaluator",
                    "metadata": {"queue_name": "queue-evaluation"},
                },
            ]
        }
        mock_response.raise_for_status = Mock()

        with patch("agents_common.lifecycle.requests.post", return_value=mock_response):
            result = discover_next_agent(mock_agent_context, "process CV")

            # Assert it returns evaluator (not self)
            assert result is not None
            assert result["agent_type"] == "evaluator"
            assert result["agent_type"] != mock_agent_context.agent_type

    def test_discover_next_agent_http_error(self, mock_agent_context):
        """Test agent discovery with HTTP error"""

        with patch("agents_common.lifecycle.requests.post") as mock_post:
            mock_post.side_effect = Exception("Connection timeout")

            result = discover_next_agent(mock_agent_context, "any capability")

            # Assert discovery failed gracefully
            assert result is None


class TestEnqueueToNextAgent:
    """Test cases for enqueue_to_next_agent function"""

    def test_enqueue_to_next_agent_success(self, mock_agent_context):
        """Test successful task enqueueing to next agent"""

        # Mock successful discovery
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {
                    "agent_type": "evaluator",
                    "metadata": {"queue_name": "queue-evaluation"},
                }
            ]
        }
        mock_response.raise_for_status = Mock()

        # Mock RQ queue
        mock_job = Mock()
        mock_job.id = "job-12345"
        mock_queue = Mock()
        mock_queue.enqueue.return_value = mock_job

        with patch(
            "agents_common.lifecycle.requests.post", return_value=mock_response
        ), patch("agents_common.lifecycle.Queue", return_value=mock_queue):

            result = enqueue_to_next_agent(
                ctx=mock_agent_context,
                capability_query="evaluate CV",
                task_type="evaluate_cv",
                payload={"job_id": "test-job-123"},
                intent="Process CV",
                steps_completed=["ocr", "parser"],
            )

            # Assert enqueue succeeded
            assert result == "job-12345"

            # Verify queue.enqueue was called with correct function path
            assert mock_queue.enqueue.called
            call_args = mock_queue.enqueue.call_args[0]
            assert "agents_common.lifecycle.process_agent_task" in call_args[0]

    def test_enqueue_to_next_agent_no_agent_found(self, mock_agent_context):
        """Test enqueueing when no suitable agent is found"""

        # Mock empty discovery response
        mock_response = Mock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = Mock()

        with patch("agents_common.lifecycle.requests.post", return_value=mock_response):
            result = enqueue_to_next_agent(
                ctx=mock_agent_context,
                capability_query="nonexistent capability",
                task_type="test_task",
                payload={},
                intent="Test",
                steps_completed=[],
            )

            # Assert enqueue failed
            assert result is None


class TestIntentValidation:
    """Test cases for intent validation functions"""

    def test_validate_intent_aligned(self, mock_agent_context):
        """Test intent validation for aligned task"""
        from agents_common import AgentTaskV2, StructuredIntent

        # Create a task with aligned intent
        intent = StructuredIntent(
            intent_id="intent-001",
            goal="Parse and extract data from CV document",
            workflow_type="cv_processing",
            context={},
            current_stage="parsing",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        task = AgentTaskV2(
            task_id="task-001",
            task_type="parse_cv",
            payload={"job_id": "job-001"},
            intent=intent,
            steps_completed=[],
            intent_validations=[],
        )

        validation = validate_intent(mock_agent_context, task)

        # Assert validation succeeded
        assert validation.agent_id == "test-agent-001"
        assert validation.agent_type == "parser"
        assert isinstance(validation.is_aligned, bool)
        assert isinstance(validation.alignment_score, float)
        assert isinstance(validation.drift_score, float)
        assert 0.0 <= validation.alignment_score <= 1.0
        assert 0.0 <= validation.drift_score <= 1.0

    def test_check_intent_drift_below_threshold(self, mock_agent_context):
        """Test drift check with low drift (should not stop workflow)"""
        from agents_common import AgentTaskV2, StructuredIntent, IntentValidation

        intent = StructuredIntent(
            intent_id="intent-001",
            goal="Process CV",
            workflow_type="cv_processing",
            context={},
            current_stage="parsing",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Create validations with low drift
        validations = [
            IntentValidation(
                agent_id="agent-1",
                agent_type="parser",
                is_aligned=True,
                alignment_score=0.9,
                drift_score=0.1,
                reasoning="Well aligned",
                suggestions=[],
            )
        ]

        task = AgentTaskV2(
            task_id="task-001",
            task_type="parse_cv",
            payload={},
            intent=intent,
            steps_completed=[],
            intent_validations=validations,
        )

        has_drift = check_intent_drift(task, threshold=0.4)

        # Assert no drift detected
        assert has_drift is False

    def test_check_intent_drift_above_threshold(self, mock_agent_context):
        """Test drift check with high drift (should stop workflow)"""
        from agents_common import AgentTaskV2, StructuredIntent, IntentValidation

        intent = StructuredIntent(
            intent_id="intent-001",
            goal="Process CV",
            workflow_type="cv_processing",
            context={},
            current_stage="parsing",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Create validations with high drift
        validations = [
            IntentValidation(
                agent_id="agent-1",
                agent_type="parser",
                is_aligned=False,
                alignment_score=0.2,
                drift_score=0.8,
                reasoning="Misaligned",
                suggestions=["Re-route"],
            )
        ]

        task = AgentTaskV2(
            task_id="task-001",
            task_type="parse_cv",
            payload={},
            intent=intent,
            steps_completed=[],
            intent_validations=validations,
        )

        has_drift = check_intent_drift(task, threshold=0.4)

        # Assert drift detected
        assert has_drift is True


class TestOfflineFunctionality:
    """Test that lifecycle functions work offline (with mocked network)"""

    def test_register_agent_offline(self, mock_agent_context):
        """Verify register_agent can be called offline (network mocked)"""

        # This test verifies the function can be called and handles errors gracefully
        with patch("agents_common.lifecycle.requests.post") as mock_post:
            mock_post.side_effect = Exception("No network connection")

            # Should not raise exception, should return False
            result = register_agent(mock_agent_context)
            assert result is False

    def test_discover_next_agent_offline(self, mock_agent_context):
        """Verify discover_next_agent can be called offline (network mocked)"""

        with patch("agents_common.lifecycle.requests.post") as mock_post:
            mock_post.side_effect = Exception("No network connection")

            # Should not raise exception, should return None
            result = discover_next_agent(mock_agent_context, "test capability")
            assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

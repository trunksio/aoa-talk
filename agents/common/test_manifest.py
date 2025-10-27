"""
Unit tests for agent manifest and registration functionality
"""

import os
import sys
import tempfile
from pathlib import Path
from datetime import datetime

import pytest
from unittest.mock import Mock, patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from manifest import AgentManifest, Agent, Capability  # noqa: E402
from register_on_start import (  # noqa: E402
    load_manifest_from_yaml,
    register_agent_from_manifest,
)


class TestCapability:
    """Tests for Capability model"""

    def test_capability_basic(self):
        """Test basic capability creation"""
        cap = Capability(
            name="test_capability",
            description="A test capability",
            input_types=["text/plain"],
            output_types=["application/json"],
        )
        assert cap.name == "test_capability"
        assert cap.description == "A test capability"
        assert cap.input_types == ["text/plain"]
        assert cap.output_types == ["application/json"]
        assert cap.parameters == {}
        assert cap.metadata == {}

    def test_capability_with_params(self):
        """Test capability with parameters and metadata"""
        cap = Capability(
            name="advanced_capability",
            description="Advanced capability",
            input_types=["image/png", "image/jpeg"],
            output_types=["application/json"],
            parameters={"max_size": 1024, "format": "json"},
            metadata={"version": "1.0", "author": "test"},
        )
        assert cap.parameters["max_size"] == 1024
        assert cap.metadata["author"] == "test"


class TestAgent:
    """Tests for Agent model"""

    def test_agent_basic(self):
        """Test basic agent creation"""
        agent = Agent(
            agent_id="test-001",
            name="Test Agent",
            description="A test agent",
            agent_type="test",
        )
        assert agent.agent_id == "test-001"
        assert agent.name == "Test Agent"
        assert agent.agent_type == "test"
        assert agent.version == "1.0.0"
        assert agent.status == "active"
        assert agent.capabilities == []

    def test_agent_with_capabilities(self):
        """Test agent with capabilities"""
        cap1 = Capability(
            name="cap1",
            description="Capability 1",
            input_types=["text/plain"],
            output_types=["application/json"],
        )
        cap2 = Capability(
            name="cap2",
            description="Capability 2",
            input_types=["image/png"],
            output_types=["text/plain"],
        )

        agent = Agent(
            agent_id="test-002",
            name="Multi-Capability Agent",
            description="Agent with multiple capabilities",
            agent_type="multi",
            capabilities=[cap1, cap2],
        )

        assert len(agent.capabilities) == 2
        assert agent.capabilities[0].name == "cap1"
        assert agent.capabilities[1].name == "cap2"


class TestAgentManifest:
    """Tests for AgentManifest model"""

    def test_manifest_basic(self):
        """Test basic manifest creation"""
        agent = Agent(
            agent_id="test-003",
            name="Manifest Test Agent",
            description="Testing manifest",
            agent_type="test",
        )
        manifest = AgentManifest(agent=agent)

        assert manifest.agent.agent_id == "test-003"
        assert manifest.registration_timestamp is None

    def test_manifest_with_timestamp(self):
        """Test manifest with registration timestamp"""
        agent = Agent(
            agent_id="test-004",
            name="Timestamped Agent",
            description="Testing timestamp",
            agent_type="test",
        )
        timestamp = datetime.utcnow()
        manifest = AgentManifest(agent=agent, registration_timestamp=timestamp)

        assert manifest.registration_timestamp == timestamp


class TestLoadManifestFromYAML:
    """Tests for load_manifest_from_yaml function"""

    def test_load_valid_manifest(self):
        """Test loading a valid manifest from YAML"""
        yaml_content = """
agent:
  agent_id: "ocr-001"
  name: "OCR Agent"
  description: "OCR processing agent"
  agent_type: "ocr"
  version: "1.0.0"
  status: "active"
  capabilities:
    - name: "extract_text"
      description: "Extract text from images"
      input_types:
        - "image/png"
        - "image/jpeg"
      output_types:
        - "text/plain"
      parameters:
        max_size_mb: 10
      metadata:
        accuracy: 0.95
  metadata:
    author: "test"
"""
        # Create temporary YAML file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            # Load manifest
            manifest = load_manifest_from_yaml(temp_path)

            # Verify agent info
            assert manifest.agent.agent_id == "ocr-001"
            assert manifest.agent.name == "OCR Agent"
            assert manifest.agent.agent_type == "ocr"
            assert manifest.agent.version == "1.0.0"

            # Verify capabilities
            assert len(manifest.agent.capabilities) == 1
            cap = manifest.agent.capabilities[0]
            assert cap.name == "extract_text"
            assert "image/png" in cap.input_types
            assert cap.parameters["max_size_mb"] == 10
            assert cap.metadata["accuracy"] == 0.95

            # Verify registration timestamp was added
            assert manifest.registration_timestamp is not None

        finally:
            # Cleanup
            os.unlink(temp_path)

    def test_load_manifest_file_not_found(self):
        """Test loading non-existent manifest file"""
        with pytest.raises(FileNotFoundError):
            load_manifest_from_yaml("/nonexistent/manifest.yaml")

    def test_load_empty_manifest(self):
        """Test loading empty manifest file"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Empty manifest file"):
                load_manifest_from_yaml(temp_path)
        finally:
            os.unlink(temp_path)

    def test_load_manifest_with_embedding(self):
        """Test loading manifest with embedding"""
        yaml_content = """
agent:
  agent_id: "test-005"
  name: "Test Agent"
  description: "Test"
  agent_type: "test"
  capabilities: []
  embedding:
    vector: [0.1, 0.2, 0.3]
    model: "test-model"
    dimension: 3
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            manifest = load_manifest_from_yaml(temp_path)
            assert manifest.agent.embedding is not None
            assert manifest.agent.embedding.vector == [0.1, 0.2, 0.3]
            assert manifest.agent.embedding.model == "test-model"
            assert manifest.agent.embedding.dimension == 3
        finally:
            os.unlink(temp_path)


class TestRegisterAgentFromManifest:
    """Tests for register_agent_from_manifest function"""

    @patch("register_on_start.requests.post")
    def test_successful_registration(self, mock_post):
        """Test successful agent registration"""
        # Create test manifest
        yaml_content = """
agent:
  agent_id: "test-006"
  name: "Test Agent"
  description: "Test registration"
  agent_type: "test"
  capabilities:
    - name: "test_cap"
      description: "Test capability"
      input_types: ["text/plain"]
      output_types: ["application/json"]
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            # Mock successful response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "success",
                "message": "Agent registered successfully",
                "agent_id": "test-006",
                "action": "created",
            }
            mock_post.return_value = mock_response

            # Register agent
            result = register_agent_from_manifest(
                temp_path,
                registry_url="http://test-registry:8000",
                max_retries=1,
            )

            # Verify success
            assert result is True
            mock_post.assert_called_once()

            # Verify request payload
            call_args = mock_post.call_args
            assert call_args[0][0] == "http://test-registry:8000/register"
            payload = call_args[1]["json"]
            assert payload["agent"]["agent_id"] == "test-006"
            assert payload["agent"]["name"] == "Test Agent"

        finally:
            os.unlink(temp_path)

    @patch("register_on_start.requests.post")
    def test_registration_retry_on_connection_error(self, mock_post):
        """Test registration retries on connection error"""
        yaml_content = """
agent:
  agent_id: "test-007"
  name: "Test Agent"
  description: "Test retry"
  agent_type: "test"
  capabilities: []
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            # Mock connection error then success
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "success",
                "agent_id": "test-007",
                "action": "created",
            }

            # First call fails, second succeeds
            mock_post.side_effect = [
                Exception("Connection error"),
                mock_response,
            ]

            # Register with short retry delay
            with patch("register_on_start.time.sleep"):
                result = register_agent_from_manifest(
                    temp_path,
                    registry_url="http://test-registry:8000",
                    max_retries=2,
                    retry_delay=1,
                )

            # Verify success after retry
            assert result is True
            assert mock_post.call_count == 2

        finally:
            os.unlink(temp_path)

    @patch("register_on_start.requests.post")
    def test_registration_failure_after_max_retries(self, mock_post):
        """Test registration failure after max retries"""
        yaml_content = """
agent:
  agent_id: "test-008"
  name: "Test Agent"
  description: "Test failure"
  agent_type: "test"
  capabilities: []
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            # Mock persistent failure
            mock_post.side_effect = Exception("Connection refused")

            # Register with short retry delay
            with patch("register_on_start.time.sleep"):
                result = register_agent_from_manifest(
                    temp_path,
                    registry_url="http://test-registry:8000",
                    max_retries=3,
                    retry_delay=1,
                )

            # Verify failure
            assert result is False
            assert mock_post.call_count == 3

        finally:
            os.unlink(temp_path)

    def test_registration_with_invalid_manifest(self):
        """Test registration with invalid manifest file"""
        result = register_agent_from_manifest(
            "/nonexistent/manifest.yaml",
            registry_url="http://test-registry:8000",
        )
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

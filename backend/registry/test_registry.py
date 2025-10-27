"""
Unit tests for AOA Registry Service
------------------------------------
Tests registration, retrieval, and search functionality.
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

# Import with absolute imports after path setup
import backend.registry.main as main_module  # noqa: E402
import backend.registry.database as db_module  # noqa: E402

app = main_module.app
get_db_session = main_module.get_db_session
Base = db_module.Base


# Test database URL (use in-memory SQLite for tests)
TEST_DATABASE_URL = "sqlite:///./test_registry.db"


@pytest.fixture(scope="function")
def test_db():
    """Create a test database"""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db_session] = override_get_db
    yield TestingSessionLocal
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db):
    """Create a test client"""
    return TestClient(app)


@pytest.fixture
def sample_agent_manifest():
    """Sample agent manifest for testing"""
    return {
        "agent": {
            "agent_id": "test-agent-001",
            "name": "Test OCR Agent",
            "description": "Agent for optical character recognition",
            "agent_type": "ocr",
            "version": "1.0.0",
            "status": "active",
            "capabilities": [
                {
                    "name": "image_to_text",
                    "description": "Extract text from images",
                    "input_types": ["image/png", "image/jpeg"],
                    "output_types": ["text/plain"],
                    "parameters": {"language": "en"},
                    "metadata": {"accuracy": "high"},
                }
            ],
            "embedding": {
                "vector": [0.1] * 384,  # 384-dim vector
                "model": "all-MiniLM-L6-v2",
                "dimension": 384,
            },
            "metadata": {"environment": "test"},
        }
    }


def test_root_endpoint(client):
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "AOA Registry running"
    assert data["service"] == "registry"


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "aoa-registry"


def test_register_agent(client, sample_agent_manifest):
    """Test agent registration"""
    response = client.post("/register", json=sample_agent_manifest)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["agent_id"] == "test-agent-001"
    assert data["action"] == "created"


def test_register_agent_update(client, sample_agent_manifest):
    """Test agent registration update (idempotency)"""
    # Register agent first time
    response1 = client.post("/register", json=sample_agent_manifest)
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["action"] == "created"

    # Register same agent again (should update)
    sample_agent_manifest["agent"]["description"] = "Updated description"
    response2 = client.post("/register", json=sample_agent_manifest)
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["action"] == "updated"


def test_get_agent(client, sample_agent_manifest):
    """Test retrieving a specific agent"""
    # Register agent first
    client.post("/register", json=sample_agent_manifest)

    # Retrieve agent
    response = client.get("/agents/test-agent-001")
    assert response.status_code == 200
    data = response.json()
    assert data["agent_id"] == "test-agent-001"
    assert data["name"] == "Test OCR Agent"
    assert len(data["capabilities"]) == 1
    assert data["capabilities"][0]["name"] == "image_to_text"


def test_get_nonexistent_agent(client):
    """Test retrieving a non-existent agent"""
    response = client.get("/agents/nonexistent-agent")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_search_agents_semantic(client, sample_agent_manifest):
    """Test semantic search for agents"""
    # Register an agent first
    client.post("/register", json=sample_agent_manifest)

    # Search for agents
    search_query = {"query": "OCR capabilities", "mode": "semantic", "limit": 10}
    response = client.post("/search", json=search_query)
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "semantic"
    assert data["total"] >= 1
    assert len(data["results"]) >= 1
    assert data["results"][0]["agent_id"] == "test-agent-001"


def test_search_agents_graph(client, sample_agent_manifest):
    """Test graph-based search for agents"""
    # Register an agent first
    client.post("/register", json=sample_agent_manifest)

    # Search using graph mode
    search_query = {"query": "text extraction", "mode": "graph", "limit": 10}
    response = client.post("/search", json=search_query)
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "graph"
    assert data["total"] >= 1


def test_search_invalid_mode(client):
    """Test search with invalid mode"""
    search_query = {"query": "test", "mode": "invalid_mode", "limit": 10}
    response = client.post("/search", json=search_query)
    assert response.status_code == 400
    assert "Invalid search mode" in response.json()["detail"]


def test_register_multiple_agents(client, sample_agent_manifest):
    """Test registering multiple agents"""
    # Register first agent
    response1 = client.post("/register", json=sample_agent_manifest)
    assert response1.status_code == 200

    # Register second agent
    sample_agent_manifest["agent"]["agent_id"] = "test-agent-002"
    sample_agent_manifest["agent"]["name"] = "Test Parser Agent"
    sample_agent_manifest["agent"]["agent_type"] = "parser"
    response2 = client.post("/register", json=sample_agent_manifest)
    assert response2.status_code == 200

    # Search and verify both agents exist
    search_query = {"query": "agent", "mode": "semantic", "limit": 10}
    response = client.post("/search", json=search_query)
    data = response.json()
    assert data["total"] == 2


def test_round_trip_registration_retrieval(client, sample_agent_manifest):
    """Test round-trip: register agent and retrieve it with all data intact"""
    # Register agent
    register_response = client.post("/register", json=sample_agent_manifest)
    assert register_response.status_code == 200

    # Retrieve agent
    get_response = client.get("/agents/test-agent-001")
    assert get_response.status_code == 200
    retrieved_data = get_response.json()

    # Verify all fields match
    original_agent = sample_agent_manifest["agent"]
    assert retrieved_data["agent_id"] == original_agent["agent_id"]
    assert retrieved_data["name"] == original_agent["name"]
    assert retrieved_data["description"] == original_agent["description"]
    assert retrieved_data["agent_type"] == original_agent["agent_type"]
    assert retrieved_data["version"] == original_agent["version"]
    assert retrieved_data["status"] == original_agent["status"]
    assert len(retrieved_data["capabilities"]) == len(original_agent["capabilities"])

    # Verify capability details
    retrieved_cap = retrieved_data["capabilities"][0]
    original_cap = original_agent["capabilities"][0]
    assert retrieved_cap["name"] == original_cap["name"]
    assert retrieved_cap["description"] == original_cap["description"]
    assert retrieved_cap["input_types"] == original_cap["input_types"]
    assert retrieved_cap["output_types"] == original_cap["output_types"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

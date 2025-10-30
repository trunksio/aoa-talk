"""
Integration tests for Registry and Discovery functionality.

This test suite verifies:
1. Registry /search endpoint returns structured results
2. enqueue_to_next_agent correctly interprets response['results']
3. OCR and Parser agents can be registered and discovered
4. Agent chaining works end-to-end
5. RQ jobs are enqueued correctly in Redis

Requirements:
- Docker services must be running (registry, redis, postgres)
- Set INTEGRATION_TEST=true to run these tests
"""

import os
import pytest
import requests
import time
from rq import Queue
from redis import Redis
from typing import Dict, Any


# Skip all tests if not in integration test mode
pytestmark = pytest.mark.skipif(
    os.getenv("INTEGRATION_TEST") != "true",
    reason="Integration tests only run with INTEGRATION_TEST=true",
)


@pytest.fixture(scope="module")
def registry_url():
    """Get registry service URL"""
    return os.getenv("REGISTRY_URL", "http://localhost:8001")


@pytest.fixture(scope="module")
def redis_conn():
    """Get Redis connection for RQ verification"""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return Redis.from_url(redis_url)


@pytest.fixture(scope="module")
def wait_for_services(registry_url):
    """Wait for services to be ready"""
    max_retries = 30
    for i in range(max_retries):
        try:
            response = requests.get(f"{registry_url}/health", timeout=2)
            if response.status_code == 200:
                # Give services a moment to fully initialize
                time.sleep(2)
                return True
        except requests.exceptions.RequestException:
            if i < max_retries - 1:
                time.sleep(2)
            else:
                raise
    raise RuntimeError("Services did not start in time")


@pytest.fixture
def ocr_agent_manifest() -> Dict[str, Any]:
    """OCR agent manifest for registration"""
    return {
        "agent": {
            "agent_id": "ocr-integration-test-001",
            "name": "OCR Integration Test Agent",
            "description": "OCR agent for integration testing",
            "agent_type": "ocr",
            "version": "1.0.0",
            "status": "active",
            "metadata": {
                "queue_name": "queue-ocr-test",
                "model": "deepseek-ocr",
            },
        },
        "capabilities": [
            {
                "name": "scanned_documents",
                "description": "Extract text from scanned documents using OCR",
                "input_types": ["image/jpeg", "image/png", "application/pdf"],
                "output_types": ["text/plain", "application/json"],
                "parameters": {
                    "languages": ["en"],
                    "dpi": 300,
                },
                "metadata": {
                    "model": "deepseek-ocr",
                    "confidence_threshold": 0.8,
                },
            }
        ],
    }


@pytest.fixture
def parser_agent_manifest() -> Dict[str, Any]:
    """Parser agent manifest for registration"""
    return {
        "agent": {
            "agent_id": "parser-integration-test-001",
            "name": "Parser Integration Test Agent",
            "description": "Parser agent for integration testing",
            "agent_type": "parser",
            "version": "1.0.0",
            "status": "active",
            "metadata": {
                "queue_name": "queue-parsing-test",
                "model": "llama3",
            },
        },
        "capabilities": [
            {
                "name": "cv_parsing",
                "description": "Parse CVs and extract structured information",
                "input_types": ["text/plain", "application/pdf"],
                "output_types": ["application/json"],
                "parameters": {
                    "fields": ["contact", "education", "experience"],
                },
                "metadata": {
                    "model": "llama3",
                },
            }
        ],
    }


@pytest.fixture
def evaluator_agent_manifest() -> Dict[str, Any]:
    """Evaluator agent manifest for registration"""
    return {
        "agent": {
            "agent_id": "evaluator-integration-test-001",
            "name": "Evaluator Integration Test Agent",
            "description": "Evaluator agent for integration testing",
            "agent_type": "evaluator",
            "version": "1.0.0",
            "status": "active",
            "metadata": {
                "queue_name": "queue-evaluation-test",
                "model": "llama3",
            },
        },
        "capabilities": [
            {
                "name": "cv_evaluation",
                "description": "Evaluate CVs against job criteria",
                "input_types": ["application/json"],
                "output_types": ["application/json"],
                "parameters": {
                    "criteria": ["skills", "experience", "education"],
                },
                "metadata": {
                    "model": "llama3",
                },
            }
        ],
    }


class TestRegistrySearchEndpoint:
    """Test registry /search endpoint returns structured results"""

    def test_search_endpoint_structure(
        self, registry_url, wait_for_services, ocr_agent_manifest
    ):
        """Verify /search endpoint returns properly structured SearchResponse"""
        # Register OCR agent
        register_response = requests.post(
            f"{registry_url}/register", json=ocr_agent_manifest, timeout=10
        )
        assert register_response.status_code == 200

        # Perform semantic search
        search_query = {
            "query": "extract text from scanned documents",
            "mode": "semantic",
            "limit": 5,
        }
        search_response = requests.post(
            f"{registry_url}/search", json=search_query, timeout=10
        )

        assert search_response.status_code == 200
        data = search_response.json()

        # Verify SearchResponse structure
        assert "query" in data
        assert "mode" in data
        assert "results" in data
        assert "total" in data
        assert "execution_time_ms" in data

        # Verify results structure
        assert isinstance(data["results"], list)
        assert data["total"] >= 1

        # Verify at least one result has correct structure
        if data["results"]:
            result = data["results"][0]
            assert "agent_id" in result
            assert "agent_type" in result
            assert "name" in result
            assert "description" in result
            assert "capabilities" in result
            assert "metadata" in result

    def test_search_returns_registered_agents(
        self,
        registry_url,
        wait_for_services,
        ocr_agent_manifest,
        parser_agent_manifest,
    ):
        """Verify search returns agents that were registered"""
        # Register both agents
        requests.post(f"{registry_url}/register", json=ocr_agent_manifest, timeout=10)
        requests.post(
            f"{registry_url}/register", json=parser_agent_manifest, timeout=10
        )

        # Search for OCR capability
        search_response = requests.post(
            f"{registry_url}/search",
            json={
                "query": "OCR text extraction from scanned documents",
                "mode": "semantic",
                "limit": 10,
            },
            timeout=10,
        )

        assert search_response.status_code == 200
        data = search_response.json()

        # Should find at least the OCR agent
        agent_ids = [r["agent_id"] for r in data["results"]]
        assert "ocr-integration-test-001" in agent_ids


class TestEnqueueToNextAgent:
    """Test enqueue_to_next_agent correctly interprets response['results']"""

    def test_discover_next_agent_response_parsing(
        self, registry_url, wait_for_services, parser_agent_manifest
    ):
        """Verify discover_next_agent correctly parses /search response"""
        # Register parser agent
        requests.post(
            f"{registry_url}/register", json=parser_agent_manifest, timeout=10
        )

        # Simulate what discover_next_agent does
        search_response = requests.post(
            f"{registry_url}/search",
            json={
                "query": "parse CV and extract structured data",
                "mode": "semantic",
                "limit": 5,
            },
            timeout=10,
        )

        assert search_response.status_code == 200
        data = search_response.json()

        # Verify we can extract results as expected
        results = data.get("results", [])
        assert len(results) > 0

        # Verify we can extract agent_type and queue_name from results
        top_result = results[0]
        assert "agent_type" in top_result
        assert "metadata" in top_result

        # Verify queue_name is in metadata
        metadata = top_result.get("metadata", {})
        assert "queue_name" in metadata

    def test_enqueue_to_next_agent_with_redis(
        self,
        registry_url,
        redis_conn,
        wait_for_services,
        evaluator_agent_manifest,
    ):
        """Verify enqueue_to_next_agent creates valid RQ jobs in Redis"""
        # Register evaluator agent
        requests.post(
            f"{registry_url}/register", json=evaluator_agent_manifest, timeout=10
        )

        # Create a queue for the evaluator agent
        queue_name = "queue-evaluation-test"
        queue = Queue(queue_name, connection=redis_conn)

        # Clear any existing jobs
        queue.empty()

        # Enqueue a test job (simulating what enqueue_to_next_agent does)
        job = queue.enqueue(
            "agents_common.lifecycle.process_agent_task",
            {
                "task_id": "test-task-001",
                "task_type": "evaluate_cv",
                "payload": {"cv_data": {"name": "Test User"}},
                "intent": "Evaluate CV for job match",
                "steps_completed": ["ocr", "parser"],
            },
            job_timeout="15m",
            result_ttl=3600,
        )

        # Verify job was created
        assert job is not None
        assert job.id is not None

        # Verify job is in Redis
        assert queue.count == 1

        # Verify job details
        fetched_job = queue.fetch_job(job.id)
        assert fetched_job is not None
        assert fetched_job.func_name == "agents_common.lifecycle.process_agent_task"
        assert fetched_job.timeout == 900  # 15 minutes in seconds


class TestAgentChaining:
    """Test full agent discovery and chaining workflow"""

    def test_ocr_to_parser_to_evaluator_chain(
        self,
        registry_url,
        redis_conn,
        wait_for_services,
        ocr_agent_manifest,
        parser_agent_manifest,
        evaluator_agent_manifest,
    ):
        """Integration test: Register agents, discover via search, and verify chaining"""
        # Step 1: Register all agents
        ocr_resp = requests.post(
            f"{registry_url}/register", json=ocr_agent_manifest, timeout=10
        )
        parser_resp = requests.post(
            f"{registry_url}/register", json=parser_agent_manifest, timeout=10
        )
        evaluator_resp = requests.post(
            f"{registry_url}/register", json=evaluator_agent_manifest, timeout=10
        )

        assert ocr_resp.status_code == 200
        assert parser_resp.status_code == 200
        assert evaluator_resp.status_code == 200

        # Step 2: Verify OCR agent can be retrieved
        get_resp = requests.get(
            f"{registry_url}/agents/ocr-integration-test-001", timeout=10
        )
        assert get_resp.status_code == 200
        ocr_data = get_resp.json()
        assert ocr_data["agent_id"] == "ocr-integration-test-001"
        assert ocr_data["agent_type"] == "ocr"
        assert len(ocr_data["capabilities"]) >= 1

        # Step 3: Simulate OCR agent discovering Parser agent
        search_for_parser = requests.post(
            f"{registry_url}/search",
            json={
                "query": "parse and extract structured data from text",
                "mode": "semantic",
                "limit": 5,
            },
            timeout=10,
        )
        assert search_for_parser.status_code == 200
        parser_results = search_for_parser.json()["results"]

        # Find parser agent in results (filter out OCR to simulate self-filtering)
        parser_agents = [
            r for r in parser_results if r["agent_type"] == "parser"
        ]
        assert len(parser_agents) > 0

        parser_agent = parser_agents[0]
        parser_queue = parser_agent["metadata"]["queue_name"]

        # Step 4: Enqueue task to Parser queue
        parser_queue_obj = Queue(parser_queue, connection=redis_conn)
        parser_queue_obj.empty()

        parser_job = parser_queue_obj.enqueue(
            "agents_common.lifecycle.process_agent_task",
            {
                "task_id": "chain-test-001",
                "task_type": "parse_cv",
                "payload": {"ocr_text": "Test CV content"},
                "intent": "Extract structured CV data",
                "steps_completed": ["ocr"],
            },
            job_timeout="15m",
        )

        assert parser_job is not None
        assert parser_queue_obj.count == 1

        # Step 5: Simulate Parser agent discovering Evaluator agent
        search_for_evaluator = requests.post(
            f"{registry_url}/search",
            json={
                "query": "evaluate CV against job criteria",
                "mode": "semantic",
                "limit": 5,
            },
            timeout=10,
        )
        assert search_for_evaluator.status_code == 200
        evaluator_results = search_for_evaluator.json()["results"]

        # Find evaluator agent
        evaluator_agents = [
            r for r in evaluator_results if r["agent_type"] == "evaluator"
        ]
        assert len(evaluator_agents) > 0

        evaluator_agent = evaluator_agents[0]
        evaluator_queue = evaluator_agent["metadata"]["queue_name"]

        # Step 6: Enqueue task to Evaluator queue (completing the chain)
        evaluator_queue_obj = Queue(evaluator_queue, connection=redis_conn)
        evaluator_queue_obj.empty()

        evaluator_job = evaluator_queue_obj.enqueue(
            "agents_common.lifecycle.process_agent_task",
            {
                "task_id": "chain-test-002",
                "task_type": "evaluate_cv",
                "payload": {"parsed_cv": {"name": "Test", "skills": ["Python"]}},
                "intent": "Evaluate CV for job match",
                "steps_completed": ["ocr", "parser"],
            },
            job_timeout="15m",
        )

        assert evaluator_job is not None
        assert evaluator_queue_obj.count == 1

        # Verify the full chain: OCR → Parser → Evaluator
        # Each step was discovered via /search and enqueued to correct queue
        assert parser_job.args[0]["steps_completed"] == ["ocr"]
        assert evaluator_job.args[0]["steps_completed"] == ["ocr", "parser"]

    def test_metadata_queue_name_propagation(
        self, registry_url, wait_for_services, ocr_agent_manifest
    ):
        """Verify queue_name in metadata is properly returned by /search"""
        # Register agent
        requests.post(f"{registry_url}/register", json=ocr_agent_manifest, timeout=10)

        # Search for agent
        search_resp = requests.post(
            f"{registry_url}/search",
            json={"query": "OCR", "mode": "semantic", "limit": 5},
            timeout=10,
        )

        results = search_resp.json()["results"]
        ocr_results = [
            r for r in results if r["agent_id"] == "ocr-integration-test-001"
        ]

        assert len(ocr_results) == 1
        ocr_result = ocr_results[0]

        # Verify metadata contains queue_name
        assert "metadata" in ocr_result
        assert "queue_name" in ocr_result["metadata"]
        assert ocr_result["metadata"]["queue_name"] == "queue-ocr-test"

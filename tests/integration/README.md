# Integration Tests

This directory contains integration tests that verify the full AOA-Talk system functionality with real services (Registry, Redis, Postgres).

## Purpose

These tests verify:
1. **Registry /search endpoint** returns properly structured SearchResponse with results
2. **Agent registration and discovery** works end-to-end
3. **enqueue_to_next_agent()** correctly interprets registry search responses
4. **RQ job enqueueing** creates valid jobs in Redis
5. **Agent chaining** (OCR → Parser → Evaluator) functions correctly

## Requirements

### Services
The following Docker services must be running:
- PostgreSQL with pgvector
- Redis
- Registry service

### Starting Services

```bash
# Start required services
docker-compose up -d postgres redis registry

# Wait for services to be healthy
docker-compose ps
```

## Running Integration Tests

### Option 1: Run all integration tests
```bash
INTEGRATION_TEST=true pytest tests/integration/ -v
```

### Option 2: Run specific test classes
```bash
INTEGRATION_TEST=true pytest tests/integration/test_registry_discovery_integration.py::TestRegistrySearchEndpoint -v
```

### Option 3: Run specific test
```bash
INTEGRATION_TEST=true pytest tests/integration/test_registry_discovery_integration.py::TestAgentChaining::test_ocr_to_parser_to_evaluator_chain -v
```

## Test Structure

### TestRegistrySearchEndpoint
- `test_search_endpoint_structure`: Verifies /search returns properly structured SearchResponse
- `test_search_returns_registered_agents`: Confirms registered agents are discoverable

### TestEnqueueToNextAgent
- `test_discover_next_agent_response_parsing`: Verifies response['results'] parsing
- `test_enqueue_to_next_agent_with_redis`: Confirms RQ jobs are created in Redis

### TestAgentChaining
- `test_ocr_to_parser_to_evaluator_chain`: Full workflow integration test
- `test_metadata_queue_name_propagation`: Verifies queue_name in metadata

## Environment Variables

- `INTEGRATION_TEST=true` - Required to run integration tests (default: skip)
- `REGISTRY_URL` - Registry service URL (default: http://localhost:8001)
- `REDIS_URL` - Redis connection URL (default: redis://localhost:6379/0)

## CI/CD Integration

Integration tests are skipped by default in CI/CD pipelines. To enable:

```yaml
- name: Run Integration Tests
  run: |
    docker-compose up -d postgres redis registry
    INTEGRATION_TEST=true pytest tests/integration/ -v
  env:
    REGISTRY_URL: http://localhost:8001
    REDIS_URL: redis://localhost:6379/0
```

## Troubleshooting

### Services not starting
```bash
# Check service logs
docker-compose logs registry
docker-compose logs redis
docker-compose logs postgres

# Restart services
docker-compose restart registry redis
```

### Test failures
1. Ensure all services are healthy: `docker-compose ps`
2. Check registry health: `curl http://localhost:8001/health`
3. Check Redis connectivity: `redis-cli ping`
4. Review test output for specific error messages

### Clean state
```bash
# Clear Redis data
redis-cli FLUSHALL

# Reset database
docker-compose down -v
docker-compose up -d postgres redis registry
```

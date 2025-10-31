# Integration Test Setup Guide

This guide explains how to run the AOA integration tests after the recent embeddings implementation.

## What Was Implemented

The registry service now supports full semantic search with automatic embedding generation:

1. **Automatic Embedding Generation** - When agents register, their descriptions and capabilities are automatically embedded using `sentence-transformers/all-MiniLM-L6-v2`
2. **Semantic Search** - The `/search` endpoint now performs real vector similarity search using cosine similarity
3. **Metadata Propagation** - Agent metadata (including `queue_name`) is properly stored and returned in search results

## Prerequisites

### 1. Rebuild the Registry Container

The registry container needs to be rebuilt to include the new dependencies (sentence-transformers, torch):

```bash
# From the repository root
docker-compose build registry
```

**Note:** The first build will download the sentence-transformers model (~80MB) which will be cached in the HuggingFace cache volume.

### 2. Start Required Services

```bash
# Start all required services
docker-compose up -d postgres redis registry

# Wait for services to be healthy (30-60 seconds)
docker-compose ps

# Verify registry is healthy
curl http://localhost:8001/health
```

## Running Integration Tests

### Option 1: Run All Integration Tests

```bash
INTEGRATION_TEST=true pytest tests/integration/ -v
```

### Option 2: Run Specific Test Classes

```bash
# Test registry search endpoint
INTEGRATION_TEST=true pytest tests/integration/test_registry_discovery_integration.py::TestRegistrySearchEndpoint -v

# Test agent discovery and enqueueing
INTEGRATION_TEST=true pytest tests/integration/test_registry_discovery_integration.py::TestEnqueueToNextAgent -v

# Test full agent chaining
INTEGRATION_TEST=true pytest tests/integration/test_registry_discovery_integration.py::TestAgentChaining -v
```

### Option 3: Run a Specific Test

```bash
# Run the full OCR → Parser → Evaluator chain test
INTEGRATION_TEST=true pytest tests/integration/test_registry_discovery_integration.py::TestAgentChaining::test_ocr_to_parser_to_evaluator_chain -v
```

## Expected Test Results

All tests should pass with the new implementation:

- ✅ `test_search_endpoint_structure` - Verifies SearchResponse structure
- ✅ `test_search_returns_registered_agents` - Confirms semantic search works
- ✅ `test_discover_next_agent_response_parsing` - Validates metadata.queue_name
- ✅ `test_enqueue_to_next_agent_with_redis` - Verifies RQ job creation
- ✅ `test_ocr_to_parser_to_evaluator_chain` - Full workflow integration
- ✅ `test_metadata_queue_name_propagation` - Confirms queue_name is returned

## Troubleshooting

### Services Not Starting

```bash
# Check service logs
docker-compose logs registry
docker-compose logs redis
docker-compose logs postgres

# Restart services
docker-compose restart registry redis
```

### Test Failures

1. **Connection Errors**: Ensure services are healthy with `docker-compose ps`
2. **Registry Health**: Check `curl http://localhost:8001/health`
3. **Redis Connectivity**: Check `redis-cli ping`
4. **Database Issues**: Check `docker-compose logs postgres`

### Clean State

```bash
# Clear Redis data
redis-cli FLUSHALL

# Reset database
docker-compose down -v
docker-compose up -d postgres redis registry
```

### Model Download Issues

If the sentence-transformers model fails to download:

```bash
# Check registry logs
docker-compose logs registry

# The model will be automatically downloaded on first use
# It will be cached in ~/aoa/hf_cache for future use
```

## Performance Notes

- **First Registration**: Takes ~2-5 seconds as the embedding model loads
- **Subsequent Registrations**: Takes ~100-500ms for embedding generation
- **Search Queries**: Takes ~50-200ms depending on number of registered agents
- **Model Loading**: One-time initialization, cached for the lifetime of the service

## What to Capture

After tests pass, capture:

1. **Test Output**:
   ```bash
   INTEGRATION_TEST=true pytest tests/integration/ -v 2>&1 | tee test_results.log
   ```

2. **Service Logs**:
   ```bash
   docker-compose logs registry > registry_logs.txt
   ```

3. **Sample Search Results**:
   ```bash
   # Register a test agent
   curl -X POST http://localhost:8001/register -H "Content-Type: application/json" -d @tests/integration/sample_agent.json

   # Perform a search
   curl -X POST http://localhost:8001/search -H "Content-Type: application/json" \
     -d '{"query": "extract text from documents", "mode": "semantic", "limit": 5}' | jq .
   ```

## Architecture Notes

The implementation follows the design outlined in issue AOA-010:

- **Registration**: Agents self-register with capabilities, metadata (including queue_name) is stored
- **Embedding Generation**: Automatic using sentence-transformers, no manual embedding required
- **Search**: Real semantic search with cosine similarity ranking
- **Response Format**: Matches the expected structure with metadata.queue_name included

## Next Steps

After integration tests pass:

1. Test with actual agent containers (OCR, Parser, Evaluator)
2. Verify end-to-end workflow with real RQ workers
3. Monitor performance with multiple concurrent registrations and searches
4. Consider implementing pgvector native similarity search for better performance at scale

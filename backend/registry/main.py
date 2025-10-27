"""
AOA Registry Service
--------------------
FastAPI service for agent registration and discovery.
Provides semantic search via pgvector and graph queries via Apache AGE.
"""

import time
from typing import List
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
import os

from .models import (
    AgentManifest,
    SearchQuery,
    SearchResponse,
    SearchResult,
    Capability,
)
from .database import (
    DatabaseManager,
    AgentModel,
    CapabilityModel,
    EmbeddingModel,
)

# Initialize FastAPI app
app = FastAPI(
    title="AOA Registry Service",
    description="Agent registration and discovery service with semantic search",
    version="1.0.0",
)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://aoa:aoa@postgres:5432/aoa")
db_manager = DatabaseManager(DATABASE_URL)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    db_manager.init_db()


@app.on_event("shutdown")
async def shutdown_event():
    """Close database on shutdown"""
    db_manager.close()


def get_db_session():
    """Dependency to get database session"""
    db = db_manager.get_session()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def root():
    """Health check endpoint"""
    return {
        "message": "AOA Registry running",
        "service": "registry",
        "version": "1.0.0",
    }


@app.post("/register")
async def register_agent(
    manifest: AgentManifest, db: Session = Depends(get_db_session)
):
    """
    Register an Agentic Unit (AU) with its manifest.

    Accepts agent information including:
    - Agent identifier and metadata
    - Capability list
    - Semantic embedding vectors

    Returns:
        dict: Registration confirmation with agent_id
    """
    try:
        agent_data = manifest.agent

        # Check if agent already exists
        existing_agent = (
            db.query(AgentModel).filter_by(agent_id=agent_data.agent_id).first()
        )

        if existing_agent:
            # Update existing agent
            existing_agent.name = agent_data.name
            existing_agent.description = agent_data.description
            existing_agent.agent_type = agent_data.agent_type
            existing_agent.version = agent_data.version
            existing_agent.status = agent_data.status
            existing_agent.agent_metadata = agent_data.metadata

            # Delete old capabilities and embeddings
            db.query(CapabilityModel).filter_by(agent_id=existing_agent.id).delete()
            db.query(EmbeddingModel).filter_by(agent_id=existing_agent.id).delete()

            agent_model = existing_agent
        else:
            # Create new agent
            agent_model = AgentModel(
                agent_id=agent_data.agent_id,
                name=agent_data.name,
                description=agent_data.description,
                agent_type=agent_data.agent_type,
                version=agent_data.version,
                status=agent_data.status,
                agent_metadata=agent_data.metadata,
            )
            db.add(agent_model)
            db.flush()  # Flush to get the ID

        # Add capabilities
        for cap in agent_data.capabilities:
            capability_model = CapabilityModel(
                agent_id=agent_model.id,
                name=cap.name,
                description=cap.description,
                input_types=cap.input_types,
                output_types=cap.output_types,
                parameters=cap.parameters,
                capability_metadata=cap.metadata,
            )
            db.add(capability_model)

        # Add embedding if provided
        if agent_data.embedding:
            embedding_model = EmbeddingModel(
                agent_id=agent_model.id,
                vector=agent_data.embedding.vector,
                model=agent_data.embedding.model,
                dimension=agent_data.embedding.dimension,
            )
            db.add(embedding_model)

        db.commit()

        return {
            "status": "success",
            "message": "Agent registered successfully",
            "agent_id": agent_data.agent_id,
            "action": "updated" if existing_agent else "created",
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@app.post("/search", response_model=SearchResponse)
async def search_agents(query: SearchQuery, db: Session = Depends(get_db_session)):
    """
    Search for agents using semantic or graph-based discovery.

    Supports three search modes:
    - semantic: Vector similarity search using pgvector
    - graph: Graph-based search using Apache AGE (placeholder for now)
    - hybrid: Combination of semantic and graph search

    Args:
        query: Search query with mode, text, and filters

    Returns:
        SearchResponse: List of matching agents with similarity scores
    """
    start_time = time.time()

    try:
        if query.mode in ["semantic", "hybrid"]:
            results = await _semantic_search(db, query)
        elif query.mode == "graph":
            results = await _graph_search(db, query)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid search mode: {query.mode}. Use 'semantic', 'graph', or 'hybrid'",
            )

        execution_time = (time.time() - start_time) * 1000  # Convert to ms

        return SearchResponse(
            query=query.query,
            mode=query.mode,
            results=results,
            total=len(results),
            execution_time_ms=execution_time,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


async def _semantic_search(db: Session, query: SearchQuery) -> List[SearchResult]:
    """
    Perform semantic search using pgvector.

    This is a simplified implementation. In production, you would:
    1. Generate embedding for the query text using the same model
    2. Use pgvector's similarity search to find closest matches
    """
    # For now, return all active agents (since we don't have embedding generation)
    # In production, you'd compute query embedding and use vector similarity

    agents = db.query(AgentModel).filter_by(status="active").limit(query.limit).all()

    results = []
    for agent in agents:
        # Load capabilities
        capabilities = db.query(CapabilityModel).filter_by(agent_id=agent.id).all()

        cap_list = [
            Capability(
                name=cap.name,
                description=cap.description,
                input_types=cap.input_types or [],
                output_types=cap.output_types or [],
                parameters=cap.parameters or {},
                metadata=cap.capability_metadata or {},
            )
            for cap in capabilities
        ]

        results.append(
            SearchResult(
                agent_id=agent.agent_id,
                name=agent.name,
                description=agent.description,
                agent_type=agent.agent_type,
                capabilities=cap_list,
                similarity_score=0.85,  # Placeholder score
                metadata=agent.agent_metadata or {},
            )
        )

    return results


async def _graph_search(db: Session, query: SearchQuery) -> List[SearchResult]:
    """
    Perform graph-based search using Apache AGE.

    This is a placeholder implementation. In production, you would:
    1. Connect to Apache AGE database
    2. Execute Cypher-like queries for graph traversal
    3. Find agents based on relationship patterns
    """
    # For now, return simple query results
    # In production, integrate with Apache AGE for graph queries

    agents = db.query(AgentModel).filter_by(status="active").limit(query.limit).all()

    results = []
    for agent in agents:
        capabilities = db.query(CapabilityModel).filter_by(agent_id=agent.id).all()

        cap_list = [
            Capability(
                name=cap.name,
                description=cap.description,
                input_types=cap.input_types or [],
                output_types=cap.output_types or [],
                parameters=cap.parameters or {},
                metadata=cap.capability_metadata or {},
            )
            for cap in capabilities
        ]

        results.append(
            SearchResult(
                agent_id=agent.agent_id,
                name=agent.name,
                description=agent.description,
                agent_type=agent.agent_type,
                capabilities=cap_list,
                similarity_score=None,  # No similarity score for graph search
                metadata=agent.agent_metadata or {},
            )
        )

    return results


@app.get("/agents/{agent_id}")
async def get_agent(agent_id: str, db: Session = Depends(get_db_session)):
    """
    Retrieve a specific agent by ID.

    Args:
        agent_id: Unique agent identifier

    Returns:
        dict: Agent information with capabilities
    """
    agent = db.query(AgentModel).filter_by(agent_id=agent_id).first()

    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    capabilities = db.query(CapabilityModel).filter_by(agent_id=agent.id).all()

    return {
        "agent_id": agent.agent_id,
        "name": agent.name,
        "description": agent.description,
        "agent_type": agent.agent_type,
        "version": agent.version,
        "status": agent.status,
        "capabilities": [
            {
                "name": cap.name,
                "description": cap.description,
                "input_types": cap.input_types,
                "output_types": cap.output_types,
                "parameters": cap.parameters,
                "metadata": cap.capability_metadata,
            }
            for cap in capabilities
        ],
        "metadata": agent.agent_metadata,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
    }


@app.get("/health")
async def health_check():
    """Service health check"""
    return {
        "status": "healthy",
        "service": "aoa-registry",
        "version": "1.0.0",
    }

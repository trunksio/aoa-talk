"""
Registry Service Data Models
-----------------------------
Pydantic models for agent manifests, capabilities, and embeddings.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class Capability(BaseModel):
    """Model for agent capability description"""

    name: str = Field(..., description="Capability name")
    description: str = Field(..., description="Capability description")
    input_types: List[str] = Field(
        default_factory=list, description="Supported input types"
    )
    output_types: List[str] = Field(
        default_factory=list, description="Supported output types"
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Capability parameters"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class Embedding(BaseModel):
    """Model for semantic embeddings"""

    vector: List[float] = Field(..., description="Embedding vector")
    model: str = Field(default="all-MiniLM-L6-v2", description="Embedding model used")
    dimension: int = Field(default=384, description="Vector dimension")


class Agent(BaseModel):
    """Model for Agentic Unit (AU)"""

    agent_id: str = Field(..., description="Unique agent identifier")
    name: str = Field(..., description="Agent name")
    description: str = Field(..., description="Agent description")
    agent_type: str = Field(..., description="Type of agent")
    capabilities: List[Capability] = Field(
        default_factory=list, description="List of agent capabilities"
    )
    embedding: Optional[Embedding] = Field(
        None, description="Semantic embedding for discovery"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    version: str = Field(default="1.0.0", description="Agent version")
    status: str = Field(default="active", description="Agent status")


class AgentManifest(BaseModel):
    """Model for agent registration manifest"""

    agent: Agent = Field(..., description="Agent information")
    registration_timestamp: Optional[datetime] = Field(
        None, description="Registration timestamp"
    )


class SearchQuery(BaseModel):
    """Model for agent search queries"""

    query: str = Field(..., description="Search query text")
    mode: str = Field(
        default="semantic",
        description="Search mode: 'semantic', 'graph', or 'hybrid'",
    )
    limit: int = Field(default=10, ge=1, le=100, description="Maximum results")
    filters: Dict[str, Any] = Field(
        default_factory=dict, description="Optional filters"
    )


class SearchResult(BaseModel):
    """Model for search result"""

    agent_id: str
    name: str
    description: str
    agent_type: str
    capabilities: List[Capability]
    similarity_score: Optional[float] = Field(
        None, description="Similarity score (0-1)"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Model for search response"""

    query: str
    mode: str
    results: List[SearchResult]
    total: int
    execution_time_ms: float

"""
Database utilities and connection management
"""

from contextlib import contextmanager
from typing import Generator, List, Optional, Dict, Any
import numpy as np
from sqlalchemy import create_engine, text, Column, Integer, String, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pgvector.sqlalchemy import Vector

from .config import get_settings
from .logging import get_logger

logger = get_logger(__name__)

Base = declarative_base()


class AgentRegistryModel(Base):
    """SQLAlchemy model for agent registry"""

    __tablename__ = "agent_registry"

    id = Column(Integer, primary_key=True)
    agent_id = Column(String(255), unique=True, nullable=False)
    agent_type = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    capabilities = Column(JSON)
    queue_name = Column(String(255), nullable=False)
    status = Column(String(50), default="active")
    semantic_embedding = Column(Vector(384))
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    last_heartbeat = Column(DateTime)
    agent_metadata = Column(JSON, default={})


class DatabaseManager:
    """Database connection and session management"""

    def __init__(self, database_url: Optional[str] = None):
        settings = get_settings()
        self.database_url = database_url or str(settings.database_url)
        self.engine = create_engine(
            self.database_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )
        logger.info("Database manager initialized", database_url=self.database_url)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Context manager for database sessions"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error("Database session error", error=str(e))
            raise
        finally:
            session.close()

    def register_agent(
        self,
        agent_id: str,
        agent_type: str,
        name: str,
        description: str,
        capabilities: Dict[str, Any],
        queue_name: str,
        semantic_embedding: Optional[np.ndarray] = None,
    ) -> bool:
        """Register an agent in the database"""
        try:
            with self.get_session() as session:
                # Check if agent exists
                existing = (
                    session.query(AgentRegistryModel)
                    .filter_by(agent_id=agent_id)
                    .first()
                )

                if existing:
                    # Update existing
                    existing.name = name
                    existing.description = description
                    existing.capabilities = capabilities
                    existing.queue_name = queue_name
                    existing.status = "active"
                    if semantic_embedding is not None:
                        existing.semantic_embedding = semantic_embedding.tolist()
                    session.execute(
                        text("UPDATE agent_registry SET last_heartbeat = NOW() WHERE agent_id = :agent_id"),
                        {"agent_id": agent_id}
                    )
                else:
                    # Create new
                    agent = AgentRegistryModel(
                        agent_id=agent_id,
                        agent_type=agent_type,
                        name=name,
                        description=description,
                        capabilities=capabilities,
                        queue_name=queue_name,
                        status="active",
                        semantic_embedding=semantic_embedding.tolist() if semantic_embedding is not None else None,
                    )
                    session.add(agent)

                session.commit()
                logger.info("Agent registered", agent_id=agent_id, agent_type=agent_type)
                return True

        except Exception as e:
            logger.error("Failed to register agent", agent_id=agent_id, error=str(e))
            return False

    def find_agents_by_capability(
        self, capability_query: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find agents by semantic similarity to capability query.

        Note: This is a simplified version that doesn't use embeddings yet.
        For semantic search, use search_agents_by_capability with embedding vector.
        """
        try:
            with self.get_session() as session:
                agents = (
                    session.query(AgentRegistryModel)
                    .filter_by(status="active")
                    .limit(limit)
                    .all()
                )

                return [
                    {
                        "agent_id": agent.agent_id,
                        "agent_type": agent.agent_type,
                        "name": agent.name,
                        "description": agent.description,
                        "queue_name": agent.queue_name,
                        "capabilities": agent.capabilities,
                    }
                    for agent in agents
                ]
        except Exception as e:
            logger.error("Failed to find agents", error=str(e))
            return []

    def search_agents_by_capability(
        self, query_embedding, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search agents using vector similarity on semantic embeddings.

        Args:
            query_embedding: numpy array or list of floats (384-dim)
            limit: Maximum number of results to return

        Returns:
            List of agent dictionaries sorted by similarity (best match first)
        """
        try:
            with self.get_session() as session:
                from sqlalchemy import text

                # Convert embedding to string format for pgvector
                embedding_str = '[' + ','.join(str(x) for x in query_embedding) + ']'

                # Use pgvector's <=> operator for cosine distance
                query = text("""
                    SELECT agent_id, agent_type, name, description, queue_name, capabilities,
                           semantic_embedding <=> CAST(:embedding AS vector) AS distance
                    FROM agent_registry
                    WHERE status = 'active'
                    ORDER BY distance
                    LIMIT :limit
                """)

                result = session.execute(query, {"embedding": embedding_str, "limit": limit})

                agents = []
                for row in result:
                    agents.append({
                        "agent_id": row[0],
                        "agent_type": row[1],
                        "name": row[2],
                        "description": row[3],
                        "queue_name": row[4],
                        "capabilities": row[5],
                        "similarity_score": 1.0 - row[6]  # Convert distance to similarity
                    })

                return agents

        except Exception as e:
            logger.error("Failed to search agents by capability", error=str(e))
            return []

    def update_heartbeat(self, agent_id: str) -> bool:
        """Update agent heartbeat timestamp"""
        try:
            with self.get_session() as session:
                session.execute(
                    text("UPDATE agent_registry SET last_heartbeat = NOW() WHERE agent_id = :agent_id"),
                    {"agent_id": agent_id}
                )
                session.commit()
                return True
        except Exception as e:
            logger.error("Failed to update heartbeat", agent_id=agent_id, error=str(e))
            return False


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Get global database manager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager

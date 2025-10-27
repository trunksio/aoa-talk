"""
Registry Service Database Models
---------------------------------
SQLAlchemy models for storing agents, capabilities, and embeddings.
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    JSON,
    ForeignKey,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, Session
from pgvector.sqlalchemy import Vector

Base = declarative_base()


class AgentModel(Base):
    """SQLAlchemy model for Agentic Units"""

    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    agent_type = Column(String(100), nullable=False, index=True)
    version = Column(String(50), default="1.0.0")
    status = Column(String(50), default="active", index=True)
    agent_metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    capabilities = relationship(
        "CapabilityModel", back_populates="agent", cascade="all, delete-orphan"
    )
    embeddings = relationship(
        "EmbeddingModel", back_populates="agent", cascade="all, delete-orphan"
    )


class CapabilityModel(Base):
    """SQLAlchemy model for agent capabilities"""

    __tablename__ = "capabilities"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    input_types = Column(JSON, default=[])
    output_types = Column(JSON, default=[])
    parameters = Column(JSON, default={})
    capability_metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    agent = relationship("AgentModel", back_populates="capabilities")


class EmbeddingModel(Base):
    """SQLAlchemy model for semantic embeddings"""

    __tablename__ = "embeddings"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    vector = Column(Vector(384), nullable=False)  # pgvector column
    model = Column(String(100), default="all-MiniLM-L6-v2")
    dimension = Column(Integer, default=384)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    agent = relationship("AgentModel", back_populates="embeddings")


class DatabaseManager:
    """Database connection and session management for Registry Service"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(
            database_url, pool_pre_ping=True, pool_size=10, max_overflow=20
        )
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

    def init_db(self):
        """Initialize database tables"""
        Base.metadata.create_all(bind=self.engine)

    def get_session(self) -> Session:
        """Get a database session"""
        return self.SessionLocal()

    def close(self):
        """Close database engine"""
        self.engine.dispose()


# Dependency for FastAPI
def get_db(db_manager: DatabaseManager):
    """Dependency to get database session"""
    db = db_manager.get_session()
    try:
        yield db
    finally:
        db.close()

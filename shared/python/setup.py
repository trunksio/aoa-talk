from setuptools import setup, find_packages

setup(
    name="cavia-common",
    version="0.1.0",
    description="Common utilities for CAVIA Agent Oriented Architecture",
    author="CAVIA Team",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "pydantic>=2.5.0",
        "pydantic-settings>=2.1.0",
        "psycopg2-binary>=2.9.9",
        "sqlalchemy>=2.0.0",
        "pgvector>=0.2.4",
        "redis>=4.5.0,<5.0.0",  # Pin to 4.x for RQ 2.6.0 compatibility
        "rq>=1.15.1",
        "minio>=7.2.0",
        "requests>=2.31.0",  # HTTP calls to agent-registry service
        "instructor>=1.0.0",  # Structured LLM outputs with Pydantic validation
        "httpx>=0.25.2",
        "tenacity>=8.2.3",
        "structlog>=24.1.0",
        "python-json-logger>=2.0.7",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "pytest-cov>=4.1.0",
            "black>=23.12.1",
            "ruff>=0.1.8",
        ]
    },
)

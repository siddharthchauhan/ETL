"""
SDTM Pipeline Configuration
===========================
Configuration for LangSmith, Neo4j, and S3 integration.
"""

import os
from dotenv import load_dotenv

load_dotenv()


def configure_langsmith():
    """Configure LangSmith for observability and tracing."""
    # Set LangSmith environment variables
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = "sdtm-pipeline"
    os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"

    # API Key from environment or default
    langchain_api_key = os.getenv(
        "LANGCHAIN_API_KEY",
        "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"
    )
    os.environ["LANGCHAIN_API_KEY"] = langchain_api_key

    print(f"LangSmith configured:")
    print(f"  Project: sdtm-pipeline")
    print(f"  Tracing: enabled")
    print(f"  Endpoint: https://api.smith.langchain.com")


def get_neo4j_config():
    """Get Neo4j configuration."""
    return {
        "uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        "user": os.getenv("NEO4J_USER", "neo4j"),
        "password": os.getenv("NEO4J_PASSWORD", "password123"),
        "database": os.getenv("NEO4J_DATABASE", "neo4j")
    }


def get_s3_config():
    """Get S3 configuration."""
    return {
        "bucket": os.getenv("S3_ETL_BUCKET", "s3dcri"),
        "region": os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
        "access_key": os.getenv("AWS_ACCESS_KEY_ID"),
        "secret_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
        "processed_prefix": "processed/sdtm"
    }


def get_tavily_config():
    """Get Tavily configuration for web search."""
    return {
        "api_key": os.getenv(
            "TAVILY_API_KEY",
            "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"
        )
    }


def get_pinecone_config():
    """Get Pinecone configuration for vector search."""
    return {
        "api_key": os.getenv(
            "PINECONE_API_KEY",
            "pcsk_6Zyakv_9V88QT2992tryFxu9JBpXnj1Pk2MoT3K4LiHfJRVaoDLDCEK4P2VzPq9zm2LfeE"
        ),
        "environment": os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
    }

"""
Neo4j Data Loader Module
========================

This module provides utilities for loading data into Neo4j graph database
as part of the ETL pipeline. It handles:

1. Connection management with connection pooling
2. Batch data loading with transactions
3. Schema management (constraints, indexes)
4. Error handling and retry logic
5. Performance optimization

Neo4j Version: 5.x compatible
Driver Version: neo4j 5.27.0

Author: ETL Orchestration Guide
Version: 1.0.0
"""

from datetime import datetime
from typing import Any, Optional, Generator
from contextlib import contextmanager
import logging
import time

from neo4j import GraphDatabase, Session, Transaction, Result
from neo4j.exceptions import (
    ServiceUnavailable,
    SessionExpired,
    TransientError,
    ConstraintError,
    ClientError
)
from pydantic import BaseModel, Field
import structlog

# Configure logging
logger = structlog.get_logger()


# =============================================================================
# CONFIGURATION MODELS
# =============================================================================

class Neo4jConfig(BaseModel):
    """Neo4j connection configuration."""
    uri: str = Field(default="bolt://localhost:7687")
    user: str = Field(default="neo4j")
    password: str = Field(default="password")
    database: str = Field(default="neo4j")
    max_connection_pool_size: int = Field(default=50)
    connection_timeout: int = Field(default=30)
    max_transaction_retry_time: int = Field(default=30)


class LoadResult(BaseModel):
    """Result of a load operation."""
    success: bool
    nodes_created: int = 0
    nodes_updated: int = 0
    relationships_created: int = 0
    relationships_updated: int = 0
    constraints_created: int = 0
    indexes_created: int = 0
    errors: list[str] = Field(default_factory=list)
    duration_seconds: float = 0.0
    loaded_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class BatchResult(BaseModel):
    """Result of a batch operation."""
    batch_id: str
    success: bool
    records_processed: int = 0
    errors: list[str] = Field(default_factory=list)


# =============================================================================
# NEO4J LOADER CLASS
# =============================================================================

class Neo4jLoader:
    """
    Neo4j data loader with connection pooling and batch operations.

    Features:
    - Connection pooling for efficient resource usage
    - Batch loading with configurable batch sizes
    - Automatic retry on transient errors
    - Schema management (constraints, indexes)
    - Transaction management
    """

    def __init__(self, config: Neo4jConfig):
        """
        Initialize Neo4j loader.

        Args:
            config: Neo4j configuration object
        """
        self.config = config
        self._driver = None

    @property
    def driver(self):
        """Lazy initialization of Neo4j driver."""
        if self._driver is None:
            logger.info("Initializing Neo4j driver",
                        uri=self.config.uri,
                        database=self.config.database)

            self._driver = GraphDatabase.driver(
                self.config.uri,
                auth=(self.config.user, self.config.password),
                max_connection_pool_size=self.config.max_connection_pool_size,
                connection_timeout=self.config.connection_timeout,
                max_transaction_retry_time=self.config.max_transaction_retry_time
            )

        return self._driver

    def close(self):
        """Close the Neo4j driver and release resources."""
        if self._driver is not None:
            self._driver.close()
            self._driver = None
            logger.info("Neo4j driver closed")

    def verify_connectivity(self) -> bool:
        """
        Verify connection to Neo4j database.

        Returns:
            True if connection is successful
        """
        try:
            self.driver.verify_connectivity()
            logger.info("Neo4j connectivity verified")
            return True
        except ServiceUnavailable as e:
            logger.error("Neo4j service unavailable", error=str(e))
            return False
        except Exception as e:
            logger.error("Neo4j connectivity check failed", error=str(e))
            return False

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """
        Context manager for Neo4j session.

        Yields:
            Neo4j session
        """
        session = self.driver.session(database=self.config.database)
        try:
            yield session
        finally:
            session.close()

    # =========================================================================
    # SCHEMA MANAGEMENT
    # =========================================================================

    def create_constraint(
        self,
        label: str,
        property_name: str,
        constraint_type: str = "unique"
    ) -> bool:
        """
        Create a constraint on a node label.

        Args:
            label: Node label
            property_name: Property to constrain
            constraint_type: Type of constraint (unique, exists)

        Returns:
            True if constraint created or already exists
        """
        constraint_name = f"{label.lower()}_{property_name.lower()}_{constraint_type}"

        if constraint_type == "unique":
            query = f"""
                CREATE CONSTRAINT {constraint_name} IF NOT EXISTS
                FOR (n:{label}) REQUIRE n.{property_name} IS UNIQUE
            """
        elif constraint_type == "exists":
            query = f"""
                CREATE CONSTRAINT {constraint_name} IF NOT EXISTS
                FOR (n:{label}) REQUIRE n.{property_name} IS NOT NULL
            """
        else:
            logger.warning("Unsupported constraint type", type=constraint_type)
            return False

        try:
            with self.session() as session:
                session.run(query)
                logger.info("Constraint created",
                            constraint=constraint_name,
                            label=label,
                            property=property_name)
                return True
        except ClientError as e:
            if "already exists" in str(e).lower():
                logger.info("Constraint already exists", constraint=constraint_name)
                return True
            logger.error("Failed to create constraint", error=str(e))
            return False

    def create_index(
        self,
        label: str,
        properties: list[str],
        index_type: str = "range"
    ) -> bool:
        """
        Create an index on node properties.

        Args:
            label: Node label
            properties: Properties to index
            index_type: Type of index (range, text, fulltext)

        Returns:
            True if index created or already exists
        """
        props_str = "_".join(properties)
        index_name = f"idx_{label.lower()}_{props_str}"

        if index_type == "range":
            props_list = ", ".join([f"n.{p}" for p in properties])
            query = f"""
                CREATE INDEX {index_name} IF NOT EXISTS
                FOR (n:{label}) ON ({props_list})
            """
        elif index_type == "text":
            if len(properties) != 1:
                logger.warning("Text index requires exactly one property")
                return False
            query = f"""
                CREATE TEXT INDEX {index_name} IF NOT EXISTS
                FOR (n:{label}) ON (n.{properties[0]})
            """
        elif index_type == "fulltext":
            props_list = ", ".join([f"n.{p}" for p in properties])
            query = f"""
                CREATE FULLTEXT INDEX {index_name} IF NOT EXISTS
                FOR (n:{label}) ON EACH [{props_list}]
            """
        else:
            logger.warning("Unsupported index type", type=index_type)
            return False

        try:
            with self.session() as session:
                session.run(query)
                logger.info("Index created",
                            index=index_name,
                            label=label,
                            properties=properties)
                return True
        except ClientError as e:
            if "already exists" in str(e).lower():
                logger.info("Index already exists", index=index_name)
                return True
            logger.error("Failed to create index", error=str(e))
            return False

    def setup_schema(self, node_definitions: list[dict]) -> dict:
        """
        Set up database schema based on node definitions.

        Args:
            node_definitions: List of node definition dicts with:
                - label: Node label
                - properties: List of property names
                - unique_constraint: Property for unique constraint
                - indexes: List of index definitions

        Returns:
            Schema setup results
        """
        results = {
            "constraints_created": 0,
            "indexes_created": 0,
            "errors": []
        }

        for node_def in node_definitions:
            label = node_def.get("label")
            if not label:
                continue

            # Create unique constraint
            unique_prop = node_def.get("unique_constraint")
            if unique_prop:
                if self.create_constraint(label, unique_prop, "unique"):
                    results["constraints_created"] += 1
                else:
                    results["errors"].append(
                        f"Failed to create constraint on {label}.{unique_prop}"
                    )

            # Create indexes
            index_props = node_def.get("indexes", [])
            for index_def in index_props:
                if isinstance(index_def, str):
                    # Simple single-property index
                    if self.create_index(label, [index_def]):
                        results["indexes_created"] += 1
                elif isinstance(index_def, dict):
                    # Complex index definition
                    props = index_def.get("properties", [])
                    idx_type = index_def.get("type", "range")
                    if props and self.create_index(label, props, idx_type):
                        results["indexes_created"] += 1

        logger.info("Schema setup complete", **results)
        return results

    # =========================================================================
    # DATA LOADING
    # =========================================================================

    def _execute_with_retry(
        self,
        session: Session,
        query: str,
        parameters: dict = None,
        max_retries: int = 3
    ) -> Optional[Result]:
        """
        Execute a query with retry logic for transient errors.

        Args:
            session: Neo4j session
            query: Cypher query
            parameters: Query parameters
            max_retries: Maximum retry attempts

        Returns:
            Query result or None on failure
        """
        retries = 0
        while retries < max_retries:
            try:
                result = session.run(query, parameters or {})
                return result
            except TransientError as e:
                retries += 1
                wait_time = 2 ** retries  # Exponential backoff
                logger.warning("Transient error, retrying",
                               error=str(e),
                               retry=retries,
                               wait_seconds=wait_time)
                time.sleep(wait_time)
            except SessionExpired:
                logger.warning("Session expired, reconnecting")
                retries += 1
                time.sleep(1)
            except Exception as e:
                logger.error("Query execution failed", error=str(e))
                return None

        logger.error("Max retries exceeded")
        return None

    def merge_nodes(
        self,
        label: str,
        records: list[dict],
        id_property: str = "id",
        batch_size: int = 1000
    ) -> LoadResult:
        """
        Merge (upsert) nodes into the database.

        Uses UNWIND for efficient batch processing.

        Args:
            label: Node label
            records: List of record dictionaries
            id_property: Property to use for matching
            batch_size: Records per transaction

        Returns:
            LoadResult with operation statistics
        """
        start_time = time.time()
        result = LoadResult(success=True)

        if not records:
            logger.warning("No records to load")
            return result

        # Batch MERGE query using UNWIND
        query = f"""
            UNWIND $batch AS row
            MERGE (n:{label} {{{id_property}: row.{id_property}}})
            SET n += row
            RETURN count(n) AS count
        """

        total_processed = 0
        with self.session() as session:
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]

                try:
                    query_result = self._execute_with_retry(
                        session, query, {"batch": batch}
                    )

                    if query_result:
                        summary = query_result.consume()
                        created = summary.counters.nodes_created
                        result.nodes_created += created
                        result.nodes_updated += len(batch) - created
                        total_processed += len(batch)

                        logger.debug("Batch processed",
                                     batch_num=i // batch_size,
                                     records=len(batch),
                                     created=created)
                    else:
                        result.errors.append(f"Batch {i // batch_size} failed")
                        result.success = False

                except ConstraintError as e:
                    result.errors.append(f"Constraint violation: {str(e)}")
                    result.success = False
                except Exception as e:
                    result.errors.append(f"Unexpected error: {str(e)}")
                    result.success = False

        result.duration_seconds = round(time.time() - start_time, 2)

        logger.info("Node merge complete",
                    label=label,
                    total_records=len(records),
                    created=result.nodes_created,
                    updated=result.nodes_updated,
                    duration=result.duration_seconds)

        return result

    def create_relationships(
        self,
        relationship_type: str,
        relationships: list[dict],
        from_label: str,
        to_label: str,
        from_id_property: str = "id",
        to_id_property: str = "id",
        batch_size: int = 1000
    ) -> LoadResult:
        """
        Create relationships between nodes.

        Args:
            relationship_type: Relationship type (e.g., "KNOWS", "WORKS_FOR")
            relationships: List of relationship dicts with from_id, to_id, and properties
            from_label: Source node label
            to_label: Target node label
            from_id_property: Property to match source nodes
            to_id_property: Property to match target nodes
            batch_size: Relationships per transaction

        Returns:
            LoadResult with operation statistics
        """
        start_time = time.time()
        result = LoadResult(success=True)

        if not relationships:
            logger.warning("No relationships to create")
            return result

        # Batch relationship creation query
        query = f"""
            UNWIND $batch AS row
            MATCH (a:{from_label} {{{from_id_property}: row.from_id}})
            MATCH (b:{to_label} {{{to_id_property}: row.to_id}})
            MERGE (a)-[r:{relationship_type}]->(b)
            SET r += row.properties
            RETURN count(r) AS count
        """

        with self.session() as session:
            for i in range(0, len(relationships), batch_size):
                batch = relationships[i:i + batch_size]

                # Ensure each relationship has a properties dict
                processed_batch = []
                for rel in batch:
                    processed_batch.append({
                        "from_id": rel.get("from_id"),
                        "to_id": rel.get("to_id"),
                        "properties": rel.get("properties", {})
                    })

                try:
                    query_result = self._execute_with_retry(
                        session, query, {"batch": processed_batch}
                    )

                    if query_result:
                        summary = query_result.consume()
                        created = summary.counters.relationships_created
                        result.relationships_created += created

                        logger.debug("Relationship batch processed",
                                     batch_num=i // batch_size,
                                     created=created)
                    else:
                        result.errors.append(f"Relationship batch {i // batch_size} failed")
                        result.success = False

                except Exception as e:
                    result.errors.append(f"Relationship error: {str(e)}")
                    result.success = False

        result.duration_seconds = round(time.time() - start_time, 2)

        logger.info("Relationship creation complete",
                    type=relationship_type,
                    created=result.relationships_created,
                    duration=result.duration_seconds)

        return result

    def execute_cypher(
        self,
        query: str,
        parameters: dict = None
    ) -> tuple[bool, Any]:
        """
        Execute an arbitrary Cypher query.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            Tuple of (success, result_data)
        """
        try:
            with self.session() as session:
                result = session.run(query, parameters or {})
                records = [dict(record) for record in result]
                return True, records
        except Exception as e:
            logger.error("Cypher execution failed", error=str(e))
            return False, str(e)

    def execute_cypher_queries(
        self,
        queries: list[str],
        parameters_list: list[dict] = None
    ) -> LoadResult:
        """
        Execute a list of Cypher queries in sequence.

        Args:
            queries: List of Cypher queries
            parameters_list: Optional list of parameter dicts (one per query)

        Returns:
            LoadResult with execution statistics
        """
        start_time = time.time()
        result = LoadResult(success=True)

        if not queries:
            return result

        parameters_list = parameters_list or [{}] * len(queries)

        with self.session() as session:
            for i, (query, params) in enumerate(zip(queries, parameters_list)):
                try:
                    query_result = self._execute_with_retry(session, query, params)

                    if query_result:
                        summary = query_result.consume()
                        result.nodes_created += summary.counters.nodes_created
                        result.nodes_updated += summary.counters.properties_set
                        result.relationships_created += summary.counters.relationships_created
                        result.constraints_created += summary.counters.constraints_added
                        result.indexes_created += summary.counters.indexes_added

                        logger.debug("Query executed",
                                     query_num=i,
                                     nodes_created=summary.counters.nodes_created)
                    else:
                        result.errors.append(f"Query {i} failed")
                        result.success = False

                except Exception as e:
                    result.errors.append(f"Query {i} error: {str(e)}")
                    result.success = False

        result.duration_seconds = round(time.time() - start_time, 2)

        logger.info("Cypher queries executed",
                    total_queries=len(queries),
                    success=result.success,
                    duration=result.duration_seconds)

        return result

    # =========================================================================
    # PIPELINE INTEGRATION
    # =========================================================================

    def load_from_agent_result(
        self,
        agent_result: dict,
        batch_size: int = 1000
    ) -> LoadResult:
        """
        Load data from LangGraph agent result into Neo4j.

        This method integrates with the ETL agent pipeline output format.

        Args:
            agent_result: Output from the LangGraph ETL agent
            batch_size: Records per batch

        Returns:
            Consolidated LoadResult
        """
        start_time = time.time()
        final_result = LoadResult(success=True)

        # Verify connectivity
        if not self.verify_connectivity():
            final_result.success = False
            final_result.errors.append("Failed to connect to Neo4j")
            return final_result

        # 1. Set up schema from graph model
        graph_model = agent_result.get("graph_model", {})
        node_definitions = graph_model.get("node_definitions", [])

        if node_definitions:
            schema_result = self.setup_schema(node_definitions)
            final_result.constraints_created = schema_result.get("constraints_created", 0)
            final_result.indexes_created = schema_result.get("indexes_created", 0)
            final_result.errors.extend(schema_result.get("errors", []))

        # 2. Execute Cypher queries
        cypher_queries = agent_result.get("cypher_queries", [])
        if cypher_queries:
            # Filter out queries that are just for schema (already handled)
            data_queries = [
                q for q in cypher_queries
                if not q.strip().upper().startswith(("CREATE CONSTRAINT", "CREATE INDEX"))
            ]

            if data_queries:
                query_result = self.execute_cypher_queries(data_queries)
                final_result.nodes_created += query_result.nodes_created
                final_result.nodes_updated += query_result.nodes_updated
                final_result.relationships_created += query_result.relationships_created
                final_result.errors.extend(query_result.errors)
                if not query_result.success:
                    final_result.success = False

        # 3. Load transformed data
        transformed_data = agent_result.get("transformed_data", {})
        batches = transformed_data.get("batches", [])

        # Determine label - use node definition or default to "Record"
        default_label = "Record"
        if node_definitions:
            default_label = node_definitions[0].get("label", "Record")

        # Load batches if present
        if batches:
            logger.info("Loading batches to Neo4j",
                        batch_count=len(batches),
                        label=default_label)

            for batch_info in batches:
                records = batch_info.get("records", [])
                if records:
                    load_result = self.merge_nodes(
                        label=default_label,
                        records=records,
                        batch_size=batch_size
                    )
                    final_result.nodes_created += load_result.nodes_created
                    final_result.nodes_updated += load_result.nodes_updated
                    final_result.errors.extend(load_result.errors)
                    if not load_result.success:
                        final_result.success = False
        else:
            # Try loading from files directly if no batches
            files = transformed_data.get("files", [])
            if files:
                logger.info("Loading files to Neo4j",
                            file_count=len(files),
                            label=default_label)

                for file_data in files:
                    records = file_data.get("records", [])
                    if records:
                        load_result = self.merge_nodes(
                            label=default_label,
                            records=records,
                            batch_size=batch_size
                        )
                        final_result.nodes_created += load_result.nodes_created
                        final_result.nodes_updated += load_result.nodes_updated
                        final_result.errors.extend(load_result.errors)
                        if not load_result.success:
                            final_result.success = False

        final_result.duration_seconds = round(time.time() - start_time, 2)

        logger.info("Agent result loaded to Neo4j",
                    success=final_result.success,
                    nodes_created=final_result.nodes_created,
                    relationships_created=final_result.relationships_created,
                    duration=final_result.duration_seconds)

        return final_result

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def get_database_stats(self) -> dict:
        """
        Get database statistics.

        Returns:
            Dictionary with node counts, relationship counts, etc.
        """
        stats = {}

        queries = [
            ("node_count", "MATCH (n) RETURN count(n) AS count"),
            ("relationship_count", "MATCH ()-[r]->() RETURN count(r) AS count"),
            ("label_counts", """
                CALL db.labels() YIELD label
                CALL apoc.cypher.run('MATCH (n:' + label + ') RETURN count(n) AS count', {})
                YIELD value
                RETURN label, value.count AS count
            """),
            ("relationship_type_counts", """
                CALL db.relationshipTypes() YIELD relationshipType
                RETURN relationshipType, 0 AS count
            """)
        ]

        with self.session() as session:
            for stat_name, query in queries:
                try:
                    result = session.run(query)

                    if stat_name in ["label_counts", "relationship_type_counts"]:
                        stats[stat_name] = {
                            record[0]: record[1] for record in result
                        }
                    else:
                        record = result.single()
                        stats[stat_name] = record["count"] if record else 0

                except Exception as e:
                    logger.warning(f"Failed to get {stat_name}", error=str(e))
                    stats[stat_name] = None

        return stats

    def clear_database(self, confirm: bool = False) -> bool:
        """
        Clear all data from the database.

        WARNING: This is destructive and cannot be undone!

        Args:
            confirm: Must be True to execute

        Returns:
            True if successful
        """
        if not confirm:
            logger.warning("clear_database called without confirmation")
            return False

        try:
            with self.session() as session:
                # Delete all relationships first
                session.run("MATCH ()-[r]->() DELETE r")
                # Delete all nodes
                session.run("MATCH (n) DELETE n")

            logger.warning("Database cleared")
            return True
        except Exception as e:
            logger.error("Failed to clear database", error=str(e))
            return False


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_loader(
    uri: str = None,
    user: str = None,
    password: str = None,
    database: str = None
) -> Neo4jLoader:
    """
    Factory function to create a Neo4j loader.

    Args:
        uri: Neo4j connection URI (default: from env or localhost)
        user: Database user (default: from env or neo4j)
        password: Database password (default: from env)
        database: Database name (default: neo4j)

    Returns:
        Configured Neo4jLoader instance
    """
    import os

    config = Neo4jConfig(
        uri=uri or os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        user=user or os.getenv("NEO4J_USER", "neo4j"),
        password=password or os.getenv("NEO4J_PASSWORD", "password"),
        database=database or os.getenv("NEO4J_DATABASE", "neo4j")
    )

    return Neo4jLoader(config)


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    from dotenv import load_dotenv

    # Load environment variables from .env file
    load_dotenv()

    # Example usage - uses environment variables by default
    loader = create_loader()

    try:
        # Verify connectivity
        if loader.verify_connectivity():
            print("Connected to Neo4j!")

            # Get stats
            stats = loader.get_database_stats()
            print(f"Database stats: {stats}")

            # Example: Load sample data
            sample_records = [
                {"id": "1", "name": "Alice", "type": "Person"},
                {"id": "2", "name": "Bob", "type": "Person"},
                {"id": "3", "name": "Acme Corp", "type": "Organization"}
            ]

            result = loader.merge_nodes(
                label="Entity",
                records=sample_records
            )

            print(f"Load result: {result.model_dump()}")

        else:
            print("Failed to connect to Neo4j")

    finally:
        loader.close()

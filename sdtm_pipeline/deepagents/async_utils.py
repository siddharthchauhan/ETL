"""
Async Utilities for SDTM Pipeline
=================================
Provides async wrappers for blocking operations to prevent
blocking the ASGI event loop in LangGraph.

This module wraps:
- Pandas read/write operations (via asyncio.to_thread)
- File system operations (via aiofiles)
- S3 operations (via aioboto3)
- Neo4j operations (via async driver)

Usage:
    from .async_utils import (
        async_read_csv,
        async_to_csv,
        async_s3_download,
        async_s3_upload,
        async_neo4j_query,
    )
"""

import os
import json
import asyncio
import zipfile
from typing import Dict, Any, List, Optional, Callable
from functools import wraps

import pandas as pd
import aiofiles
import aiofiles.os


# =============================================================================
# DECORATOR FOR CONVERTING SYNC TOOLS TO ASYNC
# =============================================================================

def async_tool(func: Callable) -> Callable:
    """
    Decorator to convert a synchronous tool function to async.

    Wraps the entire function execution in asyncio.to_thread() to prevent
    blocking the event loop. Use this for tools that perform I/O operations.

    Usage:
        @tool
        @async_tool
        def my_blocking_tool(arg: str) -> Dict[str, Any]:
            # blocking code here
            return {"result": "value"}
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await asyncio.to_thread(func, *args, **kwargs)
    return wrapper


# =============================================================================
# PANDAS ASYNC WRAPPERS
# =============================================================================

async def async_read_csv(file_path: str, **kwargs) -> pd.DataFrame:
    """
    Async wrapper for pandas read_csv.

    Runs pd.read_csv in a thread pool to avoid blocking the event loop.

    Args:
        file_path: Path to the CSV file
        **kwargs: Additional arguments passed to pd.read_csv

    Returns:
        DataFrame with the CSV contents
    """
    return await asyncio.to_thread(pd.read_csv, file_path, **kwargs)


async def async_to_csv(df: pd.DataFrame, file_path: str, **kwargs) -> None:
    """
    Async wrapper for DataFrame.to_csv.

    Args:
        df: DataFrame to save
        file_path: Output file path
        **kwargs: Additional arguments passed to to_csv
    """
    # Ensure directory exists
    dir_path = os.path.dirname(file_path)
    if dir_path:
        await aiofiles.os.makedirs(dir_path, exist_ok=True)

    await asyncio.to_thread(df.to_csv, file_path, **kwargs)


async def async_read_json(file_path: str) -> Dict[str, Any]:
    """
    Async JSON file reading.

    Args:
        file_path: Path to JSON file

    Returns:
        Parsed JSON as dictionary
    """
    async with aiofiles.open(file_path, 'r') as f:
        content = await f.read()
        return json.loads(content)


async def async_write_json(data: Dict[str, Any], file_path: str, indent: int = 2) -> None:
    """
    Async JSON file writing.

    Args:
        data: Dictionary to save
        file_path: Output file path
        indent: JSON indentation
    """
    dir_path = os.path.dirname(file_path)
    if dir_path:
        await aiofiles.os.makedirs(dir_path, exist_ok=True)

    async with aiofiles.open(file_path, 'w') as f:
        await f.write(json.dumps(data, indent=indent))


# =============================================================================
# FILE SYSTEM ASYNC WRAPPERS
# =============================================================================

async def async_makedirs(path: str, exist_ok: bool = True) -> None:
    """Async version of os.makedirs."""
    await aiofiles.os.makedirs(path, exist_ok=exist_ok)


async def async_getsize(path: str) -> int:
    """Async version of os.path.getsize."""
    stat_result = await aiofiles.os.stat(path)
    return stat_result.st_size


async def async_walk(directory: str) -> List[tuple]:
    """
    Async version of os.walk.

    Note: os.walk is inherently sequential, so we run it in a thread.

    Args:
        directory: Directory to walk

    Returns:
        List of (root, dirs, files) tuples
    """
    def _walk():
        return list(os.walk(directory))

    return await asyncio.to_thread(_walk)


async def async_extract_zip(zip_path: str, extract_dir: str) -> List[str]:
    """
    Async ZIP extraction.

    Args:
        zip_path: Path to ZIP file
        extract_dir: Directory to extract to

    Returns:
        List of extracted file paths
    """
    # Ensure extract directory exists
    await aiofiles.os.makedirs(extract_dir, exist_ok=True)

    def _extract():
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
            return zip_ref.namelist()

    # Run in thread since zipfile is blocking
    return await asyncio.to_thread(_extract)


# =============================================================================
# S3 ASYNC WRAPPERS (using aioboto3)
# =============================================================================

async def async_s3_download(bucket: str, key: str, local_path: str) -> Dict[str, Any]:
    """
    Async S3 file download using aioboto3.

    Args:
        bucket: S3 bucket name
        key: S3 object key
        local_path: Local file path to save to

    Returns:
        Download result with file info
    """
    import aioboto3

    # Ensure directory exists
    dir_path = os.path.dirname(local_path)
    if dir_path:
        await aiofiles.os.makedirs(dir_path, exist_ok=True)

    session = aioboto3.Session()
    async with session.client('s3') as s3:
        await s3.download_file(bucket, key, local_path)

    size = await async_getsize(local_path)
    return {
        "success": True,
        "local_path": local_path,
        "size_bytes": size,
    }


async def async_s3_upload(local_path: str, bucket: str, key: str) -> Dict[str, Any]:
    """
    Async S3 file upload using aioboto3.

    Args:
        local_path: Local file path
        bucket: S3 bucket name
        key: S3 object key

    Returns:
        Upload result with S3 URI
    """
    import aioboto3

    session = aioboto3.Session()
    async with session.client('s3') as s3:
        await s3.upload_file(local_path, bucket, key)

    return {
        "success": True,
        "s3_uri": f"s3://{bucket}/{key}",
    }


# =============================================================================
# NEO4J ASYNC WRAPPERS
# =============================================================================

async def async_neo4j_execute(
    uri: str,
    user: str,
    password: str,
    query: str,
    parameters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Async Neo4j query execution.

    Uses the async Neo4j driver for non-blocking database operations.

    Args:
        uri: Neo4j connection URI
        user: Database username
        password: Database password
        query: Cypher query to execute
        parameters: Query parameters

    Returns:
        List of result records as dictionaries
    """
    from neo4j import AsyncGraphDatabase

    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    try:
        async with driver.session() as session:
            result = await session.run(query, parameters or {})
            records = await result.data()
            return records
    finally:
        await driver.close()


async def async_neo4j_load_dataframe(
    df: pd.DataFrame,
    uri: str,
    user: str,
    password: str,
    label: str,
    batch_size: int = 1000,
) -> Dict[str, Any]:
    """
    Async load DataFrame to Neo4j as nodes.

    Args:
        df: DataFrame to load
        uri: Neo4j connection URI
        user: Database username
        password: Database password
        label: Node label (e.g., "SDTM_DM")
        batch_size: Records per batch

    Returns:
        Load result with node count
    """
    from neo4j import AsyncGraphDatabase

    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    records = df.to_dict(orient='records')
    total_created = 0

    try:
        async with driver.session() as session:
            # Process in batches
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]

                # Clean records (remove NaN values)
                clean_batch = []
                for record in batch:
                    clean_record = {k: v for k, v in record.items() if pd.notna(v)}
                    clean_batch.append(clean_record)

                # Create nodes using UNWIND for efficiency
                query = f"""
                UNWIND $records AS record
                CREATE (n:{label})
                SET n = record
                RETURN count(n) as created
                """

                result = await session.run(query, {"records": clean_batch})
                data = await result.single()
                total_created += data["created"]

        return {
            "success": True,
            "label": label,
            "nodes_created": total_created,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }
    finally:
        await driver.close()


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def run_sync(coro):
    """
    Run an async coroutine synchronously.

    Useful for testing or when async context is not available.

    Args:
        coro: Coroutine to run

    Returns:
        Result of the coroutine
    """
    try:
        loop = asyncio.get_running_loop()
        # If we're in an async context, we need to use to_thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        # No running loop, safe to use asyncio.run
        return asyncio.run(coro)

"""
Generated Documents File Server
================================
Lightweight HTTP server that serves generated documents (PPTX, XLSX, DOCX, CSV)
for frontend download.

Run alongside the LangGraph dev server:
    python file_server.py

Default port: 8090 (configurable via FILE_SERVER_PORT env var)

The server:
- Serves files from ./generated_documents/
- Provides CORS headers for cross-origin frontend requests
- Lists available files at GET /files
- Downloads files at GET /download/{filename}
"""

import os
import sys
import mimetypes
from pathlib import Path

# Ensure proper MIME types
mimetypes.add_type(
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".pptx",
)
mimetypes.add_type(
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xlsx",
)
mimetypes.add_type(
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".docx",
)

# ---------- Configuration ----------

PORT = int(os.getenv("FILE_SERVER_PORT", "8090"))
HOST = os.getenv("FILE_SERVER_HOST", "0.0.0.0")
DOCS_DIR = os.getenv(
    "GENERATED_DOCS_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated_documents"),
)

# Allowed file extensions
ALLOWED_EXTENSIONS = {".pptx", ".xlsx", ".docx", ".csv", ".pdf", ".txt", ".json"}

# ---------- Server ----------

try:
    from aiohttp import web
except ImportError:
    print("aiohttp is required. Install with: pip install aiohttp")
    sys.exit(1)


def _cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
    }


async def handle_options(request: web.Request) -> web.Response:
    """CORS preflight handler."""
    return web.Response(status=204, headers=_cors_headers())


async def handle_health(request: web.Request) -> web.Response:
    """Health check."""
    return web.json_response(
        {"status": "ok", "service": "file-server", "docs_dir": DOCS_DIR},
        headers=_cors_headers(),
    )


async def handle_list_files(request: web.Request) -> web.Response:
    """List all generated files available for download."""
    files = []
    docs_path = Path(DOCS_DIR)

    if docs_path.exists():
        for fp in sorted(docs_path.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if fp.is_file() and fp.suffix.lower() in ALLOWED_EXTENSIONS:
                stat = fp.stat()
                files.append({
                    "filename": fp.name,
                    "file_type": fp.suffix.lstrip("."),
                    "size_bytes": stat.st_size,
                    "created_at": stat.st_mtime,
                    "download_url": f"/download/{fp.name}",
                })

    return web.json_response({"files": files, "count": len(files)}, headers=_cors_headers())


async def handle_download(request: web.Request) -> web.Response:
    """Download a generated file by filename."""
    filename = request.match_info["filename"]

    # Security: prevent path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        return web.json_response(
            {"error": "Invalid filename"}, status=400, headers=_cors_headers()
        )

    filepath = os.path.join(DOCS_DIR, filename)

    if not os.path.isfile(filepath):
        return web.json_response(
            {"error": "File not found"}, status=404, headers=_cors_headers()
        )

    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return web.json_response(
            {"error": "File type not allowed"}, status=403, headers=_cors_headers()
        )

    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    headers = {
        **_cors_headers(),
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": content_type,
    }

    return web.FileResponse(filepath, headers=headers)


# ---------- Feedback API Endpoints ----------


async def handle_feedback_post(request: web.Request) -> web.Response:
    """Record a user feedback event.

    POST /feedback
    Body: {
        "signal": "thumbs_up" | "thumbs_down" | "response_copied" | "dwell_time" | ...,
        "thread_id": "session_abc123",
        "context": "optional description",
        "domain": "DM",
        "metadata": {"dwell_time_seconds": 15}
    }
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response(
            {"error": "Invalid JSON body"}, status=400, headers=_cors_headers()
        )

    signal_str = data.get("signal", "")
    thread_id = data.get("thread_id", "unknown")
    context = data.get("context", "")
    domain = data.get("domain", "")
    metadata = data.get("metadata", {})

    try:
        from sdtm_pipeline.deepagents.feedback import FeedbackSignal, get_feedback_collector

        # Validate signal
        try:
            signal = FeedbackSignal(signal_str)
        except ValueError:
            valid = [s.value for s in FeedbackSignal]
            return web.json_response(
                {"error": f"Invalid signal: {signal_str}", "valid_signals": valid},
                status=400,
                headers=_cors_headers(),
            )

        collector = get_feedback_collector()
        event = collector.record(
            signal=signal,
            thread_id=thread_id,
            user_query=context,
            domain=domain.upper() if domain else None,
            metadata=metadata,
        )

        return web.json_response(
            {
                "success": True,
                "event_id": event.event_id,
                "signal": signal_str,
                "sentiment": event.sentiment.value,
            },
            headers=_cors_headers(),
        )
    except ImportError:
        return web.json_response(
            {"error": "Feedback module not available"},
            status=503,
            headers=_cors_headers(),
        )
    except Exception as e:
        return web.json_response(
            {"error": str(e)}, status=500, headers=_cors_headers()
        )


async def handle_feedback_stats(request: web.Request) -> web.Response:
    """Return aggregated feedback analytics.

    GET /feedback/stats
    """
    try:
        from sdtm_pipeline.deepagents.learning_store import get_learning_store

        store = get_learning_store()
        metrics = store.compute_metrics()

        return web.json_response(metrics, headers=_cors_headers())
    except ImportError:
        return web.json_response(
            {"error": "Learning store not available"},
            status=503,
            headers=_cors_headers(),
        )
    except Exception as e:
        return web.json_response(
            {"error": str(e)}, status=500, headers=_cors_headers()
        )


async def handle_feedback_events(request: web.Request) -> web.Response:
    """Return recent feedback events for debugging.

    GET /feedback/events?limit=50&thread_id=xxx
    """
    try:
        from sdtm_pipeline.deepagents.learning_store import get_learning_store

        store = get_learning_store()

        limit = int(request.query.get("limit", "50"))
        thread_id = request.query.get("thread_id")

        events = store.read_events(limit=limit, thread_id=thread_id)

        return web.json_response(
            {
                "events": [e.to_dict() for e in events],
                "count": len(events),
            },
            headers=_cors_headers(),
        )
    except ImportError:
        return web.json_response(
            {"error": "Learning store not available"},
            status=503,
            headers=_cors_headers(),
        )
    except Exception as e:
        return web.json_response(
            {"error": str(e)}, status=500, headers=_cors_headers()
        )


def create_app() -> web.Application:
    """Create the aiohttp application."""
    app = web.Application()

    # CORS preflight for all routes
    app.router.add_route("OPTIONS", "/{path:.*}", handle_options)

    # File serving routes
    app.router.add_get("/health", handle_health)
    app.router.add_get("/files", handle_list_files)
    app.router.add_get("/download/{filename}", handle_download)

    # Feedback & learning API routes
    app.router.add_post("/feedback", handle_feedback_post)
    app.router.add_get("/feedback/stats", handle_feedback_stats)
    app.router.add_get("/feedback/events", handle_feedback_events)

    return app


if __name__ == "__main__":
    os.makedirs(DOCS_DIR, exist_ok=True)
    print(f"[File Server] Serving generated documents from: {DOCS_DIR}")
    print(f"[File Server] Listening on {HOST}:{PORT}")
    print(f"[File Server] Download URL: http://{HOST}:{PORT}/download/{{filename}}")
    app = create_app()
    web.run_app(app, host=HOST, port=PORT, print=None)

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
        "Access-Control-Allow-Methods": "GET, OPTIONS",
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


def create_app() -> web.Application:
    """Create the aiohttp application."""
    app = web.Application()

    # CORS preflight for all routes
    app.router.add_route("OPTIONS", "/{path:.*}", handle_options)

    # Routes
    app.router.add_get("/health", handle_health)
    app.router.add_get("/files", handle_list_files)
    app.router.add_get("/download/{filename}", handle_download)

    return app


if __name__ == "__main__":
    os.makedirs(DOCS_DIR, exist_ok=True)
    print(f"[File Server] Serving generated documents from: {DOCS_DIR}")
    print(f"[File Server] Listening on {HOST}:{PORT}")
    print(f"[File Server] Download URL: http://{HOST}:{PORT}/download/{{filename}}")
    app = create_app()
    web.run_app(app, host=HOST, port=PORT, print=None)

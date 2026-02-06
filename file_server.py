"""
Generated Documents File Server + Skills & Connectors API
==========================================================
Lightweight HTTP server that serves generated documents (PPTX, XLSX, DOCX, CSV)
for frontend download, and provides CRUD APIs for skills and connectors so the
frontend and backend agent stay in sync.

Run alongside the LangGraph dev server:
    python file_server.py

Default port: 8090 (configurable via FILE_SERVER_PORT env var)

The server:
- Serves files from ./generated_documents/
- Provides CORS headers for cross-origin frontend requests
- Lists available files at GET /files
- Downloads files at GET /download/{filename}
- Skills CRUD: GET/POST /skills, GET/PUT/DELETE /skills/{dirName}
- Connectors sync: GET/PUT /connectors, GET /connectors/tools
"""

import os
import re
import sys
import json
import shutil
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

# Skills directory (markdown-based agent skills)
SKILLS_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "sdtm_pipeline" / "deepagents" / "skills"

# Connector state file (persists frontend connector enable/disable state)
CONNECTORS_STATE_FILE = Path(os.path.dirname(os.path.abspath(__file__))) / "connectors_state.json"

# Import the canonical connector-to-tool map from the graph module.
# Falls back to a local copy if the graph module isn't loadable (e.g. standalone mode).
try:
    from sdtm_pipeline.langgraph_chat.graph import CONNECTOR_TOOL_MAP
except ImportError:
    CONNECTOR_TOOL_MAP = {
        "clinicaltrials": ["search_clinical_trials", "get_clinical_trial_details"],
        "npi-registry": ["search_npi_registry"],
        "cms-coverage": ["search_cms_coverage"],
        "icd10": ["search_icd10_codes"],
        "chembl": ["search_chembl_compounds", "get_chembl_bioactivities"],
        "biorxiv": ["search_biorxiv_papers"],
        "aws-s3": ["load_data_from_s3", "upload_sdtm_to_s3"],
        "neo4j": ["load_sdtm_to_neo4j"],
        "pinecone": [
            "search_knowledge_base", "get_sdtm_guidance", "get_validation_rules",
            "get_mapping_specification", "get_controlled_terminology",
            "get_business_rules", "search_sdtm_guidelines",
            "search_dta_document", "upload_dta_to_knowledge_base",
        ],
    }

# ---------- Server ----------

try:
    from aiohttp import web
except ImportError:
    print("aiohttp is required. Install with: pip install aiohttp")
    sys.exit(1)


def _cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
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


# ---------- Skills API Helpers ----------


def _validate_dir_name(dir_name: str) -> bool:
    """Return True if dir_name is safe (no path traversal)."""
    return bool(dir_name) and ".." not in dir_name and "/" not in dir_name and "\\" not in dir_name


def _slugify(name: str) -> str:
    """Convert a skill name to a filesystem-safe directory name."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "unnamed-skill"


def _parse_skill_md(skill_path: Path) -> dict:
    """Parse a SKILL.md file, returning {name, description, content, dirName}."""
    skill_file = skill_path / "SKILL.md"
    if not skill_file.exists():
        return {}

    raw = skill_file.read_text(encoding="utf-8")
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw, re.DOTALL)

    if fm_match:
        frontmatter = fm_match.group(1)
        body = fm_match.group(2)
        name_m = re.search(r"^name:\s*(.+)$", frontmatter, re.MULTILINE)
        desc_m = re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE)
        name = name_m.group(1).strip() if name_m else skill_path.name
        description = desc_m.group(1).strip() if desc_m else ""
    else:
        name = skill_path.name
        description = ""
        body = raw

    return {
        "name": name,
        "description": description,
        "content": body.strip(),
        "dirName": skill_path.name,
    }


def _write_skill_md(skill_dir: Path, name: str, description: str, content: str):
    """Write a SKILL.md file with YAML frontmatter."""
    skill_dir.mkdir(parents=True, exist_ok=True)
    text = f"---\nname: {name}\ndescription: {description}\n---\n{content}\n"
    (skill_dir / "SKILL.md").write_text(text, encoding="utf-8")


def _try_reload_skills():
    """Attempt to call reload_skills() so the agent picks up changes."""
    try:
        from sdtm_pipeline.langgraph_chat.graph import reload_skills
        reload_skills()
    except Exception as e:
        print(f"[File Server] Warning: could not reload skills: {e}")


# ---------- Skills API Endpoints ----------


async def handle_list_skills_api(request: web.Request) -> web.Response:
    """GET /skills - List all skills from the skills directory."""
    skills = []
    if SKILLS_DIR.exists():
        for d in sorted(SKILLS_DIR.iterdir()):
            if d.is_dir():
                parsed = _parse_skill_md(d)
                if parsed:
                    skills.append({
                        "name": parsed["name"],
                        "description": parsed["description"],
                        "dirName": parsed["dirName"],
                    })
    return web.json_response({"skills": skills}, headers=_cors_headers())


async def handle_get_skill(request: web.Request) -> web.Response:
    """GET /skills/{dirName} - Get full skill detail."""
    dir_name = request.match_info["dirName"]
    if not _validate_dir_name(dir_name):
        return web.json_response({"error": "Invalid skill name"}, status=400, headers=_cors_headers())

    skill_path = SKILLS_DIR / dir_name
    if not skill_path.is_dir():
        return web.json_response({"error": "Skill not found"}, status=404, headers=_cors_headers())

    parsed = _parse_skill_md(skill_path)
    if not parsed:
        return web.json_response({"error": "Skill has no SKILL.md"}, status=404, headers=_cors_headers())

    return web.json_response(parsed, headers=_cors_headers())


async def handle_create_skill(request: web.Request) -> web.Response:
    """POST /skills - Create a new skill.

    Body: { "name": str, "description": str, "content": str }
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON body"}, status=400, headers=_cors_headers())

    name = data.get("name", "").strip()
    description = data.get("description", "").strip()
    content = data.get("content", "").strip()

    if not name:
        return web.json_response({"error": "name is required"}, status=400, headers=_cors_headers())

    dir_name = _slugify(name)
    skill_dir = SKILLS_DIR / dir_name

    # Avoid overwriting existing skill
    if skill_dir.exists():
        # Append a numeric suffix
        i = 2
        while (SKILLS_DIR / f"{dir_name}-{i}").exists():
            i += 1
        dir_name = f"{dir_name}-{i}"
        skill_dir = SKILLS_DIR / dir_name

    _write_skill_md(skill_dir, name, description, content)
    _try_reload_skills()

    return web.json_response({"dirName": dir_name, "name": name}, status=201, headers=_cors_headers())


async def handle_update_skill(request: web.Request) -> web.Response:
    """PUT /skills/{dirName} - Update an existing skill."""
    dir_name = request.match_info["dirName"]
    if not _validate_dir_name(dir_name):
        return web.json_response({"error": "Invalid skill name"}, status=400, headers=_cors_headers())

    skill_dir = SKILLS_DIR / dir_name
    if not skill_dir.is_dir():
        return web.json_response({"error": "Skill not found"}, status=404, headers=_cors_headers())

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON body"}, status=400, headers=_cors_headers())

    name = data.get("name", "").strip()
    description = data.get("description", "").strip()
    content = data.get("content", "").strip()

    if not name:
        return web.json_response({"error": "name is required"}, status=400, headers=_cors_headers())

    _write_skill_md(skill_dir, name, description, content)
    _try_reload_skills()

    return web.json_response({"ok": True}, headers=_cors_headers())


async def handle_delete_skill(request: web.Request) -> web.Response:
    """DELETE /skills/{dirName} - Delete a skill directory."""
    dir_name = request.match_info["dirName"]
    if not _validate_dir_name(dir_name):
        return web.json_response({"error": "Invalid skill name"}, status=400, headers=_cors_headers())

    skill_dir = SKILLS_DIR / dir_name
    if not skill_dir.is_dir():
        return web.json_response({"error": "Skill not found"}, status=404, headers=_cors_headers())

    shutil.rmtree(skill_dir)
    _try_reload_skills()

    return web.json_response({"ok": True}, headers=_cors_headers())


async def handle_upload_skill(request: web.Request) -> web.Response:
    """POST /skills/upload - Upload a .md file as a new skill.

    Body: { "content": str, "fileName": str }
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON body"}, status=400, headers=_cors_headers())

    content = data.get("content", "").strip()
    file_name = data.get("fileName", "uploaded-skill.md").strip()

    if not content:
        return web.json_response({"error": "content is required"}, status=400, headers=_cors_headers())

    # Derive name from filename (strip .md extension)
    base = Path(file_name).stem
    name = base.replace("-", " ").replace("_", " ").title()
    dir_name = _slugify(base)

    # Parse frontmatter from uploaded content if present
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if fm_match:
        frontmatter = fm_match.group(1)
        body = fm_match.group(2)
        name_m = re.search(r"^name:\s*(.+)$", frontmatter, re.MULTILINE)
        desc_m = re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE)
        if name_m:
            name = name_m.group(1).strip()
            dir_name = _slugify(name)
        description = desc_m.group(1).strip() if desc_m else ""
    else:
        body = content
        description = ""

    skill_dir = SKILLS_DIR / dir_name
    if skill_dir.exists():
        i = 2
        while (SKILLS_DIR / f"{dir_name}-{i}").exists():
            i += 1
        dir_name = f"{dir_name}-{i}"
        skill_dir = SKILLS_DIR / dir_name

    _write_skill_md(skill_dir, name, description, body.strip())
    _try_reload_skills()

    return web.json_response({"dirName": dir_name, "name": name}, status=201, headers=_cors_headers())


async def handle_reload_skills(request: web.Request) -> web.Response:
    """POST /skills/reload - Trigger a skill reload so the agent picks up changes."""
    _try_reload_skills()
    skills_count = sum(1 for d in SKILLS_DIR.iterdir() if d.is_dir() and (d / "SKILL.md").exists()) if SKILLS_DIR.exists() else 0
    return web.json_response({"ok": True, "skills_count": skills_count}, headers=_cors_headers())


# ---------- Connectors API Helpers ----------


def _load_connector_state() -> dict:
    """Read connector state from JSON file."""
    if CONNECTORS_STATE_FILE.exists():
        try:
            return json.loads(CONNECTORS_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"app_connectors": {}, "api_connectors": [], "mcp_connectors": []}


def _save_connector_state(state: dict):
    """Write connector state to JSON file."""
    CONNECTORS_STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _try_reload_connectors():
    """Attempt to call reload_connectors() so the agent updates its tool set."""
    try:
        from sdtm_pipeline.langgraph_chat.graph import reload_connectors
        reload_connectors()
    except Exception as e:
        print(f"[File Server] Warning: could not reload connectors: {e}")


# ---------- Connectors API Endpoints ----------


async def handle_get_connectors(request: web.Request) -> web.Response:
    """GET /connectors - Return current connector state + available tool mapping."""
    state = _load_connector_state()
    return web.json_response({
        **state,
        "available_connectors": list(CONNECTOR_TOOL_MAP.keys()),
        "tool_map": CONNECTOR_TOOL_MAP,
    }, headers=_cors_headers())


async def handle_put_connectors(request: web.Request) -> web.Response:
    """PUT /connectors - Save connector state from frontend.

    Body: { "app_connectors": {id: {enabled, config?}}, "api_connectors": [...], "mcp_connectors": [...] }
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON body"}, status=400, headers=_cors_headers())

    state = {
        "app_connectors": data.get("app_connectors", {}),
        "api_connectors": data.get("api_connectors", []),
        "mcp_connectors": data.get("mcp_connectors", []),
    }
    _save_connector_state(state)
    _try_reload_connectors()

    return web.json_response({"ok": True}, headers=_cors_headers())


async def handle_get_connector_tools(request: web.Request) -> web.Response:
    """GET /connectors/tools - List active tools based on connector state."""
    state = _load_connector_state()
    app_state = state.get("app_connectors", {})

    active_tools = []
    disabled_tools = []

    for connector_id, tool_names in CONNECTOR_TOOL_MAP.items():
        connector = app_state.get(connector_id, {})
        enabled = connector.get("enabled", True)  # Default to enabled if not explicitly set
        if enabled:
            active_tools.extend(tool_names)
        else:
            disabled_tools.extend(tool_names)

    return web.json_response({
        "active_tools": active_tools,
        "disabled_tools": disabled_tools,
    }, headers=_cors_headers())


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

    # Skills CRUD API routes
    app.router.add_get("/skills", handle_list_skills_api)
    app.router.add_post("/skills", handle_create_skill)
    app.router.add_post("/skills/upload", handle_upload_skill)
    app.router.add_post("/skills/reload", handle_reload_skills)
    # Parameterised routes AFTER static routes to avoid matching conflicts
    app.router.add_get("/skills/{dirName}", handle_get_skill)
    app.router.add_put("/skills/{dirName}", handle_update_skill)
    app.router.add_delete("/skills/{dirName}", handle_delete_skill)

    # Connectors sync API routes
    app.router.add_get("/connectors", handle_get_connectors)
    app.router.add_put("/connectors", handle_put_connectors)
    app.router.add_get("/connectors/tools", handle_get_connector_tools)

    return app


if __name__ == "__main__":
    os.makedirs(DOCS_DIR, exist_ok=True)
    print(f"[File Server] Serving generated documents from: {DOCS_DIR}")
    print(f"[File Server] Listening on {HOST}:{PORT}")
    print(f"[File Server] Download URL: http://{HOST}:{PORT}/download/{{filename}}")
    app = create_app()
    web.run_app(app, host=HOST, port=PORT, print=None)

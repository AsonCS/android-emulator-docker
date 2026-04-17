import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from socketio import ASGIApp

import config
import screencast
from api import adb, app as app_router, diagnostics, emulator, env, files
from api import input as input_router
from api import logs, screen

TAGS_METADATA = [
    {
        "name": "Emulator",
        "description": "Manage the Android emulator lifecycle: query status, reboot, and wipe data.",
    },
    {
        "name": "ADB",
        "description": "Execute raw ADB commands against the connected emulator. "
        "Only an allowlisted set of subcommands is accepted to prevent shell injection.",
    },
    {
        "name": "Screen",
        "description": "Capture screenshots and manage screen recordings on the emulator.",
    },
    {
        "name": "Logs",
        "description": "Retrieve and filter logcat output from the Android emulator.",
    },
    {
        "name": "Diagnostics",
        "description": "Collect Android diagnostics via dumpsys, dumpstate, and bugreport.",
    },
    {
        "name": "Files",
        "description": "Transfer files between the client, the Docker container, and the emulator.",
    },
    {
        "name": "App",
        "description": "Install, uninstall, and manage Android applications on the emulator.",
    },
    {
        "name": "Input",
        "description": "Simulate touch, swipe, text, and hardware key events on the emulator.",
    },
    {
        "name": "Environment",
        "description": "Simulate environment conditions: GPS location and network state.",
    },
    {
        "name": "Screencast",
        "description": "Live screenshot streaming via Socket.IO. View real-time emulator screen with adjustable refresh rates.",
    },
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    for subdir in ("", "container", "recordings"):
        os.makedirs(os.path.join(config.TEMP_DIR, subdir), exist_ok=True)
    yield


# Create FastAPI application
application = FastAPI(
    title="Android Emulator REST API",
    description=(
        "REST API for controlling, monitoring, and interacting with an Android Emulator "
        "running inside a Docker container. Designed for CI pipelines and automated test runners.\n\n"
        "**Swagger UI:** `/docs` &nbsp;|&nbsp; **ReDoc:** `/redoc` &nbsp;|&nbsp; **OpenAPI JSON:** `/openapi.json`\n\n"
        "**Screencast:** `/screencast` – Real-time screenshot streaming via Socket.IO"
    ),
    version="1.0.0",
    openapi_tags=TAGS_METADATA,
    lifespan=lifespan,
)

application.include_router(emulator.router, prefix="/emulator", tags=["Emulator"])
application.include_router(adb.router, prefix="/adb", tags=["ADB"])
application.include_router(screen.router, prefix="/screen", tags=["Screen"])
application.include_router(logs.router, prefix="/logs", tags=["Logs"])
application.include_router(diagnostics.router, prefix="/diagnostics", tags=["Diagnostics"])
application.include_router(files.router, prefix="/files", tags=["Files"])
application.include_router(app_router.router, prefix="/app", tags=["App"])
application.include_router(input_router.router, prefix="/input", tags=["Input"])
application.include_router(env.router, prefix="/env", tags=["Environment"])


# ── Screencast (Socket.IO) ─────────────────────────────────────────────────────


@application.get(
    "/screencast",
    tags=["Screencast"],
    summary="View screencast",
    responses={
        200: {
            "description": "HTML page for real-time screenshot streaming",
            "content": {"text/html": {}},
        }
    },
)
async def screencast_page(
    device_id: str | None = Query(
        None,
        description=(
            "ADB device identifier (serial or host:port) for live screencast, "
            "input gestures, and logcat streaming. If omitted, the default target is used."
        ),
    ),
):
    """
    Serve the live screencast viewer page.
    
    Connects to the server via Socket.IO and displays real-time screenshots
    at configurable intervals. Automatically starts capturing when a client connects
    and stops when all clients disconnect.
    
    **Features:**
    - Real-time screenshot streaming as base64-encoded PNG images
    - Adjustable screenshot interval (0.1 - 10 seconds)
    - Shows frame count and server statistics
    - Responsive design for mobile and desktop
    """
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    return FileResponse(os.path.join(static_dir, "index.html"), media_type="text/html")


# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    application.mount("/static", StaticFiles(directory=static_dir), name="static")


# ── Socket.IO Setup ───────────────────────────────────────────────────────────

sio = screencast.get_sio()
screencast.register_screencast_handlers(sio)

# Wrap FastAPI with Socket.IO ASGI middleware
app = ASGIApp(sio, application, socketio_path="socket.io")

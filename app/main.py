import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

import config
from api import adb, app as app_router, emulator, env, files
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
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    for subdir in ("", "container", "recordings"):
        os.makedirs(os.path.join(config.TEMP_DIR, subdir), exist_ok=True)
    yield


application = FastAPI(
    title="Android Emulator REST API",
    description=(
        "REST API for controlling, monitoring, and interacting with an Android Emulator "
        "running inside a Docker container. Designed for CI pipelines and automated test runners.\n\n"
        "**Swagger UI:** `/docs` &nbsp;|&nbsp; **ReDoc:** `/redoc` &nbsp;|&nbsp; **OpenAPI JSON:** `/openapi.json`"
    ),
    version="1.0.0",
    openapi_tags=TAGS_METADATA,
    lifespan=lifespan,
)

application.include_router(emulator.router, prefix="/emulator", tags=["Emulator"])
application.include_router(adb.router, prefix="/adb", tags=["ADB"])
application.include_router(screen.router, prefix="/screen", tags=["Screen"])
application.include_router(logs.router, prefix="/logs", tags=["Logs"])
application.include_router(files.router, prefix="/files", tags=["Files"])
application.include_router(app_router.router, prefix="/app", tags=["App"])
application.include_router(input_router.router, prefix="/input", tags=["Input"])
application.include_router(env.router, prefix="/env", tags=["Environment"])

# Android Emulator Docker :robot: :whale:

REST API and tooling to run and control an Android Emulator inside Docker, with optional live screencast streaming via Socket.IO.

## Scope :mag:

This README documents the active project files and flow.

## What This Project Provides :sparkles:

- Android emulator runtime in containers
- FastAPI REST API for emulator control
- ADB command endpoints (restricted/allowlisted by API design)
- Screenshot/screen-record/log/diagnostic endpoints
- Socket.IO screencast viewer

## Run The Python App Locally With run_app.sh :snake:

Script: [`run_app.sh`](run_app.sh)

Prerequisites :clipboard:

- `python3`
- `git`

What the script does:

1. Creates a local virtual environment at `.venv`
2. Changes directory to `./app`
3. Installs dependencies from `app/requirements.txt`
4. Starts Uvicorn with `main:app` on host `0.0.0.0`

Run it:

#### Linux / WSL | Windows (Git Bash) | Mac

```bash
git clone https://github.com/AsonCS/android-emulator-docker.git
cd android-emulator-docker/
chmod +x ./run_app.sh
sh ./run_app.sh
```

Run with custom port (default is `8001`):

```bash
./run_app.sh 9000
```

After startup:

- API base URL: `http://localhost:<PORT>/`
- Swagger UI: `http://localhost:<PORT>/docs`
- ReDoc: `http://localhost:<PORT>/redoc`
- Screencast page: `http://localhost:<PORT>/screencast`

## Prerequisites :clipboard:

- Docker and Docker Compose
- Linux host with `/dev/kvm` support for emulator acceleration
- `python3` installed (required to run local app with `run_app.sh`)

## App Entry Point Explained (app/main.py) :gear:

Main file: [`app/main.py`](app/main.py)

Core behavior:

- Builds a FastAPI app with metadata and grouped tags (Emulator, ADB, Screen, Logs, Diagnostics, Files, App, Input, Environment, Screencast)
- Registers routers under prefixes such as:
  - `/emulator`
  - `/adb`
  - `/screen`
  - `/logs`
  - `/diagnostics`
  - `/files`
  - `/app`
  - `/input`
  - `/env`
- Creates required runtime directories under `config.TEMP_DIR` during lifespan startup
- Exposes `/` healthcheck endpoint returning readiness status and UTC timestamp
- Exposes `/screencast` HTML viewer route
- Mounts `app/static` as `/static` when present
- Wraps FastAPI in Socket.IO ASGI middleware:
  - `sio = screencast.get_sio()`
  - `app = ASGIApp(sio, application, socketio_path="socket.io")`

This means the module exports two app objects:

- `application`: plain FastAPI app
- `app`: Socket.IO-wrapped ASGI app (the one used by Uvicorn in this repo)

## Docker Compose Overview (docker-compose.yaml) :whale2:

File: [`docker-compose.yaml`](docker-compose.yaml)

It defines two services:

1. `app`
- Build from `Dockerfile.app`
- Container name: `android-emulator-docker-app`
- Mounts project files/directories into `/home/ubuntu/...` for development
- Loads env vars from `.env`
- Publishes API on host port `8001` to container port `80`
- Adds `host.docker.internal:host-gateway`

2. `emulator`
- Build from `Dockerfile.emulator`
- Container name: `android-emulator-docker-emulator`
- Requires KVM device mapping (`/dev/kvm`)
- Loads env vars from `.env`
- Publishes:
  - `8000:80` (API)
  - `5595:5595` (ADB forwarding)
- Adds `host.docker.internal:host-gateway`

Start both services:

```bash
docker compose up -d --build
```

Start one service:

```bash
docker compose up -d --build app
docker compose up -d --build emulator
```

## commands.md Guide :bookmark_tabs:

File: [`commands.md`](commands.md)

This file is a command cookbook grouped by topic:

- App image build/run commands
- Base image build/run commands
- Emulator image build/run/exec commands
- Android SDK and ADB helper commands
- Docker cleanup commands (`builder prune`, `image prune`)
- Network/host snippets (`host.docker.internal`, `network_mode: host`, `privileged`)
- Host OS note for `hosts` file configuration

Use it as a quick operational reference when debugging or running commands manually.

## Root Dockerfiles And Shell Scripts (Brief) :card_file_box:

### Dockerfiles

- [`Dockerfile.base`](Dockerfile.base)
  - Creates the foundational image on Ubuntu 24.04
  - Installs Java, Python, and Android dependencies
  - Runs `setup_base.sh` to install command-line tools + platform-tools

- [`Dockerfile.emulator`](Dockerfile.emulator)
  - Extends base image for emulator runtime
  - Sets emulator/API env vars
  - Runs `setup.sh` (installs emulator packages/system images and downloads APK assets)
  - Copies startup scripts and launches `entrypoint.sh`

- [`Dockerfile.app`](Dockerfile.app)
  - Builds a slim Python API image
  - Reuses Android SDK components from base image
  - Copies app source and runs FastAPI entrypoint

### Shell Scripts

- [`setup_base.sh`](setup_base.sh)
  - Downloads Android command-line tools
  - Accepts licenses and installs platform-tools

- [`setup.sh`](setup.sh)
  - Installs emulator/build-tools/platform/system image packages
  - Downloads normal APKs and priv-app payloads from env-configured URLs

- [`build_image.sh`](build_image.sh)
  - Creates AVD (if needed)
  - Starts emulator and waits for boot completion
  - Installs APKs and pushes privileged APK/XML files into system paths

- [`entrypoint.sh`](entrypoint.sh)
  - Configures ADB private key from `ADB_KEY`
  - Starts emulator flow through `build_image.sh`
  - Forwards ADB TCP with `socat`
  - Starts API app entrypoint

- [`run_app.sh`](run_app.sh)
  - Local developer helper to run API without Docker using Python virtualenv + Uvicorn

## License :page_facing_up:

See [`LICENSE`](LICENSE).

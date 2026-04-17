"""
Socket.IO screencast server for real-time screenshot streaming.

Broadcasts base64-encoded screenshots to connected clients at configurable intervals.
Only captures when clients are connected.
"""
import asyncio
import base64
import logging
from typing import Optional
from urllib.parse import parse_qs

from socketio import AsyncServer

import adb_runner.runner as adb
import config

logger = logging.getLogger(__name__)

# Global screencast state
_screencast_task: Optional[asyncio.Task] = None
_screenshot_interval: float = 1.0  # Default 1 second between screenshots
_connected_clients: set = set()
_client_device_ids: dict[str, Optional[str]] = {}
_client_logcat_tasks: dict[str, asyncio.Task] = {}
_client_logcat_state: dict[str, dict[str, object]] = {}

_LOGCAT_FLUSH_INTERVAL_S = 0.2
_LOGCAT_BATCH_SIZE = 25
_LOGCAT_MAX_FILTER_LEN = 128


def get_sio() -> AsyncServer:
    """Create and return Socket.IO AsyncServer instance."""
    return AsyncServer(
        async_mode="asgi",
        cors_allowed_origins="*",
        logger=False,
        engineio_logger=False,
    )


async def screenshot_to_base64(device_id: Optional[str] = None) -> Optional[str]:
    """
    Capture a screenshot and convert it to base64 string.
    
    Returns:
        Base64-encoded PNG string, or None if capture fails.
    """
    try:
        png_bytes = adb.run_binary(
            ["exec-out", "screencap", "-p"],
            timeout=15,
            device_id=device_id,
        )
        if not png_bytes:
            logger.warning("Screenshot returned empty data")
            return None
        return base64.b64encode(png_bytes).decode("utf-8")
    except adb.ADBError as exc:
        logger.error(f"Screenshot capture failed: {exc}")
        return None
    except Exception as exc:
        logger.error(f"Unexpected error capturing screenshot: {exc}")
        return None


async def _screenshot_loop(sio: AsyncServer):
    """
    Continuously capture screenshots and broadcast to connected clients.
    Only runs while clients are connected.
    """
    logger.info("Screenshot broadcast loop started")
    try:
        while _connected_clients:
            for sid in list(_connected_clients):
                screenshot_b64 = await screenshot_to_base64(_client_device_ids.get(sid))
                if screenshot_b64:
                    await sio.emit("screenshot", {"image": screenshot_b64}, to=sid)
            await asyncio.sleep(_screenshot_interval)
    except asyncio.CancelledError:
        logger.info("Screenshot broadcast loop cancelled")
    except Exception as exc:
        logger.error(f"Error in screenshot loop: {exc}")
    finally:
        logger.info("Screenshot broadcast loop stopped")


async def _logcat_loop(sio: AsyncServer, sid: str):
    """Stream logcat lines for one client using its selected adb target."""
    logger.info("Logcat stream loop started for %s", sid)
    state = _client_logcat_state.setdefault(
        sid,
        {"enabled": False, "filter": "", "filter_lower": ""},
    )
    device_id = _client_device_ids.get(sid)
    buffers: list[str] = []
    logcat_command = [config.ADB_PATH]
    if device_id:
        logcat_command.extend(["-s", device_id])
    else:
        logcat_command.extend(["-s", config.EMULATOR_SERIAL])
    logcat_command.extend(["logcat", "-v", "time", "-T", "1"])

    try:
        process = await asyncio.create_subprocess_exec(
            *logcat_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
    except Exception as exc:
        logger.error("Unable to start logcat stream for %s: %s", sid, exc)
        await sio.emit("error", {"message": f"Unable to start logcat stream: {exc}"}, to=sid)
        return

    loop = asyncio.get_running_loop()
    last_flush = loop.time()

    try:
        while sid in _connected_clients and bool(state.get("enabled", False)):
            try:
                raw_line = await asyncio.wait_for(
                    process.stdout.readline(),
                    timeout=_LOGCAT_FLUSH_INTERVAL_S,
                )
            except asyncio.TimeoutError:
                raw_line = b""

            if raw_line:
                line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
                if line:
                    lower_line = line.lower()
                    filter_text = str(state.get("filter_lower", ""))
                    if not filter_text or filter_text in lower_line:
                        buffers.append(line)

            now = loop.time()
            if now - last_flush >= _LOGCAT_FLUSH_INTERVAL_S:
                if buffers and sid in _connected_clients:
                    await sio.emit("logcat_lines", {"lines": buffers}, to=sid)
                buffers.clear()
                last_flush = now
            elif len(buffers) >= _LOGCAT_BATCH_SIZE:
                await sio.emit("logcat_lines", {"lines": buffers}, to=sid)
                buffers.clear()
                last_flush = now

            if process.returncode is not None and not raw_line:
                logger.warning("logcat process exited with code %s", process.returncode)
                break
    except asyncio.CancelledError:
        logger.info("Logcat stream loop cancelled for %s", sid)
    except Exception as exc:
        logger.error("Error in logcat stream loop for %s: %s", sid, exc)
    finally:
        if buffers and sid in _connected_clients:
            await sio.emit("logcat_lines", {"lines": buffers}, to=sid)
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=2)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
        _client_logcat_tasks.pop(sid, None)
        logger.info("Logcat stream loop stopped for %s", sid)


async def _ensure_logcat_task(sio: AsyncServer, sid: str):
    """Start or stop one logcat loop for the given client."""
    should_run = sid in _connected_clients and bool(
        _client_logcat_state.get(sid, {}).get("enabled", False)
    )
    current_task = _client_logcat_tasks.get(sid)

    if should_run:
        if current_task is None or current_task.done():
            _client_logcat_tasks[sid] = asyncio.create_task(_logcat_loop(sio, sid))
            logger.info("Started logcat stream loop for %s", sid)
        return

    if current_task and not current_task.done():
        current_task.cancel()
        try:
            await current_task
        except asyncio.CancelledError:
            pass
        logger.info("Stopped logcat stream loop for %s", sid)
    _client_logcat_tasks.pop(sid, None)


def _extract_device_id(environ, auth) -> Optional[str]:
    """Read device_id from Socket.IO auth first, then query string fallback."""
    if isinstance(auth, dict):
        auth_device_id = auth.get("device_id")
        if isinstance(auth_device_id, str) and auth_device_id.strip():
            return auth_device_id.strip()

    query_string = environ.get("QUERY_STRING", "") if isinstance(environ, dict) else ""
    parsed = parse_qs(query_string)
    query_device_id = parsed.get("device_id", [""])[0].strip()
    return query_device_id or None


def register_screencast_handlers(sio: AsyncServer):
    """
    Register Socket.IO event handlers for screencast functionality.
    
    Args:
        sio: Socket.IO AsyncServer instance.
    """

    @sio.on("connect")
    async def on_connect(sid: str, environ, auth=None):
        """Handle client connection."""
        logger.info(f"Client connected: {sid}")
        _connected_clients.add(sid)
        _client_device_ids[sid] = _extract_device_id(environ, auth)
        _client_logcat_state[sid] = {
            "enabled": False,
            "filter": "",
            "filter_lower": "",
        }

        # Start screenshot broadcast loop if not already running
        global _screencast_task
        if _screencast_task is None or _screencast_task.done():
            _screencast_task = asyncio.create_task(_screenshot_loop(sio))
            logger.info("Started screenshot broadcast loop")

    @sio.on("disconnect")
    async def on_disconnect(sid: str):
        """Handle client disconnection."""
        logger.info(f"Client disconnected: {sid}")
        _connected_clients.discard(sid)
        _client_device_ids.pop(sid, None)
        _client_logcat_state.pop(sid, None)

        # Stop screenshot broadcast loop if no clients connected
        global _screencast_task
        if not _connected_clients and _screencast_task and not _screencast_task.done():
            _screencast_task.cancel()
            try:
                await _screencast_task
            except asyncio.CancelledError:
                pass
            _screencast_task = None
            logger.info("Stopped screenshot broadcast loop (no connected clients)")

        await _ensure_logcat_task(sio, sid)

    @sio.on("set_interval")
    async def on_set_interval(sid: str, data: dict):
        """
        Handle interval update request from client.
        
        Args:
            sid: Socket ID of the requesting client.
            data: Dict with 'interval' key (in seconds, min 0.1, max 10).
        """
        global _screenshot_interval
        try:
            interval = float(data.get("interval", 1.0))
            # Clamp interval between 0.1 and 10 seconds
            interval = max(0.1, min(interval, 10.0))
            _screenshot_interval = interval
            logger.info(f"Screenshot interval updated to {interval}s by {sid}")
            await sio.emit("interval_updated", {"interval": interval}, to=sid)
        except (ValueError, TypeError) as exc:
            logger.error(f"Invalid interval value: {exc}")
            await sio.emit("error", {"message": "Invalid interval value"}, to=sid)

    @sio.on("get_status")
    async def on_get_status(sid: str):
        """
        Handle status request from client.
        
        Args:
            sid: Socket ID of the requesting client.
        """
        status = {
            "connected_clients": len(_connected_clients),
            "screenshot_interval": _screenshot_interval,
            "broadcast_active": _screencast_task is not None
            and not _screencast_task.done(),
            "logcat_active": sid in _client_logcat_tasks and not _client_logcat_tasks[sid].done(),
            "logcat_enabled": bool(_client_logcat_state.get(sid, {}).get("enabled", False)),
            "logcat_filter": str(_client_logcat_state.get(sid, {}).get("filter", "")),
            "device_id": _client_device_ids.get(sid),
        }
        await sio.emit("status", status, to=sid)

    @sio.on("set_logcat")
    async def on_set_logcat(sid: str, data: dict):
        """Enable/disable logcat streaming and update the per-client filter."""
        state = _client_logcat_state.setdefault(
            sid,
            {"enabled": False, "filter": "", "filter_lower": ""},
        )
        enabled = bool(data.get("enabled", False))
        filter_text = str(data.get("filter", "")).strip()
        if len(filter_text) > _LOGCAT_MAX_FILTER_LEN:
            filter_text = filter_text[:_LOGCAT_MAX_FILTER_LEN]

        state["enabled"] = enabled
        state["filter"] = filter_text
        state["filter_lower"] = filter_text.lower()

        await _ensure_logcat_task(sio, sid)

        await sio.emit(
            "logcat_status",
            {
                "enabled": enabled,
                "filter": filter_text,
                "active": sid in _client_logcat_tasks and not _client_logcat_tasks[sid].done(),
            },
            to=sid,
        )

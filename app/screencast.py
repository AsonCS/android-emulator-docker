"""
Socket.IO screencast server for real-time screenshot streaming.

Broadcasts base64-encoded screenshots to connected clients at configurable intervals.
Only captures when clients are connected.
"""
import asyncio
import base64
import logging
from typing import Optional

from socketio import AsyncServer

import adb_runner.runner as adb
import config

logger = logging.getLogger(__name__)

# Global screencast state
_screencast_task: Optional[asyncio.Task] = None
_screenshot_interval: float = 1.0  # Default 1 second between screenshots
_connected_clients: set = set()
_logcat_task: Optional[asyncio.Task] = None
_logcat_lock = asyncio.Lock()
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


async def screenshot_to_base64() -> Optional[str]:
    """
    Capture a screenshot and convert it to base64 string.
    
    Returns:
        Base64-encoded PNG string, or None if capture fails.
    """
    try:
        png_bytes = adb.run_binary(["exec-out", "screencap", "-p"], timeout=15)
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
            screenshot_b64 = await screenshot_to_base64()
            if screenshot_b64:
                await sio.emit(
                    "screenshot",
                    {"image": screenshot_b64},
                    to=None,  # Broadcast to all clients
                )
            await asyncio.sleep(_screenshot_interval)
    except asyncio.CancelledError:
        logger.info("Screenshot broadcast loop cancelled")
    except Exception as exc:
        logger.error(f"Error in screenshot loop: {exc}")
    finally:
        logger.info("Screenshot broadcast loop stopped")


def _has_logcat_subscribers() -> bool:
    """Return True if at least one connected client has logcat enabled."""
    for sid, state in _client_logcat_state.items():
        if sid in _connected_clients and bool(state.get("enabled", False)):
            return True
    return False


async def _flush_logcat_buffers(
    sio: AsyncServer,
    buffers: dict[str, list[str]],
):
    """Flush buffered log lines to each subscribed client."""
    for sid, lines in list(buffers.items()):
        if not lines:
            continue
        if sid not in _connected_clients:
            continue
        await sio.emit("logcat_lines", {"lines": lines}, to=sid)
    buffers.clear()


async def _logcat_loop(sio: AsyncServer):
    """Stream logcat lines and fan out to clients with server-side filtering."""
    logger.info("Logcat stream loop started")
    buffers: dict[str, list[str]] = {}

    try:
        process = await asyncio.create_subprocess_exec(
            config.ADB_PATH,
            "-s",
            config.EMULATOR_SERIAL,
            "logcat",
            "-v",
            "time",
            "-T",
            "1",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
    except Exception as exc:
        logger.error("Unable to start logcat stream: %s", exc)
        return

    loop = asyncio.get_running_loop()
    last_flush = loop.time()

    try:
        while _has_logcat_subscribers():
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
                    for sid, state in list(_client_logcat_state.items()):
                        if sid not in _connected_clients or not bool(state.get("enabled", False)):
                            continue
                        filter_text = str(state.get("filter_lower", ""))
                        if filter_text and filter_text not in lower_line:
                            continue
                        buffers.setdefault(sid, []).append(line)

            now = loop.time()
            if now - last_flush >= _LOGCAT_FLUSH_INTERVAL_S:
                await _flush_logcat_buffers(sio, buffers)
                last_flush = now
            elif any(len(lines) >= _LOGCAT_BATCH_SIZE for lines in buffers.values()):
                await _flush_logcat_buffers(sio, buffers)
                last_flush = now

            if process.returncode is not None and not raw_line:
                logger.warning("logcat process exited with code %s", process.returncode)
                break
    except asyncio.CancelledError:
        logger.info("Logcat stream loop cancelled")
    except Exception as exc:
        logger.error("Error in logcat stream loop: %s", exc)
    finally:
        await _flush_logcat_buffers(sio, buffers)
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=2)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
        logger.info("Logcat stream loop stopped")


async def _ensure_logcat_task(sio: AsyncServer):
    """Start or stop the shared logcat loop based on active subscribers."""
    global _logcat_task
    async with _logcat_lock:
        should_run = _has_logcat_subscribers()

        if should_run:
            if _logcat_task is None or _logcat_task.done():
                _logcat_task = asyncio.create_task(_logcat_loop(sio))
                logger.info("Started logcat stream loop")
            return

        if _logcat_task and not _logcat_task.done():
            _logcat_task.cancel()
            try:
                await _logcat_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped logcat stream loop (no subscribers)")
        _logcat_task = None


def register_screencast_handlers(sio: AsyncServer):
    """
    Register Socket.IO event handlers for screencast functionality.
    
    Args:
        sio: Socket.IO AsyncServer instance.
    """

    @sio.on("connect")
    async def on_connect(sid: str, environ):
        """Handle client connection."""
        logger.info(f"Client connected: {sid}")
        _connected_clients.add(sid)
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

        await _ensure_logcat_task(sio)

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
            "logcat_active": _logcat_task is not None and not _logcat_task.done(),
            "logcat_enabled": bool(_client_logcat_state.get(sid, {}).get("enabled", False)),
            "logcat_filter": str(_client_logcat_state.get(sid, {}).get("filter", "")),
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

        await _ensure_logcat_task(sio)

        await sio.emit(
            "logcat_status",
            {
                "enabled": enabled,
                "filter": filter_text,
                "active": _logcat_task is not None and not _logcat_task.done(),
            },
            to=sid,
        )

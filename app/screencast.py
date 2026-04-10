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
from config import TEMP_DIR

logger = logging.getLogger(__name__)

# Global screencast state
_screencast_task: Optional[asyncio.Task] = None
_screenshot_interval: float = 1.0  # Default 1 second between screenshots
_connected_clients: set = set()


def get_sio() -> AsyncServer:
    """Create and return Socket.IO AsyncServer instance."""
    return AsyncServer(
        async_mode="asgi",
        cors_allowed_origins="*",
        logger=True,
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
        }
        await sio.emit("status", status, to=sid)

# Screencast Feature

Real-time screenshot streaming to connected clients via Socket.IO.

## Overview

The screencast module provides live emulator screen viewing through a WebSocket connection (Socket.IO). Screenshots are captured at a configurable interval (0.1 - 10 seconds) and broadcast to all connected clients as base64-encoded PNG images.

## How It Works

1. **Lazy Initialization**: Screenshot capturing only begins when a client connects
2. **Efficient Broadcasting**: Screenshots are broadcast to all connected clients simultaneously
3. **Auto Shutdown**: Capturing stops automatically when the last client disconnects
4. **Configurable Intervals**: Clients can adjust the screenshot interval in real-time

## Accessing the Screencast

Navigate to the home page in your browser:
```
http://<server-addr>:<port>/screencast
```

## WebSocket Events

### Server → Client

| Event | Data | Description |
|-------|------|-------------|
| `screenshot` | `{"image": "<base64_png>"}` | New screenshot frame |
| `interval_updated` | `{"interval": <float>}` | Confirmation of interval change |
| `status` | `{...}` | Server status info |
| `error` | `{"message": "<string>"}` | Error message |

### Client → Server

| Event | Data | Description |
|-------|------|-------------|
| `set_interval` | `{"interval": <float>}` | Change screenshot interval (0.1 - 10 sec) |
| `get_status` | (none) | Request current server status |

## UI Features

- **Real-time Display**: Live screenshot updates at configured interval
- **Interval Control**: Adjust screenshot frequency via input field
- **Frame Counter**: Shows total frames received in session
- **Status Indicator**: Connected/Disconnected status with live indicator
- **Client Stats**: View current interval, frame count, and connected client count
- **Responsive Design**: Works on mobile and desktop

## Technical Details

### Screenshot Capture

Uses ADB command to capture emulator screen:
```bash
adb exec-out screencap -p
```

Returns raw PNG bytes which are then:
1. Base64-encoded
2. Broadcast to connected clients
3. Displayed as `data:image/png;base64,...` in HTML `<img>` tag

### Event Loop

The screenshot broadcast loop:
- Starts when first client connects
- Runs continuously while clients are connected
- Captures screenshot at configured interval
- Stops when last client disconnects

### Default Configuration

- **Screenshot Interval**: 1.0 second
- **Minimum Interval**: 0.1 second
- **Maximum Interval**: 10.0 seconds

## Examples

### Python Client

```python
import socketio

sio = socketio.Client()

@sio.event
def connect():
    print("Connected to screencast")

@sio.on("screenshot")
def on_screenshot(data):
    # data['image'] is base64-encoded PNG
    with open("frame.png", "wb") as f:
        f.write(base64.b64decode(data['image']))

@sio.event
def disconnect():
    print("Disconnected")

sio.connect("http://localhost:8000/socket.io/")

# Change interval
sio.emit("set_interval", {"interval": 0.5})

# Get status
sio.emit("get_status")

sio.wait()
```

### Interval Parameter

Via query string in Socket.IO client options:
```javascript
const socket = io("http://server:port", {
  query: { interval: 2.0 }
});
```

## Performance Considerations

- Screenshot capture takes ~100-200ms on typical emulator
- Base64 encoding adds minimal overhead
- Network bandwidth depends on screenshot interval and image size
- Default 1-second interval with ~500KB screenshots ≈ 500KB/sec per client

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No images appearing | Check browser console for connection errors, ensure ADB is working |
| Slow updates | Increase screenshot interval or reduce frame rate |
| High CPU usage | Increase interval between screenshots (default 1s) |
| Error: "ADB unreachable" | Verify emulator is running and ADB is functional |

## API Integration

The screencast is fully integrated with the main FastAPI app. To start the server:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Socket.IO is available at `/socket.io/` endpoint and the UI is at `/screencast`.

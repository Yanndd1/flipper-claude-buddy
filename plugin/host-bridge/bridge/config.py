"""Configuration for the host bridge daemon — Windows port."""

import os
import sys
import tempfile
from pathlib import Path

# Platform-specific runtime directory
if sys.platform == "win32":
    _RUNTIME_DIR = Path(tempfile.gettempdir()) / "claude-flipper"
    _RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
else:
    _RUNTIME_DIR = Path("/tmp")

# IPC: on Windows use TCP localhost (no AF_UNIX in Python Store 3.9).
IPC_USE_TCP = sys.platform == "win32" or os.environ.get("FLIPPER_IPC_TCP", "0") == "1"
IPC_TCP_HOST = "127.0.0.1"
IPC_TCP_PORT = int(os.environ.get("FLIPPER_IPC_TCP_PORT", "47353"))

# Legacy Unix socket path (used on non-Windows)
SOCKET_PATH = os.environ.get(
    "FLIPPER_BRIDGE_SOCKET",
    str(_RUNTIME_DIR / "claude-flipper-bridge.sock"),
)

# Runtime files
PID_PATH = str(_RUNTIME_DIR / "claude-flipper-bridge.pid")
LOG_PATH = str(_RUNTIME_DIR / "claude-flipper-bridge.log")
REFCOUNT_PATH = str(_RUNTIME_DIR / "claude-flipper-bridge.refcount")
TURN_STATS_PATH = str(_RUNTIME_DIR / "claude-flipper-turn-stats.json")
SKIP_STOP_FLAG = str(_RUNTIME_DIR / "claude-flipper-skip-stop.flag")

SERIAL_BAUD = 115200
SERIAL_PORT = os.environ.get("FLIPPER_SERIAL_PORT", "")

PING_INTERVAL = 5.0
DICTATION_POLL_INTERVAL = 2.0
SPACE_REPEAT_INTERVAL = 0.01

# Dictation backend — Windows: none by default.
_default_dictation = "macos" if sys.platform == "darwin" else "none"
DICTATION_BACKEND = os.environ.get("FLIPPER_DICTATION_BACKEND", _default_dictation)
DICTATION_START_CMD = os.environ.get("FLIPPER_DICTATION_START_CMD", "")
DICTATION_STOP_CMD = os.environ.get("FLIPPER_DICTATION_STOP_CMD", "")
DICTATION_CHECK_CMD = os.environ.get("FLIPPER_DICTATION_CHECK_CMD", "")

TRANSPORT = os.environ.get("FLIPPER_TRANSPORT", "auto")

_plugin_data = os.environ.get("FLIPPER_PLUGIN_DATA", "")
BT_NAME_CACHE = os.path.join(_plugin_data, "bt_name") if _plugin_data else ""

FLIPPER_ADV_UUID = "00003082-0000-1000-8000-00805f9b34fb"
BT_DEVICE_NAME = os.environ.get("FLIPPER_BT_NAME", "Flipper")
BT_SCAN_TIMEOUT = float(os.environ.get("FLIPPER_BT_SCAN_TIMEOUT", "10"))
BT_WRITE_CHUNK = 128

# USB serial port pattern (Windows uses VID/PID enumeration, not glob)
if sys.platform == "linux":
    SERIAL_GLOB_PATTERN = "/dev/ttyACM*"
elif sys.platform == "darwin":
    SERIAL_GLOB_PATTERN = "/dev/cu.usbmodem*"
else:
    SERIAL_GLOB_PATTERN = ""

PROJECT_DIR = os.environ.get(
    "FLIPPER_PROJECT_DIR",
    str(Path(__file__).parent.parent.parent),
)

CUSTOM_COMMANDS_FILES = [
    str(Path.home() / ".claude" / "flipper-commands.txt"),
    os.environ.get("FLIPPER_PROJECT_DIR", str(Path(__file__).parent.parent.parent))
    + "/.claude/flipper-commands.txt",
]

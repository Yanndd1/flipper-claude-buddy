"""Common helper for hook scripts to talk to the bridge.

Uses TCP localhost on Windows, Unix socket elsewhere. Plugin user-config
options for transport / serial port / bluetooth name are also resolved here.
"""

import json
import os
import socket
import sys
import tempfile
from pathlib import Path


def _runtime_dir() -> Path:
    if sys.platform == "win32":
        d = Path(tempfile.gettempdir()) / "claude-flipper"
        d.mkdir(parents=True, exist_ok=True)
        return d
    return Path("/tmp")


_RUNTIME_DIR = _runtime_dir()
SOCKET_PATH = str(_RUNTIME_DIR / "claude-flipper-bridge.sock")
PID_PATH = str(_RUNTIME_DIR / "claude-flipper-bridge.pid")
LOG_PATH = str(_RUNTIME_DIR / "claude-flipper-bridge.log")
REFCOUNT_PATH = str(_RUNTIME_DIR / "claude-flipper-bridge.refcount")
TURN_STATS_PATH = str(_RUNTIME_DIR / "claude-flipper-turn-stats.json")
SKIP_STOP_FLAG = str(_RUNTIME_DIR / "claude-flipper-skip-stop.flag")

# IPC selection — TCP on Windows, Unix elsewhere
USE_TCP = sys.platform == "win32" or os.environ.get("FLIPPER_IPC_TCP", "0") == "1"
TCP_HOST = "127.0.0.1"
TCP_PORT = int(os.environ.get("FLIPPER_IPC_TCP_PORT", "47353"))


def is_bridge_running() -> bool:
    """Quick check: is the bridge accepting connections?"""
    if USE_TCP:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        try:
            s.connect((TCP_HOST, TCP_PORT))
            s.close()
            return True
        except (OSError, socket.timeout):
            return False
    else:
        return os.path.exists(SOCKET_PATH)


def send_request(payload: dict, timeout: float = 60.0) -> dict:
    """Send a JSON action to the bridge and return the JSON response.

    Raises ConnectionError if the bridge is unreachable.
    """
    if USE_TCP:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        addr = (TCP_HOST, TCP_PORT)
    else:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        addr = SOCKET_PATH
    s.settimeout(timeout)
    try:
        s.connect(addr)
        s.sendall(json.dumps(payload).encode())
        try:
            s.shutdown(socket.SHUT_WR)
        except OSError:
            pass
        chunks = []
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
        data = b"".join(chunks)
        return json.loads(data.decode()) if data else {}
    finally:
        try:
            s.close()
        except Exception:
            pass


def send_fire_and_forget(payload: dict, timeout: float = 2.0) -> None:
    """Send a JSON action without waiting for a response (best-effort)."""
    try:
        send_request(payload, timeout=timeout)
    except Exception:
        pass


def project_name_from_cwd(cwd: str, max_len: int = 8) -> str:
    """Return a short basename of cwd for use as Flipper notification prefix."""
    if not cwd:
        return ""
    base = os.path.basename(cwd.rstrip("/\\")) or os.path.basename(os.path.dirname(cwd.rstrip("/\\")))
    if not base:
        return ""
    return base[:max_len]


def prefix_with_project(detail: str, cwd: str, max_total: int = 21) -> str:
    """Prefix detail with '<project>: ' so the Flipper shows the source project.

    Truncates to max_total chars. If detail is empty, returns project only.
    """
    project = project_name_from_cwd(cwd, max_len=8)
    if not project:
        return (detail or "")[:max_total]
    if not detail:
        return project[:max_total]
    sep = ": "
    avail = max_total - len(project) - len(sep)
    if avail < 1:
        return project[:max_total]
    return (project + sep + detail)[:max_total]

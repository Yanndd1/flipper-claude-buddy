#!/usr/bin/env python3
"""SessionStart hook (Windows port).

Ensures the bridge daemon is running, then sends a 'claude_connect' notify.
Cross-platform replacement for the original on-session-start.sh.
"""

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

# Import _bridge_client from the same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bridge_client as bc

SOURCES = {
    "startup": "New session",
    "resume":  "Resumed",
    "clear":   "After clear",
    "compact": "After compaction",
}


def read_payload() -> dict:
    try:
        return json.loads(sys.stdin.read())
    except Exception:
        return {}


def find_bridge_module() -> Path | None:
    """Locate the bridge package next to this script (plugin layout)."""
    here = Path(__file__).resolve().parent
    # scripts/ -> ../host-bridge
    candidate = here.parent / "host-bridge"
    if (candidate / "bridge" / "__main__.py").exists():
        return candidate
    return None


def start_bridge() -> bool:
    """Spawn the bridge daemon as a detached pythonw process."""
    bridge_dir = find_bridge_module()
    if bridge_dir is None:
        return False

    # Find pythonw (no console). Fall back to sys.executable.
    pythonw = sys.executable
    if pythonw.lower().endswith("python.exe"):
        pyw = pythonw[:-len("python.exe")] + "pythonw.exe"
        if Path(pyw).exists():
            pythonw = pyw

    env = os.environ.copy()
    # Make sure the bridge package is importable
    env["PYTHONPATH"] = str(bridge_dir) + os.pathsep + env.get("PYTHONPATH", "")
    # Forward Claude plugin config -> bridge env
    for key, target in (
        ("CLAUDE_PLUGIN_OPTION_serial_port", "FLIPPER_SERIAL_PORT"),
        ("CLAUDE_PLUGIN_OPTION_transport", "FLIPPER_TRANSPORT"),
        ("CLAUDE_PLUGIN_OPTION_bluetoothName", "FLIPPER_BT_NAME"),
    ):
        v = os.environ.get(key, "")
        if v:
            env[target] = v
    plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA", "")
    if plugin_data:
        env["FLIPPER_PLUGIN_DATA"] = plugin_data

    # Detached process
    DETACHED_PROCESS = 0x00000008 if sys.platform == "win32" else 0
    CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
    creationflags = DETACHED_PROCESS | CREATE_NO_WINDOW if sys.platform == "win32" else 0

    log_file = open(bc.LOG_PATH, "ab")
    try:
        proc = subprocess.Popen(
            [pythonw, "-m", "bridge"],
            cwd=str(bridge_dir),
            env=env,
            stdout=log_file,
            stderr=log_file,
            stdin=subprocess.DEVNULL,
            creationflags=creationflags,
            close_fds=False,
        )
        # Write pidfile
        try:
            Path(bc.PID_PATH).write_text(str(proc.pid), encoding="utf-8")
        except Exception:
            pass

        # Wait up to 6s for the bridge to start listening
        for _ in range(60):
            if bc.is_bridge_running():
                return True
            time.sleep(0.1)
        return False
    except Exception as e:
        log_file.close()
        print(f"[bridge] start failed: {e}", file=sys.stderr)
        return False


def increment_refcount() -> None:
    try:
        path = Path(bc.REFCOUNT_PATH)
        n = int(path.read_text(encoding="utf-8")) if path.exists() else 0
        path.write_text(str(n + 1), encoding="utf-8")
    except Exception:
        pass


def main():
    payload = read_payload()
    source = payload.get("source") or ""
    subtext = SOURCES.get(source) or (payload.get("model") or "")[:21]

    if not bc.is_bridge_running():
        ok = start_bridge()
        if not ok:
            # No bridge -> exit silently, user can launch it manually
            return

    increment_refcount()

    project_dir = os.getcwd()
    bc.send_fire_and_forget({
        "action": "claude_connect",
        "project_dir": project_dir,
    })

    bc.send_fire_and_forget({
        "action": "notify",
        "sound": "connect",
        "vibro": False,
        "text": "Claude Code",
        "subtext": subtext or "Connected",
    })


if __name__ == "__main__":
    main()

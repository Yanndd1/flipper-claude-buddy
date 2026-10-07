#!/usr/bin/env python3
"""SessionEnd hook (Windows port). Decrements refcount, stops bridge if zero."""

import os
import signal
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bridge_client as bc


def main():
    refcount_path = Path(bc.REFCOUNT_PATH)
    try:
        n = int(refcount_path.read_text(encoding="utf-8")) if refcount_path.exists() else 0
    except Exception:
        n = 0
    n = max(0, n - 1)
    if n > 0:
        refcount_path.write_text(str(n), encoding="utf-8")
        # Still notify disconnect for the closing session (best-effort)
        bc.send_fire_and_forget({"action": "claude_disconnect"})
        return

    # Last session — stop bridge
    refcount_path.unlink(missing_ok=True)
    bc.send_fire_and_forget({"action": "claude_disconnect"})
    pid_path = Path(bc.PID_PATH)
    if pid_path.exists():
        try:
            pid = int(pid_path.read_text(encoding="utf-8"))
            if sys.platform == "win32":
                import ctypes
                PROCESS_TERMINATE = 0x0001
                h = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
                if h:
                    ctypes.windll.kernel32.TerminateProcess(h, 0)
                    ctypes.windll.kernel32.CloseHandle(h)
            else:
                os.kill(pid, signal.SIGTERM)
        except Exception:
            pass
        pid_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Stop hook (Windows port). Notify Flipper when Claude finishes a turn."""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bridge_client as bc
import _xiaozhi_client as xz


def main():
    # Read payload first - on en a besoin meme si le bridge Flipper est mort
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        payload = {}
    interrupted = bool(payload.get("interrupted", False))
    cwd = payload.get("cwd", "") or os.getcwd()

    # Build subtext from turn stats (toujours, meme sans bridge)
    summary = ""
    stats_path = Path(bc.TURN_STATS_PATH)
    if stats_path.exists():
        try:
            stats = json.loads(stats_path.read_text(encoding="utf-8"))
            parts = sorted(stats.items(), key=lambda x: -x[1])
            summary = " ".join(f"{v} {k}" for k, v in parts)
        except Exception:
            pass
        stats_path.unlink(missing_ok=True)

    # Skip flag : si un autre hook a deja notifie directement, on n'envoie rien
    skip_flag = Path(bc.SKIP_STOP_FLAG)
    if skip_flag.exists():
        skip_flag.unlink(missing_ok=True)
        return

    # Prefix with project name so the Flipper shows which project sent this
    subtext = bc.prefix_with_project(summary, cwd)

    # 1. Notif Flipper (best-effort, n'empeche pas Xiaozhi si indispo)
    if bc.is_bridge_running():
        if interrupted:
            bc.send_fire_and_forget({
                "action": "notify",
                "sound": "interrupt",
                "vibro": False,
                "text": "Interrupted",
                "subtext": subtext,
            })
        else:
            bc.send_fire_and_forget({
                "action": "notify",
                "sound": "success",
                "vibro": False,
                "text": "Turn complete",
                "subtext": subtext,
            })

    # 2. Notif Xiaozhi (independant du Flipper) - seulement sur interrupted (turn complete = trop verbeux)
    if interrupted and xz.is_enabled():
        project = bc.project_name_from_cwd(cwd) or "le projet courant"
        xz.notify(f"Tour interrompu sur {project}.", priority="warn")


if __name__ == "__main__":
    main()

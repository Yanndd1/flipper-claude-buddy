#!/usr/bin/env python3
"""StopFailure hook (Windows port). Error notification on Flipper."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bridge_client as bc
import _xiaozhi_client as xz


def main():
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        payload = {}
    error_type = payload.get("error_type", "error")
    cwd = payload.get("cwd", "") or os.getcwd()
    subtext = bc.prefix_with_project(error_type, cwd)

    # 1. Notif Flipper (best-effort)
    if bc.is_bridge_running():
        bc.send_fire_and_forget({
            "action": "notify",
            "sound": "error",
            "vibro": False,
            "text": "API error",
            "subtext": subtext,
        })

    # 2. Notif Xiaozhi (best-effort, independant)
    if xz.is_enabled():
        project = bc.project_name_from_cwd(cwd) or "le projet courant"
        xz.notify(f"Erreur API {error_type} sur {project}.", priority="critical")


if __name__ == "__main__":
    main()

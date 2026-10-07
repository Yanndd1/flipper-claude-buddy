#!/usr/bin/env python3
"""TaskCompleted hook (Windows port). Subagent finished a task."""

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
    name = payload.get("task_name", "")
    cwd = payload.get("cwd", "") or os.getcwd()
    subtext = bc.prefix_with_project(name, cwd)

    # 1. Notif Flipper (best-effort)
    if bc.is_bridge_running():
        bc.send_fire_and_forget({
            "action": "notify",
            "sound": "success",
            "vibro": False,
            "text": "Task done",
            "subtext": subtext,
        })

    # 2. Notif Xiaozhi (best-effort, independant)
    if xz.is_enabled():
        project = bc.project_name_from_cwd(cwd) or "le projet courant"
        xz.notify(f"Tache {name} terminee sur {project}.", priority="info")


if __name__ == "__main__":
    main()

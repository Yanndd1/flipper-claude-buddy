#!/usr/bin/env python3
"""SubagentStop hook (Windows port).

Se declenche quand un sub-agent lance via le tool Agent termine. C'est le bon
hook pour notifier "Claude a fini sa tache" sur les sub-agents (le cas le plus
frequent), distinct de TaskCompleted qui ne vise que les TaskCreate.

Notifie le Flipper (si bridge running) ET le Xiaozhi (si enabled) en best-effort.
Aucun ne bloque l'autre : si l'un est indispo, l'autre fonctionne quand meme.
"""

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
    agent_type = payload.get("agent_type", "agent")[:30]
    cwd = payload.get("cwd", "") or os.getcwd()

    # 1. Notif Flipper (best-effort)
    if bc.is_bridge_running():
        subtext = bc.prefix_with_project(agent_type, cwd)
        bc.send_fire_and_forget({
            "action": "notify",
            "sound": "success",
            "vibro": False,
            "text": "Subagent done",
            "subtext": subtext,
        })

    # 2. Notif Xiaozhi (best-effort, independant du Flipper). Coupee par defaut
    # depuis le 2026-10-07 : avec les workflows, une annonce par minute environ.
    # Reactiver avec la variable utilisateur XIAOZHI_SUBAGENT_NOTIFY=1.
    if xz.is_enabled() and xz._read_user_env("XIAOZHI_SUBAGENT_NOTIFY", "0") == "1":
        project = bc.project_name_from_cwd(cwd) or "le projet courant"
        xz.notify(f"Sous-agent {agent_type} termine sur {project}.", priority="info")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""PostToolUse hook (Windows port). Counts tool usage for the turn summary."""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bridge_client as bc


def main():
    # Note : PAS de bc.is_bridge_running() ici. Ce hook tourne a CHAQUE appel
    # d'outil (chemin le plus chaud) et n'ecrit qu'un fichier local de stats ;
    # ouvrir une socket TCP a chaque fois serait du gaspillage. Le fichier de
    # stats est consomme et nettoye par on-stop.py en fin de tour.
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        return
    tool_name = payload.get("tool_name", "")
    if not tool_name or tool_name.startswith("mcp__"):
        return

    stats_path = Path(bc.TURN_STATS_PATH)
    try:
        stats = json.loads(stats_path.read_text(encoding="utf-8")) if stats_path.exists() else {}
    except Exception:
        stats = {}
    stats[tool_name] = stats.get(tool_name, 0) + 1
    try:
        stats_path.write_text(json.dumps(stats), encoding="utf-8")
    except Exception:
        pass


if __name__ == "__main__":
    main()

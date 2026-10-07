#!/usr/bin/env python3
"""PostToolUseFailure hook (Windows port)."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bridge_client as bc


def main():
    if not bc.is_bridge_running():
        return
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        payload = {}
    tool_name = payload.get("tool_name", "")
    cwd = payload.get("cwd", "") or os.getcwd()
    subtext = bc.prefix_with_project(tool_name, cwd)
    bc.send_fire_and_forget({
        "action": "notify",
        "sound": "error",
        "vibro": False,
        "text": "Tool failed",
        "subtext": subtext,
    })


if __name__ == "__main__":
    main()

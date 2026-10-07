#!/usr/bin/env python3
"""Notification hook (Windows port)."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bridge_client as bc

NOTIFY_MAP = {
    "idle_prompt": ("alert", "Claude", "Waiting for input"),
}


def main():
    if not bc.is_bridge_running():
        return
    try:
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        return
    notification_type = hook_input.get("notification_type", "")
    entry = NOTIFY_MAP.get(notification_type)
    if not entry:
        return
    sound, text, subtext = entry
    cwd = hook_input.get("cwd", "") or os.getcwd()
    subtext = bc.prefix_with_project(subtext, cwd)
    bc.send_fire_and_forget({
        "action": "notify",
        "sound": sound,
        "vibro": False,
        "text": text,
        "subtext": subtext,
    })


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""UserPromptSubmit hook (Windows port). Plays a quiet click on the Flipper."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bridge_client as bc


def main():
    if not bc.is_bridge_running():
        return
    bc.send_fire_and_forget({
        "action": "notify",
        "sound": "led_flash",
        "vibro": False,
        "text": "",
        "subtext": "",
    })


if __name__ == "__main__":
    main()

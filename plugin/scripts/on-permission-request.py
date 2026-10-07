#!/usr/bin/env python3
"""PermissionRequest hook (Windows port) — coordination Flipper + Xiaozhi.

Deux canaux de validation en parallele, le PREMIER qui repond gagne :
  - Flipper : bouton OK (allow) / Back (deny) via le bridge TCP (bloquant ~60s)
  - Xiaozhi : annonce vocale + l'utilisateur dit "approuve"/"refuse" (poll ~60s)

Cas degrades :
  - Flipper seul (xz desactive)         -> comportement Flipper classique
  - Xiaozhi seul (bridge Flipper absent) -> validation 100% vocale
  - Les deux absents                     -> exit 1, Claude affiche son dialog natif
"""

import json
import os
import sys
import threading
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bridge_client as bc
import _xiaozhi_client as xz

TIMEOUT = 60


def extract_detail(tool_name: str, tool_input: dict, limit: int = 21) -> str:
    if "__" in tool_name:
        parts = tool_name.split("__")
        if len(parts) >= 3:
            return parts[-1][:limit]
    if tool_name == "Bash":
        desc = tool_input.get("description", "")
        if desc:
            return desc[:limit]
        cmd = tool_input.get("command", "")
        return cmd[:limit] if cmd else ""
    if tool_name in ("Edit", "Write", "Read"):
        path = tool_input.get("file_path", "")
        return os.path.basename(path)[:limit] if path else ""
    if tool_name in ("WebFetch", "WebSearch"):
        val = tool_input.get("url") or tool_input.get("query", "")
        for prefix in ("https://", "http://"):
            if val.startswith(prefix):
                val = val[len(prefix):]
                break
        return val[:limit]
    if tool_name == "Agent":
        return tool_input.get("description", "")[:limit]
    return ""


def main():
    bridge_up = bc.is_bridge_running()
    xz_on = xz.is_enabled()

    # Aucun canal -> on laisse Claude gerer (dialog natif)
    if not bridge_up and not xz_on:
        sys.exit(1)

    try:
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        sys.exit(1)

    tool_name_raw = hook_input.get("tool_name", "Unknown")
    tool_input = hook_input.get("tool_input", {})

    if "__" in tool_name_raw:
        parts = tool_name_raw.split("__")
        tool_name = f"{parts[0]}_{parts[1]}" if len(parts) >= 2 else tool_name_raw
    else:
        tool_name = tool_name_raw

    detail_short = extract_detail(tool_name_raw, tool_input, limit=21)   # pour l'ecran Flipper
    detail_voice = extract_detail(tool_name_raw, tool_input, limit=80)   # pour la voix
    cwd = hook_input.get("cwd", "") or os.getcwd()
    detail_prefixed = bc.prefix_with_project(detail_short, cwd)
    project = bc.project_name_from_cwd(cwd) or "ce projet"

    decision_id = uuid.uuid4().hex

    # Etat partage entre les deux workers
    state = {"decision": None, "source": None, "always": False, "xz_won": False}
    lock = threading.Lock()
    done = threading.Event()

    def flipper_worker():
        try:
            res = bc.send_request(
                {"action": "permission_request", "tool": tool_name, "detail": detail_prefixed},
                timeout=TIMEOUT,
            )
        except Exception:
            return
        status = res.get("status")
        with lock:
            if state["decision"] is not None:
                return  # l'autre canal a deja gagne
            if status == "ok":
                state["decision"] = "allow" if res.get("allowed") else "deny"
                state["source"] = "flipper"
                state["always"] = res.get("always", False)
                done.set()
            elif status == "ask" and not state["xz_won"]:
                # Flipper a dismisse de lui-meme (l'utilisateur a defere a Claude)
                state["decision"] = "ask"
                state["source"] = "flipper"
                done.set()

    def xiaozhi_worker():
        spoken = (
            f"Claude sur {project} demande l'autorisation pour {tool_name}. "
            f"{detail_voice}. Approuve ou refuse ?"
        )
        xz.notify(spoken, priority="warn", decision_id=decision_id)
        d = xz.poll_decision(decision_id, timeout=TIMEOUT, stop_event=done)
        if d in ("allow", "deny"):
            with lock:
                if state["decision"] is None:
                    state["decision"] = d
                    state["source"] = "xiaozhi"
                    state["xz_won"] = True
                    done.set()
                    # Annuler le canal Flipper : un notify dismisse la permission en attente
                    if bridge_up:
                        bc.send_fire_and_forget({
                            "action": "notify", "sound": "success", "vibro": False,
                            "text": "Repondu par la voix", "subtext": project[:21],
                        })

    threads = []
    if bridge_up:
        threads.append(threading.Thread(target=flipper_worker, daemon=True))
    if xz_on:
        threads.append(threading.Thread(target=xiaozhi_worker, daemon=True))
    for th in threads:
        th.start()

    # Attendre la premiere decision (ou timeout global)
    done.wait(timeout=TIMEOUT + 5)

    # Nettoyage : annuler la decision Xiaozhi en attente si le Flipper a gagne
    if state["source"] == "flipper" and xz_on:
        xz.cancel_decision(decision_id)

    decision = state["decision"]

    if decision == "allow":
        out = {"behavior": "allow"}
        if state["always"]:
            suggestions = hook_input.get("permission_suggestions", [])
            if suggestions:
                out["updatedPermissions"] = suggestions
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PermissionRequest", "decision": out}}))
        sys.exit(0)

    if decision == "deny":
        src = "voix" if state["source"] == "xiaozhi" else "Flipper"
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PermissionRequest",
            "decision": {"behavior": "deny", "message": f"Refuse via {src}"}}}))
        sys.exit(0)

    if decision == "ask":
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PermissionRequest",
            "decision": {"behavior": "ask"}}}))
        sys.exit(0)

    # Timeout des deux canaux -> Claude affiche son dialog natif
    sys.exit(1)


if __name__ == "__main__":
    main()

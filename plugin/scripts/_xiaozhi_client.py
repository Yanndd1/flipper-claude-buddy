"""Minimal client to push TTS notifications to the Xiaozhi server.

Best-effort : never blocks the hook longer than 2s, never raises.
Activation via env var ENABLE_XIAOZHI_NOTIFY=1 (default OFF for safety).

Sur Windows, si la variable n'est pas dans os.environ (cas frequent quand la
session Claude Code a ete lancee AVANT le setx), on tombe en fallback sur
HKEY_CURRENT_USER\\Environment (registre des variables d'env User).
"""
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.request


def _read_user_env(name: str, default: str = "") -> str:
    """Lit une variable d'env utilisateur depuis le registre Windows si absente du process.

    1. Cherche d'abord dans os.environ (process env, heritage du parent)
    2. Sinon, lit HKEY_CURRENT_USER\\Environment (variables d'env User Windows)
    3. Sinon, retourne default

    Sur Linux/macOS, retourne os.environ.get sans fallback registre.
    """
    val = os.environ.get(name, "")
    if val:
        return val
    if sys.platform != "win32":
        return default
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
            try:
                val, _ = winreg.QueryValueEx(key, name)
                return str(val) if val is not None else default
            except FileNotFoundError:
                return default
    except Exception:
        return default


# ─── Configuration ────────────────────────────────────────────────────────
ENABLED = _read_user_env("ENABLE_XIAOZHI_NOTIFY", "0") == "1"
URL = _read_user_env("XIAOZHI_NOTIFY_URL", "http://127.0.0.1:8003/api/claude/notify")
DEFAULT_DEVICE_ID = _read_user_env("XIAOZHI_DEVICE_ID", "")  # optionnel
TIMEOUT_S = float(_read_user_env("XIAOZHI_TIMEOUT", "2.0"))

# Base des routes /api/claude (derivee de l'URL notify)
_BASE = URL.rsplit("/notify", 1)[0] if URL.endswith("/notify") else URL.rsplit("/", 1)[0]


# ─── API ──────────────────────────────────────────────────────────────────
def notify(text: str, device_id: str = "", priority: str = "info", decision_id: str = "") -> bool:
    """POST a TTS message to the Xiaozhi server. Returns True on success.

    Si decision_id est fourni, le serveur enregistre une "decision en attente"
    que poll_decision() pourra recuperer (validation vocale).
    Silently no-op when ENABLE_XIAOZHI_NOTIFY != 1. Caps text to 240 chars.
    """
    if not ENABLED:
        return False
    if not text:
        return False
    payload = {
        "text": text[:240],
        "priority": priority,
    }
    target_device = device_id or DEFAULT_DEVICE_ID
    if target_device:
        payload["device_id"] = target_device
    if decision_id:
        payload["decision_id"] = decision_id
    try:
        req = urllib.request.Request(
            URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            return resp.status == 200
    except urllib.error.HTTPError:
        return False
    except (socket.timeout, urllib.error.URLError, OSError):
        return False
    except Exception:
        return False


def poll_decision(decision_id: str, timeout: float = 60.0, interval: float = 0.6,
                  stop_event=None) -> str:
    """Interroge le serveur pour la decision (allow|deny) jusqu'a timeout.

    Retourne "allow", "deny", ou "" (timeout / erreur / annule).
    stop_event : threading.Event optionnel pour interrompre tot (l'autre canal a repondu).
    """
    if not ENABLED or not decision_id:
        return ""
    url = f"{_BASE}/decision/{decision_id}"
    deadline = time.time() + timeout
    while time.time() < deadline:
        if stop_event is not None and stop_event.is_set():
            return ""
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                decision = data.get("decision")
                if decision in ("allow", "deny"):
                    return decision
        except Exception:
            pass  # serveur indispo : on retente jusqu'au timeout
        time.sleep(interval)
    return ""


def cancel_decision(decision_id: str) -> None:
    """Annule une decision en attente cote serveur (best-effort, quand le Flipper a repondu)."""
    if not ENABLED or not decision_id:
        return
    url = f"{_BASE}/decision/{decision_id}/cancel"
    try:
        req = urllib.request.Request(url, data=b"", method="POST")
        urllib.request.urlopen(req, timeout=TIMEOUT_S).close()
    except Exception:
        pass


def is_enabled() -> bool:
    return ENABLED


if __name__ == "__main__":
    # CLI test : py -3.13 _xiaozhi_client.py "Bonjour Xiaozhi"
    text = " ".join(sys.argv[1:]) or "Test depuis le PC"
    if not ENABLED:
        print("ENABLE_XIAOZHI_NOTIFY=0, simulation only.")
        print(f"Would POST {URL!r} with text={text!r}")
    else:
        ok = notify(text)
        print(f"notify -> {ok}")

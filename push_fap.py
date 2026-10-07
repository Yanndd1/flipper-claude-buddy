"""Push claude_buddy.fap to the Flipper via CLI serial 'storage write_chunk'.

Usage :
  py -3.13 push_fap.py [chemin_local.fap] [PORT]
Le port est auto-detecte (VID 0483 / PID 5740) si non fourni.
"""
import os
import serial
import time
import sys
from serial.tools import list_ports

FLIPPER_VID, FLIPPER_PID = 0x0483, 0x5740


def detect_port():
    """Retourne le port COM du Flipper (VID/PID Flipper Zero), sinon None."""
    cands = [p.device for p in list_ports.comports()
             if p.vid == FLIPPER_VID and p.pid == FLIPPER_PID]
    try:
        cands.sort(key=lambda d: int(d.replace("COM", "")))
    except Exception:
        cands.sort()
    return cands[-1] if cands else None


LOCAL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.expanduser("~"), "claude_buddy.fap")
PORT = sys.argv[2] if len(sys.argv) > 2 else (detect_port() or "COM15")
REMOTE = "/ext/apps/USB/claude_buddy.fap"


def wait_prompt(ser, timeout=5.0):
    deadline = time.time() + timeout
    buf = b""
    while time.time() < deadline:
        if ser.in_waiting:
            buf += ser.read(ser.in_waiting)
            if b">: " in buf:
                return buf.decode("utf-8", errors="replace")
        else:
            time.sleep(0.05)
    return buf.decode("utf-8", errors="replace") + "[TIMEOUT]"


def send_cmd(ser, cmd, timeout=5.0):
    ser.reset_input_buffer()
    ser.write(cmd.encode() + b"\r")
    ser.flush()
    return wait_prompt(ser, timeout)


def main():
    data = open(LOCAL, "rb").read()
    size = len(data)
    print(f"Local file: {LOCAL} ({size} bytes)")

    ser = serial.Serial(PORT, 115200, timeout=2.0, write_timeout=10.0)
    time.sleep(1.5)
    ser.reset_input_buffer()
    ser.write(b"\r")
    time.sleep(0.3)
    ser.reset_input_buffer()
    print("Port ouvert")

    # mkdir parents
    print("mkdir /ext/apps")
    send_cmd(ser, "storage mkdir /ext/apps")
    print("mkdir /ext/apps/USB")
    send_cmd(ser, "storage mkdir /ext/apps/USB")

    # Si fichier existe deja, le supprimer
    print(f"remove {REMOTE}")
    send_cmd(ser, f"storage remove {REMOTE}")

    # write_chunk SIZE puis envoi binaire
    print(f"write_chunk {REMOTE} {size}")
    ser.reset_input_buffer()
    ser.write(f"storage write_chunk {REMOTE} {size}\r".encode())
    ser.flush()
    time.sleep(0.5)
    # Possible message "Ready, send..."
    if ser.in_waiting:
        pre = ser.read(ser.in_waiting).decode("utf-8", errors="replace")
        print(f"  pre-response: {pre.strip()[:200]}")

    # Envoyer les bytes en chunks
    chunk_size = 4096
    sent = 0
    for i in range(0, size, chunk_size):
        chunk = data[i:i+chunk_size]
        ser.write(chunk)
        ser.flush()
        sent += len(chunk)
        if i // chunk_size % 4 == 0:
            print(f"  sent {sent}/{size} ({sent*100//size}%)")
        time.sleep(0.02)
    print(f"  sent {sent}/{size} (100%)")

    # Lire la confirmation
    resp = wait_prompt(ser, timeout=10.0)
    print(f"Response: {resp.strip()[-300:]}")

    # Verifier la taille
    print(f"storage list /ext/apps/USB")
    resp = send_cmd(ser, "storage list /ext/apps/USB")
    print(resp.strip())

    ser.close()
    print("FIN")


if __name__ == "__main__":
    main()

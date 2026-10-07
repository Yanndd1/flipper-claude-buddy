"""USB CDC transport — wraps serial_asyncio. Cross-platform port detection."""

import glob
import logging
import sys

import serial_asyncio

from . import config
from .transport import Transport

log = logging.getLogger(__name__)

# Flipper Zero USB IDs (Momentum & official firmware share the same VID/PID)
FLIPPER_VID = 0x0483
FLIPPER_PID = 0x5740


class UsbTransport(Transport):
    def __init__(self):
        self._reader = None
        self._writer = None

    async def connect(self) -> bool:
        port = self._detect_port()
        if not port:
            log.warning("USB: no Flipper serial port found")
            return False
        try:
            self._reader, self._writer = await serial_asyncio.open_serial_connection(
                url=port, baudrate=config.SERIAL_BAUD
            )
            log.info("USB: connected on %s", port)
            return True
        except Exception as e:
            log.error("USB: connect failed on %s: %s", port, e)
            return False

    async def readline(self) -> bytes:
        return await self._reader.readline()

    async def write(self, data: bytes) -> None:
        self._writer.write(data)

    async def drain(self) -> None:
        await self._writer.drain()

    def close(self) -> None:
        if self._writer:
            try:
                self._writer.close()
            except Exception:
                pass

    @property
    def is_closing(self) -> bool:
        if self._writer:
            t = self._writer.transport
            return t is not None and t.is_closing()
        return False

    # ── Port detection ─────────────────────────────────────────────

    def _detect_port(self) -> str | None:
        if config.SERIAL_PORT:
            return config.SERIAL_PORT

        if sys.platform == "win32":
            return self._detect_port_windows()

        # macOS/Linux: glob the pattern, take the highest suffix (Channel 1 = app port)
        ports = sorted(glob.glob(config.SERIAL_GLOB_PATTERN))
        return ports[-1] if ports else None

    def _detect_port_windows(self) -> str | None:
        """Enumerate via pyserial list_ports, filter by Flipper VID/PID.

        Flipper exposes a single CDC port on Windows (COMx). Channels are
        multiplexed differently than on macOS/Linux dual-port mode.
        """
        try:
            from serial.tools import list_ports
        except ImportError:
            log.error("pyserial not available; cannot enumerate ports on Windows")
            return None
        candidates = []
        for info in list_ports.comports():
            if info.vid == FLIPPER_VID and info.pid == FLIPPER_PID:
                candidates.append(info.device)
                log.debug("Found Flipper: %s (%s)", info.device, info.description)
        if not candidates:
            return None
        # Sort by COM number ascending; take the highest (channel 1)
        try:
            candidates.sort(key=lambda p: int(p.replace("COM", "")))
        except Exception:
            candidates.sort()
        return candidates[-1]

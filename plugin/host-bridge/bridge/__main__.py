"""Entry point: python -m bridge  [--transport usb|ble]"""

import argparse
import asyncio
import logging
import os
import signal
import sys

from . import config
from .daemon import Daemon


def _make_transport(name: str):
    if name == "ble":
        from .transport_bt import BtTransport
        return BtTransport()
    if name == "usb":
        from .transport_usb import UsbTransport
        return UsbTransport()
    from .transport_auto import AutoTransport
    return AutoTransport()


def main():
    parser = argparse.ArgumentParser(description="Flipper Claude Buddy bridge")
    parser.add_argument(
        "--transport",
        choices=["auto", "usb", "ble"],
        default=config.TRANSPORT,
        help="Communication transport (default: %(default)s)",
    )
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error"],
        default=os.environ.get("FLIPPER_LOG_LEVEL", "info"),
        help="Log level (default: info, env: FLIPPER_LOG_LEVEL)",
    )
    args = parser.parse_args()

    # Logging — also write to file
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(config.LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

    transport = _make_transport(args.transport)
    daemon = Daemon(transport)

    async def _run():
        loop = asyncio.get_running_loop()
        stop_event = asyncio.Event()

        # Windows: signal handlers are not supported via asyncio.
        # Fall back to a thread-based watchdog using the default signal module.
        if sys.platform != "win32":
            for sig in (signal.SIGINT, signal.SIGTERM):
                try:
                    loop.add_signal_handler(sig, stop_event.set)
                except (NotImplementedError, RuntimeError):
                    pass
        else:
            # On Windows, asyncio.run() catches KeyboardInterrupt automatically.
            # We rely on that + the finally clause of asyncio.run.
            pass

        daemon_task = asyncio.create_task(daemon.run())
        stopper = asyncio.create_task(stop_event.wait())
        done, _ = await asyncio.wait(
            {daemon_task, stopper}, return_when=asyncio.FIRST_COMPLETED
        )
        if daemon_task not in done:
            daemon_task.cancel()
            try:
                await daemon_task
            except asyncio.CancelledError:
                pass
        stopper.cancel()

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        pass
    finally:
        logging.info("Bridge stopped.")


if __name__ == "__main__":
    main()

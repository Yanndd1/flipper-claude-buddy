"""IPC server for Claude Code hooks — TCP on Windows, Unix socket elsewhere."""

import asyncio
import json
import logging
import os

from . import config

log = logging.getLogger(__name__)


class ClaudeIPC:
    def __init__(self):
        self._server: asyncio.Server | None = None
        self._on_action = None

    def on_action(self, callback):
        self._on_action = callback

    async def start(self):
        if config.IPC_USE_TCP:
            self._server = await asyncio.start_server(
                self._handle_client, host=config.IPC_TCP_HOST, port=config.IPC_TCP_PORT
            )
            log.info("IPC listening on tcp://%s:%d", config.IPC_TCP_HOST, config.IPC_TCP_PORT)
        else:
            if os.path.exists(config.SOCKET_PATH):
                os.unlink(config.SOCKET_PATH)
            self._server = await asyncio.start_unix_server(
                self._handle_client, path=config.SOCKET_PATH
            )
            try:
                os.chmod(config.SOCKET_PATH, 0o666)
            except OSError:
                pass
            log.info("IPC listening on %s", config.SOCKET_PATH)

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        try:
            data = await asyncio.wait_for(reader.read(65536), timeout=10.0)
            if not data:
                return
            request = json.loads(data.decode().strip())
            if self._on_action:
                response = await self._on_action(request)
            else:
                response = {"status": "ok"}
            writer.write(json.dumps(response).encode() + b"\n")
            await writer.drain()
        except asyncio.TimeoutError:
            log.warning("IPC: read timeout")
        except (ConnectionError, BrokenPipeError):
            log.debug("IPC: client disconnected")
        except Exception as e:
            log.error("IPC: error: %s", e)
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def stop(self):
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        if not config.IPC_USE_TCP and os.path.exists(config.SOCKET_PATH):
            os.unlink(config.SOCKET_PATH)

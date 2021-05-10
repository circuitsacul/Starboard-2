import asyncio
import json
import pathlib
import ssl
from typing import Any, Callable, Optional

import websockets

SSL_CONTEXT = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
SSL_CONTEXT.load_verify_locations(pathlib.Path("localhost.pem"))


class WebsocketConnection:
    def __init__(
        self,
        name: str,
        on_command: Callable[[dict[str, Any]], Any],
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        self.on_command = on_command

        self.callbacks: dict[str, list[dict[str, Any]]] = {}
        self.current_callback = 0

        self.websocket: Optional[websockets.WebSocketCommonProtocol] = None
        self.loop = loop or asyncio.get_event_loop()
        self.task = None

        self.name_id = name

    async def send_command(
        self, name: str, data: dict, expect_resp: bool = False
    ) -> Optional[list[dict[str, Any]]]:
        if not self.websocket:
            raise Exception("Websocket not initialized.")

        to_send: dict[str, Any] = {
            "type": "command",
            "name": name,
            "respond": expect_resp,
            "callback": self._next_callback() if expect_resp else None,
            "data": data,
            "author": self.name_id,
        }

        if expect_resp:
            self.callbacks[to_send["callback"]] = []

        try:
            await self.websocket.send(json.dumps(to_send).encode("utf-8"))
        except websockets.ConnectionClosed as exc:
            if exc.code == 1000:
                return None
            raise

        if expect_resp:
            await asyncio.sleep(0.1)
            return self.callbacks.pop(to_send["callback"])
        return None

    async def send_response(self, callback: int, data: Any) -> None:
        if not self.websocket:
            raise Exception("Websocket not initialized.")

        to_send = {
            "type": "response",
            "callback": callback,
            "data": data,
            "author": self.name_id,
        }

        try:
            await self.websocket.send(json.dumps(to_send).encode("utf-8"))
        except websockets.ConnectionClosed as exc:
            if exc.code == 1000:
                return
            raise

    async def handle_command(self, msg: dict[str, Any]):
        resp = await self.on_command(msg)
        if msg["respond"] and resp:
            await self.send_response(msg["callback"], resp)

    async def recv_loop(self):
        if not self.websocket:
            raise Exception("Websocket not initialized.")

        while True:
            try:
                msg = await self.websocket.recv()
            except websockets.ConnectionClosed as exc:
                if exc.code == 1000:
                    return
                raise

            msg: dict[str, Any] = json.loads(msg)

            if msg["type"] == "response":
                if msg["callback"] in self.callbacks:
                    self.callbacks[msg["callback"]].append(msg)
                continue

            await self.loop.create_task(self.handle_command(msg))

    async def ensure_connection(self):
        self.websocket = await websockets.connect(
            "wss://localhost:4000", ssl=SSL_CONTEXT
        )
        await self.websocket.send(self.name_id.encode("utf-8"))
        await self.websocket.recv()

        self.task = self.loop.create_task(self.recv_loop())
        self.task.add_done_callback(self._done_callback)

    def _next_callback(self) -> str:
        self.current_callback += 1
        return str(self.current_callback)

    @staticmethod
    def _done_callback(task: asyncio.Task):
        try:
            task.result()
        except (SystemExit, asyncio.CancelledError):
            pass

    async def close(self, *args, **kwargs) -> None:
        if self.websocket:
            await self.websocket.close(*args, **kwargs)

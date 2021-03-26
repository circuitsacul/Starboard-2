import asyncio
import json
from typing import Optional, List, Union

import websockets


class WebsocketConnection:
    def __init__(
        self,
        name: str,
        on_command: callable,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        self.on_command = on_command

        self.callbacks = {}
        self.current_callback = 0

        self.websocket = None
        self.loop = loop or asyncio.get_event_loop()
        self.task = None

        self.name_id = name

    async def send_command(
        self, name: str, data: dict, expect_resp: bool = False
    ) -> Optional[List[str]]:
        to_send = {
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
                return
            raise

        if expect_resp:
            await asyncio.sleep(0.5)
            return self.callbacks.pop(to_send["callback"])

    async def send_response(
        self, callback: int, data: Union[dict, str]
    ) -> None:
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

    async def recv_loop(self):
        while True:
            try:
                msg = await self.websocket.recv()
            except websockets.ConnectionClosed as exc:
                if exc.code == 1000:
                    return
                raise

            msg = json.loads(msg)

            if msg["type"] == "response":
                if msg["callback"] in self.callbacks:
                    self.callbacks[msg["callback"]].append(msg)
                continue

            resp = await self.on_command(msg)

            if msg["respond"] and resp:
                await self.send_response(msg["callback"], resp)

    async def ensure_connection(self):
        self.websocket = await websockets.connect("ws://localhost:4000")
        await self.websocket.send(self.name_id.encode("utf-8"))
        await self.websocket.recv()

        self.task = self.loop.create_task(self.recv_loop())
        self.task.add_done_callback(self._done_callback)

    def _next_callback(self) -> int:
        self.current_callback += 1
        return self.current_callback

    def _done_callback(self, task: asyncio.Task):
        try:
            task.result()
        except (SystemExit, asyncio.CancelledError):
            pass

    async def close(self, *args, **kwargs) -> None:
        await self.websocket.close(*args, **kwargs)

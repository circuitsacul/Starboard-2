import asyncio
import pathlib
import signal
import ssl
from typing import Dict

import websockets

CLIENTS: Dict[str, websockets.WebSocketServerProtocol] = {}

SSL_CONTEXT = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
SSL_CONTEXT.load_cert_chain(pathlib.Path("localhost.pem"))


async def dispatch(data):
    for _, client in CLIENTS.items():
        await client.send(data)


async def serve(ws: websockets.WebSocketServerProtocol, path: str):
    cluster_name = await ws.recv()
    if isinstance(cluster_name, bytes):
        cluster_name = cluster_name.decode()
    if cluster_name in CLIENTS:
        print(f"IPC: {cluster_name} attempted reconnection")
        await ws.close(4029, "already connected")
        return
    CLIENTS[cluster_name] = ws
    try:
        await ws.send(b'{"status":"ok"}')
        print(f"IPC: {cluster_name} connected successfully")
        async for msg in ws:
            await dispatch(msg)
    finally:
        CLIENTS.pop(cluster_name)
        print(f"IPC: {cluster_name} disconnected")


def run():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    signal.signal(signal.SIGTERM, signal.SIG_DFL)

    server = websockets.serve(serve, "localhost", 4000, ssl=SSL_CONTEXT)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(server)
    loop.run_forever()


if __name__ == "__main__":
    run()

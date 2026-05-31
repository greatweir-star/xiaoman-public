import json
import asyncio

import pytest
import websockets


async def ws_smoke():
    try:
        async with websockets.connect('ws://localhost:18789') as ws:
            print("Connected!")
            await ws.send(json.dumps({"type": "auth", "userId": "test123"}))
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            print("Received:", msg)
    except Exception as e:
        print(f"Error: {e}")


def test_ws_smoke_requires_running_server():
    pytest.skip("Manual websocket smoke: run this file directly with backend listening on :18789.")


if __name__ == "__main__":
    asyncio.run(ws_smoke())

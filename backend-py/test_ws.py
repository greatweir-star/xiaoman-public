import asyncio
import websockets
import json

async def test():
    try:
        async with websockets.connect('ws://localhost:18789') as ws:
            print("Connected!")
            await ws.send(json.dumps({"type": "auth", "userId": "test123"}))
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            print("Received:", msg)
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test())

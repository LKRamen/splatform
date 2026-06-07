"""
Test WebSocket stream: connects, receives 100 frames, validates structure.
Requires server to be running: uvicorn src.backend.server:app --port 8765
"""
import asyncio, json
import websockets


async def main():
    uri = 'ws://localhost:8765/simulate/v1'
    print(f'Connecting to {uri}...')
    async with websockets.connect(uri) as ws:
        frames = []
        for i in range(100):
            msg = await ws.recv()
            frame = json.loads(msg)
            frames.append(frame)

    first, last = frames[0], frames[-1]
    assert len(first['joints']) == 29, f'Expected 29 joints, got {len(first["joints"])}'
    assert len(last['joints'])  == 29, f'Expected 29 joints, got {len(last["joints"])}'
    assert 'scores' in first
    assert 'position' in first
    assert len(first['position']) == 3

    print(f'PASS — received 100 frames')
    print(f'First frame: step={first["step"]} total_score={first["scores"]["total"]:.4f}')
    print(f'Last  frame: step={last["step"]}  total_score={last["scores"]["total"]:.4f}')


asyncio.run(main())

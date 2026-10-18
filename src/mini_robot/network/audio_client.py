import json

from websockets.asyncio.client import connect

from mini_robot.audio.capture import record_audio


async def send_recording(
    host: str,
    port: int = 8765,
    duration: float = 5.0,
    device=None,
):
    print(f"Recording {duration} seconds...")

    audio = record_audio(
        duration=duration,
        sample_rate=16000,
        device=device,
    )

    print("Recording complete")

    uri = f"ws://{host}:{port}"

    async with connect(
        uri,
        max_size=10 * 1024 * 1024,
    ) as websocket:
        print(f"Connected to {uri}")

        await websocket.send(audio.tobytes())
        print("Audio sent")

        response = json.loads(await websocket.recv())

        if "error" in response:
            raise RuntimeError(response["error"])

        return response
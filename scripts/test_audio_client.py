import argparse
import asyncio

from mini_robot.network.audio_client import send_recording


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--duration", type=float, default=5.0)
    parser.add_argument("--device", type=int, default=None)
    args = parser.parse_args()

    result = await send_recording(
        host=args.host,
        duration=args.duration,
        device=args.device,
    )

    print(f"\nRecognised: {result['text']}")
    print(f"Processing time: {result['processing_seconds']}s")


if __name__ == "__main__":
    asyncio.run(main())
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

    print(f"\nYou: {result['text']}")

    if result.get("response"):
        print(f"Mini: {result['response']}")
        print(f"Emotion: {result['emotion']}")
        print(f"Gesture: {result['gesture']}")
        print(f"Personality: {result['personality']}")
        print(f"Total processing: {result['processing_seconds']:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
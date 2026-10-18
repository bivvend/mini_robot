import asyncio

from mini_robot.network.audio_server import run_server


if __name__ == "__main__":
    asyncio.run(run_server())
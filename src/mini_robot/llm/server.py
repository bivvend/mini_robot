# src/mini_robot/llm/server.py

import subprocess
import time
from pathlib import Path

import httpx


class LLMServer:
    def __init__(
        self,
        executable: Path,
        model_path: Path,
        host: str = "127.0.0.1",
        port: int = 8080,
    ):
        self.executable = Path(executable).resolve()
        self.model_path = Path(model_path).resolve()
        self.host = host
        self.port = port
        self.process = None

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def is_ready(self) -> bool:
        try:
            response = httpx.get(
                f"{self.base_url}/health",
                timeout=1.0,
            )
            return response.status_code == 200
        except httpx.RequestError:
            return False

    def start(self, timeout: float = 60.0) -> None:
        if self.is_ready():
            print("LLM server already running.")
            return

        if not self.executable.is_file():
            raise FileNotFoundError(self.executable)

        if not self.model_path.is_file():
            raise FileNotFoundError(self.model_path)

        print("Starting LLM server...")

        self.process = subprocess.Popen(
            [
                str(self.executable),
                "--model", str(self.model_path),
                "--gpu-layers", "all",
                "--ctx-size", "4096",
                "--host", self.host,
                "--port", str(self.port),
            ],
            cwd=self.executable.parent,
        )

        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            if self.is_ready():
                print("LLM server ready.")
                return

            if self.process.poll() is not None:
                raise RuntimeError(
                    f"LLM server exited with code "
                    f"{self.process.returncode}"
                )

            time.sleep(0.5)

        raise TimeoutError(
            "LLM server did not become ready in time."
        )

    def stop(self) -> None:
        # Only stop a server that this instance started.
        if self.process is not None:
            self.process.terminate()

            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()

            self.process = None
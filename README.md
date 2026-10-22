# Mini Robot

**A small, voice-controlled robot powered by a PC-hosted language model, with a Raspberry Pi handling audio.**

Mini Robot is an experimental Python project for building a conversational desktop robot. The Raspberry Pi listens for speech, sends recorded utterances over Wi-Fi to a PC, and speaks the replies using a local text-to-speech model. The PC handles transcription, language-model inference, conversation history, user identification and longer-term memory.

The design is deliberately modular: the robot can use a **local LLM through llama.cpp** for ordinary conversation, or a **remote OpenAI model**. Web search is implemented using the OpenAI API. Personalities are defined in JSON and can give the robot different speaking styles and interests.

> **Project status:** Work in progress. The PC server and Raspberry Pi voice client are implemented and have been used together. Motion/physical expression is not yet integrated into the main audio client; the Arduino firmware directory currently contains placeholders. This README describes the code in this repository rather than a finished robot kit.

## Features

- **Two-device architecture:** Raspberry Pi microphone/speaker client and PC-based inference server, connected by WebSockets.
- **Hands-free voice detection:** Silero VAD detects utterances on the Pi, with pre-speech buffering and a maximum recording duration.
- **Speech recognition:** `faster-whisper` on the PC, currently using `base.en` on CPU, with basic audio normalisation and transcription-quality checks.
- **Text-to-speech:** Piper runs on the Pi; the generated audio is played locally. Emoji and some formatting characters are removed before synthesis.
- **LLM backends:** local OpenAI-compatible llama.cpp server, or the OpenAI API for conversation.
- **Structured responses:** Pydantic `RobotResponse` objects contain `speech`, `emotion` and `gesture` fields.
- **Personalities:** JSON definitions for neutral, evil and super-cute variants, including traits, speaking style and initial interests.
- **Conversation memory:** SQLite-backed conversation history and semantic memories, with a background reflection worker.
- **User identification:** an explicit spoken introduction can select a user-specific conversation and memory context.
- **Voice commands:** volume up, volume down and mute are routed to the Pi without a normal LLM response.
- **Web search:** an explicit spoken search request uses the OpenAI Responses API `web_search` tool.

## Architecture

```text
       Raspberry Pi                              PC / server
  ┌───────────────────────┐              ┌────────────────────────────┐
  │ USB microphone        │              │ WebSocket server           │
  │       ↓               │  16 kHz PCM  │       ↓                    │
  │ Silero voice detection├─────────────►│ faster-whisper             │
  │                       │              │       ↓                    │
  │                       │              │ User / command detection   │
  │                       │              │       ↓                    │
  │                       │              │ Conversation + memory      │
  │                       │              │       ↓                    │
  │                       │              │ Local or remote LLM        │
  │                       │◄─────────────┤ JSON reply / command       │
  │ Piper TTS or command  │              │                            │
  │       ↓               │              │ Background reflection      │
  │ Speaker               │              │ SQLite database            │
  └───────────────────────┘              └────────────────────────────┘
```

The Pi sends **mono, signed 16-bit little-endian PCM at 16 kHz** as binary WebSocket messages. The server returns JSON. Ordinary replies include the text to speak plus emotion and gesture labels; local control commands have `type: "command"`.

The current Pi client logs emotion and gesture values but does not yet turn them into physical movement or a face display.

## Repository layout

```text
mini_robot/
├── data/
│   ├── personality.json
│   ├── personality_neutral.json
│   ├── personality_evil.json
│   ├── personality_super_cute.json
│   └── memory.db                 # Runtime SQLite database in supplied archive
├── firmware/mini_robot/         # Arduino / motion placeholders
├── scripts/                     # Development and diagnostic scripts
├── src/mini_robot/
│   ├── main.py                   # PC WebSocket server
│   ├── main_pi.py                # Raspberry Pi audio client
│   ├── config.py                 # Model and personality configuration
│   ├── audio/                    # Capture, VAD, Whisper, Piper, volume
│   ├── commands/                 # Spoken-command detection
│   ├── conversation/             # History, user detection, memory, reflection
│   ├── llm/                      # LLM client, schemas, llama.cpp launcher
│   ├── personality/              # Personality prompts and interests
│   ├── network/                  # Earlier networking components
│   └── robot/                    # Robot controller/protocol placeholders
├── tests/                        # Development tests
├── pyproject.toml                # Currently empty
└── LICENSE                       # GNU GPL v3
```

The `data/voices/` directory and Piper voice files were omitted from the shared archive because of their size. They must be supplied separately on the Pi.

## Hardware

**Raspberry Pi side**

- Raspberry Pi capable of running Python and connecting to the PC over Wi-Fi (developed with a Raspberry Pi 5).
- USB microphone.
- Speaker or USB audio output.
- A Piper ONNX voice model and its accompanying configuration file.

**PC side**

- Windows, Linux or another system capable of running Python, `faster-whisper` and an LLM backend.
- For offline conversation, a working [llama.cpp](https://github.com/ggml-org/llama.cpp) server and a compatible GGUF model.
- For OpenAI-hosted conversation or web search, an OpenAI API key and internet connectivity.

The local configuration references **Qwen3-4B-Instruct-2507** through a llama.cpp OpenAI-compatible endpoint. GPU acceleration is useful but not required for the CPU-based Whisper configuration in this repository.

## Installation

> **Important:** The supplied `pyproject.toml` is empty and there is no populated dependency lockfile. The commands below install the dependencies evident from the source. They are a starting point, **not** a reproducible, tested installation recipe. A packaging file and pinned requirements should be added later.

Clone the repository separately on the PC and the Pi:

```bash
git clone https://github.com/bivvend/mini_robot.git
cd mini_robot
```

Create a Python virtual environment appropriate for your platform and activate it.

**Windows (PowerShell):**

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

**Raspberry Pi / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### PC dependencies

```bash
python -m pip install openai pydantic websockets numpy faster-whisper httpx
```

### Raspberry Pi dependencies

The Pi uses PortAudio through `sounddevice`. On Raspberry Pi OS, system audio libraries may be required:

```bash
sudo apt update
sudo apt install -y libportaudio2 libsndfile1
python -m pip install numpy sounddevice soundfile websockets silero-vad onnxruntime piper-tts emoji
```

Some installations of Silero VAD also require PyTorch and/or additional dependencies; follow the upstream package's installation instructions if necessary. Piper's package name and supported Python versions can vary by platform.

### Importing the `src` package

Until project packaging is configured, run the modules with `src` on `PYTHONPATH` **from the repository root**.

**Windows PowerShell:**

```powershell
$env:PYTHONPATH = "src"
```

**Linux / Raspberry Pi:**

```bash
export PYTHONPATH=src
```

This avoids assuming that `pip install -e .` works while `pyproject.toml` is empty.

## PC setup and running the server

### 1. Choose the personality and LLM mode

Edit `src/mini_robot/config.py`:

```python
USE_REMOTE_LLM_FOR_CONVERSATION = False
USE_REMOTE_LLM_FOR_REFLECTION = True
PERSONALITY = "personality_neutral.json"
```

Set `USE_REMOTE_LLM_FOR_CONVERSATION` to `True` to use the remote OpenAI model for ordinary replies. The server currently constructs **both** local and remote clients and uses the remote client for web search. The remote model identifier is set in `src/mini_robot/main.py`; change it there if necessary to a model available to your API account.

Other personality files in `data/` include `personality_evil.json` and `personality_super_cute.json`.

`config.py` also contains machine-specific Windows paths for the llama.cpp executable and GGUF model. Update those paths for your machine if using the `LLMServer` launcher; the main server currently expects the local LLM endpoint to be running separately.

### 2. Start a local llama.cpp server (local conversation mode)

Start llama.cpp separately with your downloaded model, for example:

```bash
llama-server -m /path/to/model.gguf --host 127.0.0.1 --port 8080 --ctx-size 4096 --reasoning-format none
```

The Python `LLMClient` defaults to `http://127.0.0.1:8080/v1`. The model must support the structured output requested by `RobotResponse`.

### 3. Configure the OpenAI API key

The remote client reads `OPENAI_API_KEY` from the environment. It is instantiated at server startup even when local conversation is selected.

**Windows PowerShell:**

```powershell
$env:OPENAI_API_KEY = "your-api-key"
```

**Linux / macOS:**

```bash
export OPENAI_API_KEY="your-api-key"
```

Do not commit API keys. The `.env.example` file in this archive is empty and the application does **not** automatically load `.env` files.

### 4. Start the server

From the repository root with the environment active and `PYTHONPATH` configured:

```bash
python -m mini_robot.main
```

The server listens on **`0.0.0.0:8765`** by default. The port, Whisper model, transcription threshold and reflection interval are currently constants near the top of `src/mini_robot/main.py`.

Ensure the PC firewall permits the Pi to reach TCP port 8765 on your trusted local network. The WebSocket connection is currently unencrypted and unauthenticated; **do not expose it directly to the public internet**.

## Raspberry Pi setup and running the client

### 1. Install a Piper voice

Place the downloaded Piper model and its matching JSON configuration file on the Pi, for example:

```text
data/voices/
├── en_GB-alan-medium.onnx
└── en_GB-alan-medium.onnx.json
```

The code's default path is `data/voices/en_GB-alan-medium.onnx`, relative to the repository root. Voice files are not included in the supplied ZIP.

### 2. Connect audio devices

Connect the microphone and speaker and verify that the Pi recognises them. If the microphone isn't the default input device, inspect the available devices:

```bash
python -c "import sounddevice as sd; print(sd.query_devices())"
```

### 3. Start the client

With the virtual environment active and `PYTHONPATH=src`, run:

```bash
python -m mini_robot.main_pi --host 192.168.1.100
```

Replace `192.168.1.100` with the PC's LAN address. Optional arguments:

```bash
python -m mini_robot.main_pi \
  --host 192.168.1.100 \
  --port 8765 \
  --device 0 \
  --voice data/voices/en_GB-alan-medium.onnx
```

The client captures audio at **16 kHz**, uses **512-sample** blocks, and sends completed utterances to the server. It then waits for a reply, performs local volume commands or generates speech with Piper, clears any audio captured during processing/playback, and resumes listening.

The current client does **not** automatically reconnect after a network failure; restart it after restoring the connection.

## Using Mini

Speak naturally once the Pi reports that it is connected and listening. Some example interactions:

| Say | Behaviour |
| --- | --- |
| “Hello Mini, I'm Alex.” | Recognises an explicit introduction and selects Alex's user session. |
| “What are black holes?” | Asks the selected LLM and speaks the structured response. |
| “Volume up.” | Sends a local volume command to the Pi. |
| “Speak quieter.” | Reduces the Pi playback volume. |
| “Mute.” | Mutes local playback. |
| “Search the web for the latest space news.” | Uses the remote OpenAI web-search tool and speaks the result. |

**User identification is deliberately strict:** the current `UserDetector` expects a greeting addressed to a configured robot name followed by an introduction, such as “Hello Mini, I'm Alex.” Simply saying “My name is Alex” is **not** recognised by the current regular expression. The configured robot names are in `config.ROBOT_NAMES`.

Volume and web-search phrases are defined in `src/mini_robot/commands/router.py` and can be extended there.

## Conversation, personality and memory

The robot personality is loaded from a JSON file and converted into a system prompt. The LLM returns a validated `RobotResponse` containing spoken text, an emotion and a gesture. The Pi currently uses the spoken text and logs the other fields for future hardware/face integration.

When a user is identified, the PC creates a user-scoped `ConversationManager` backed by `data/memory.db`. It records messages, retrieves relevant context and uses a background `ReflectionWorker` to extract selected longer-term memories. Anonymous conversations do not write personal conversation history in the same way.

Robot interests are stored using `RobotInterestStore` and included in the system prompt. Initial interests are seeded from the active personality. The intention is for Mini to have its own curiosities rather than merely repeat the user's interests.

**Privacy:** `data/memory.db` contains persisted conversation and memory information. Treat it as private application data; don't publish real user conversations or commit a populated database to a public repository.

## Speech pipeline details

- **VAD on Pi:** `VoiceActivityDetector` uses Silero ONNX with 300 ms of pre-speech buffering, a 1,500 ms silence threshold and a 15-second maximum utterance by default.
- **PCM transport:** raw 16-bit little-endian audio, 16 kHz mono, over WebSockets.
- **Whisper on PC:** `WhisperSTT` converts PCM to `float32`, applies limited gain and transcribes in English using `base.en` with CPU/int8 inference.
- **Low-confidence handling:** if transcription is empty or `avg_logprob` is below the configured threshold (currently `-0.8`), the server asks the user to repeat the utterance. This is a heuristic, not a calibrated confidence score.
- **Piper on Pi:** text is cleaned of emoji and selected formatting characters, and an ellipsis is appended before speech synthesis. The Pi synthesises and plays the WAV locally.

## WebSocket messages

**Pi → PC:** binary PCM bytes representing a detected utterance.

**PC → Pi, conversational response:**

```json
{
  "type": "response",
  "text": "What are black holes?",
  "response": "They're regions of spacetime with extremely strong gravity.",
  "emotion": "curious",
  "gesture": "nod"
}
```

Normal conversation responses may also contain the active personality, user ID, memory status and timing measurements.

**PC → Pi, hardware command:**

```json
{
  "type": "command",
  "name": "volume_up",
  "text": "Volume up"
}
```

Errors use an `error` key. The Pi logs errors rather than trying to speak them.

## Development scripts and tests

The `scripts/` directory includes experiments and diagnostics for audio capture, VAD, Whisper, Piper, LLM connections, personalities, memory, user detection and web search. The `tests/` directory contains early tests for the conversation, LLM and personality modules.

These scripts are useful for isolating a problem before running the full two-device system. They are development utilities, not a fully automated integration test suite.

## Current limitations and planned directions

- **Physical expression:** emotion and gesture labels are produced but are not yet connected to actuators or a display.
- **Deployment:** automatic startup/reconnection and service configuration are not included in the current entry points.
- **Packaging:** add a real `pyproject.toml`, separate PC/Pi dependency groups and pinned versions.
- **Configuration:** move hard-coded paths, ports, model names and API options into documented configuration/environment variables.
- **Web search context:** explicit search works, but the search tool currently receives only the extracted query rather than the complete conversation context.
- **Security:** add appropriate authentication/encryption if operating beyond a trusted LAN.
- **Repository hygiene:** ignore local databases, `.env`, caches, build metadata and large voice/model files before publishing real runtime data.

## Licence

This repository includes the **GNU General Public License, version 3 (GPL-3.0)**. See [`LICENSE`](LICENSE).

---

*Mini Robot is an ongoing personal robotics and conversational AI experiment.*

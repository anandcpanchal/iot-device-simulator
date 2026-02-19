# IoT Device Simulator 🌐

A lightweight, highly configurable IoT device simulation platform designed to serve as a companion for the **[rust-mqtt-ingestor](https://github.com/anandcpanchal/rust-mqtt-ingestor)** project. This tool allows developers to simulate thousands of IoT devices publishing data via MQTT with customizable payloads, intervals, and data types, facilitating end-to-end testing of data ingestion pipelines.

## ✨ Features

- **🚀 High Performance**: Built with FastAPI and Python's `asyncio`, capable of simulating thousands of devices concurrently.
- **🎨 Dynamic Dashboard**: A modern, responsive web interface to manage your simulation in real-time.
- **🛠️ Advanced Payload Control**:
  - **Auto-Headers**: Each payload includes `device_id`, `time` (ISO 8601), and an auto-incrementing `sequence_id`.
  - **Flexible Data Types**: Support for `int`, `float`, `bool`, `string`, and auto-populated `timestamp`.
  - **Flat JSON**: Messages are published at the root level for maximum compatibility.
- **📥 Command & Control**: Devices can subscribe to individual topics to receive and display messages.
- **📂 Multiple Modes**:
  - **Random Mode**: Generate data based on configurable ranges and rules.
  - **CSV Playback**: Stream real-world sensor data from CSV files.
- **👯 Device Duplication**: Clone existing device configurations with a single click.
- **🐳 Docker Ready**: Fully containerized for easy deployment.

## 🛠️ Tech Stack

- **Backend**: Python 3.13, FastAPI, `paho-mqtt`.
- **Database**: SQLite (via `aiosqlite`).
- **Frontend**: Vanilla JS, HTML5, CSS3 (Modern Responsive Design).
- **Environment**: Managed by `uv`.

## 🚀 Getting Started

### Prerequisites

- [Python 3.13+](https://www.python.org/)
- [uv](https://github.com/astral-sh/uv) (Recommended)
- An MQTT Broker (e.g., [EMQX](https://www.emqx.io/) or [Mosquitto](https://mosquitto.org/))

### Local Setup

1. **Clone and Install**:
   ```bash
   # Create environment and install dependencies
   uv sync
   ```

2. **Configure Environment**:
   Create a `.env` file (or set environment variables):
   ```env
   MQTT_HOST=localhost
   MQTT_PORT=1883
   MQTT_USERNAME=your_user
   MQTT_PASSWORD=your_password
   ```

3. **Run the Simulator**:
   ```bash
   uv run uvicorn app.main:app --reload
   ```
   Visit `http://localhost:8000` to access the dashboard.

### Docker Setup

```bash
docker compose up --build
```

## 📖 How to Use

1. **Add a Device**: Open the dashboard and click "Add Device".
2. **Configure Parameters**:
   - Add parameters like `temperature` (float), `battery` (int), or `status` (string).
   - Use the `timestamp` type for auto-generated ISO times.
3. **Control Simulation**: Use the **Start/Stop** buttons on each device card to toggle data publishing.
4. **Monitor Messages**: If a "Subscribe Topic" is configured, received messages will appear directly on the device card.
### 📊 CSV Playback Mode

Switch from random data to streaming real-world sensor logs.

1. **Prepare your CSV**:
   The simulator treats each row as a message. Headers are used as JSON keys.
   ```csv
   temperature,humidity,status
   22.5,45.0,NORMAL
   23.1,44.8,WARNING
   ```

2. **Upload & Activate**:
   - **Web UI**: Click the **CSV** button on a device card to upload your file. The device mode will automatically switch to `CSV_PLAYBACK`.
   - **API**:
     ```bash
     curl -X POST "http://localhost:8000/api/devices/{uuid}/upload-csv" \
          -F "file=@your_data.csv"
     ```

3. **Looping**: By default, the simulator will restart from the first row after reaching the end of the file. This can be toggled in the device settings.

## 📂 Project Structure

- `app/`: Pure Python backend (API & Simulation Engine).
- `static/`: Frontend assets (Dashboard UI).
- `data/`: SQLite database and local CSV storage.
- `docker-compose.yml`: Local infrastructure setup.

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).

---
Developed with clean code, modular architecture, and performance in mind.

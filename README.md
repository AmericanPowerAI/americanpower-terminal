# 🧐 American Power Terminal

> ⚡️ Advanced remote Linux command execution backend with FastAPI, AI integration, and Kali tools compatibility — built for the Lea-Nero Android terminal on [AmericanPower.us](https://www.americanpower.us/).

## 🔥 Features

- ✅ FastAPI-based API for shell command execution
- ✅ Works with common Linux commands (`ls`, `ping`, `nmap`, etc.)
- ✅ Secure command whitelist
- ✅ Destroy logs, toggle firewall, proxy, VPN, and Tor (simulated options)
- ✅ Future: AI-enhanced command suggestions and smart terminal

---

## 📁 Folder Structure

```
americanpower-terminal/
├── app.py                  # FastAPI application setup
├── terminal_routes.py     # Command execution and utilities API
├── requirements.txt       # Python dependencies
├── Procfile               # Render deployment start command
└── README.md              # This file
```

---

## 🚀 Quick Start

### 🔧 Requirements

- Python 3.8+
- Git (optional, for cloning)
- Linux (or WSL/macOS/compatible shell environment)

### ⚒️ Setup

```bash
git clone https://github.com/AmericanPowerAI/americanpower-terminal.git
cd americanpower-terminal
python -m venv venv
venv\Scripts\activate  # On Windows
pip install -r requirements.txt
```

### ▶️ Run the Server

```bash
uvicorn app:app --reload --port 10000
```

This starts your API at: **http://localhost:10000**

---

## 📡 API Endpoints

### `POST /terminal/run`
Run a command (only whitelisted ones).

**Request**
```json
{
  "command": "ls"
}
```
**Response**
```json
{
  "output": "...command output..."
}
```

### Other Endpoints
- `/terminal/destroy-logs`: Delete log and temp files
- `/terminal/proxy`: Enable proxy (simulated)
- `/terminal/firewall`: Enable UFW firewall
- `/terminal/tor`: Start Tor service (if available)
- `/terminal/vpn`: Simulate VPN activation

---

## 🔐 Security Tips

- Deploy with authentication (API keys, JWT, etc.)
- Run inside a sandbox or Docker container
- Log requests and monitor for abuse

---

## 📆 Coming Soon

- AI-guided shell assistant (via Nero)
- Tiered command access (Free/Pro/Enterprise)
- Full frontend web terminal with integrated API

---

## 📢 Contact
Need help? Contact us at: [help@americanpower.us](mailto:help@americanpower.us)

© 2025 American Power Global. All rights reserved.

# 🧠 American Power Terminal

> ⚡️ An advanced remote Linux command execution backend with AI integration, real shell support, and Kali tools compatibility — built for the Lea-Nero Android terminal on [AmericanPower.us](https://www.americanpower.us/).

## 🔥 Features

- ✅ Fully working shell execution (`bash`, `sh`, or your default shell)
- ✅ Works with any Linux command (`ls`, `apt`, `ping`, etc.)
- ✅ Integrates into Google Sites or any frontend using simple fetch
- ✅ Optional AI-enhanced command assist mode (coming soon)
- ✅ Secure sandbox (local-only by default, restrict as needed)
- ✅ Compatible with **Kali tools** and Linux pentest utilities
- ✅ Returns real-time stdout + stderr

---

## 📁 Folder Structure

americanpower-terminal/ ├── server.js # Node.js backend for executing shell commands ├── package.json # Dependencies └── README.md # This file

yaml
Copy
Edit

---

## 🚀 Quick Start

### 🔧 Requirements

- Node.js (v18+)
- Linux environment (for full compatibility)

### 🛠 Install

```bash
git clone https://github.com/AmericanPowerAI/americanpower-terminal.git
cd americanpower-terminal
npm install
▶️ Run
bash
Copy
Edit
npm start
This starts the terminal server on http://localhost:5005.

📡 API
POST /exec
Run any shell command and return the output.

Request
json
Copy
Edit
{
  "cmd": "ls -la"
}
Response
json
Copy
Edit
{
  "output": "total 8\n-rw-r--r-- 1 user user 0 Apr 21 test.txt"
}
⚠️ Commands execute on your server, so restrict access before deploying publicly.

🔐 Security Tips
Use authentication (API keys or tokens) before production.

Limit commands if exposing to public users.

Run inside a secure VM or container (e.g. on a Kali VPS).

Regularly audit logs for abuse or dangerous commands.

🌐 Use with Frontend
Embed this in any HTML frontend (e.g., Google Sites, React, etc):

js
Copy
Edit
const res = await fetch('https://your-terminal-backend.com/exec', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ cmd: 'ls -la' })
});
const data = await res.json();
console.log(data.output);
🧰 Optional: Preload Kali Tools
Run this if you're on a Debian/Kali-compatible server:

bash
Copy
Edit
sudo apt update && sudo apt install -y kali-linux-core
This gives you access to hundreds of tools like nmap, hydra, sqlmap, etc.

📫 Contact
Need help setting this up? Reach us at help@americanpower.us

© 2025 American Power Global. All rights reserved.

yaml
Copy
Edit

---

### ✅ Next Steps:

- I can generate the full backend files (`server.js`, `package.json`) and zip them for upload if you want.
- Want me to do that now and send you a GitHub-ready ZIP?

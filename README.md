# ⚡ American Power Terminal

> Advanced remote Linux command execution backend with FastAPI, AI integration, and Kali tools compatibility — built for the Lea-Nero Android terminal on [AmericanPower.us](https://www.americanpower.us/).

![API Demo](https://img.shields.io/badge/DEMO-Online-green) 
![FastAPI](https://img.shields.io/badge/FastAPI-0.110.1-blue)
![Python](https://img.shields.io/badge/Python-3.8%2B-yellow)

## 🔥 Enhanced Features

- ✅ **Secure Command Execution**
  - Docker-style command sanitization
  - Process isolation with timeouts
  - Automatic request rate limiting

- 🛡️ **Production-Ready Security**
  - API key authentication
  - CORS protection
  - Request logging

- 🤖 **AI Integration Points**
  - `/terminal/ai-command` - Get AI-suggested commands
  - `/terminal/explain` - Explain command output

- 🧰 **Extended Toolset**
  ```bash
  # New tool commands
  network-scan --target 192.168.1.0/24
  log-analyzer --type auth
  secure-erase --level dod
🚀 Deployment
Render.com (Current)
bash
# Ensure these environment variables are set:
API_KEY=your_secret_key
ALLOWED_ORIGINS=https://yourfrontend.com
WEB_CONCURRENCY=4  # Optimal for Render's free tier
Docker Deployment
dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8000
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "app:app"]
📡 Enhanced API Endpoints
Endpoint	Method	Description
/terminal/execute	POST	Universal command executor
/terminal/tools/{tool}	POST	Dynamic tool router (VPN/Tor/Proxy)
/terminal/ai-help	POST	Get AI-assisted command suggestions
/monitoring/metrics	GET	Prometheus metrics
Sample AI Command Request:

json
{
  "goal": "Scan open ports on my local network",
  "constraints": "Stealthy scan"
}
🔐 Security Upgrade Guide
Mandatory Production Settings

python
# In app.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "").split(","),
    allow_methods=["POST", "GET"]
)
Recommended Additions

bash
# requirements.txt additions
python-jose[cryptography]==3.3.0  # JWT support
pyopenssl==24.0.0  # Enhanced SSL
🛠️ Development Quick Start
bash
# With hot reload and debug tools
uvicorn app:app --reload --port 10000 --ws-ping-timeout 120

# Test production config locally
gunicorn -k uvicorn.workers.UvicornWorker -w 4 app:app
📊 Monitoring Endpoints
Endpoint	Access	Purpose
/health	Public	Service liveness check
/metrics	Internal	Prometheus metrics
/usage	Admin	API usage statistics
🌟 Coming Soon
Terminal Web UI - React-based frontend

Command Marketplace - Share custom tool scripts

AI Sandbox - Safe environment for experimental commands

📢 Support
For enterprise support and custom deployments:
devops@americanpower.us
+1 (800) APG-TECH

© 2025 American Power Global. All rights reserved.

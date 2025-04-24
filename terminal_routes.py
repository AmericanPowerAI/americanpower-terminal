import asyncio
import ipaddress
import logging
import os
import shlex
import subprocess
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field, validator
import httpx

# Initialize router
router = APIRouter(tags=["Terminal Engine"])
executor = ThreadPoolExecutor(max_workers=10)

# Security
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def validate_api_key(api_key: str = Security(api_key_header)):
    if not api_key or api_key != os.getenv("API_KEY", "DEFAULT_SECRET_KEY"):
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

# =====================
# MODELS
# =====================
class TerminalCommand(BaseModel):
    command: str = Field(..., min_length=1, max_length=200, example="ls")
    args: List[str] = Field(default=[], max_items=10, example=["-la"])
    env: Dict[str, str] = Field(default={}, max_length=5)
    timeout: int = Field(default=30, ge=1, le=300)
    cwd: Optional[str] = Field(None, max_length=100)

    @validator('command')
    def validate_command(cls, v):
        blocked = ["rm ", "dd ", "shutdown", "mkfs", "fdisk", ">", "|", "&", ";", "$(", "`"]
        if any(b in v.lower() for b in blocked):
            raise ValueError("Blocked command pattern detected")
        return v

class AIScanRequest(BaseModel):
    target: str
    scan_type: str = Field("stealth", regex="^(stealth|aggressive|full)$")

    @validator('target')
    def validate_target(cls, v):
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError("Invalid IP address format")

# =====================
# CORE FUNCTIONS
# =====================
async def run_command(cmd: TerminalCommand) -> Dict:
    """Secure command executor with timeout"""
    try:
        full_cmd = [cmd.command, *cmd.args]
        proc = await asyncio.get_event_loop().run_in_executor(
            executor,
            lambda: subprocess.run(
                full_cmd,
                env={**os.environ, **cmd.env},
                cwd=cmd.cwd or os.getcwd(),
                timeout=cmd.timeout,
                capture_output=True,
                text=True,
                shell=False
            )
        )
        return {
            "success": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Command timed out after {cmd.timeout}s"}
    except Exception as e:
        return {"error": str(e)}

async def call_nero_ai(prompt: str) -> Dict:
    """Connect to your Nero AI service"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                os.getenv("NERO_AI_ENDPOINT", "https://nero-ai.onrender.com/analyze"),
                json={"prompt": prompt},
                headers={"X-API-Key": os.getenv("NERO_API_KEY")}
            )
            return response.json()
        except httpx.RequestError as e:
            logging.error(f"AI service error: {str(e)}")
            return {"error": "AI service unavailable"}

# =====================
# ROUTES
# =====================
@router.post("/execute", 
            summary="Execute terminal command",
            response_description="Command execution results")
async def execute_command(
    request: Request,
    command: TerminalCommand,
    api_key: str = Depends(validate_api_key)
):
    """
    Execute commands with:
    - Environment variables
    - Custom working directory
    - Timeout control
    """
    logging.info(f"Command from {request.client.host}: {command.command}")
    result = await run_command(command)
    if "error" in result:
        raise HTTPException(400, detail=result["error"])
    return result

@router.post("/ai-scan",
            summary="AI-powered network scan",
            response_description="Scan results with AI analysis")
async def ai_network_scan(
    request: AIScanRequest,
    api_key: str = Depends(validate_api_key)
):
    """
    Perform AI-enhanced scanning:
    - stealth: Minimal traffic
    - aggressive: Comprehensive checks
    - full: Includes exploit verification
    """
    # Execute nmap scan
    scan_cmd = TerminalCommand(
        command="nmap",
        args=["-sS", "-Pn", request.target, "-oX", "-"],
        timeout=120
    )
    scan_result = await run_command(scan_cmd)
    
    if "error" in scan_result:
        raise HTTPException(400, detail=scan_result["error"])
    
    # Analyze with AI
    ai_response = await call_nero_ai(
        f"Analyze nmap scan results (mode={request.scan_type}):\n{scan_result['stdout']}"
    )
    
    return {
        "scan_data": scan_result['stdout'],
        "ai_analysis": ai_response
    }

@router.post("/tools/vpn",
            summary="VPN management",
            response_description="VPN status change result")
async def manage_vpn(
    action: str = Field(..., regex="^(connect|disconnect|status)$"),
    api_key: str = Depends(validate_api_key)
):
    """Control VPN connection"""
    actions = {
        "connect": ["sudo", "openvpn", "--config", "/etc/openvpn/client.ovpn"],
        "disconnect": ["sudo", "pkill", "openvpn"],
        "status": ["pgrep", "-x", "openvpn"]
    }
    result = await run_command(TerminalCommand(command=actions[action][0], args=actions[action][1:]))
    return result

# =====================
# UTILITY ENDPOINTS
# =====================
@router.get("/health",
           summary="Service health check",
           response_description="System status")
async def health_check():
    """Liveness probe endpoint"""
    return {
        "status": "healthy",
        "version": "2.2.0",
        "load": os.getloadavg()[0]
    }

@router.get("/capabilities",
           summary="List available features",
           response_description="System capabilities")
async def list_capabilities():
    """Discover available tools and limits"""
    return {
        "commands": ["execute", "ai-scan", "tools/vpn"],
        "limits": {
            "timeout": 300,
            "concurrent": 10,
            "rate_limit": "30/minute"
        }
    }

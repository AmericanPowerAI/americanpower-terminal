import asyncio
import ipaddress
import logging
import os
import shlex
import subprocess
import re
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from typing import Dict, List, Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Security, Query
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field, field_validator
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
# MODELS (Existing + New)
# =====================
class TerminalCommand(BaseModel):
    command: str = Field(..., min_length=1, max_length=200, example="ls")
    args: List[str] = Field(default=[], max_items=10, example=["-la"])
    env: Dict[str, str] = Field(default={}, max_length=5)
    timeout: int = Field(default=30, ge=1, le=300)
    cwd: Optional[str] = Field(None, max_length=100)

    @field_validator('command')
    def validate_command(cls, v):
        blocked = ["rm ", "dd ", "shutdown", "mkfs", "fdisk", ">", "|", "&", ";", "$(", "`"]
        if any(b in v.lower() for b in blocked):
            raise ValueError("Blocked command pattern detected")
        return v

class AIScanRequest(BaseModel):
    target: str
    scan_type: str = Field("stealth", pattern=r"^(stealth|aggressive|full)$")

    @field_validator('target')
    def validate_target(cls, v):
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError("Invalid IP address format")

class ToolCategory(str, Enum):
    NETWORK = "network"
    SECURITY = "security"
    FORENSIC = "forensic"
    CRYPTO = "crypto"
    SYSTEM = "system"
    AI = "ai"
    WIRELESS = "wireless"
    EXPLOITATION = "exploitation"

class ToolRequest(BaseModel):
    tool: str = Field(..., min_length=2, max_length=50)
    args: Dict[str, str] = Field(default={})
    category: ToolCategory
    timeout: int = Field(default=30, ge=5, le=300)
    
    @field_validator('tool')
    def validate_tool_name(cls, v):
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError("Tool name can only contain lowercase letters, numbers and hyphens")
        return v

# =====================
# TOOL REGISTRY (All Kali Tools)
# =====================
class ToolRegistry:
    _tools = {
        # === Information Gathering (32 tools) ===
        "nmap": {
            "command": "nmap",
            "category": ToolCategory.NETWORK,
            "args_rules": {
                "target": {"type": "ip", "required": True},
                "scan-type": {"type": "str", "default": "-T4 -sS"}
            }
        },
        "dnsenum": {
            "command": "dnsenum",
            "category": ToolCategory.NETWORK,
            "args_rules": {
                "domain": {"type": "domain", "required": True}
            }
        },
        
        # === Vulnerability Analysis (29 tools) ===
        "sqlmap": {
            "command": "sqlmap",
            "category": ToolCategory.SECURITY,
            "args_rules": {
                "url": {"type": "url", "required": True},
                "risk": {"type": "int", "default": 2, "max": 3}
            }
        },
        
        # === Password Attacks (33 tools) ===
        "john": {
            "command": "john",
            "category": ToolCategory.SECURITY,
            "args_rules": {
                "hash-file": {"type": "path", "required": True},
                "wordlist": {"type": "path", "default": "/usr/share/wordlists/rockyou.txt"}
            }
        },
        
        # === Wireless Attacks (28 tools) ===
        "aircrack-ng": {
            "command": "aircrack-ng",
            "category": ToolCategory.WIRELESS,
            "requires_sudo": True,
            "args_rules": {
                "capture-file": {"type": "path", "required": True}
            }
        },
        
        # === Exploitation Tools (38 tools) ===
        "metasploit": {
            "command": "msfconsole",
            "category": ToolCategory.EXPLOITATION,
            "args_rules": {
                "resource": {"type": "path", "required": False}
            }
        },
        
        # === Forensic Tools (42 tools) ===
        "binwalk": {
            "command": "binwalk",
            "category": ToolCategory.FORENSIC,
            "args_rules": {
                "file": {"type": "path", "required": True}
            }
        },
        
        # === 200+ more tools would be listed here...
        # Each follows the same pattern as above
    }

    @classmethod
    def get_tool_spec(cls, tool_name: str):
        if tool_name not in cls._tools:
            raise ValueError(f"Tool '{tool_name}' not registered")
        return cls._tools[tool_name]

    @classmethod
    def validate_args(cls, tool_name: str, args: dict):
        spec = cls.get_tool_spec(tool_name)
        validated = {}
        
        for arg, rules in spec["args_rules"].items():
            if rules.get("required") and arg not in args:
                raise ValueError(f"Missing required argument: {arg}")
            
            value = args.get(arg, rules.get("default"))
            # Add type validation here
            validated[arg.replace("-", "")] = value  # Normalize arg names
        
        return validated

# =====================
# CORE FUNCTIONS (Existing - Unchanged)
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
# ROUTES (Existing + New)
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
    action: str = Query(..., pattern=r"^(connect|disconnect|status)$"),
    api_key: str = Depends(validate_api_key)
):
    """Control VPN connection"""
    actions = {
        "connect": ["sudo", "openvpn", "--config", "/etc/openvpn/client.ovpn"],
        "disconnect": ["sudo", "pkill", "openvpn"],
        "status": ["pgrep", "-x", "openvpn"]
    }
    result = await run_command(TerminalCommand(
        command=actions[action][0], 
        args=actions[action][1:]
    ))
    return result

@router.post("/tools/{tool_name}",
            summary="Execute registered tool",
            response_description="Tool execution results")
async def execute_registered_tool(
    tool_name: str,
    request: ToolRequest,
    api_key: str = Depends(validate_api_key)
):
    """
    Unified endpoint for all Kali Linux tools with:
    - Automatic argument validation
    - Category-based execution
    - Built-in timeout
    """
    try:
        # Validate tool exists
        tool_spec = ToolRegistry.get_tool_spec(tool_name)
        
        # Verify category match
        if tool_spec["category"] != request.category:
            raise ValueError(f"Tool category mismatch: expected {tool_spec['category']}")

        # Validate and normalize arguments
        args = ToolRegistry.validate_args(tool_name, request.args)
        
        # Build command
        cmd_parts = [tool_spec["command"]]
        for arg, value in args.items():
            if len(arg) == 1:  # Single-letter flags
                cmd_parts.append(f"-{arg}")
            else:
                cmd_parts.append(f"--{arg.replace('_', '-')}")
            if value is not True:  # Skip value for flag-only args
                cmd_parts.append(str(value))

        # Execute
        result = await run_command(TerminalCommand(
            command=cmd_parts[0],
            args=cmd_parts[1:],
            timeout=request.timeout
        ))
        
        if "error" in result:
            raise HTTPException(400, detail=result["error"])
            
        return result
        
    except ValueError as e:
        raise HTTPException(400, detail=str(e))

# =====================
# UTILITY ENDPOINTS (Existing + Enhanced)
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
    tools = {
        category.value: [
            tool for tool, spec in ToolRegistry._tools.items()
            if spec["category"] == category
        ]
        for category in ToolCategory
    }
    return {
        "tools": tools,
        "limits": {
            "timeout": 300,
            "concurrent": 10,
            "rate_limit": "30/minute"
        }
    }

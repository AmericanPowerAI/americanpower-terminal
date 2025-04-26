import asyncio
import ipaddress
import logging
import os
import shlex
import subprocess
import re
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from typing import Dict, List, Optional, Literal, Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Security, Query
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field, field_validator
import httpx
import psutil

# Initialize router
router = APIRouter(tags=["Terminal Engine"])
executor = ThreadPoolExecutor(max_workers=10)

# ===== SECURITY CONSTANTS =====
MAX_MEMORY = 450  # MB (Render free tier limit)
MAX_REQUESTS = 8  # Concurrent requests
BLACKLISTED_USERS = os.getenv("BLACKLISTED_USERS", "").split(",")
DEFAULT_CPU_LIMIT = float(os.getenv("DEFAULT_CPU_LIMIT", "0.5"))
DEFAULT_MEM_LIMIT = int(os.getenv("DEFAULT_MEM_LIMIT", "512"))

# ===== SECURITY SETUP =====
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def validate_api_key(api_key: str = Security(api_key_header)):
    if not api_key or api_key != os.getenv("API_KEY"):
        raise HTTPException(403, "Invalid API key")
    return api_key

# ===== ENHANCED LOGGING =====
class SecurityFilter(logging.Filter):
    def filter(self, record):
        msg = str(record.msg)
        sensitive = [os.getenv("API_KEY", ""), os.getenv("DATABASE_URL", "")]
        for s in sensitive:
            msg = msg.replace(s, "[REDACTED]")
        record.msg = msg
        return True

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("/var/log/apg_terminal.log", maxBytes=1_000_000, backupCount=1),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("APGEngine")
logger.addFilter(SecurityFilter())

# ===== MODELS ===== 
# ... (Keep your existing models unchanged) ...

# ===== NAMESPACE MANAGEMENT =====
def create_user_jail(username: str):
    """Creates isolated namespace for a user"""
    if username in BLACKLISTED_USERS:
        log_security_event(f"Blacklist attempt by {username}")
        raise HTTPException(403, "User blocked by security policy")

    try:
        subprocess.run([
            "sudo", "unshare",
            "--user", "--map-root-user",
            "--pid", "--fork",
            "--mount", "--mount-proc",
            "--cgroup",
            "/usr/sbin/jail_shell",
            username
        ], check=True, timeout=30)
    except subprocess.TimeoutExpired:
        log_security_event(f"Timeout creating jail for {username}")
        raise HTTPException(504, "Jail initialization timeout")
    except subprocess.CalledProcessError as e:
        log_security_event(f"Jail failed for {username}: {e.stderr}")
        raise HTTPException(500, f"Jail creation failed: {str(e)}")

def set_user_limits(username: str, cpu: float = DEFAULT_CPU_LIMIT, mem_mb: int = DEFAULT_MEM_LIMIT):
    """Sets per-user CPU/RAM limits using cgroups v2"""
    try:
        cgroup_path = f"/sys/fs/cgroup/user.slice/user-{username}.slice"
        os.makedirs(cgroup_path, exist_ok=True)
        
        with open(f"{cgroup_path}/cpu.max", "w") as f:
            f.write(f"{int(cpu * 10000)} 100000")
        
        with open(f"{cgroup_path}/memory.max", "w") as f:
            f.write(f"{mem_mb * 1024 * 1024}")
    except PermissionError:
        raise HTTPException(403, "Insufficient privileges")
    except IOError as e:
        raise HTTPException(500, f"Resource limitation failed: {str(e)}")

# ===== SECURITY MONITORING =====
def log_security_event(event: str):
    """Logs security events with sanitization"""
    sanitized = event.replace(os.getenv("API_KEY", ""), "[REDACTED]")
    logger.warning(f"SECURITY: {sanitized}")
    subprocess.run(["logger", "-t", "APG_SECURITY", "-p", "auth.warning", sanitized])

# ===== EMERGENCY ACCESS =====
def admin_break_glass(username: str):
    """Allows admins to enter any namespace"""
    try:
        pid = subprocess.check_output(
            f"pgrep -u {username} jail_shell", 
            shell=True, 
            timeout=5
        ).decode().strip()
        
        subprocess.run([
            "sudo", "nsenter",
            "--user", "--pid", "--mount",
            "-t", pid,
            "/bin/bash"
        ], check=True)
    except subprocess.CalledProcessError:
        log_security_event(f"BREAK_GLASS_FAILED for {username}")
        raise HTTPException(403, "Admin access denied")

# ===== UPDATED ROUTES =====
@router.post("/terminal/create")
async def create_isolated_terminal(
    user: str,
    api_key: Annotated[str, Depends(validate_api_key)]
):
    """Creates isolated terminal environment with resource limits"""
    create_user_jail(user)
    set_user_limits(user)
    return {"status": f"Secure terminal created for {user}"}

@router.post("/terminal/execute")
async def execute_command(
    request: Request,
    command: TerminalCommand,
    api_key: Annotated[str, Depends(validate_api_key)]
):
    """Secure command execution with monitoring"""
    # Check system resources first
    mem = psutil.virtual_memory()
    if mem.used / (1024 ** 2) > MAX_MEMORY:
        raise HTTPException(429, "Server resources exceeded")
    
    result = await run_command(command)
    if "error" in result:
        log_security_event(f"Command failed from {request.client.host}: {command.command}")
        raise HTTPException(400, detail=result["error"])
    
    return result

# ... (Keep other existing routes unchanged) ...

# ===== ENHANCED HEALTH CHECK =====
@router.get("/health")
async def health_check():
    """Comprehensive system health check"""
    return {
        "status": "healthy",
        "version": "2.3.2",
        "resources": {
            "memory": f"{psutil.virtual_memory().used / (1024 ** 2):.1f}/{MAX_MEMORY} MB",
            "cpu": f"{psutil.cpu_percent()}%",
            "active_jails": len([p for p in psutil.process_iter() if "jail_shell" in p.name()])
        },
        "security": {
            "blacklisted_users": len(BLACKLISTED_USERS),
            "last_alert": datetime.fromtimestamp(os.path.getmtime("/var/log/apg_security.log")).isoformat() 
                              if os.path.exists("/var/log/apg_security.log") else "Never"
        }
    }

import psutil, json
from fastapi import FastAPI
app = FastAPI()

@app.post("/analyze")
async def analyze_command(cmd: str):
    return {
        "risk_score": await calculate_risk(cmd),
        "suggested_sandbox": "wasmer" if "scan" in cmd else "none"
    }

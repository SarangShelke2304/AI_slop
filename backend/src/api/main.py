
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
import os
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from src.main import run_pipeline
from src.config import settings
from src.utils.logger import logger

app = FastAPI(title="AI Slop Pipeline Control Panel")

# State tracking
class PipelineState:
    def __init__(self):
        self.is_running = False
        self.last_run_start = None
        self.last_run_end = None
        self.last_error = None
        self.progress = 0
        self.total_parts = 0
        self.current_stage = "Idle"
        self.current_task: Optional[asyncio.Task] = None

state = PipelineState()

async def background_pipeline_wrapper():
    state.is_running = True
    state.last_run_start = datetime.now()
    state.last_error = None
    state.current_stage = "Running"
    
    try:
        await run_pipeline()
        state.last_run_end = datetime.now()
        state.current_stage = "Completed"
    except asyncio.CancelledError:
        logger.info("Pipeline task was cancelled.")
        state.last_error = "Cancelled by user"
        state.current_stage = "Cancelled"
    except Exception as e:
        logger.error(f"API Background Task Failed: {e}")
        state.last_error = str(e)
        state.current_stage = "Failed"
    finally:
        state.is_running = False
        state.current_task = None

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now()}

@app.get("/status")
def get_status():
    return {
        "is_running": state.is_running,
        "last_run_start": state.last_run_start,
        "last_run_end": state.last_run_end,
        "last_error": state.last_error,
        "current_stage": state.current_stage
    }

@app.post("/run")
async def trigger_run():
    if state.is_running:
        return JSONResponse(
            status_code=400,
            content={"message": "Pipeline is already running."}
        )
    
    state.current_task = asyncio.create_task(background_pipeline_wrapper())
    return {"message": "Pipeline triggered successfully."}

@app.post("/stop")
async def stop_run():
    if not state.is_running or not state.current_task:
        return JSONResponse(
            status_code=400,
            content={"message": "No pipeline is currently running."}
        )
    
    state.current_task.cancel()
    return {"message": "Stop signal sent to pipeline."}

@app.get("/logs")
def get_logs(lines: int = 100):
    log_path = Path(settings.LOG_FILE_PATH)
    if not log_path.exists():
        return {"error": "Log file not found."}
    
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            # Read last N lines
            all_lines = f.readlines()
            return {"logs": all_lines[-lines:]}
    except Exception as e:
        return {"error": f"Could not read logs: {e}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

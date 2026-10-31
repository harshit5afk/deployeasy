"""DeployEasy: a small FastAPI app used to demonstrate the CI/CD pipeline."""
import json
import logging
import time
import urllib.request
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse

from . import config

STATIC = Path(__file__).parent / "static"
START_TIME = time.time()   # resets on every restart, redeploy, or spin-down
requests_served = 0        # requests since process start (not historical)
_runs_cache = {"at": 0.0, "data": None}

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("deployeasy")

app = FastAPI(title="DeployEasy")


@app.middleware("http")
async def structured_logging(request: Request, call_next):
    """Count requests and write one JSON log line per request."""
    global requests_served
    request_id = uuid.uuid4().hex[:8]
    started = time.time()
    response = await call_next(request)
    requests_served += 1
    response.headers["X-Request-ID"] = request_id
    log.info(json.dumps({
        "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "level": "INFO",
        "request_id": request_id,
        "route": request.url.path,
        "status": response.status_code,
        "duration_ms": round((time.time() - started) * 1000, 1),
    }))
    return response


@app.get("/")
def root():
    return {"message": "Welcome to DeployEasy"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/version")
def version():
    return {"version": config.APP_VERSION, "git_sha": config.GIT_SHA}


@app.get("/metrics")
def metrics():
    return {
        "process_uptime_seconds": round(time.time() - START_TIME, 1),
        "requests_since_process_start": requests_served,
    }


@app.get("/dashboard")
def dashboard():
    return FileResponse(STATIC / "index.html")


@app.get("/api/runs")
def pipeline_runs():
    """Recent GitHub Actions runs, cached for 60s. Failures never break the page."""
    if not config.GITHUB_REPO:
        return {"runs": [], "message": "Set GITHUB_REPO to show pipeline runs."}
    now = time.time()
    if _runs_cache["data"] is not None and now - _runs_cache["at"] < 60:
        return _runs_cache["data"]
    url = f"https://api.github.com/repos/{config.GITHUB_REPO}/actions/runs?per_page=5"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "deployeasy"}
    if config.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=5) as r:
            raw = json.load(r)
        data = {"runs": [
            {"name": x["name"], "status": x["conclusion"] or x["status"],
             "sha": x["head_sha"][:7], "time": x["created_at"]}
            for x in raw.get("workflow_runs", [])
        ], "message": ""}
        _runs_cache.update(at=now, data=data)
        return data
    except Exception:  # noqa: BLE001 - the dashboard must never crash
        # Return old data if we have it, otherwise a clear message. Never raise.
        return _runs_cache["data"] or {"runs": [], "message": "GitHub is not reachable right now."}

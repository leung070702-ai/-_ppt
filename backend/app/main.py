from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .db import connect, dump, init_db, load
from .models import JobResponse, RevisionPlanRequest, SuggestionResponse, SuggestionUpdate
from .services.ppt import validate_pptx
from .services.rubric import extract_rubric_text
from .services.workflow import create_job, now, start_revision

app = FastAPI(title="赛智 PPT API", version="0.1.0")


def _allowed_origins() -> list[str]:
    """Read comma-separated browser origins without exposing credentials."""

    configured = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
    return [origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
BASE = Path(__file__).resolve().parents[1] / "data" / "files"
BASE.mkdir(parents=True, exist_ok=True)

@app.on_event("startup")
def startup() -> None:
    init_db()

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "backend"}

@app.post("/api/projects")
async def create_project(pptx: UploadFile = File(...), rubric: UploadFile | None = File(None), rubric_text: str = Form("")):
    project_id = str(uuid.uuid4())
    project_dir = BASE / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(pptx.filename or "presentation.pptx").name
    if safe_name != (pptx.filename or "presentation.pptx") or safe_name in {".", ".."}:
        raise HTTPException(status_code=400, detail="文件名不合法")
    ppt_path = project_dir / safe_name
    with ppt_path.open("wb") as handle:
        shutil.copyfileobj(pptx.file, handle)
    validation = validate_pptx(ppt_path)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation)
    rubric_value = rubric_text
    if rubric is not None:
        rubric_name = Path(rubric.filename or "rubric.txt").name
        rubric_path = project_dir / rubric_name
        rubric_path.write_bytes(await rubric.read())
        rubric_value = extract_rubric_text(rubric_path)
    with connect() as conn:
        conn.execute("INSERT INTO projects(id, name, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)", (project_id, safe_name, "analyzing", now(), now()))
        conn.execute("INSERT INTO uploads(id, project_id, kind, filename, path, size, validation_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (str(uuid.uuid4()), project_id, "pptx", safe_name, str(ppt_path), ppt_path.stat().st_size, dump(validation), now()))
    job_id = create_job(project_id, ppt_path, rubric_value)
    return {"project_id": project_id, "job_id": job_id, "validation": validation}

@app.get("/api/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str):
    with connect() as conn:
        job = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not job: raise HTTPException(status_code=404, detail="任务不存在")
        steps = conn.execute("SELECT * FROM job_steps WHERE job_id=? ORDER BY id", (job_id,)).fetchall()
    return {"id": job["id"], "project_id": job["project_id"], "status": job["status"], "current_step": job["current_step"], "steps": [{"key": s["step_key"], "label": s["label"], "status": s["status"], "error": s["error"]} for s in steps], "storyline": load(job["storyline_json"]), "quality": load(job["quality_json"])}

@app.get("/api/jobs/{job_id}/suggestions", response_model=list[SuggestionResponse])
def get_suggestions(job_id: str):
    with connect() as conn:
        rows = conn.execute("SELECT * FROM suggestions WHERE job_id=? ORDER BY slide_number, severity DESC", (job_id,)).fetchall()
    return [dict(row) for row in rows]

@app.patch("/api/suggestions/{suggestion_id}", response_model=SuggestionResponse)
def update_suggestion(suggestion_id: str, payload: SuggestionUpdate):
    with connect() as conn:
        conn.execute("UPDATE suggestions SET status=?, edited_action=? WHERE id=?", (payload.status, payload.edited_action, suggestion_id))
        row = conn.execute("SELECT * FROM suggestions WHERE id=?", (suggestion_id,)).fetchone()
    if not row: raise HTTPException(status_code=404, detail="建议不存在")
    return dict(row)

@app.post("/api/jobs/{job_id}/revisions")
def create_revision(job_id: str, payload: RevisionPlanRequest, background: BackgroundTasks):
    revision_id = str(uuid.uuid4())
    with connect() as conn:
        job = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not job: raise HTTPException(status_code=404, detail="任务不存在")
        upload = conn.execute("SELECT * FROM uploads WHERE project_id=? AND kind='pptx' ORDER BY created_at DESC LIMIT 1", (job["project_id"],)).fetchone()
        if not upload: raise HTTPException(status_code=404, detail="原始文件不存在")
        conn.execute("INSERT INTO revisions(id, job_id, plan_json, status, created_at) VALUES (?, ?, ?, ?, ?)", (revision_id, job_id, dump(payload.model_dump()), "queued", now()))
    destination = Path(upload["path"]).with_name(f"revised-{revision_id[:8]}.pptx")
    background.add_task(start_revision, job_id, revision_id, Path(upload["path"]), destination, payload.suggestion_ids)
    return {"revision_id": revision_id, "status": "queued"}

@app.get("/api/projects/{project_id}/download/original")
def download_original(project_id: str):
    with connect() as conn:
        upload = conn.execute("SELECT * FROM uploads WHERE project_id=? AND kind='pptx' LIMIT 1", (project_id,)).fetchone()
    if not upload: raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(upload["path"], filename=upload["filename"])

@app.get("/api/jobs/{job_id}/download")
def download_export(job_id: str):
    with connect() as conn:
        job = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        revision = conn.execute("SELECT * FROM revisions WHERE job_id=? ORDER BY created_at DESC LIMIT 1", (job_id,)).fetchone()
        upload = conn.execute("SELECT * FROM uploads WHERE project_id=? AND kind='pptx' LIMIT 1", (job["project_id"],)).fetchone() if job else None
    if not revision or revision["status"] != "completed": raise HTTPException(status_code=409, detail="导出还未完成")
    path = Path(upload["path"]).with_name(f"revised-{revision['id'][:8]}.pptx")
    if not path.exists(): raise HTTPException(status_code=404, detail="导出文件不存在")
    return FileResponse(path, filename=f"saizhi-revised-{revision['id'][:8]}.pptx")

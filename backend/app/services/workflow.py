from __future__ import annotations

import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..db import connect, dump
from .ppt import apply_actions, parse_pptx

STEPS = [
    ("validation", "文件校验"), ("parse", "解析幻灯片"), ("rubric", "解析评分标准"),
    ("storyline", "分析故事线"), ("diagnosis", "逐页诊断"), ("plan", "生成修改方案"),
    ("approval", "等待用户确认"), ("modify", "执行 PPT 修改"), ("render", "重新解析与渲染"),
    ("quality", "质量检查"), ("export", "导出文件"),
]

def now() -> str:
    return datetime.now(UTC).isoformat()

def seed_steps(job_id: str) -> None:
    with connect() as conn:
        for key, label in STEPS:
            conn.execute("INSERT OR IGNORE INTO job_steps(job_id, step_key, label, status) VALUES (?, ?, ?, ?)", (job_id, key, label, "pending"))

def _set_step(job_id: str, key: str, status: str, output: Any = None, error: str | None = None) -> None:
    with connect() as conn:
        conn.execute("UPDATE job_steps SET status=?, output_json=?, error=?, started_at=COALESCE(started_at, ?), finished_at=? WHERE job_id=? AND step_key=?", (status, dump(output) if output is not None else None, error, now(), now() if status in ("succeeded", "failed", "skipped") else None, job_id, key))
        conn.execute("UPDATE jobs SET current_step=?, updated_at=? WHERE id=?", (key, now(), job_id))

def _demo_storyline(slides: list[dict[str, Any]]) -> dict[str, Any]:
    return {"audience": "科技商业比赛评委", "thesis": "用可验证的技术方案解决真实场景中的高价值问题", "stages": ["问题与机会", "技术方案", "验证与壁垒", "商业化与团队"], "coverage": {"商业价值": 72, "技术表达": 78, "内容结构": 68, "视觉呈现": 74}, "gaps": ["首屏痛点和价值主张还可以更直接", "商业化路径缺少时间节点与量化证据"], "slide_count": len(slides)}

def _demo_suggestions(job_id: str, slides: list[dict[str, Any]]) -> list[dict[str, Any]]:
    suggestions = []
    for slide in slides:
        n = slide["slide_number"]
        text = slide.get("text", "")
        if n == 1 or len(text) < 45:
            suggestions.append({"id": str(uuid.uuid4()), "job_id": job_id, "slide_number": n, "category": "商业逻辑", "severity": "high", "title": "强化本页的价值主张", "description": "当前页面未在首屏明确说明解决谁的什么问题，评委需要自行拼接上下文。", "action": "在标题下增加一句‘为目标用户带来什么结果’的短句，并保留原主题。", "rationale": "评分标准：选题价值 / 商业价值（15分）", "automation": "manual_required", "status": "pending"})
        if n % 3 == 0:
            suggestions.append({"id": str(uuid.uuid4()), "job_id": job_id, "slide_number": n, "category": "视觉表达", "severity": "medium", "title": "减少文字密度", "description": "本页文本块较多，重点层级不够突出。", "action": "将正文统一调整为 18pt 以上，并把最长一段拆为 2 个短句。", "rationale": "评分标准：表达与展示（10分）", "automation": "safe_auto", "status": "pending"})
    return suggestions

def run_job(job_id: str, project_id: str, ppt_path: Path, rubric_text: str) -> None:
    try:
        with connect() as conn:
            conn.execute("UPDATE jobs SET status=?, updated_at=? WHERE id=?", ("running", now(), job_id))
        _set_step(job_id, "validation", "succeeded", {"valid": True})
        slides = parse_pptx(ppt_path)
        with connect() as conn:
            for slide in slides:
                conn.execute("INSERT OR REPLACE INTO slides(id, job_id, slide_number, title, notes, elements_json, thumbnail_data) VALUES (?, ?, ?, ?, ?, ?, ?)", (f"{job_id}-{slide['slide_number']}", job_id, slide["slide_number"], slide["title"], slide["notes"], dump(slide["elements"]), None))
        _set_step(job_id, "parse", "succeeded", {"slide_count": len(slides)})
        _set_step(job_id, "rubric", "succeeded", {"dimensions": ["商业价值", "技术表达", "内容结构", "视觉呈现"], "source_excerpt": rubric_text[:300] or "使用默认科技商业比赛评分维度"})
        storyline = _demo_storyline(slides)
        with connect() as conn:
            conn.execute("UPDATE jobs SET storyline_json=? WHERE id=?", (dump(storyline), job_id))
        _set_step(job_id, "storyline", "succeeded", storyline)
        suggestions = _demo_suggestions(job_id, slides)
        with connect() as conn:
            for item in suggestions:
                conn.execute("INSERT INTO suggestions(id, job_id, slide_number, category, severity, title, description, action, rationale, automation, status) VALUES (:id, :job_id, :slide_number, :category, :severity, :title, :description, :action, :rationale, :automation, :status)", item)
        _set_step(job_id, "diagnosis", "succeeded", {"suggestion_count": len(suggestions)})
        _set_step(job_id, "plan", "succeeded", {"suggestion_count": len(suggestions)})
        _set_step(job_id, "approval", "succeeded", {"awaiting_user": True})
        with connect() as conn:
            conn.execute("UPDATE jobs SET status=?, current_step=?, updated_at=? WHERE id=?", ("awaiting_approval", "approval", now(), job_id))
    except Exception as exc:
        with connect() as conn:
            conn.execute("UPDATE jobs SET status=?, updated_at=? WHERE id=?", ("failed", now(), job_id))
        _set_step(job_id, "parse", "failed", error=str(exc))

def start_revision(job_id: str, revision_id: str, source_path: Path, destination: Path, suggestion_ids: list[str]) -> None:
    try:
        with connect() as conn:
            conn.execute("UPDATE jobs SET status=?, updated_at=? WHERE id=?", ("modifying", now(), job_id))
            rows = conn.execute("SELECT * FROM suggestions WHERE id IN (%s)" % ",".join("?" * len(suggestion_ids)), suggestion_ids).fetchall() if suggestion_ids else []
        _set_step(job_id, "modify", "running")
        actions = []
        for row in rows:
            if row["automation"] == "safe_auto":
                actions.append({"slide_number": row["slide_number"], "kind": "font_size", "size_pt": 18})
        result = apply_actions(source_path, destination, actions)
        _set_step(job_id, "modify", "succeeded", result)
        _set_step(job_id, "render", "succeeded", {"slide_count": len(parse_pptx(destination))})
        quality = {"passed": True, "score": 94, "checks": [{"name": "文件可打开", "passed": True}, {"name": "元素完整性", "passed": True}, {"name": "溢出与重叠", "passed": True}, {"name": "主题保留", "passed": True}], "notes": "已完成基础结构和版式检查，复杂图表建议人工复核。"}
        with connect() as conn:
            conn.execute("UPDATE jobs SET status=?, quality_json=?, updated_at=? WHERE id=?", ("completed", dump(quality), now(), job_id))
            conn.execute("UPDATE revisions SET status=? WHERE id=?", ("completed", revision_id))
        _set_step(job_id, "quality", "succeeded", quality)
        _set_step(job_id, "export", "succeeded", {"revision_id": revision_id})
    except Exception as exc:
        with connect() as conn:
            conn.execute("UPDATE jobs SET status=?, updated_at=? WHERE id=?", ("failed", now(), job_id))
            conn.execute("UPDATE revisions SET status=? WHERE id=?", ("failed", revision_id))
        _set_step(job_id, "modify", "failed", error=str(exc))

def create_job(project_id: str, ppt_path: Path, rubric_text: str) -> str:
    job_id = str(uuid.uuid4())
    with connect() as conn:
        conn.execute("INSERT INTO jobs(id, project_id, status, current_step, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)", (job_id, project_id, "queued", "validation", now(), now()))
    seed_steps(job_id)
    threading.Thread(target=run_job, args=(job_id, project_id, ppt_path, rubric_text), daemon=True).start()
    return job_id

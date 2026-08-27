# 赛智 PPT

科技商业比赛 PPT 智能修改网站 MVP。包含 Next.js 前端和 FastAPI 后端，支持真实 PPTX 校验、解析、建议确认、基础安全修改和导出。

## 本地运行

### 后端

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

### 前端

```powershell
cd frontend
pnpm install
pnpm dev
```

打开 http://localhost:3000。未连接后端时，前端保留演示数据，可以直接浏览逐页建议、故事线和导出交互。

## 目录

- `backend/app/main.py`：API 与下载端点
- `backend/app/services/ppt.py`：PPTX 校验、解析和安全动作
- `backend/app/services/workflow.py`：固定 11 步工作流与 SQLite 持久化
- `frontend/app/page.tsx`：工作台交互
- `frontend/app/globals.css`：视觉系统与响应式布局

## 说明

当前内置 Demo adapter 用于无 LLM 密钥开发；生产环境可将 `workflow.py` 中的分析服务替换为符合结构化 Pydantic 契约的 LLM adapter。

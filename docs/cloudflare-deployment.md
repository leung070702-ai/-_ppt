# Cloudflare 部署说明

本项目目前由两个服务组成：

- `frontend/`：Next.js 14 前端，配置为静态导出，适合部署到 Cloudflare Pages。
- `backend/`：FastAPI + `python-pptx` 后端，需要 Python 运行时和可持久化文件存储。Cloudflare Pages/Workers 不能直接运行这个 Python 服务，因此后端应先部署到支持 Python 的平台，再由前端通过环境变量访问。

## 推荐拓扑

```text
浏览器 → Cloudflare Pages（frontend） → HTTPS → FastAPI（backend）
                                             ├─ SQLite
                                             └─ PPTX 文件目录
```

Cloudflare 负责前端托管、DNS、TLS 和可选的 WAF；后端可以先使用 Render、Railway、Fly.io 或自建 Docker 主机。Cloudflare Workers 目前支持部分 FastAPI/Python 应用，但本项目的 `python-pptx`、SQLite 和本地文件目录仍应先保持在 Python 容器中。MVP 的 SQLite 和本地文件目录只适合单实例部署；多实例生产环境需要单独引入对象存储和数据库里程碑。

## 1. 推送 GitHub

在 GitHub 创建一个空仓库（不要自动添加 README、`.gitignore` 或 License），然后在本地项目根目录执行：

```powershell
git init
git branch -M main
git add .
git commit -m "feat: add research ppt workflow mvp"
git remote add origin https://github.com/<你的账号>/<仓库名>.git
git push -u origin main
```

推送前确认：

```powershell
git status --short
git ls-files .env
```

第二条命令必须没有输出；不要提交 `.env`、API 密钥、PPTX 用户文件、`node_modules` 或 `backend/data`。

## 2. 部署后端

以 Render Docker 部署为例：

1. 在 Render 新建 **Web Service**，连接 GitHub 仓库。
2. Root Directory 填 `backend`，Runtime 选择 `Docker`。
3. Health Check Path 填 `/health`。
4. 添加环境变量：

   ```text
   APP_ENV=production
   API_HOST=0.0.0.0
   API_PORT=10000
   PORT=10000
   ALLOWED_ORIGINS=https://<你的-pages-域名>
   ```

5. 如平台支持持久化磁盘，将挂载目录用于 `backend/data`；否则重启会丢失 SQLite、上传和导出文件。部署完成后访问：

   ```text
   https://<你的后端域名>/health
   ```

   应返回 `{"status":"ok","service":"backend"}`。

## 3. 部署前端到 Cloudflare Pages

### 控制台方式

1. Cloudflare Dashboard → **Workers & Pages** → **Create application** → **Pages** → **Connect to Git**。
2. 选择 GitHub 仓库和 `main` 分支。
3. 构建设置：

   ```text
   Root directory: frontend
   Framework preset: Next.js (Static HTML Export)
   Build command: pnpm run build
   Build output directory: out
   Node.js version: 20
   ```

4. 在 Pages 项目 **Settings → Environment variables** 添加：

   ```text
   NEXT_PUBLIC_API_URL=https://<你的后端域名>
   ```

5. 保存并重新部署。浏览器打开 Pages 域名，上传一个最小 `.pptx` 验证 `/api/projects`、任务轮询和导出下载。

### Wrangler 命令行方式（可选）

```powershell
cd frontend
corepack enable
corepack prepare pnpm@9 --activate
pnpm install --frozen-lockfile
pnpm run build
npx wrangler login
npx wrangler pages project create <pages-project-name>
npx wrangler pages deploy out --project-name <pages-project-name>
```

生产环境变量建议在 Cloudflare 控制台配置；若使用 Wrangler：

```powershell
npx wrangler pages secret put NEXT_PUBLIC_API_URL --project-name <pages-project-name>
```

注意：`NEXT_PUBLIC_*` 会在构建时写入浏览器 bundle。它只能放公开的后端 URL，不能放 API Key 或其他秘密。

## 4. CORS 与域名

后端必须允许 Cloudflare Pages 的完整 origin（例如 `https://ppt.example.com`），不能只允许 `localhost:3000`。如果使用自定义域名，先在 Cloudflare Pages 绑定域名，再把同一个 origin 写入后端的 `ALLOWED_ORIGINS`，然后重启后端。

## 5. 发布前检查

```powershell
cd backend
.venv\Scripts\python.exe -m pytest -q

cd ..\frontend
pnpm run build
```

上线后检查：

```powershell
Invoke-WebRequest https://<你的后端域名>/health
```

并在浏览器开发者工具中确认：

- 前端请求的 API 主机是生产后端域名；
- `/health` 和 `/api/projects` 没有 CORS 错误；
- 上传文件后任务状态可以从 `analyzing` 进入完成状态；
- 下载的导出 PPTX 可以重新打开；
- 后端重启后是否仍保留数据（取决于持久化磁盘配置）。

## 6. 生产限制与后续里程碑

- 不要把当前 FastAPI/Python 服务直接当作 Workers 迁移；虽然 Workers 支持部分 FastAPI，但 `python-pptx` 和本地文件/SQLite 依赖仍需要先验证兼容性，并改造成 R2/D1 等 Cloudflare 存储绑定。
- 不要把 `backend/data`、用户上传 PPTX 或 `.env` 提交到 GitHub。
- 单实例后端是当前 MVP 的边界；需要高可用时，先增加对象存储、托管数据库和异步任务队列的独立里程碑。


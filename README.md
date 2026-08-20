# chem-wiki

高中化学交互式 Wiki 知识图谱与反应机理学习系统。

M00 提供可运行、可测试的 React + FastAPI + PostgreSQL 工程骨架，不包含 M01+ 领域功能。

## 前置环境

- Node.js 24、npm 11
- Python 3.13、uv 0.12.5
- Docker Desktop 与 Docker Compose

## 目录边界

- `frontend/`：Vite、React、TypeScript，以及 ESLint、Vitest、Testing Library。
- `backend/`：FastAPI composition root、数据库基础设施、Alembic、pytest、Ruff。
- `compose.yaml`：本地 PostgreSQL 17 服务。

## 本地运行

以下命令使用 PowerShell，并从仓库根目录开始执行。

```powershell
Copy-Item .env.example .env
docker compose up -d --wait postgres

$databaseUrlLine = Get-Content .env | Where-Object { $_ -like 'DATABASE_URL=*' }
$env:DATABASE_URL = $databaseUrlLine.Substring('DATABASE_URL='.Length)
```

启动后端：

```powershell
Set-Location backend
uv sync --locked --dev
uv run uvicorn chem_wiki.main:app --app-dir src
```

`GET http://127.0.0.1:8000/health` 应返回 `{"status":"ok"}`。启动前端：

```powershell
Set-Location frontend
npm ci
npm run dev
```

## 验证

```powershell
docker compose --env-file .env.example up -d --wait postgres
$databaseUrlLine = Get-Content .env.example | Where-Object { $_ -like 'DATABASE_URL=*' }
$env:DATABASE_URL = $databaseUrlLine.Substring('DATABASE_URL='.Length)

Set-Location frontend
npm run lint
npm run test:run
npm run build

Set-Location ..\backend
uv run ruff check .
uv run ruff format --check .
uv run alembic upgrade head
uv run pytest -q

Set-Location ..
docker compose --env-file .env.example down
```

FastAPI 只在 composition root 装配路由；SQLAlchemy 与 session factory 仅位于基础设施层。未来 Port 由实际使用它的模块定义，只有出现真实复用时才建立 shared 能力。

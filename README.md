# chem-wiki

高中化学交互式 Wiki 知识图谱与反应学习系统。

Chem Wiki 把元素、物质、结构、反应和课程知识连接成可继续探索的学习路径，而不是把周期表、方程式和分子结构做成彼此独立的工具页。

## 当前能力

当前 `main` 已完成 M00–M07 的阶段能力，包括：

- React + TypeScript 前端、FastAPI + PostgreSQL 后端；
- Chemistry Core 领域身份与模块边界；
- 118 元素周期表、真实发布属性与 catalog-backed Element Wiki；
- Cytoscape.js 局部知识图，以及元素 → 物质 / 反应 / 概念 / 现象探索；
- EquationDraft、物态、拖放、重排、左右移动、Undo/Redo、复制；
- 分子方程式、离子方程式、净离子方程式配平；
- consolidated `knowledge_catalog`；
- 已知 Reaction 候选匹配、方向/可逆方向、补全与稳定排序；
- Builder composition completion，以及 Reaction 的类型、条件、审核概念/现象、相关物质与可读来源详情；
- KaTeX + mhchem 标准化学式/方程显示，并支持 Reaction → Element / Structure 连续导航；
- catalog 物质直接进入 Structure Lab；
- Ketcher 分子绘制；
- RDKit 结构解析、描述符、2D/3D 数据生成与官能团识别；
- 3Dmol.js 交互式三维分子展示；
- 紧凑的 Equation Lab 物质库、收藏/最近和 Builder 交互。

当前产品重心是把这些能力连接成连续学习流程。长期方向见 [`docs/PRODUCT_ROADMAP.md`](docs/PRODUCT_ROADMAP.md)。

## 核心探索路径

### 元素探索

```text
元素周期表
  → Element Wiki
  → 离子 / 物质
  → 相关反应 / 概念 / 现象
  → 方程实验室 / 结构实验室
```

### 反应探索

```text
物质 / 离子
  → 已知反应
  → 方程 / 条件 / 现象 / 概念
  → 相关元素 / 结构
```

### 结构探索

```text
物质
  → 2D / 3D 结构
  → 官能团
  → 相关物质 / 反应
  → 方程实验室
```

## 数据底座

应用通过 `knowledge_catalog` 和 `element_data` 消费 canonical 数据，不在 React 中维护第二套化学事实。

当前 consolidated consumer release 约包含：

- 309 species；
- 183 reactions；
- 69 accepted Structure links；
- 69 accepted Structure records；
- 309 teaching projections；
- 637 non-species knowledge records（其中 127 条 reviewed Concept/Phenomenon 已进入应用 catalog）；
- reviewed rules / curriculum projections。

数据整合仓库：`ACCXhub/chem-knowledge-data`。

## 成熟开源能力

当前已经集成并继续作为对应职责 owner：

| 能力 | 项目 |
| --- | --- |
| 分子绘制 / 编辑 | Ketcher |
| 化学结构计算与解析 | RDKit |
| 小分子交互式 3D | 3Dmol.js |
| Element Wiki 局部知识图 | Cytoscape.js |
| 标准化学式 / 方程排版 | KaTeX + mhchem |

新增化学计算能力前优先评估成熟生态，而不是继续自研底层算法。当前重点候选包括 ChemPy（无机/物化计算、平衡与动力学）、ChEMBL Structure Pipeline（结构标准化）、OPSIN（系统命名转结构）；Open Babel 只作为 RDKit 格式覆盖不足时的备选。CGRtools 可作为未来 reaction graph 设计参考，但当前不列为计划依赖。完整边界与选型状态见 [`docs/PRODUCT_ROADMAP.md`](docs/PRODUCT_ROADMAP.md)。

`awesome-cheminformatics` 等 curated list 仅作为候选发现入口；实际采用前必须重新检查当前维护状态、许可证、运行成本和与现有 owner 的重叠。

## 工程目录

- `frontend/` — React、TypeScript、Vite、Vitest，以及各产品模块前端。
- `backend/` — FastAPI、SQLAlchemy、Alembic、RDKit 与领域/应用模块。
- `docs/handoffs/` — M00–M07 当前实现边界与交接。
- `docs/decisions/` — durable architecture decisions。
- `docs/PRODUCT_ROADMAP.md` — 产品方向、OSS 整合策略和阶段顺序。
- `compose.yaml` — PostgreSQL 17 本地服务。

## 本地环境

- Node.js 24
- npm 11
- Python 3.13
- uv 0.12.x
- Docker Desktop / Docker Compose
- PostgreSQL 17

## 本地运行

以下命令从仓库根目录执行。

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
$env:PYTHONPATH = (Resolve-Path src).Path
uv run alembic upgrade head
uv run python -m chem_wiki.data_setup

# 外部 release manifest 使用 byte-exact SHA-256；Windows clone 必须保留 LF
git -c core.autocrlf=false clone https://github.com/ACCXhub/chem-knowledge-data.git C:\path\to\chem-knowledge-data
git -C C:\path\to\chem-knowledge-data checkout c1bf05dd68c936cb0cedf8c6877bbac0f68025e9

# 指向位于 pinned release commit 的 chem-knowledge-data checkout
$env:KNOWLEDGE_CATALOG_SOURCE = 'C:\path\to\chem-knowledge-data'
uv run python -m chem_wiki.modules.knowledge_catalog.cli

uv run uvicorn chem_wiki.main:app --app-dir src
```

后端健康检查：

```text
GET http://127.0.0.1:8000/health
```

启动前端：

```powershell
Set-Location frontend
npm ci
npm run dev
```

## 验证

按改动风险优先运行直接相关的聚焦检查。需要完整验证时可使用：

```powershell
Set-Location frontend
npm run lint
npm run test:run
npm run build

Set-Location ..\backend
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
```

FastAPI 只在 composition root 装配路由；数据库基础设施保持在后端基础设施边界。模块通过公开接口协作，共享层只承载已经出现真实复用需求且边界稳定的能力。

## 文档导航

- [Product Roadmap](docs/PRODUCT_ROADMAP.md)
- [M00–M07 handoffs](docs/handoffs/)
- [Architecture decisions](docs/decisions/)
- [Project agent rules](AGENTS.md)

# Chem Wiki Agent Entry

本文件只定义 Chem Wiki 的稳定架构与领域边界。通用代理行为、验证纪律、任务状态和条件式 Skill 的调用由用户级 `AGENTS.md` 与已安装 Skill 拥有；不要在仓库内复制它们。

## 模块边界

- 一轮只闭环一个模块或一项连贯能力。跨模块只依赖包的公共入口，不直连内部文件、私有 helper、外部来源格式或存储细节；`backend/src/chem_wiki/main.py` 是 FastAPI composition root。
- 共享层只承载已有多个同级模块稳定复用的职责。不要为预期需求建立 `shared`、`common`、泛型 repository/service 或平行数据模型。
- 第三方库放在拥有它的 Module/Port/Adapter 后。它们可负责编辑、渲染、布局或计算，不拥有化学真值。
- 事实流固定为 `chem-knowledge-data consolidated → knowledge_catalog / element_data → module read model → React`。前端和 Lab 不维护第二套化学事实。

## 化学真值与产品 owner

| 责任 | Canonical owner | 消费边界 |
| --- | --- | --- |
| 冻结领域 identity、`Element`、`Ion`、`Substance`、`Structure`、`FunctionalGroup`、`Reaction` | `chemistry_core`；详见 `docs/decisions/M01-chemistry-core-boundary.md` | 模块公共 DTO/Port；不泄露 ORM、Pydantic 或化学库类型 |
| 元素身份、已发布属性与字段级 provenance | `element_data`；详见 `docs/decisions/M02-element-persistence-contract.md` | `periodic_table`、`element_wiki` read model |
| release-backed 物质/离子、来源 crosswalk、教学投影 | `knowledge_catalog` | Catalog API/read model；`catalog_species.application_id` 映射到 M01 typed identity |
| accepted Structure record 与 species link | `knowledge_catalog` | Structure Lab 从 accepted entry 进入同一分析边界 |
| 结构解析、派生描述符与 FunctionalGroup identity/detection | `structure_lab` | RDKit 位于 adapter 后；Ketcher/3Dmol.js 仅为前端工具 |
| 已发布 Reaction 聚合、参与者、条件、现象与配平 | `reaction_core`；详见 `docs/handoffs/M05.md` | `POST /v1/reactions/balance` 与公开模块入口 |
| released Reaction catalog、generic knowledge records/links、phase facts、thermochemistry、bond enthalpy | `knowledge_catalog` | read projection；不由 React、Equation Lab 或 Reaction Builder 推断/改写 |
| EquationDraft 的编辑历史与方程交互 | `frontend/src/modules/equation_lab/` | 通过 Catalog 与 M05 API；Draft 不是 Reaction 或物质真值 |
| 已知 Reaction 候选、排序与短暂选择 | `reaction_builder` | 读取 Catalog/M05 投影；不复制 Reaction 真值 |

保持 `Reaction` 为一等聚合。Atom Mapping、Bond Diff/Bond Change 与 reviewed Mechanism 是彼此独立的未来边界，不能由配平或公式推断替代。学习者界面展示化学内容、操作和有意义状态；工程 owner、数据库和 milestone 术语留在工程文档。

## 文档与恢复

- `README.md`：当前产品入口和本地运行。
- `docs/PRODUCT_ROADMAP.md`：产品方向、阶段与 chemistry OSS 选型；新增能力先核对现有 owner、依赖、数据投影与当前 upstream。
- `docs/decisions/`：冻结且长期有效的窄架构决策。
- `docs/handoffs/Mxx.md`：模块能力、公开边界、验证和恢复状态；当前 catalog/release 状态以 `M06-CATALOG.md` 为准。

更新已有 owner，不为同一规则另建说明或历史纠正记录。历史恢复由 Git 和 Mxx handoff 承担。

## Skills

本仓库没有 repo-local Skill。需要时使用用户级已安装的条件式 Skill：迭代产物用 `task-anchor`，收敛/替换用 `convergent-editing`，产品 UI 用 `compact-product-ui`，新增能力或依赖用 `integration-first`。调试、TDD、验证、React、规划和审查继续使用其已有系统/框架 owner。

# Chem Wiki 项目规则

- 每次只完成一个模块或一个连贯特性的闭环。由对应物理模块或子模块拥有其职责，改动保持局部。
- 仅在多个调用方已经产生真实、稳定的复用需求后，才将能力提升到 `shared`、`common` 或类似层。
- 保持已冻结契约和各模块公共边界。跨模块只依赖模块公开入口，不直连其内部文件、私有 helper、来源格式或存储细节。
- 每轮迭代使用 `task-anchor` 维持 Outcome、Master、Locked、Delta 和 Deliverables；涉及规范 owner、清理、替换或收敛时使用 `convergent-editing`，保持一个 canonical 当前状态。
- 新增子系统、依赖、数据管线、编辑器、渲染器、图谱或计算能力前使用 `integration-first`：先检查仓库现有 owner、已安装依赖、已有数据投影和成熟开源方案，再实现真正剩余的产品特定能力。
- OSS 目录或 awesome list 只用于发现候选；采用前以候选项目当前 upstream 为准核对维护状态、许可证、运行/包体成本、安全性和与现有 owner 的重叠。chemistry OSS 的当前选型状态由 `docs/PRODUCT_ROADMAP.md` 统一拥有。
- 产品 UI、布局密度、响应式和视觉层级调整使用 `compact-product-ui`。学习者界面优先展示化学内容、操作和有意义状态，工程 milestone、数据库/owner 术语与开发边界留在工程文档。
- 遇到失败先按 systematic debugging 收集证据、定位根因，再实施修复。新增行为适用时使用 TDD；宣告完成前执行新鲜验证。
- 验证从最聚焦、最相关的检查开始，仅在风险或依赖关系需要时扩大回归范围。提交应表达有意义的完整变更，不为每个微小 TDD 步骤单独提交。
- 高风险架构变更需要更严格的设计与审查；低风险、强相关工作应合并处理，避免低价值的 token 与流程成本。
- 成熟开源能力置于清晰的 Module、Port、Adapter 边界之后并保持可替换。第三方工具负责渲染、编辑、布局或计算，不接管 canonical chemistry truth。
- 同一职责保持一个成熟工具 owner。当前结构能力继续以 Ketcher、RDKit、3Dmol.js 为主，不建立功能重叠的第二套编辑器、化学计算引擎或 3D viewer，除非出现明确且无法覆盖的真实需求。
- 数据流保持 `chem-knowledge-data consolidated → knowledge_catalog / element_data → module read model → React`。前端不建立平行化学事实库。
- 产品开发优先形成可连续探索的用户闭环，而不是增加孤立 demo 页面。当前 canonical 产品方向见 `docs/PRODUCT_ROADMAP.md`。
- 不创建推测性抽象，不做无关重构。除非确有必要，不额外创建仓库副本、持久 worktree 或分散在桌面的产物。
- 文档只描述当前 canonical 状态；直接更新 `README.md`、`docs/PRODUCT_ROADMAP.md`、对应 handoff/decision owner，不累积纠正记录或历史叙述。

## Codex Skills

自定义 Skill 的 canonical upstream 为 `ACCXhub/codex-skills`，用户级安装目录通常为 `%USERPROFILE%\.codex\skills\`。

chem-wiki 的项目自定义 Skill 集合固定为：

- `task-anchor`
- `convergent-editing`
- `compact-product-ui`
- `integration-first`

开始相关任务时确保这四个本地副本与 upstream 当前版本一致。删除本地已经被这些 Skill 取代的旧名、重复或过时自定义副本；保留与其他项目有关的独立 Skill。系统/框架提供的 debugging、TDD、verification、React、planning 等 Skill 按任务需要调用，不复制成项目私有重复版本。

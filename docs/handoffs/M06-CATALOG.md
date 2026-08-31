# Consolidated Knowledge Catalog Handoff

## Established boundary

- `chem_wiki.modules.knowledge_catalog` 是应用消费 `consolidated-1.1.0` 的唯一 owner。
  外部 schema 在 release adapter 处终止；M01 typed identity、M05 Reaction aggregate 与 M06
  Structure 边界保持不变。
- `release.py` 固定 repository、release、commit
  `a6311150436038ca06fa7b9d05de39da9e1de815` 和 `READY_FOR_APP_IMPORT`，从
  `generated/manifest.json` 开始校验，并验证本阶段消费的 JSONL 文件存在、记录数与
  byte-exact SHA-256。Windows source checkout 必须使用 `git -c core.autocrlf=false clone`；
  CRLF 改写会按 release contract 被识别为 artifact hash mismatch。
- 本地数据通过 `--source` 或 `KNOWLEDGE_CATALOG_SOURCE` 指向外部 Git checkout/cache；
  generated artifacts 未 vendoring 到 chem-wiki。Windows cache 必须使用
  `git -c core.autocrlf=false clone`，否则严格 byte hash 会拒绝 CRLF 改写后的文件。

## Persistence and identity

- migrations `20260826_03_knowledge_catalog`、`20260828_04_phase1_knowledge`、
  `20260829_05_phase2a_reaction_experience` 与 `20260831_06_phase3a_knowledge_activation` 建立
  release/artifact、species mapping、source crosswalk、teaching projection、Structure link、
  catalog Reaction/participant、reviewed knowledge / accepted Structure record，以及 learner-facing
  source attribution、generic knowledge link、phase fact 与 typed thermochemistry 表。
- 309 条 species 全部导入：58 个 ion、251 个 substance。consolidated ID 是稳定外部 key；
  `catalog_species.application_id` 是稳定 UUID，并由 `entity_kind` 明确解释为 M01 `IonId` 或
  `SubstanceId`。二次导入保持 UUID 与行数不变。
- 309 条 source crosswalk 与 provenance/external ID 保留；309 条 teaching projection 保留
  primary category、tags、search tokens、priority、连续 Palette rank，以及 molecular /
  ionic / net-ionic suitability。
- 69 条 accepted Structure link 全部解析到 application species UUID，并保留 published
  `structure_id` 与独立 application Structure UUID mapping；未关联 species 不生成结构数据。
- pinned release 的 637 条 generic reviewed knowledge envelope 全部导入；structured-only records
  允许 `content_zh` 为空且保留完整 payload。176 条 resolved links 独立持久化，不由 React 猜测 identity。
  Structure Registry 的 69 条 accepted records 保留 canonical/isomeric SMILES 与 provenance。
- pinned inorganic / Structural Chemistry / Thermochemistry source registries 中 16 条可读 attribution 进入
  `catalog_source_attribution`。这是 durable provenance → learner attribution read projection，避免
  request-time 依赖外部 checkout；未解析来源不会把内部 ID 暴露给学习者。

## Reaction materialization

- 183 条 released Reaction 全部进入 catalog/import 层，保留 source identity、完整原始 payload
  与 701 条 participant 语义。
- 175 条正数值计量且 participant 全部解析为 M01 typed UUID 的记录，以稳定 Reaction /
  participant UUID 通过现有 `PostgresReactionRepository` 物化到 M05。
- 8 条保留为 `catalog_only`，机器可读原因包括 `symbolic_stoichiometry`；酚醛树脂记录同时为
  `non_species_participant`。符号系数 `n` 与 `non_species_ref` 原样保留，不提升为 Substance、
  不生成伪造 UUID。
- catalog Reaction 与 M05 materialized Reaction 是明确的两个状态；catalog-only 可由查询服务
  读取，不被视为 release import 失败。

## Query API

- `GET /v1/catalog/species` 支持中文名、alias、英文/search token、ASCII formula、
  `primary_category`、`equation_mode` 与 `1..50` limit；无 mode 时按文本匹配与默认 Palette
  排序，有 mode 时优先 recommended / available / deemphasized。
- 返回值明确区分 `ion | substance`，并包含 consolidated ID、稳定 application UUID、formula、
  charge、category、tags、Palette rank 与三种 equation suitability。结果语义为 `0..N`。
- `GET /v1/catalog/species/completions` 保留 exact lookup 之外的 composition completion：默认仅返回
  substance，并按 exact composition、已选计数满足度、缺口、额外元素/原子、方程适用性、教学优先级、
  Palette rank 与 consolidated ID 稳定排序。
- `GET /v1/catalog/reactions/{consolidated_id}` 提供 catalog Reaction 的 materialization state、
  原因、原始 coefficient、non-species ref 与 application target mapping，供后续阶段追溯。
- `GET /v1/catalog/reactions/{consolidated_id}/detail` 投影 canonical participants、可逆性、类型、条件、
  reviewed concepts/phenomena、related species、Structure 可用性与已解析 source attribution；空字段省略。
- `GET /v1/catalog/species/{application_species_id}/structure` 返回 accepted Structure entry，
  供 Structure Lab 从稳定 application species UUID 直接载入已知结构。
- `GET /v1/catalog/knowledge` 按 stable knowledge ID、source package/type、linked species、
  accepted Structure 或 element atomic number 做 bounded 查询，返回 payload、resolved links 与可读来源。
- `GET /v1/catalog/species/{application_species_id}/thermochemistry` 返回 standard/default phase、
  allowed teaching phases、全部 phase-specific thermochemistry 与相关 phase transitions。H2O(g)/H2O(l)
  保持同一 application species。14 条 bond enthalpy 只提供内部 repository read seam，未增加 learner API 或计算。

## Release-aware local startup

- Windows launcher 在 migration 后先检查 `catalog_release`。已存在 `consolidated-1.1.0` 时直接跳过；
  新 pin 首次启动时从 `KNOWLEDGE_CATALOG_SOURCE` 或仓库同级 `chem-knowledge-data` 精确 checkout 导入一次。
- request-time 不依赖外部 checkout；旧 release history 保留，不 drop/reset 数据库。

## Verification

- 聚焦 release/import/query：`6 passed`，覆盖错误 release/state、错误 Git identity、artifact
  tampering、309/309/69/183/175/8 计数、participant resolution、二次导入、稳定 UUID，以及
  `硫酸`、`硫酸根`、`sulfate`、`SO4`、`Fe`、category 与 equation-mode 排序。
- 后端完整回归：`136 passed, 2 skipped`。
- Ruff：`All checks passed`；format：`90 files already formatted`。
- Alembic `upgrade head` 与 `check` 通过，结果为 `No new upgrade operations detected.`。
- 实际 CLI import 输出：309 species、309 teaching projections、69 Structure links、183 catalog
  reactions、175 M05 materialized reactions、8 catalog-only reactions、7 source attributions。
- Phase 3A release/unit `14 passed`；catalog + Periodic Table + Element Wiki + Reaction Builder +
  Structure Lab 聚焦回归 `37 passed`；真实 PostgreSQL migration/import/idempotence `1 passed`；
  Ruff check/相关格式检查通过。

## Preserved scope

- rules 与 curriculum 继续留在 consolidated release，不强塞进应用表或前端常量。
- 本阶段只激活 data/read seams；未新增 Structure learner UI，未计算 reaction enthalpy，未从 formula
  推断 bond changes。
- Equation Lab 的既有 M05/M07 视觉、EquationDraft 与 Reaction Builder 继续由对应模块拥有；
  Atom Mapping、Bond Diff、Mechanism 与 Synthesis 未在本轮引入。

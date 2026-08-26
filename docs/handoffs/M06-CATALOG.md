# Consolidated Knowledge Catalog Handoff

## Established boundary

- `chem_wiki.modules.knowledge_catalog` 是应用消费 `consolidated-1.0.0` 的唯一 owner。
  外部 schema 在 release adapter 处终止；M01 typed identity、M05 Reaction aggregate 与 M06
  Structure 边界保持不变。
- `release.py` 固定 repository、release、commit
  `c1bf05dd68c936cb0cedf8c6877bbac0f68025e9` 和 `READY_FOR_APP_IMPORT`，从
  `generated/manifest.json` 开始校验，并验证本阶段消费的五个 JSONL 文件存在、记录数与
  SHA-256。
- 本地数据通过 `--source` 或 `KNOWLEDGE_CATALOG_SOURCE` 指向外部 Git checkout/cache；
  generated artifacts 未 vendoring 到 chem-wiki。Windows cache 必须使用
  `git -c core.autocrlf=false clone`，否则严格 byte hash 会拒绝 CRLF 改写后的文件。

## Persistence and identity

- migration `20260826_03_knowledge_catalog` 建立 release/artifact、species mapping、source
  crosswalk、teaching projection、Structure link、catalog Reaction 与 participant 表。
- 309 条 species 全部导入：58 个 ion、251 个 substance。consolidated ID 是稳定外部 key；
  `catalog_species.application_id` 是稳定 UUID，并由 `entity_kind` 明确解释为 M01 `IonId` 或
  `SubstanceId`。二次导入保持 UUID 与行数不变。
- 309 条 source crosswalk 与 provenance/external ID 保留；309 条 teaching projection 保留
  primary category、tags、search tokens、priority、连续 Palette rank，以及 molecular /
  ionic / net-ionic suitability。
- 69 条 accepted Structure link 全部解析到 application species UUID，并保留 published
  `structure_id` 与独立 application Structure UUID mapping；未关联 species 不生成结构数据。

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
- `GET /v1/catalog/reactions/{consolidated_id}` 提供 catalog Reaction 的 materialization state、
  原因、原始 coefficient、non-species ref 与 application target mapping，供后续阶段追溯。

## Verification

- 聚焦 release/import/query：`6 passed`，覆盖错误 release/state、错误 Git identity、artifact
  tampering、309/309/69/183/175/8 计数、participant resolution、二次导入、稳定 UUID，以及
  `硫酸`、`硫酸根`、`sulfate`、`SO4`、`Fe`、category 与 equation-mode 排序。
- 后端完整回归：`136 passed, 2 skipped`。
- Ruff：`All checks passed`；format：`90 files already formatted`。
- Alembic `upgrade head` 与 `check` 通过，结果为 `No new upgrade operations detected.`。
- 实际 CLI import 输出：309 species、309 teaching projections、69 Structure links、183 catalog
  reactions、175 M05 materialized reactions、8 catalog-only reactions。

## Preserved scope

- 637 条 non-species knowledge records、rules 与 curriculum 仅保留 manifest 后的未来消费边界，
  本阶段未强塞入无关表。
- Equation Lab 视觉/交互、运行时 pin/reorder/recent-use、M07 Reaction Builder、Atom Mapping、
  Bond Diff、Mechanism 与 Synthesis 均未实现。

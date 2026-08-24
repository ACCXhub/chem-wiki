# M02 元素数据 PostgreSQL 持久化契约

## 状态与范围

本决议冻结 M02 的最小 PostgreSQL 持久化边界，覆盖正式 1–118 号元素、来源证据、
字段级发布选择和幂等重导入。本决议不定义 migration、ORM、adapter、公开 API、
通用审核工作流、Wiki 内容或 M03+ 行为。

M01 保持不变。`ElementId` 是 canonical 内部 UUID；`atomic_number` 是导入时定位
元素的不可变自然键，而不是主键。

## 1. 表及职责

### `element`

持久化 M01 的 canonical 身份和名称。

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `id` | `uuid` | PK |
| `atomic_number` | `smallint` | NOT NULL, UNIQUE, CHECK 1–118 |
| `symbol` | `varchar(3)` | NOT NULL, UNIQUE |
| `name_zh` | `varchar(16)` | NOT NULL, UNIQUE |
| `name_en` | `varchar(64)` | NOT NULL, UNIQUE |

插入后不得修改 `id` 或 `atomic_number`。M02 不把 predicted/historical 记录写入
此表；它们仅保留为 source record/quarantine，不生成 `element_claim`。

### `element_property`

与 `element` 一对一，保存结构已经明确的 canonical、source-neutral 属性；该表不
扩展冻结的 M01 `Element` 公共模型。

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `element_id` | `uuid` | PK, FK → `element.id` ON DELETE CASCADE |
| `atomic_weight_value` | `numeric` | 可空 |
| `atomic_weight_lower` | `numeric` | 可空 |
| `atomic_weight_upper` | `numeric` | 可空 |
| `atomic_weight_uncertainty` | `numeric` | 可空 |
| `group_no` | `smallint` | 可空, CHECK 1–18 |
| `period_no` | `smallint` | 可空, CHECK 1–7 |
| `block` | `varchar(1)` | 可空, CHECK `s/p/d/f` |
| `electronegativity_value` | `numeric(5,3)` | 可空 |
| `electronegativity_scale` | `varchar(32)` | 与 value 同时为空或非空 |
| `first_ionization_energy_value` | `numeric(10,3)` | 可空 |
| `first_ionization_energy_unit` | `varchar(24)` | 与 value 同时为空或非空 |
| `atomic_radius_value` | `numeric(10,3)` | 可空 |
| `atomic_radius_unit` | `varchar(24)` | 与 value 同时为空或非空 |
| `atomic_radius_qualifier` | `varchar(32)` | 与 value 同时为空或非空 |

原子量只能采用单值，或采用 lower/upper 区间，不能同时采用两种表示。其他候选
属性在其 canonical 结构另行冻结前只保留在 raw record 中。

### `element_source`

M02 专用来源注册表，不承担通用内容平台职责。

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `id` | `uuid` | PK |
| `source_key` | `varchar(64)` | NOT NULL, UNIQUE |
| `title` | `varchar(240)` | NOT NULL |
| `publisher` | `varchar(160)` | 可空 |
| `source_type` | `varchar(32)` | NOT NULL, CHECK `standard/database/open_source/manual` |
| `base_url` | `text` | 可空 |
| `license_code` | `varchar(80)` | 可空 |
| `reuse_policy` | `varchar(32)` | NOT NULL, CHECK `allowed/review_required/prohibited` |

`source_key` 是映射到 M01 `ProvenanceRef.source_id` 的稳定字符串；UUID 只用于
数据库外键。

### `element_source_record`

保存不可变的来源记录和获取证据。这是唯一允许容纳 source-specific payload 的表。

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `id` | `uuid` | PK |
| `source_id` | `uuid` | NOT NULL, FK → `element_source.id` |
| `source_version` | `varchar(120)` | NOT NULL |
| `record_key` | `varchar(160)` | NOT NULL |
| `source_url` | `text` | 可空 |
| `retrieved_at` | `timestamptz` | NOT NULL |
| `content_sha256` | `char(64)` | NOT NULL |
| `raw_payload` | `jsonb` | 可空；是否保存取决于来源 reuse policy |

UNIQUE (`source_id`, `source_version`, `record_key`, `content_sha256`)。若许可证
不允许保留完整 payload，URL、hash、record key 和 claim 级 `raw_value` 仍是必需
证据；若连 raw value 都不允许保留，该来源不得进入 M02 导入流程。

### `element_claim`

保存从一个 source record 得到的不可变、字段级规范化 claim。

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `id` | `uuid` | PK |
| `element_id` | `uuid` | NOT NULL, FK → `element.id` |
| `source_record_id` | `uuid` | NOT NULL, FK → `element_source_record.id` |
| `field_name` | `varchar(64)` | NOT NULL，使用下述 M02 allowlist |
| `raw_value` | `text` | NOT NULL |
| `normalized_text` | `text` | 可空 |
| `normalized_integer` | `integer` | 可空 |
| `normalized_numeric` | `numeric` | 可空 |
| `normalized_lower` | `numeric` | 可空 |
| `normalized_upper` | `numeric` | 可空 |
| `canonical_unit` | `varchar(24)` | 可空 |
| `uncertainty` | `numeric` | 可空 |
| `qualifier` | `varchar(64)` | 可空 |
| `verification_status` | `varchar(16)` | NOT NULL, CHECK `unverified/verified/rejected` |
| `transform_version` | `varchar(64)` | NOT NULL |

初始 allowlist 为 `atomic_number`、`symbol`、`name_zh`、`name_en`、
`atomic_weight`、`group_no`、`period_no`、`block`、`electronegativity`、
`first_ionization_energy`、`atomic_radius`。

一个 claim 只能包含一个 scalar normalized value，或同时包含 lower/upper 两个区间
端点。UNIQUE (`source_record_id`, `field_name`, `transform_version`) 防止同一转换
重复生成 claim。UNIQUE (`id`, `element_id`, `field_name`) 用于支持下述组合外键。

### `element_published_value`

为每个 canonical 字段选择当前唯一 published claim。它是当前决策表，不是事件日志
或工作流引擎。

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `element_id` | `uuid` | FK → `element.id` |
| `field_name` | `varchar(64)` | 与 `element_claim` 使用相同 allowlist |
| `claim_id` | `uuid` | NOT NULL |
| `selection_method` | `varchar(16)` | CHECK `authority_policy/manual` |
| `policy_version` | `varchar(64)` | NOT NULL |
| `selected_by` | `varchar(120)` | NOT NULL；policy 或 reviewer 标识 |
| `selection_reason` | `text` | NOT NULL |
| `selected_at` | `timestamptz` | NOT NULL |

PK (`element_id`, `field_name`)。组合 FK (`claim_id`, `element_id`,
`field_name`) → `element_claim(id, element_id, field_name)`，确保 published claim
属于同一元素和字段。

## 2. Canonical 与 raw 边界

- `element` 和 `element_property` 只保存当前 published、source-neutral 值。
- `element_source`、`element_source_record`、`element_claim` 和
  `element_published_value` 保存证据及发布元数据，不成为 M01 domain 字段。
- 来源字段名、来源记录 ID、原始单位、缺失标记、复杂 variants、未支持属性及未选中
  冲突保留在 `raw_payload`/`raw_value` 中。
- source payload、CAS/CID 等来源标识、拼音、长文本和视觉资产均不得由 M02 加入
  M01 `Element`。

## 3. 字段级 provenance 与发布不变量

`element`/`element_property` 的每个已填充 canonical 字段组都必须恰好对应一条
`element_published_value`。字段组可以是一列，也可以是同一属性的一组关系列，例如
`atomic_weight` 对应 value 或 lower/upper 及 uncertainty。

selected claim 可继续追溯 source record、source registry、raw value、normalized
value、单位、qualifier、uncertainty、获取时间、来源版本和内容 hash。canonical 列
更新与 published selection 更新必须在同一事务内完成。claim 即使失去 current 状态
也不得覆盖或删除。

加载 M01 `Element.provenance` 时，将各 published claim 的获胜来源去重并映射成
`ProvenanceRef` 摘要；字段级明细仍由 M02 持久化边界负责。

## 4. 幂等导入与更新规则

1. 按 `source_key` upsert `element_source`。
2. 按 source record 四列唯一键去重；完全相同的重导入为 no-op。
3. 按 `atomic_number` 查找或创建 `element`；UUID 只生成一次，永不替换。
4. 按 source record、字段和 `transform_version` 去重 claim。新来源版本或转换版本
   产生新证据，不修改旧证据。
5. validation 或 source conflict 不直接修改 canonical 值。只有 resolver/reviewer
   选中的 claim 才能在同一事务内更新 canonical 列和 `element_published_value`。
6. 重复选择当前 claim 为 no-op；获胜 claim 改变时只替换当前 selection 和物化值，
   所有竞争 claim 均保留。
7. atomic number、UUID、symbol 和名称不得跨元素静默重分配；身份冲突必须使 publish
   事务失败并进入人工复核。

## 5. 已发现数据字典冲突的精确解决

1. 将原建议的 `element.id smallint PK` 改为 `element.id uuid PK`；新增
   `atomic_number smallint NOT NULL UNIQUE CHECK 1–118` 作为自然/upsert key，保持
   M01 `ElementId` 语义。
2. 增加必填 `name_en`；它已是 M01 `Element` 的冻结字段，canonical persistence
   不得省略。
3. 删除记录级 `element.source_id`。字段级 provenance 使用
   `element_published_value → element_claim → element_source_record →
   element_source` 表示。
4. 不把来源 UUID 填入 M01 `ProvenanceRef.source_id`；repository 边界映射稳定的
   `element_source.source_key` 字符串。
5. 已知查询字段保留在关系化 `element_property` 中；JSONB 仅用于 source-specific
   raw payload。
6. predicted/historical 不成为 M02 canonical `element` 行，从而无需修改 M01 即可
   与正式 1–118 集合隔离。

## 6. 剩余 blocker

PostgreSQL 契约无剩余 blocker。Periodic Table PRO 缺少明确许可证，仍阻断未经审核
的整批导入或再分发；`raw_payload` 可空及强制 hash/raw-value 证据允许其他许可明确的
来源先行，且不会削弱 provenance。

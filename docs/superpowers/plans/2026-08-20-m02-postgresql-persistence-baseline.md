# M02 PostgreSQL Persistence Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development while executing every code task. This plan is executed inline in the current session because the user explicitly requested immediate implementation; do not commit.

**Goal:** 实现已冻结的六张 M02 PostgreSQL 表、SQLAlchemy 映射、Alembic migration 和聚焦持久化测试。

**Architecture:** 在独立 `chem_wiki.modules.element_data` 模块中集中定义六张表的 declarative mappings 和 metadata。Alembic 只引用该 metadata；测试先验证映射契约，再在真实 PostgreSQL 上验证 upgrade、约束和 downgrade。

**Tech Stack:** Python 3.13、SQLAlchemy 2.x、Alembic、PostgreSQL 17、psycopg、pytest、Ruff。

**Spec:** `docs/decisions/M02-element-persistence-contract.md`

## Global Constraints

- 只实现契约冻结的 `element`、`element_property`、`element_source`、`element_source_record`、`element_claim`、`element_published_value`。
- M01 `ElementId` 继续使用 UUID；`atomic_number` 是唯一自然/upsert key，不是 PK。
- `raw_payload` JSONB 只允许出现在 `element_source_record`；canonical、claim 和 published selection 保持分离。
- 字段 provenance 链固定为 `element_published_value → element_claim → element_source_record → element_source`。
- M02 若引用 M01，只能从 `chem_wiki.modules.chemistry_core` 包根导入。
- 不实现 adapter、网络请求、resolver、review workflow、repository framework、event sourcing 或 M03+ 功能。
- 不提交。

---

### Task 1: 六表 SQLAlchemy mapping

**Files:**
- Create: `backend/tests/modules/element_data/test_persistence.py`
- Create: `backend/src/chem_wiki/modules/element_data/__init__.py`
- Create: `backend/src/chem_wiki/modules/element_data/persistence.py`

**Interfaces:**
- Produces: `ElementDataBase.metadata`；`ElementRow`、`ElementPropertyRow`、`ElementSourceRow`、`ElementSourceRecordRow`、`ElementClaimRow`、`ElementPublishedValueRow`。

- [ ] **Step 1: 写映射契约失败测试**

```python
def test_metadata_contains_only_the_six_frozen_m02_tables() -> None:
    assert set(ElementDataBase.metadata.tables) == {
        "element", "element_property", "element_source",
        "element_source_record", "element_claim", "element_published_value",
    }

def test_element_uses_uuid_pk_and_atomic_number_natural_key() -> None:
    table = ElementDataBase.metadata.tables["element"]
    assert [column.name for column in table.primary_key.columns] == ["id"]
    assert table.c.atomic_number.primary_key is False
    assert table.c.name_en.nullable is False
```

- [ ] **Step 2: 运行测试并确认 RED**

Run: `backend\.venv\Scripts\python.exe -m pytest tests/modules/element_data/test_persistence.py -q`

Expected: FAIL，原因是 `chem_wiki.modules.element_data` 尚不存在。

- [ ] **Step 3: 最小实现 mappings**

使用 SQLAlchemy 2.x `DeclarativeBase`、`Mapped` 和 `mapped_column`。按契约逐项定义列、命名的 CHECK/UNIQUE/FK；`element_claim` 增加 `(id, element_id, field_name)` 唯一约束，`element_published_value` 使用对应组合外键。所有 UUID 主键由应用传入，不在 schema 内引入随机生成扩展。

- [ ] **Step 4: 运行映射测试并确认 GREEN**

Run: `backend\.venv\Scripts\python.exe -m pytest tests/modules/element_data/test_persistence.py -q`

Expected: PASS。

### Task 2: Alembic migration 与真实 PostgreSQL 约束

**Files:**
- Create: `backend/tests/integration/test_element_persistence_migration.py`
- Modify: `backend/migrations/env.py`
- Create: `backend/migrations/versions/20260820_01_m02_element_persistence.py`

**Interfaces:**
- Consumes: `ElementDataBase.metadata`。
- Produces: Alembic revision `20260820_01`，支持从 `base` upgrade 到六表并 downgrade 回 `base`。

- [ ] **Step 1: 写 migration 失败测试**

```python
@pytest.mark.integration
def test_migration_creates_constraints_and_downgrades(database_url: str) -> None:
    command.upgrade(config, "head")
    inspector = inspect(create_engine(database_url))
    assert FROZEN_TABLES <= set(inspector.get_table_names())
    # 插入合法行，并断言重复 atomic_number 与越界 atomic_number 被 PostgreSQL 拒绝。
    command.downgrade(config, "base")
    assert FROZEN_TABLES.isdisjoint(set(inspect(engine).get_table_names()))
```

- [ ] **Step 2: 运行测试并确认 RED**

Run: `$env:DATABASE_URL='<postgres-url>'; backend\.venv\Scripts\python.exe -m pytest tests/integration/test_element_persistence_migration.py -q`

Expected: FAIL，原因是 revision 不存在且 Alembic 尚未加载 M02 metadata。

- [ ] **Step 3: 最小实现 migration**

令 `migrations/env.py` 的 `target_metadata` 指向 `ElementDataBase.metadata`。revision 使用显式 `op.create_table` 按依赖顺序创建六表，使用 PostgreSQL `UUID`/`JSONB`、命名约束和契约组合外键；使用 deferred constraint triggers 在提交时保证 canonical 字段组与 published claim 双向一致，并用触发器保护不可变证据和来源许可策略；`downgrade()` 按反向依赖顺序删除触发器、函数和表。

- [ ] **Step 4: 运行 migration 测试并确认 GREEN**

Run: `$env:DATABASE_URL='<postgres-url>'; backend\.venv\Scripts\python.exe -m pytest tests/integration/test_element_persistence_migration.py -q`

Expected: PASS，结束时回到 Alembic `base`。

### Task 3: 收口验证

**Files:**
- Modify only if verification exposes an implementation defect in Task 1–2 files.

- [ ] **Step 1: 运行聚焦 M02 测试**

Run: `$env:DATABASE_URL='<postgres-url>'; backend\.venv\Scripts\python.exe -m pytest tests/modules/element_data tests/integration/test_element_persistence_migration.py -q`

- [ ] **Step 2: 运行全部 backend 测试**

Run: `$env:DATABASE_URL='<postgres-url>'; backend\.venv\Scripts\python.exe -m pytest -q`

- [ ] **Step 3: 运行 Ruff**

Run: `backend\.venv\Scripts\ruff.exe check .`

Run: `backend\.venv\Scripts\ruff.exe format --check .`

- [ ] **Step 4: 核对 migration 和变更范围**

Run: `$env:DATABASE_URL='<postgres-url>'; backend\.venv\Scripts\alembic.exe upgrade head; backend\.venv\Scripts\alembic.exe current; backend\.venv\Scripts\alembic.exe downgrade base`

Run: `git status --short; git diff --check`

Expected: revision 可往返、六表映射和 migration 一致、测试与 Ruff 全绿，且没有 commit。

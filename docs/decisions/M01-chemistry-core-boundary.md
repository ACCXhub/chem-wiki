# M01 Chemistry Core 边界决策

- 状态：已冻结，供 M01 实现使用
- 日期：2026-08-20

## 1. M01 范围

M01 只实现以下六个顶层领域实体：

- `Element`
- `Ion`
- `Substance`
- `Structure`
- `FunctionalGroup`
- `Reaction`

`ReactionParticipant` 是 `Reaction` 聚合内的子实体，具有稳定的
`ReactionParticipantId`。它不是独立聚合根。

M01 只定义上述实体实际使用的值对象：

- 对应六个实体及参与者的强类型 ID；
- `Element` 使用的 `AtomicNumber`、`ElementSymbol`；
- `Ion`、`Substance` 使用的 `ChemicalFormula`、`CompositionEntry`，以及 `Ion`
  使用的 `ElectricCharge`；
- `Structure` 使用的表示格式与文本载荷；该载荷不得暴露化学库类型；
- `Reaction` 使用的 `ReactionCode`、`ReactionStatus`、`ParticipantTarget`、
  `ReactionRole`、`StoichiometricCoefficient`、`Phase`、`Condition`；
- 需要记录来源的实体字段和参与关系使用的 `ProvenanceRef`。

不建立通用 `Entity` 基类、`ChemicalSpecies` 层次、泛型 repository/service，
也不预先定义尚无 M01 使用方的值对象。

## 2. Reaction 与 Participant 不变量

- `Reaction` 是一等实体和聚合根，不得退化为 `Substance -> Substance` 边。
- 每个 `Reaction` 至少有一个 `reactant` 和一个 `product`。
- 每个参与者具有在该 Reaction 生命周期内稳定且唯一的
  `ReactionParticipantId`。
- `ParticipantTarget` 是显式可辨识联合：`SubstanceId | IonId`；不得使用通用
  `ChemicalSpecies` 父类或无类型字符串引用。
- `StoichiometricCoefficient` 必须大于零；参与者角色限定为现有契约中的
  `reactant | product | catalyst | solvent`。
- `Condition` 是 Reaction 内嵌值对象，没有独立 ID、repository 或生命周期。
- `equation_text`、`reaction_smiles` 等表示不能取代结构化参与者，也不是 Reaction
  身份或化学真值的来源。
- 质量守恒、电荷守恒、配平、离子/净离子方程式和发布校验属于 M05；M01 不提供
  绕过这些校验的发布工作流。

## 3. Provenance 边界

M01 仅定义最小 `ProvenanceRef`：必需的 `source_id`，以及可选的
`source_url`、`citation`、`retrieved_at`、`source_version`。它是外部来源记录的
不透明引用，不要求 M01 拥有来源实体。

来源应附着在具体的外部事实或参与关系上，而不能只给整个聚合一个笼统来源。
`ContentSource`、`ContentRevision`、置信度、审核状态、修订流程及其持久化由后续
内容模块实现。M01 不实现这两个实体。

## 4. 明确延期

- `KnowledgeEdge` 及知识图节点/关系、图遍历和排名；
- `ContentSource`、`ContentRevision` 及内容审核、发布、修订流程；
- `Experiment`、`Phenomenon`、`Concept`、`Question`、`ExamTag`、
  `ExamOccurrence`；
- Structure 解析、化学有效性验证、规范化、指纹、相似性、2D/3D 生成和官能团
  检测；
- Reaction 配平、质量/电荷守恒、分子/离子/净离子方程式、氧化还原分析及现象
  关联；
- `AtomMapping`、`BondDiff`/`BondChange`、`Mechanism`、`MechanismStep`、
  `ElectronFlow`/`ElectronMove`。

最后一组不在 M01 中建立 ID、接口或占位类型。后续必须保持 Atom Mapping、Bond
Diff 和 Reviewed Mechanism 三层独立；Atom Mapping 不能推导或宣称 Mechanism 为
真，Electron Flow 只能属于经来源与审核支持的 Mechanism。

## 5. 契约不一致及决议

| 现有不一致 | M01 决议 |
|---|---|
| 数据字典列出大量“一等实体”，M01 模块还要求 `KnowledgeEdge`、`ContentSource`、`ContentRevision` | 数据字典视为全产品目录，不视为单个模块实现清单；M01 仅实现本决策第 1 节范围，三个实体延期。 |
| Reaction Schema 的参与者只有 `substance_id`，无法表达 `Ion` | 领域模型使用可辨识的 `SubstanceId | IonId`；旧 Schema 不作为 M01 领域模型的权威契约，后续应改为带 `kind` 和 `id` 的 target。 |
| `ReactionParticipant` 在字典中是一等概念，但 Schema 中匿名且无 ID | 冻结为 Reaction 子实体，并要求稳定 `ReactionParticipantId`。 |
| Schema 的 `minItems: 2` 不能保证同时存在反应物和产物 | 由 Reaction 聚合显式执行“至少一个 reactant、至少一个 product”的不变量。 |
| `Condition` 在字典/知识图中像实体，在 Reaction Schema 中却内嵌 | M01 选择内嵌值对象；不创建 Condition 节点或 repository。 |
| `Structure` 与 Substance 分离，但现有契约未定义其独立生命周期 | M01 保留独立实体和稳定 ID，只保存库无关表示；解析、验证及派生能力延期。 |
| provenance 要求字段/关系级追踪，但 Reaction/Mechanism Schema 基本未表达 | M01 使用最小 `ProvenanceRef` 附着于具体事实或参与关系；完整来源与审核模型延期。 |
| `ExamTag` 在数据字典/关系中出现却不在知识图节点清单，节点清单另有 `ExamOccurrence` | 两者均不属于 M01，由后续考试/内容模块统一契约。 |
| `Condition`、`BondChange` 被图关系引用却不在节点清单；Mechanism 示例与 Schema 还存在 `index`/`order`、ID、review/provenance 差异 | M01 不修补这些跨模块契约，也不创建占位；由各自后续模块在实现前冻结。 |

## 6. 依赖规则与阻塞项

领域代码不得依赖 FastAPI、Pydantic、SQLAlchemy 或任何化学库专用类型。API DTO、
ORM 映射和化学计算库只能通过外层 Adapter 转换为领域类型。具体 repository Port
只在出现实际 M01 用例时定义。

在遵守本决策并且不把旧 JSON/YAML Schema 当作当前领域模型权威的前提下，M01
纯领域实现没有剩余阻塞项。旧机器契约必须在相应接口或后续模块开始实现前另行
对齐，但不阻塞本次边界冻结。

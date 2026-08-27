import { useEffect, useMemo, useState, type FormEvent } from 'react'

import { loadPeriodicTableElements } from '../periodic_table'
import { balanceEquation, searchCatalogSpecies } from './api'
import ChemistryNotation from './ChemistryNotation'
import {
  addParticipant,
  addBuilderBlock,
  adjustBuilderBlock,
  canSubmitDraft,
  clearBuilderTray,
  moveParticipant,
  resolveBuilderTray,
  serializeEquationDraft,
  updateParticipantPhase,
} from './composer'
import {
  loadPalettePreferences,
  orderPaletteSpecies,
  recordPaletteRecent,
  savePalettePreferences,
  togglePaletteFavorite,
} from './palette-preferences'
import type {
  BalanceEquationResponse,
  BuilderBlock,
  BuilderTrayEntry,
  CatalogSpecies,
  CatalogSpeciesQuery,
  EquationDraft,
  EquationDraftParticipant,
  EquationMode,
  EquationPhase,
} from './types'
import type { PeriodicTableElement } from '../periodic_table'
import './equation-lab.css'


interface EquationLabProps {
  onBack: () => void
}

type DraftSide = 'reactants' | 'products'
type PaletteMode = 'search' | 'builder'

type SearchSpecies = (
  query: CatalogSpeciesQuery,
  signal?: AbortSignal,
) => Promise<CatalogSpecies[]>

interface EquationLabViewProps extends EquationLabProps {
  onBalance: (
    equation: string,
    mode: EquationMode,
  ) => Promise<BalanceEquationResponse>
  onSearch?: SearchSpecies
  onLoadElements?: () => Promise<PeriodicTableElement[]>
}

const EXAMPLES: Array<{
  label: string
  equation: string
  mode: EquationMode
}> = [
  { label: '水的生成', equation: 'H2 + O2 -> H2O', mode: 'molecular' },
  {
    label: '沉淀示例',
    equation: 'Ag+(aq) + Cl-(aq) -> AgCl(s)',
    mode: 'net_ionic',
  },
  {
    label: '无净反应示例',
    equation: 'Na+(aq) + NO3-(aq)',
    mode: 'net_ionic',
  },
]

const MODE_LABELS: Record<EquationMode, string> = {
  molecular: '分子方程式',
  ionic: '离子方程式',
  net_ionic: '净离子方程式',
}

const CATEGORY_OPTIONS = [
  ['', '全部'],
  ['elemental_substance', '单质'],
  ['acid', '酸'],
  ['base', '碱'],
  ['salt', '盐'],
  ['oxide', '氧化物'],
  ['cation', '阳离子'],
  ['anion', '阴离子'],
  ['organic', '有机物'],
  ['other', '其他'],
] as const

const SUITABILITY_LABELS = {
  recommended: '推荐',
  available: '可用',
  deemphasized: '非典型',
} as const

const EMPTY_DRAFT: EquationDraft = {
  mode: 'molecular',
  reactants: [],
  products: [],
}

const COMMON_ELEMENT_SYMBOLS = new Set([
  'H', 'C', 'N', 'O', 'F', 'Na', 'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'K', 'Ca', 'Fe', 'Cu', 'Zn', 'Ag', 'Ba',
])

function elementBlock(element: PeriodicTableElement): BuilderBlock {
  return {
    id: `element:${element.id}`,
    label: element.nameZh,
    formula: element.symbol,
    composition: { [element.symbol]: 1 },
    charge: 0,
    kind: 'element',
  }
}

function ionBlock(species: CatalogSpecies): BuilderBlock | null {
  if (species.entityKind !== 'ion' || !species.composition) return null
  return {
    id: `catalog:${species.applicationId}`,
    label: species.nameZh,
    formula: species.formula,
    composition: species.composition,
    charge: species.charge,
    kind: 'ion',
  }
}

export function EquationLabView({
  onBack,
  onBalance,
  onSearch = searchCatalogSpecies,
  onLoadElements = loadPeriodicTableElements,
}: EquationLabViewProps) {
  const [draft, setDraft] = useState<EquationDraft>(EMPTY_DRAFT)
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('')
  const [catalog, setCatalog] = useState<CatalogSpecies[]>([])
  const [catalogLoading, setCatalogLoading] = useState(true)
  const [catalogError, setCatalogError] = useState<string | null>(null)
  const [paletteMode, setPaletteMode] = useState<PaletteMode>('search')
  const [preferences, setPreferences] = useState(loadPalettePreferences)
  const [builderElements, setBuilderElements] = useState<PeriodicTableElement[]>([])
  const [builderCations, setBuilderCations] = useState<CatalogSpecies[]>([])
  const [builderAnions, setBuilderAnions] = useState<CatalogSpecies[]>([])
  const [builderTray, setBuilderTray] = useState<BuilderTrayEntry[]>([])
  const [builderMatches, setBuilderMatches] = useState<CatalogSpecies[]>([])
  const [builderLoading, setBuilderLoading] = useState(false)
  const [builderError, setBuilderError] = useState<string | null>(null)
  const [showAllElements, setShowAllElements] = useState(false)
  const [directEquation, setDirectEquation] = useState(EXAMPLES[0].equation)
  const [directMode, setDirectMode] = useState<EquationMode>(EXAMPLES[0].mode)
  const [result, setResult] = useState<BalanceEquationResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      setCatalogLoading(true)
      setCatalogError(null)
      void onSearch({
        query,
        primaryCategory: category || undefined,
        equationMode: draft.mode,
        limit: 50,
      }, controller.signal)
        .then(setCatalog)
        .catch((reason: unknown) => {
          if (reason instanceof DOMException && reason.name === 'AbortError') return
          setCatalog([])
          setCatalogError(reason instanceof Error ? reason.message : '物种目录加载失败')
        })
        .finally(() => {
          if (!controller.signal.aborted) setCatalogLoading(false)
        })
    }, 160)
    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [category, draft.mode, onSearch, query])

  useEffect(() => {
    if (paletteMode !== 'builder') return
    const controller = new AbortController()
    const blocksRequest = Promise.allSettled([
      onLoadElements(),
      onSearch({ primaryCategory: 'cation', equationMode: 'ionic', limit: 50 }, controller.signal),
      onSearch({ primaryCategory: 'anion', equationMode: 'ionic', limit: 50 }, controller.signal),
    ])
    void Promise.resolve().then(() => {
      if (!controller.signal.aborted) {
        setBuilderLoading(true)
        setBuilderError(null)
      }
    })
    void blocksRequest.then(([elements, cations, anions]) => {
      if (controller.signal.aborted) return
      if (elements.status === 'fulfilled') setBuilderElements(elements.value)
      if (cations.status === 'fulfilled') setBuilderCations(cations.value)
      if (anions.status === 'fulfilled') setBuilderAnions(anions.value)
      const failures = [elements, cations, anions].filter((item) => item.status === 'rejected')
      if (failures.length) {
        setBuilderError('部分构建块暂不可用；目录中可用的块仍可继续组合。')
      }
    }).finally(() => {
      if (!controller.signal.aborted) setBuilderLoading(false)
    })
    return () => controller.abort()
  }, [onLoadElements, onSearch, paletteMode])

  const builderResolution = useMemo(() => resolveBuilderTray(builderTray), [builderTray])

  useEffect(() => {
    if (!builderResolution || paletteMode !== 'builder') return
    const controller = new AbortController()
    const matchRequest = onSearch({
      composition: builderResolution.composition,
      charge: builderResolution.totalCharge,
      entityKind: builderResolution.entityKind,
      equationMode: draft.mode,
      limit: 50,
    }, controller.signal)
    void Promise.resolve().then(() => {
      if (!controller.signal.aborted) {
        setBuilderLoading(true)
        setBuilderError(null)
      }
    })
    void matchRequest.then((matches) => {
      if (!controller.signal.aborted) setBuilderMatches(matches)
    }).catch((reason: unknown) => {
      if (!controller.signal.aborted) {
        setBuilderMatches([])
        setBuilderError(reason instanceof Error ? reason.message : '已知物种匹配失败')
      }
    }).finally(() => {
      if (!controller.signal.aborted) setBuilderLoading(false)
    })
    return () => controller.abort()
  }, [builderResolution, draft.mode, onSearch, paletteMode])

  const orderedCatalog = useMemo(
    () => orderPaletteSpecies(catalog, preferences),
    [catalog, preferences],
  )

  const runBalance = async (equation: string, mode: EquationMode) => {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      setResult(await onBalance(equation, mode))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '方程式处理失败')
    } finally {
      setLoading(false)
    }
  }

  const handleComposerSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (!canSubmitDraft(draft)) return
    void runBalance(serializeEquationDraft(draft), draft.mode)
  }

  const handleDirectSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (!directEquation.trim()) return
    void runBalance(directEquation.trim(), directMode)
  }

  const chooseExample = (example: (typeof EXAMPLES)[number]) => {
    setDirectEquation(example.equation)
    setDirectMode(example.mode)
    setResult(null)
    setError(null)
  }

  const changeSide = (
    side: DraftSide,
    update: (participants: EquationDraftParticipant[]) => EquationDraftParticipant[],
  ) => {
    setDraft((current) => ({ ...current, [side]: update(current[side]) }))
    setResult(null)
    setError(null)
  }

  const addToSide = (side: DraftSide, species: CatalogSpecies) => {
    changeSide(side, (participants) => addParticipant(participants, species))
    setPreferences((current) => {
      const next = recordPaletteRecent(current, species.applicationId)
      savePalettePreferences(next)
      return next
    })
  }

  const toggleFavorite = (species: CatalogSpecies) => {
    setPreferences((current) => {
      const next = togglePaletteFavorite(current, species.applicationId)
      savePalettePreferences(next)
      return next
    })
  }

  return (
    <main className="equation-lab-page">
      <nav className="lab-breadcrumb" aria-label="面包屑导航">
        <button type="button" onClick={onBack}>元素周期表</button>
        <span aria-hidden="true">/</span>
        <span>方程实验室</span>
      </nav>

      <header className="equation-lab-header">
        <div>
          <p className="eyebrow">M05 · Equation Composer</p>
          <h1>方程实验室</h1>
          <p>从课程物种目录选择反应物与生成物，再交给守恒引擎配平。</p>
        </div>
        <span className="engine-boundary">Catalog draft → M05 balance</span>
      </header>

      <form className="composer-panel" onSubmit={handleComposerSubmit}>
        <div className="composer-toolbar">
          <div className="mode-switcher" role="group" aria-label="方程式模式">
            {Object.entries(MODE_LABELS).map(([value, label]) => (
              <button
                key={value}
                type="button"
                aria-pressed={draft.mode === value}
                onClick={() => {
                  setDraft((current) => ({ ...current, mode: value as EquationMode }))
                  setResult(null)
                  setError(null)
                }}
              >
                {label}
              </button>
            ))}
          </div>
          <button
            className="clear-draft"
            type="button"
            onClick={() => {
              setDraft((current) => ({ ...current, reactants: [], products: [] }))
              setResult(null)
              setError(null)
            }}
            disabled={!draft.reactants.length && !draft.products.length}
          >
            清空草稿
          </button>
        </div>

        <div className="equation-composer" aria-label="结构化方程式草稿">
          <DraftSidePanel
            title="反应物"
            participants={draft.reactants}
            onClear={() => changeSide('reactants', () => [])}
            onRemove={(id) => changeSide('reactants', (items) => items.filter((item) => item.applicationId !== id))}
            onMove={(index, direction) => changeSide('reactants', (items) => moveParticipant(items, index, direction))}
            onPhase={(id, phase) => changeSide('reactants', (items) => updateParticipantPhase(items, id, phase))}
          />
          <div className="composer-arrow" aria-label="生成">→</div>
          <DraftSidePanel
            title="生成物"
            participants={draft.products}
            onClear={() => changeSide('products', () => [])}
            onRemove={(id) => changeSide('products', (items) => items.filter((item) => item.applicationId !== id))}
            onMove={(index, direction) => changeSide('products', (items) => moveParticipant(items, index, direction))}
            onPhase={(id, phase) => changeSide('products', (items) => updateParticipantPhase(items, id, phase))}
          />
        </div>

        <div className="composer-actions">
          <p>
            {draft.mode === 'net_ionic' && draft.reactants.length && !draft.products.length
              ? '净离子模式允许仅提交反应物，以检查“无净离子反应”状态。'
              : '选择物种后可设置物态；方程字符串由草稿自动生成。'}
          </p>
          <button className="lab-submit" type="submit" disabled={loading || !canSubmitDraft(draft)}>
            {loading ? '正在计算…' : '配平并验证'}
          </button>
        </div>
      </form>

      <div className="equation-workspace">
        <section className="species-palette" aria-labelledby="palette-heading">
          <div className="lab-heading compact">
            <div><p className="eyebrow">Species catalog</p><h2 id="palette-heading">物种目录</h2></div>
            <span>{catalogLoading ? '查询中…' : `${catalog.length} 项`}</span>
          </div>
          <div className="palette-mode-switch" role="group" aria-label="物种选择方式">
            <button type="button" aria-pressed={paletteMode === 'search'} onClick={() => setPaletteMode('search')}>搜索物种</button>
            <button type="button" aria-pressed={paletteMode === 'builder'} onClick={() => setPaletteMode('builder')}>构建物种</button>
          </div>
          {paletteMode === 'search' ? <>
            <label className="species-search">
              <span>搜索名称、别名或化学式</span>
              <input
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="例如：硫酸根 / sulfate / SO4"
              />
            </label>
            <div className="category-nav" aria-label="物种分类">
              {CATEGORY_OPTIONS.map(([value, label]) => (
              <button
                key={value || 'all'}
                type="button"
                aria-pressed={category === value}
                onClick={() => setCategory(value)}
              >
                {label}
              </button>
              ))}
            </div>
            {catalogError ? <div className="catalog-state is-error" role="alert">{catalogError}</div> : null}
            {!catalogError && !catalogLoading && !catalog.length ? (
              <div className="catalog-state">没有匹配当前搜索与分类的物种。</div>
            ) : null}
            <div className="species-list" aria-live="polite">
              {orderedCatalog.map((species) => {
              const suitability = species.equationModes[draft.mode]
              const isFavorite = preferences.favorites.includes(species.applicationId)
              const isRecent = preferences.recents.includes(species.applicationId)
              return (
                <article
                  key={species.consolidatedId}
                  className={`species-row kind-${species.entityKind} suitability-${suitability}`}
                >
                  <div className="species-identity">
                    <ChemistryNotation formula={species.formula} charge={species.charge} />
                    <span><strong>{species.nameZh}</strong><small>{species.nameEn}</small></span>
                  </div>
                  <span className="suitability-label">{SUITABILITY_LABELS[suitability]}</span>
                  <div className="species-add-actions">
                    <button type="button" className="species-favorite" aria-pressed={isFavorite} onClick={() => toggleFavorite(species)} aria-label={`${isFavorite ? '取消收藏' : '收藏'}${species.nameZh}`}>{isFavorite ? '★ 收藏' : '☆ 收藏'}</button>
                    <button type="button" onClick={() => addToSide('reactants', species)} aria-label={`将${species.nameZh}添加到反应物`}>+ 反应物</button>
                    <button type="button" onClick={() => addToSide('products', species)} aria-label={`将${species.nameZh}添加到生成物`}>+ 生成物</button>
                    {isRecent ? <span className="recent-label">最近</span> : null}
                  </div>
                </article>
              )
              })}
            </div>
          </> : <SpeciesBuilder
            elements={builderElements}
            cations={builderCations}
            anions={builderAnions}
            tray={builderTray}
            matches={builderResolution ? builderMatches : []}
            resolution={builderResolution}
            loading={builderLoading}
            error={builderError}
            showAllElements={showAllElements}
            onShowAllElements={() => setShowAllElements((value) => !value)}
            onAddBlock={(block) => setBuilderTray((current) => addBuilderBlock(current, block))}
            onAdjustBlock={(id, delta) => setBuilderTray((current) => adjustBuilderBlock(current, id, delta))}
            onClear={() => setBuilderTray(clearBuilderTray())}
            onAddToSide={addToSide}
          />}
        </section>

        <section className="lab-result" aria-labelledby="result-heading">
          <div className="lab-heading compact">
            <div><p className="eyebrow">Conservation</p><h2 id="result-heading">配平与守恒</h2></div>
          </div>
          {error ? <div className="lab-error" role="alert"><strong>无法配平</strong><p>{error}</p></div> : null}
          {!result && !error ? (
            <div className="lab-empty"><span>→</span><p>提交结构化草稿后，这里显示最简系数和守恒明细。</p></div>
          ) : null}
          {result ? <EquationResult result={result} /> : null}
        </section>
      </div>

      <details className="advanced-equation-input">
        <summary>高级：直接输入完整方程式</summary>
        <form onSubmit={handleDirectSubmit}>
          <div className="lab-examples" aria-label="方程式示例">
            {EXAMPLES.map((example) => (
              <button key={example.label} type="button" onClick={() => chooseExample(example)}>
                {example.label}
              </button>
            ))}
          </div>
          <label htmlFor="direct-equation">化学方程式</label>
          <textarea
            id="direct-equation"
            value={directEquation}
            onChange={(event) => setDirectEquation(event.target.value)}
            spellCheck={false}
            rows={3}
          />
          <label htmlFor="direct-equation-mode">表示层级</label>
          <select
            id="direct-equation-mode"
            value={directMode}
            onChange={(event) => setDirectMode(event.target.value as EquationMode)}
          >
            {Object.entries(MODE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
          <button type="submit" disabled={loading || !directEquation.trim()}>直接配平</button>
        </form>
      </details>

      <p className="lab-scope-note">
        此处只组合已知物种并调用 M05 守恒引擎；不预测生成物，不执行原子映射、键变化或机理推断。
      </p>
    </main>
  )
}

interface DraftSidePanelProps {
  title: string
  participants: EquationDraftParticipant[]
  onClear: () => void
  onRemove: (applicationId: string) => void
  onMove: (index: number, direction: -1 | 1) => void
  onPhase: (applicationId: string, phase: EquationPhase | null) => void
}

function DraftSidePanel({
  title,
  participants,
  onClear,
  onRemove,
  onMove,
  onPhase,
}: DraftSidePanelProps) {
  return (
    <section className="draft-side" aria-label={title}>
      <header>
        <h2>{title}</h2>
        <button type="button" onClick={onClear} disabled={!participants.length}>清空</button>
      </header>
      {!participants.length ? <p className="draft-placeholder">从物种目录添加</p> : null}
      <div className="draft-participants">
        {participants.map((participant, index) => (
          <div key={participant.applicationId} className={`draft-participant kind-${participant.entityKind}`}>
            <div className="draft-species-main">
              <ChemistryNotation formula={participant.formula} charge={participant.charge} phase={participant.phase} />
              <span>{participant.nameZh}</span>
              <button type="button" onClick={() => onRemove(participant.applicationId)} aria-label={`移除${participant.nameZh}`}>×</button>
            </div>
            <div className="draft-species-controls">
              <label>
                <span>物态</span>
                <select
                  aria-label={`${participant.nameZh}的物态`}
                  value={participant.phase ?? ''}
                  onChange={(event) => onPhase(
                    participant.applicationId,
                    (event.target.value || null) as EquationPhase | null,
                  )}
                >
                  <option value="">未指定</option>
                  <option value="aq">aq</option>
                  <option value="s">s</option>
                  <option value="l">l</option>
                  <option value="g">g</option>
                </select>
              </label>
              {participants.length > 1 ? (
                <span className="reorder-actions">
                  <button type="button" onClick={() => onMove(index, -1)} disabled={index === 0} aria-label={`${participant.nameZh}前移`}>←</button>
                  <button type="button" onClick={() => onMove(index, 1)} disabled={index === participants.length - 1} aria-label={`${participant.nameZh}后移`}>→</button>
                </span>
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

interface SpeciesBuilderProps {
  elements: PeriodicTableElement[]
  cations: CatalogSpecies[]
  anions: CatalogSpecies[]
  tray: BuilderTrayEntry[]
  matches: CatalogSpecies[]
  resolution: ReturnType<typeof resolveBuilderTray>
  loading: boolean
  error: string | null
  showAllElements: boolean
  onShowAllElements: () => void
  onAddBlock: (block: BuilderBlock) => void
  onAdjustBlock: (id: string, delta: -1 | 1) => void
  onClear: () => void
  onAddToSide: (side: DraftSide, species: CatalogSpecies) => void
}

function SpeciesBuilder({
  elements,
  cations,
  anions,
  tray,
  matches,
  resolution,
  loading,
  error,
  showAllElements,
  onShowAllElements,
  onAddBlock,
  onAdjustBlock,
  onClear,
  onAddToSide,
}: SpeciesBuilderProps) {
  const visibleElements = showAllElements
    ? elements
    : elements.filter((element) => COMMON_ELEMENT_SYMBOLS.has(element.symbol))
  const cationBlocks = cations.flatMap((species) => {
    const block = ionBlock(species)
    return block ? [block] : []
  })
  const anionBlocks = anions.flatMap((species) => {
    const block = ionBlock(species)
    return block ? [block] : []
  })
  return (
    <section className="species-builder" aria-labelledby="builder-heading">
      <div className="builder-heading">
        <div><p className="eyebrow">Catalog resolution</p><h2 id="builder-heading">受控构建</h2></div>
        <span>只匹配已有目录物种</span>
      </div>
      <p className="builder-intro">从元素与目录离子组成配方，再按组成和总电荷查找已知物种。</p>
      {error ? <div className="catalog-state is-error" role="alert">{error}</div> : null}
      <BuilderBlockGroup title="常用阳离子" blocks={cationBlocks} onAddBlock={onAddBlock} />
      <BuilderBlockGroup title="阴离子 / 多原子离子" blocks={anionBlocks} onAddBlock={onAddBlock} />
      <BuilderBlockGroup
        title={showAllElements ? '全部元素' : '常用元素'}
        blocks={visibleElements.map(elementBlock)}
        onAddBlock={onAddBlock}
      />
      {elements.length > visibleElements.length || showAllElements ? (
        <button className="show-elements" type="button" onClick={onShowAllElements}>
          {showAllElements ? '收起到常用元素' : `显示全部 ${elements.length} 个元素`}
        </button>
      ) : null}
      <div className="builder-tray" aria-label="组成托盘">
        <div className="builder-tray-heading">
          <strong>组成托盘</strong>
          <button type="button" onClick={onClear} disabled={!tray.length}>清空</button>
        </div>
        {!tray.length ? <p>添加受控块后，在此查看组成与总电荷。</p> : (
          <div className="tray-entries">
            {tray.map((entry) => (
              <div className="tray-entry" key={entry.block.id}>
                <ChemistryNotation formula={entry.block.formula} charge={entry.block.charge} />
                <span>{entry.block.label}</span>
                <div className="tray-count">
                  <button type="button" onClick={() => onAdjustBlock(entry.block.id, -1)} aria-label={`减少${entry.block.label}`}>−</button>
                  <strong>× {entry.count}</strong>
                  <button type="button" onClick={() => onAdjustBlock(entry.block.id, 1)} aria-label={`增加${entry.block.label}`}>+</button>
                </div>
              </div>
            ))}
          </div>
        )}
        {resolution ? (
          <p className="builder-facts">
            组成 {Object.entries(resolution.composition).map(([element, count]) => `${element}${count > 1 ? count : ''}`).join(' ')}
            <span>总电荷 {resolution.totalCharge > 0 ? '+' : ''}{resolution.totalCharge}</span>
          </p>
        ) : null}
      </div>
      <div className="builder-matches" aria-live="polite">
        <strong>已知物种匹配</strong>
        {!resolution ? <p>等待组成托盘。</p> : loading ? <p>正在匹配目录…</p> : !matches.length ? (
          <p>没有匹配的已知目录物种；不会创建新的物种 identity。</p>
        ) : (
          <>
            <p>{matches.length === 1 ? '已找到 1 个已知物种。' : `已找到 ${matches.length} 个有效候选，请选择。`}</p>
            <div className="builder-match-list">
              {matches.map((species) => (
                <article key={species.applicationId} className="builder-match">
                  <div><ChemistryNotation formula={species.formula} charge={species.charge} /><span>{species.nameZh}</span></div>
                  <div className="species-add-actions">
                    <button type="button" onClick={() => onAddToSide('reactants', species)} aria-label={`将${species.nameZh}添加到反应物`}>+ 反应物</button>
                    <button type="button" onClick={() => onAddToSide('products', species)} aria-label={`将${species.nameZh}添加到生成物`}>+ 生成物</button>
                  </div>
                </article>
              ))}
            </div>
          </>
        )}
      </div>
    </section>
  )
}

function BuilderBlockGroup({
  title,
  blocks,
  onAddBlock,
}: {
  title: string
  blocks: BuilderBlock[]
  onAddBlock: (block: BuilderBlock) => void
}) {
  if (!blocks.length) return null
  return (
    <div className="builder-block-group">
      <strong>{title}</strong>
      <div className="builder-blocks">
        {blocks.map((block) => (
          <button type="button" key={block.id} onClick={() => onAddBlock(block)} aria-label={`添加${block.label}`}>
            <ChemistryNotation formula={block.formula} charge={block.charge} />
            <span>{block.label}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

function EquationResult({ result }: { result: BalanceEquationResponse }) {
  const inputLabel = result.state === 'no_net_ionic'
    ? '无净离子反应'
    : result.inputState === 'balanced'
      ? '输入已经守恒'
      : '输入未配平，已求得最简整数比'
  return (
    <div className="equation-result-body">
      <span className={`lab-status state-${result.state}`}>{inputLabel}</span>
      <div className="formatted-equation" aria-label="配平结果">{result.formattedEquation}</div>
      {result.message ? <p className="lab-message">{result.message}</p> : null}
      {result.phenomenon ? <p className="lab-phenomenon"><strong>现象</strong>{result.phenomenon}</p> : null}
      {result.products.length > 0 && result.conservation.elements.length > 0 ? (
        <div className="conservation-table-wrap">
          <table>
            <caption>守恒核对</caption>
            <thead><tr><th>项目</th><th>反应物侧</th><th>生成物侧</th><th>状态</th></tr></thead>
            <tbody>
              {result.conservation.elements.map((item) => (
                <tr key={item.element}>
                  <th>{item.element}</th><td>{item.reactants}</td><td>{item.products}</td>
                  <td>{item.conserved ? '守恒' : '不守恒'}</td>
                </tr>
              ))}
              {result.conservation.charge ? (
                <tr><th>总电荷</th><td>{result.conservation.charge.reactants}</td><td>{result.conservation.charge.products}</td><td>{result.conservation.charge.conserved ? '守恒' : '不守恒'}</td></tr>
              ) : null}
            </tbody>
          </table>
        </div>
      ) : null}
      <aside className="redox-boundary">
        <strong>不从配平结果推断机理</strong>
        <p>{result.redox.message}</p>
      </aside>
    </div>
  )
}

export default function EquationLab({ onBack }: EquationLabProps) {
  return <EquationLabView onBack={onBack} onBalance={balanceEquation} />
}

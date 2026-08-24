import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type FormEvent,
} from 'react'

import { loadPeriodicTableElements } from './api'
import type { ElementCategory, PeriodicTableElement } from './types'
import './periodic-table.css'

type DisplayMode = 'category' | 'electronegativity' | 'firstIonizationEnergy'

interface PeriodicTableViewProps {
  elements: readonly PeriodicTableElement[]
  onElementSelect?: (elementId: string) => void
}

interface PeriodicTableProps {
  onElementSelect?: (elementId: string) => void
}

const CATEGORY_LABELS: Record<ElementCategory, string> = {
  'alkali-metal': '碱金属',
  'alkaline-earth-metal': '碱土金属',
  'transition-metal': '过渡金属',
  'post-transition-metal': '后过渡金属',
  metalloid: '类金属',
  'reactive-nonmetal': '活泼非金属',
  halogen: '卤素',
  'noble-gas': '稀有气体',
  lanthanide: '镧系元素',
  actinide: '锕系元素',
}

const MODES: readonly { id: DisplayMode; label: string }[] = [
  { id: 'category', label: '元素类别' },
  { id: 'electronegativity', label: '电负性' },
  { id: 'firstIonizationEnergy', label: '第一电离能' },
]

function propertyFor(element: PeriodicTableElement, mode: DisplayMode) {
  if (mode === 'electronegativity') {
    return element.properties.electronegativity
  }
  if (mode === 'firstIonizationEnergy') {
    return element.properties.firstIonizationEnergy
  }
  return null
}

function formatValue(value: number | null): string {
  return value === null ? '暂无数据' : String(value)
}

export function PeriodicTableView({
  elements,
  onElementSelect,
}: PeriodicTableViewProps) {
  const [mode, setMode] = useState<DisplayMode>('category')
  const [selectedId, setSelectedId] = useState<string | null>(
    elements[0]?.id ?? null,
  )
  const [hoveredId, setHoveredId] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [searchMessage, setSearchMessage] = useState('')
  const buttonRefs = useRef(new Map<string, HTMLButtonElement>())

  const selectedElement =
    elements.find((element) => element.id === selectedId) ?? elements[0]
  const previewElement =
    elements.find((element) => element.id === hoveredId) ?? selectedElement

  const heatExtent = useMemo(() => {
    if (mode === 'category') return null
    const values = elements.flatMap((element) => {
      const value = propertyFor(element, mode)?.value
      return value === null || value === undefined ? [] : [value]
    })
    if (values.length === 0) return null
    return { min: Math.min(...values), max: Math.max(...values) }
  }, [elements, mode])

  function selectElement(element: PeriodicTableElement) {
    setSelectedId(element.id)
    setSearchMessage('')
    onElementSelect?.(element.id)
  }

  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const normalized = query.trim().toLocaleLowerCase()
    const match = elements.find(
      (element) =>
        String(element.atomicNumber) === normalized ||
        element.symbol.toLocaleLowerCase() === normalized ||
        element.nameZh.includes(query.trim()) ||
        element.nameEn.toLocaleLowerCase() === normalized,
    )
    if (!match) {
      setSearchMessage('未找到匹配元素')
      return
    }
    selectElement(match)
    buttonRefs.current.get(match.id)?.focus()
  }

  return (
    <div className="periodic-table-page">
      <header className="periodic-hero">
        <div>
          <p className="eyebrow">M03 · Explore</p>
          <h1>高中化学交互式 Wiki</h1>
          <p className="hero-copy">
            从元素位置出发，观察性质的周期性。当前展示 PostgreSQL 中的 canonical 数据。
          </p>
        </div>
        <div className="hero-stat" aria-label={`${elements.length} 个元素`}>
          <strong>{elements.length}</strong>
          <span>个正式元素</span>
        </div>
      </header>

      <section className="periodic-workspace" aria-label="元素周期表探索器">
        <div className="periodic-main">
          <div className="periodic-toolbar">
            <form className="element-search" role="search" onSubmit={handleSearch}>
              <label htmlFor="element-search">搜索元素</label>
              <div className="search-field">
                <input
                  id="element-search"
                  type="search"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="中文名 / 符号 / 原子序数"
                />
                <button type="submit">定位</button>
              </div>
              <span className="search-message" role="status">
                {searchMessage}
              </span>
            </form>

            <div className="mode-switcher" aria-label="显示属性">
              <span>着色方式</span>
              <div className="mode-buttons">
                {MODES.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className={mode === item.id ? 'is-active' : undefined}
                    aria-pressed={mode === item.id}
                    onClick={() => setMode(item.id)}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="table-scroll" tabIndex={0} aria-label="可横向滚动的周期表">
            <div className="periodic-grid">
              {elements.map((element) => {
                const property = propertyFor(element, mode)
                const value = property?.value ?? null
                const range = heatExtent
                const heat =
                  value === null || range === null
                    ? null
                    : (value - range.min) / (range.max - range.min || 1)
                const style = {
                  gridColumn: element.layout.column,
                  gridRow: element.layout.row,
                  '--heat': heat ?? 0,
                } as CSSProperties
                return (
                  <button
                    key={element.id}
                    ref={(node) => {
                      if (node) buttonRefs.current.set(element.id, node)
                      else buttonRefs.current.delete(element.id)
                    }}
                    type="button"
                    className={`element-cell category-${element.category}${
                      mode === 'category' ? '' : ' heatmap-cell'
                    }${value === null && mode !== 'category' ? ' is-missing' : ''}`}
                    style={style}
                    aria-label={`${element.atomicNumber} ${element.nameZh} ${element.symbol}`}
                    aria-pressed={element.id === selectedId}
                    data-element-id={element.id}
                    onClick={() => selectElement(element)}
                    onMouseEnter={() => setHoveredId(element.id)}
                    onMouseLeave={() => setHoveredId(null)}
                    onFocus={() => setHoveredId(element.id)}
                    onBlur={() => setHoveredId(null)}
                  >
                    <span className="atomic-number">{element.atomicNumber}</span>
                    <strong className="element-symbol">{element.symbol}</strong>
                    <span className="element-name">{element.nameZh}</span>
                    {mode === 'category' ? null : (
                      <span className="cell-value">{formatValue(value)}</span>
                    )}
                  </button>
                )
              })}
            </div>
          </div>

          <div className="periodic-legend" role="group" aria-label="图例">
            {mode === 'category' ? (
              <div className="category-legend">
                {Object.entries(CATEGORY_LABELS).map(([category, label]) => (
                  <span key={category}>
                    <i className={`legend-dot category-${category}`} />
                    {label}
                  </span>
                ))}
              </div>
            ) : (
              <div className="heat-legend">
                <span>暂无数据：斜线</span>
                <div className="heat-scale" aria-hidden="true" />
                <span>低</span>
                <span>高</span>
                <strong>
                  单位：{mode === 'electronegativity' ? 'Pauling' : 'eV'}
                </strong>
              </div>
            )}
          </div>
        </div>

        {previewElement ? (
          <aside className="element-inspector" aria-live="polite">
            <div className="inspector-heading">
              <span className={`inspector-mark category-${previewElement.category}`} />
              <div>
                <p>{previewElement.nameEn}</p>
                <h2>{`${previewElement.nameZh} ${previewElement.symbol}`}</h2>
              </div>
              <span className="status-badge">
                {previewElement.status === 'confirmed' ? '正式元素' : '预测元素'}
              </span>
            </div>
            <dl className="element-facts">
              <div>
                <dt>原子序数</dt>
                <dd>{previewElement.atomicNumber}</dd>
              </div>
              <div>
                <dt>周期 / 族</dt>
                <dd>
                  {previewElement.layout.period} / {previewElement.layout.group ?? '镧锕系'}
                </dd>
              </div>
              <div>
                <dt>元素类别</dt>
                <dd>{CATEGORY_LABELS[previewElement.category]}</dd>
              </div>
              <div>
                <dt>电子区块</dt>
                <dd>{previewElement.layout.block.toUpperCase()} 区</dd>
              </div>
            </dl>
            <div className="property-cards">
              <article>
                <span>电负性</span>
                <strong>
                  {formatValue(previewElement.properties.electronegativity.value)}
                </strong>
                <small>{previewElement.properties.electronegativity.unit ?? '—'}</small>
              </article>
              <article>
                <span>第一电离能</span>
                <strong>
                  {formatValue(
                    previewElement.properties.firstIonizationEnergy.value,
                  )}
                </strong>
                <small>
                  {previewElement.properties.firstIonizationEnergy.unit ?? '—'}
                </small>
              </article>
            </div>
            <p className="wiki-extension">
              选择元素后可通过稳定元素 ID 打开 Element Wiki。
            </p>
          </aside>
        ) : null}
      </section>
    </div>
  )
}

export default function PeriodicTable({ onElementSelect }: PeriodicTableProps) {
  const [elements, setElements] = useState<PeriodicTableElement[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    loadPeriodicTableElements()
      .then((data) => {
        if (active) setElements(data)
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(reason instanceof Error ? reason.message : '周期表数据加载失败')
        }
      })
    return () => {
      active = false
    }
  }, [])

  if (error) {
    return (
      <main className="periodic-state">
        <h1>高中化学交互式 Wiki</h1>
        <p role="alert">{error}</p>
      </main>
    )
  }
  if (!elements) {
    return (
      <main className="periodic-state">
        <h1>高中化学交互式 Wiki</h1>
        <p>正在读取 canonical 元素数据…</p>
      </main>
    )
  }
  return (
    <main>
      <PeriodicTableView elements={elements} onElementSelect={onElementSelect} />
    </main>
  )
}

import {
  Suspense,
  Component,
  lazy,
  useMemo,
  useEffect,
  useState,
  type ComponentType,
  type FormEvent,
  type ReactNode,
} from 'react'

import { analyzeStructure, loadStructureExploration } from './api'
import type {
  AnalyzeStructureResponse,
  CatalogStructureExploration,
  MoleculeViewer3DProps,
  StructuralTeachingFact,
  StructureEditorProps,
  StructureInputFormat,
} from './types'
import './structure-lab.css'


const LazyKetcherEditor = lazy(() => import('./adapters/KetcherEditor'))
const LazyMoleculeViewer3D = lazy(() => import('./adapters/MoleculeViewer3D'))

interface StructureLabProps {
  onBack: () => void
  onNavigate?: (path: string) => void
  speciesId?: string | null
}

interface StructureLabViewProps extends StructureLabProps {
  onAnalyze: (
    format: StructureInputFormat,
    text: string,
  ) => Promise<AnalyzeStructureResponse>
  EditorComponent?: ComponentType<StructureEditorProps>
  Viewer3DComponent?: ComponentType<MoleculeViewer3DProps>
  initialSmiles?: string | null
  catalogExploration?: CatalogStructureExploration | null
}

interface AdapterErrorBoundaryProps {
  children: ReactNode
  message: string
}

class AdapterErrorBoundary extends Component<
  AdapterErrorBoundaryProps,
  { failed: boolean }
> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  render() {
    if (this.state.failed) {
      return <div className="structure-viewer-error" role="status">{this.props.message}</div>
    }
    return this.props.children
  }
}

const EXAMPLES: Array<{ label: string; text: string }> = [
  { label: '乙醇', text: 'CCO' },
  { label: '甘氨酸', text: 'NCC(=O)O' },
  { label: '乙酸乙酯', text: 'CCOC(=O)C' },
]

function formulaWithSubscripts(formula: string): string {
  const subscripts: Record<string, string> = {
    '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
    '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
  }
  return formula.replace(/\d/g, (digit) => subscripts[digit])
}

const GROUP_LEARNING_MEANING: Record<string, string> = {
  alkene: '碳碳双键是烯烃的特征结构。',
  alkyne: '碳碳三键是炔烃的特征结构。',
}

const STRUCTURAL_TEACHING_COPY: Record<string, { heading: string; description: string }> = {
  carbon_carbon_double_bond: {
    heading: 'C=C',
    description: '碳碳双键是烯烃的特征结构。',
  },
  carbon_carbon_triple_bond: {
    heading: 'C≡C',
    description: '碳碳三键是炔烃的特征结构。',
  },
  tetrahedral_carbon: {
    heading: '四面体结构',
    description: '中心碳原子周围的四个成键方向构成四面体。',
  },
}

function structuralTeachingLabel(fact: StructuralTeachingFact): string | null {
  const labels: Record<string, string> = {
    sp3_hybridization: 'sp³ 杂化',
    sp2_hybridization: 'sp² 杂化',
    sp_hybridization: 'sp 杂化',
    trigonal_planar_geometry: '局部为平面三角形',
    linear_geometry: '局部为直线形',
    approximately_planar_skeleton: '分子骨架近似平面',
  }
  if (fact.key === 'ideal_bond_angle' && fact.value !== null) {
    return `理想键角约 ${fact.value}°`
  }
  return labels[fact.key] ?? null
}

export function StructureLabView({
  onBack,
  onNavigate,
  onAnalyze,
  EditorComponent = LazyKetcherEditor,
  Viewer3DComponent = LazyMoleculeViewer3D,
  initialSmiles = null,
  catalogExploration = null,
}: StructureLabViewProps) {
  const [text, setText] = useState(initialSmiles ?? EXAMPLES[0].text)
  const [label, setLabel] = useState(catalogExploration?.species.nameZh ?? (initialSmiles ? '目录物质' : EXAMPLES[0].label))
  const [result, setResult] = useState<AnalyzeStructureResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [editorError, setEditorError] = useState<string | null>(null)
  const [loading, setLoading] = useState(Boolean(initialSmiles))
  const [highlightedAtoms, setHighlightedAtoms] = useState<number[]>([])

  useEffect(() => {
    if (!initialSmiles) return
    void onAnalyze('smiles', initialSmiles).then(setResult).catch((reason: unknown) => {
      setError(reason instanceof Error ? reason.message : '结构分析失败')
    }).finally(() => setLoading(false))
  }, [initialSmiles, onAnalyze])

  const highlightedCoordinates = useMemo(() => {
    if (!result?.depiction) return []
    const selected = new Set(highlightedAtoms)
    return result.depiction.atomCoordinates.filter((atom) => selected.has(atom.atomIndex))
  }, [highlightedAtoms, result])

  if (catalogExploration && !catalogExploration.structure) {
    return (
      <main className="structure-lab-page">
        <nav className="structure-breadcrumb" aria-label="面包屑导航">
          <button type="button" onClick={onBack}>元素周期表</button><span aria-hidden="true">/</span><span>结构实验室</span>
        </nav>
        <section className="structure-unavailable" aria-labelledby="unavailable-title">
          <span>目录物质</span>
          <h1 id="unavailable-title">{catalogExploration.species.nameZh}</h1>
          <p>{formulaWithSubscripts(catalogExploration.species.formula)}</p>
          <strong>暂无可用的已确认结构</strong>
          <small>可在结构实验室中继续分析你自己的 SMILES 或 molblock。</small>
          {onNavigate ? <button type="button" onClick={() => onNavigate('/structure-lab')}>打开自由结构分析</button> : null}
        </section>
      </main>
    )
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setLoading(true)
    setError(null)
    setResult(null)
    setHighlightedAtoms([])
    try {
      setResult(await onAnalyze('smiles', text.trim()))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '结构分析失败')
    } finally {
      setLoading(false)
    }
  }

  const chooseExample = (example: (typeof EXAMPLES)[number]) => {
    setText(example.text)
    setLabel(example.label)
    setResult(null)
    setError(null)
    setEditorError(null)
    setHighlightedAtoms([])
  }

  return (
    <main className="structure-lab-page">
      <nav className="structure-breadcrumb" aria-label="面包屑导航">
        <button type="button" onClick={onBack}>元素周期表</button>
        <span aria-hidden="true">/</span>
        <span>结构实验室</span>
      </nav>

      <header className="structure-hero">
        <div>
          <h1>结构实验室</h1>
          <p>从分子结构出发，验证化学表示、观察二维与三维构型，并定位官能团。</p>
        </div>
        <div className="structure-hero-mark" aria-hidden="true">
          <span>2D</span><i>↔</i><span>3D</span>
        </div>
      </header>

      {catalogExploration ? (
        <section className="structure-catalog-context" aria-labelledby="catalog-species-heading">
          <div className="structure-catalog-title">
            <span>目录物质</span>
            <h2 id="catalog-species-heading">{catalogExploration.species.nameZh}</h2>
            {catalogExploration.species.nameEn ? <small>{catalogExploration.species.nameEn}</small> : null}
            <strong>{formulaWithSubscripts(catalogExploration.species.formula)}</strong>
          </div>
          <div className="structure-catalog-learning">
            <span>结构要点</span>
            {result?.structuralTeaching?.primary ? (() => {
              const copy = STRUCTURAL_TEACHING_COPY[result.structuralTeaching.primary.key]
              if (!copy) return <p>可从下方二维与三维视图继续观察此结构。</p>
              const observations = result.structuralTeaching.observations
                .map(structuralTeachingLabel)
                .filter((item): item is string => item !== null)
              return <>
                <h3>{copy.heading}</h3>
                <p>{copy.description}</p>
                {observations.length ? (
                  <details>
                    <summary>查看结构观察</summary>
                    <ul>{observations.map((observation) => <li key={observation}>{observation}</li>)}</ul>
                  </details>
                ) : null}
              </>
            })() : (
              <p>{result?.state === 'valid' ? '可从下方二维与三维视图继续观察此结构。' : '正在从已确认结构整理要点…'}</p>
            )}
          </div>
        </section>
      ) : null}

      <div className="structure-workspace">
        <section className="structure-panel structure-editor-panel" aria-labelledby="editor-heading">
          <div className="structure-panel-heading">
            <div><h2 id="editor-heading">绘制分子</h2></div>
            <span>绘制或编辑结构</span>
          </div>
          <div className="structure-examples" aria-label="结构示例">
            {EXAMPLES.map((example) => (
              <button key={example.label} type="button" onClick={() => chooseExample(example)}>
                {example.label}
              </button>
            ))}
          </div>
          <AdapterErrorBoundary message="结构编辑器加载失败，可继续使用 SMILES 输入">
            <Suspense fallback={<div className="structure-adapter-loading">正在载入结构编辑器…</div>}>
              <EditorComponent value={text} onChange={(value) => { setText(value); setLabel('当前结构') }} onError={setEditorError} />
            </Suspense>
          </AdapterErrorBoundary>
          {editorError ? <p className="structure-inline-error" role="status">{editorError}</p> : null}
          <form className="structure-smiles-form" onSubmit={handleSubmit}>
            <label htmlFor="structure-smiles">SMILES</label>
            <div>
              <input
                id="structure-smiles"
                value={text}
                onChange={(event) => { setText(event.target.value); setLabel('当前结构') }}
                spellCheck={false}
              />
              <button type="submit" disabled={loading || !text.trim()}>
                {loading ? '正在分析…' : '分析结构'}
              </button>
            </div>
          </form>
          <p className="structure-input-note">接受 SMILES；绘图内容会同步到输入框。</p>
        </section>

        <section className="structure-panel structure-visual-panel" aria-labelledby="visual-heading">
          <div className="structure-panel-heading">
            <div><h2 id="visual-heading">分子视图</h2></div>
            <span>二维 / 三维</span>
          </div>
          {!result && !error && !loading ? (
            <div className="structure-empty"><span>⌬</span><p>分析后生成 2D 描图与可旋转 3D 构象。</p></div>
          ) : null}
          {loading ? <div className="structure-empty" role="status"><span>···</span><p>RDKit 正在验证并生成构象…</p></div> : null}
          {error ? <div className="structure-error" role="alert"><strong>服务暂不可用</strong><p>{error}</p></div> : null}
          {result && result.state !== 'valid' ? (
            <div className={`structure-error state-${result.state}`} role="alert">
              <strong>{result.state === 'unsupported' ? '暂不支持该表示' : '结构无效'}</strong>
              <p>{result.message}</p>
            </div>
          ) : null}
          {result?.state === 'valid' && result.depiction ? (
            <>
              <div className="structure-depiction">
                <img
                  src={`data:image/svg+xml;charset=utf-8,${encodeURIComponent(result.depiction.svg)}`}
                  alt={`${label}的二维结构`}
                />
                <svg
                  className="structure-highlight-layer"
                  viewBox={`0 0 ${result.depiction.width} ${result.depiction.height}`}
                  aria-hidden="true"
                >
                  {highlightedCoordinates.map((atom) => (
                    <circle
                      key={atom.atomIndex}
                      data-highlighted-atom={atom.atomIndex}
                      cx={atom.x}
                      cy={atom.y}
                      r="22"
                    />
                  ))}
                </svg>
              </div>
              <div className="structure-3d-frame">
                {result.conformer?.state === 'available' && result.conformer.molBlock ? (
                  <AdapterErrorBoundary message="3D 查看器加载失败，二维结构仍可使用">
                    <Suspense fallback={<div className="structure-adapter-loading">正在载入 3Dmol.js…</div>}>
                      <Viewer3DComponent molBlock={result.conformer.molBlock} />
                    </Suspense>
                  </AdapterErrorBoundary>
                ) : <p role="status">{result.conformer?.reason ?? '当前结构没有可用三维构象'}</p>}
              </div>
            </>
          ) : null}
        </section>

        <section className="structure-panel structure-analysis-panel" aria-labelledby="analysis-heading">
          <div className="structure-panel-heading">
            <div><h2 id="analysis-heading">结构分析</h2></div>
          </div>
          {result?.state === 'valid' && result.descriptors && result.formula ? (
            <>
              <div className="structure-formula">
                <span>分子式</span><strong>{formulaWithSubscripts(result.formula)}</strong>
                <code>{result.canonicalSmiles}</code>
              </div>
              <dl className="structure-descriptors">
                <div><dt>相对分子质量</dt><dd>{result.descriptors.molecularWeight} g/mol</dd></div>
                <div><dt>重原子数</dt><dd>{result.descriptors.heavyAtomCount}</dd></div>
                <div><dt>氢键供体 / 受体</dt><dd>{result.descriptors.hydrogenBondDonors} / {result.descriptors.hydrogenBondAcceptors}</dd></div>
                <div><dt>可旋转键</dt><dd>{result.descriptors.rotatableBondCount}</dd></div>
              </dl>
              <div className="functional-groups">
                <div className="functional-heading"><h3>检测到的官能团</h3><span>{result.functionalGroups.length}</span></div>
                {result.functionalGroups.length ? result.functionalGroups.map((group) => {
                  const atoms = group.occurrences.flatMap((occurrence) => occurrence.atomIndices)
                  return (
                    <button
                      key={group.functionalGroupId}
                      type="button"
                      onMouseEnter={() => setHighlightedAtoms(atoms)}
                      onMouseLeave={() => setHighlightedAtoms([])}
                      onFocus={() => setHighlightedAtoms(atoms)}
                      onBlur={() => setHighlightedAtoms([])}
                      aria-label={`${group.nameZh}，${group.occurrences.length} 处`}
                    >
                  <span><strong>{group.nameZh}</strong><small>{group.nameEn}</small></span>
                  <em>{group.occurrences.length} 处</em>
                  {!catalogExploration && GROUP_LEARNING_MEANING[group.key] ? <p>{GROUP_LEARNING_MEANING[group.key]}</p> : null}
                </button>
                  )
                }) : <p className="structure-no-groups">当前结构未检测到典型有机官能团。</p>}
              </div>
              <aside className="structure-boundary">
                <strong>结构分析范围</strong>
                <p>这里展示分子结构、基础描述符与官能团，不从结构猜测反应或机理。</p>
              </aside>
            </>
          ) : (
            <div className="structure-empty compact"><p>有效结构的分子式、基础描述符和官能团会显示在这里。</p></div>
          )}
        </section>
      </div>

      {catalogExploration ? (
        <section className="structure-catalog-exploration" aria-labelledby="catalog-exploration-heading">
          <div className="structure-catalog-exploration-heading">
            <span>延伸探索</span>
            <h2 id="catalog-exploration-heading">从结构继续学习</h2>
          </div>
          {catalogExploration.knowledge.length ? (
            <details className="structure-catalog-knowledge">
              <summary>相关知识（{catalogExploration.knowledge.length}）</summary>
              <ul>{catalogExploration.knowledge.map((item) => (
                <li key={item.consolidatedId}>
                  <strong>{item.displayNameZh}</strong>
                  {item.contentZh ? <span>{item.contentZh}</span> : null}
                </li>
              ))}</ul>
            </details>
          ) : null}
          <div className="structure-catalog-links">
            {catalogExploration.relatedSpecies.length ? (
              <div><span>相关物质</span>{catalogExploration.relatedSpecies.map((species) => <button key={species.applicationId} type="button" onClick={() => onNavigate?.(`/structure-lab?species=${encodeURIComponent(species.applicationId)}`)} disabled={!species.structureAvailable}>{species.nameZh}</button>)}</div>
            ) : null}
            <div>
              <span>相关反应</span>
              {catalogExploration.relatedReactions.length ? catalogExploration.relatedReactions.map((reaction) => <button key={reaction.consolidatedId} type="button" aria-label={`在方程实验室中查看${reaction.nameZh}`} onClick={() => onNavigate?.(`/equation-lab?reaction=${encodeURIComponent(reaction.consolidatedId)}`)}>{reaction.nameZh}</button>) : <small>当前目录中暂无可继续查看的真实反应。</small>}
            </div>
          </div>
        </section>
      ) : null}
    </main>
  )
}

export default function StructureLab({ onBack, onNavigate, speciesId }: StructureLabProps) {
  const [catalogExploration, setCatalogExploration] = useState<CatalogStructureExploration | null | undefined>(speciesId ? undefined : null)
  const [entryError, setEntryError] = useState<string | null>(null)

  useEffect(() => {
    if (!speciesId) return
    let active = true
    void loadStructureExploration(speciesId).then((entry) => {
      if (active) setCatalogExploration(entry)
    }).catch((reason: unknown) => {
      if (active) setEntryError(reason instanceof Error ? reason.message : '已知结构加载失败')
    })
    return () => { active = false }
  }, [speciesId])

  if (speciesId && catalogExploration === undefined && !entryError) return <main className="structure-lab-page structure-entry-state" role="status">正在载入目录物质…</main>
  if (speciesId && entryError) return <main className="structure-lab-page structure-entry-state" role="alert">{entryError}</main>
  const knownSmiles = catalogExploration?.structure?.isomericSmiles ?? catalogExploration?.structure?.canonicalSmiles ?? null
  return <StructureLabView key={speciesId ?? 'manual'} onBack={onBack} onNavigate={onNavigate} onAnalyze={analyzeStructure} initialSmiles={knownSmiles} catalogExploration={catalogExploration} />
}

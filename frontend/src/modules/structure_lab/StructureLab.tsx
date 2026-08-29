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

import { analyzeStructure, loadCatalogStructure } from './api'
import type {
  AnalyzeStructureResponse,
  MoleculeViewer3DProps,
  StructureEditorProps,
  StructureInputFormat,
} from './types'
import './structure-lab.css'


const LazyKetcherEditor = lazy(() => import('./adapters/KetcherEditor'))
const LazyMoleculeViewer3D = lazy(() => import('./adapters/MoleculeViewer3D'))

interface StructureLabProps {
  onBack: () => void
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

export function StructureLabView({
  onBack,
  onAnalyze,
  EditorComponent = LazyKetcherEditor,
  Viewer3DComponent = LazyMoleculeViewer3D,
  initialSmiles = null,
}: StructureLabViewProps) {
  const [text, setText] = useState(initialSmiles ?? EXAMPLES[0].text)
  const [label, setLabel] = useState(initialSmiles ? '目录物质' : EXAMPLES[0].label)
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
                    </button>
                  )
                }) : <p className="structure-no-groups">当前课程目录未匹配到官能团。</p>}
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
    </main>
  )
}

export default function StructureLab({ onBack, speciesId }: StructureLabProps) {
  const [knownSmiles, setKnownSmiles] = useState<string | null>(null)
  const [entryError, setEntryError] = useState<string | null>(null)

  useEffect(() => {
    if (!speciesId) return
    let active = true
    void loadCatalogStructure(speciesId).then((entry) => {
      if (active) setKnownSmiles(entry.isomericSmiles ?? entry.canonicalSmiles)
    }).catch((reason: unknown) => {
      if (active) setEntryError(reason instanceof Error ? reason.message : '已知结构加载失败')
    })
    return () => { active = false }
  }, [speciesId])

  return (
    <>
      {entryError ? <div className="structure-entry-error" role="alert">{entryError}</div> : null}
      <StructureLabView
        key={knownSmiles ?? 'manual'}
        onBack={onBack}
        onAnalyze={analyzeStructure}
        initialSmiles={knownSmiles}
      />
    </>
  )
}

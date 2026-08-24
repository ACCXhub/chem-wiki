import { useEffect, useState } from 'react'

import { loadElementWiki } from './api'
import type {
  ElementWikiPage,
  ElementWikiProperty,
  KnowledgeNode,
} from './types'
import './element-wiki.css'


interface ElementWikiProps {
  elementId: string
  onBack: () => void
}

interface ElementWikiViewProps {
  page: ElementWikiPage
  onBack: () => void
}

const CATEGORY_LABELS = {
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
} as const

const PROPERTY_LABELS: Record<string, string> = {
  atomic_number: '原子序数',
  symbol: '元素符号',
  name_zh: '中文名',
  name_en: '英文名',
  atomicWeight: '相对原子质量',
  electronegativity: '电负性',
  firstIonizationEnergy: '第一电离能',
  atomicRadius: '原子半径',
}

const SECTION_DEFINITIONS = [
  { key: 'ions', title: '常见离子', hint: '与该元素相关的已审核离子' },
  { key: 'substances', title: '相关物质', hint: '包含该元素的已审核物质' },
  { key: 'reactions', title: '相关反应', hint: 'Reaction 保持为独立节点' },
  { key: 'phenomena', title: '实验现象', hint: '与反应或实验关联的现象' },
  { key: 'concepts', title: '相关概念', hint: '课程知识点与前置概念' },
  { key: 'questions', title: '关联题目', hint: '具有明确来源的题目关联' },
] as const

function formatProperty(property: ElementWikiProperty): string {
  if (property.status === 'missing') return '暂无数据'
  if (property.lower !== null && property.upper !== null) {
    return `${property.lower}–${property.upper}`
  }
  return property.value === null ? '暂无数据' : String(property.value)
}

function NodeList({ nodes }: { nodes: KnowledgeNode[] }) {
  if (nodes.length === 0) return <p className="wiki-empty">暂无已审核数据</p>
  return (
    <ul className="wiki-node-list">
      {nodes.map((node) => (
        <li key={`${node.type}:${node.id}`}>
          <span>{node.type}</span>
          <strong>{node.label}</strong>
          {node.secondaryLabel ? <small>{node.secondaryLabel}</small> : null}
        </li>
      ))}
    </ul>
  )
}

export function ElementWikiView({ page, onBack }: ElementWikiViewProps) {
  const { identity, classification } = page
  const centerNode = page.graph.nodes.find(
    (node) => node.id === page.graph.centerNodeId,
  )
  const relatedNodes = page.graph.nodes.filter(
    (node) => node.id !== page.graph.centerNodeId,
  )

  return (
    <main className="element-wiki-page">
      <nav className="wiki-breadcrumb" aria-label="面包屑导航">
        <button type="button" onClick={onBack}>元素周期表</button>
        <span aria-hidden="true">/</span>
        <span>{identity.nameZh}</span>
      </nav>

      <header className={`wiki-hero category-${classification.category}`}>
        <div className="wiki-symbol" aria-hidden="true">
          <span>{identity.atomicNumber}</span>
          <strong>{identity.symbol}</strong>
        </div>
        <div className="wiki-title">
          <p className="eyebrow">M04 · Element Wiki</p>
          <h1>{identity.nameZh}</h1>
          <p>{identity.nameEn}</p>
        </div>
        <dl className="wiki-classification">
          <div><dt>类别</dt><dd>{CATEGORY_LABELS[classification.category]}</dd></div>
          <div><dt>周期</dt><dd>{classification.period}</dd></div>
          <div><dt>族</dt><dd>{classification.group ?? '镧锕系'}</dd></div>
          <div><dt>区块</dt><dd>{classification.block.toUpperCase()} 区</dd></div>
        </dl>
      </header>

      <div className="wiki-layout">
        <div className="wiki-primary">
          <section className="wiki-panel" aria-labelledby="property-heading">
            <div className="wiki-section-heading">
              <div>
                <p className="eyebrow">Canonical properties</p>
                <h2 id="property-heading">已校准属性</h2>
              </div>
              <p>仅展示已发布值；缺失值不推测。</p>
            </div>
            <div className="wiki-properties">
              {page.properties.map((property) => (
                <article key={property.key} className={property.status === 'missing' ? 'is-missing' : undefined}>
                  <span>{property.label}</span>
                  <strong>{formatProperty(property)}</strong>
                  <small>
                    {property.status === 'missing'
                      ? '未发现 canonical 发布值'
                      : [property.unit, property.qualifier].filter(Boolean).join(' · ') || '无量纲'}
                  </small>
                </article>
              ))}
            </div>
          </section>

          <section className="wiki-panel" aria-labelledby="sections-heading">
            <div className="wiki-section-heading">
              <div>
                <p className="eyebrow">Structured sections</p>
                <h2 id="sections-heading">元素知识导航</h2>
              </div>
              <p>关联内容只接受审核后的 typed node。</p>
            </div>
            <div className="wiki-sections">
              {SECTION_DEFINITIONS.map((section) => (
                <article key={section.key}>
                  <header>
                    <h3>{section.title}</h3>
                    <p>{section.hint}</p>
                  </header>
                  <NodeList nodes={page.sections[section.key]} />
                </article>
              ))}
            </div>
          </section>
        </div>

        <aside className="wiki-secondary">
          <section className="wiki-panel knowledge-map" aria-labelledby="graph-heading">
            <div className="wiki-section-heading">
              <div>
                <p className="eyebrow">Local knowledge graph</p>
                <h2 id="graph-heading">基础知识图</h2>
              </div>
            </div>
            <div className="graph-canvas" aria-label="元素局部知识图">
              {centerNode ? (
                <div className="graph-center">
                  <span>{centerNode.type}</span>
                  <strong>{centerNode.label}</strong>
                  <small>{centerNode.secondaryLabel}</small>
                </div>
              ) : null}
              {relatedNodes.length > 0 ? <NodeList nodes={relatedNodes} /> : null}
            </div>
            {page.graph.edges.length === 0 && page.graph.emptyReason ? (
              <p className="graph-empty">{page.graph.emptyReason}</p>
            ) : (
              <ul className="graph-edges">
                {page.graph.edges.map((edge) => (
                  <li key={edge.id}><span>{edge.type}</span>{edge.label}</li>
                ))}
              </ul>
            )}
          </section>

          <section className="wiki-panel wiki-sources" aria-labelledby="sources-heading">
            <div className="wiki-section-heading">
              <div>
                <p className="eyebrow">Provenance</p>
                <h2 id="sources-heading">数据来源</h2>
              </div>
            </div>
            {page.sources.length === 0 ? (
              <p className="wiki-empty">暂无可展示来源</p>
            ) : (
              <ul>
                {page.sources.map((source) => (
                  <li key={source.key}>
                    {source.url ? (
                      <a href={source.url} target="_blank" rel="noreferrer">{source.title}</a>
                    ) : <strong>{source.title}</strong>}
                    <span>{source.publisher ?? '发布机构未注明'}</span>
                    <small>
                      字段：{source.fields.map((field) => PROPERTY_LABELS[field] ?? field).join('、')}
                    </small>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </aside>
      </div>
    </main>
  )
}

export default function ElementWiki({ elementId, onBack }: ElementWikiProps) {
  const [page, setPage] = useState<ElementWikiPage | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    loadElementWiki(elementId)
      .then((result) => {
        if (active) setPage(result)
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(reason instanceof Error ? reason.message : '元素详情加载失败')
        }
      })
    return () => {
      active = false
    }
  }, [elementId])

  if (error) {
    return (
      <main className="wiki-state">
        <p className="eyebrow">M04 · Element Wiki</p>
        <h1>无法打开元素详情</h1>
        <p role="alert">{error}</p>
        <button type="button" onClick={onBack}>返回元素周期表</button>
      </main>
    )
  }
  if (!page) {
    return (
      <main className="wiki-state">
        <p className="eyebrow">M04 · Element Wiki</p>
        <h1>正在读取元素详情…</h1>
      </main>
    )
  }
  return <ElementWikiView page={page} onBack={onBack} />
}

import { useEffect, useMemo, useRef, useState } from 'react'
import type { Core } from 'cytoscape'

import type { ElementWikiPage, KnowledgeNode } from './types'

interface ElementKnowledgeGraphProps {
  graph: ElementWikiPage['graph']
  onNavigate?: (href: string) => void
}

const NODE_COLORS: Record<KnowledgeNode['type'], string> = {
  Element: '#efc878',
  Ion: '#72b39d',
  Substance: '#74a9d6',
  Reaction: '#d88794',
  Concept: '#a889d2',
  Phenomenon: '#e5a65a',
  Question: '#8da49c',
}

const NODE_LABELS: Record<KnowledgeNode['type'], string> = {
  Element: '元素',
  Ion: '离子',
  Substance: '物质',
  Reaction: '反应',
  Concept: '概念',
  Phenomenon: '现象',
  Question: '题目',
}

export default function ElementKnowledgeGraph({
  graph,
  onNavigate,
}: ElementKnowledgeGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [selectedId, setSelectedId] = useState(graph.centerNodeId)
  const selected = useMemo(
    () => graph.nodes.find((node) => node.id === selectedId) ?? graph.nodes[0],
    [graph.nodes, selectedId],
  )

  useEffect(() => {
    let active = true
    let instance: Core | undefined
    if (!containerRef.current || !graph.nodes.length) return undefined
    void import('cytoscape').then(({ default: cytoscape }) => {
      if (!active || !containerRef.current) return
      const headless = navigator.userAgent.toLowerCase().includes('jsdom')
      instance = cytoscape({
        container: headless ? undefined : containerRef.current,
        headless,
        elements: [
          ...graph.nodes.map((node) => ({
            data: {
              id: node.id,
              label: node.label,
              type: node.type,
              color: NODE_COLORS[node.type],
            },
          })),
          ...graph.edges.map((edge) => ({
            data: {
              id: edge.id,
              source: edge.source,
              target: edge.target,
              label: edge.label,
            },
          })),
        ],
        style: [
          {
            selector: 'node',
            style: {
              'background-color': 'data(color)',
              'border-color': '#071310',
              'border-width': 2,
              color: '#ecf4f1',
              label: 'data(label)',
              'font-family': 'Inter, Noto Sans SC, Microsoft YaHei, sans-serif',
              'font-size': 11,
              'min-zoomed-font-size': 8,
              'text-background-color': '#071310',
              'text-background-opacity': 0.78,
              'text-background-padding': '3px',
              'text-margin-y': 14,
              'text-wrap': 'ellipsis',
              'text-max-width': '92px',
              height: '30px',
              width: '30px',
            },
          },
          {
            selector: `node[id = "${graph.centerNodeId}"]`,
            style: { height: '48px', width: '48px', 'border-color': '#f4d795', 'border-width': 3 },
          },
          {
            selector: 'node:selected',
            style: { 'border-color': '#ffffff', 'border-width': 4 },
          },
          {
            selector: 'edge',
            style: {
              width: 1.2,
              'line-color': '#45675c',
              'target-arrow-color': '#45675c',
              'target-arrow-shape': 'triangle',
              'curve-style': 'bezier',
              opacity: 0.76,
            },
          },
        ],
        layout: {
          name: 'concentric',
          concentric: (node) => {
            const type = node.data('type') as KnowledgeNode['type']
            if (type === 'Element') return 3
            if (type === 'Ion' || type === 'Substance') return 2
            return 1
          },
          levelWidth: () => 1,
          minNodeSpacing: 34,
          animate: !headless,
          animationDuration: 260,
          fit: true,
          padding: 30,
        },
        minZoom: 0.5,
        maxZoom: 2,
      })
      instance.on('select tap', 'node', (event) => setSelectedId(event.target.id()))
      instance.getElementById(graph.centerNodeId).select()
    })
    return () => {
      active = false
      instance?.destroy()
    }
  }, [graph])

  return (
    <>
      <div ref={containerRef} className="graph-canvas" aria-label="元素局部知识图" />
      {selected ? (
        <div className="graph-selection" aria-live="polite">
          <span>{NODE_LABELS[selected.type]}</span>
          <strong>{selected.label}</strong>
          {selected.secondaryLabel ? <p>{selected.secondaryLabel}</p> : null}
          {selected.href && selected.type !== 'Element' ? (
            <button type="button" onClick={() => onNavigate?.(selected.href!)}>
              {selected.type === 'Reaction' ? '在方程实验室中打开' : '在结构实验室中打开'}
            </button>
          ) : null}
        </div>
      ) : null}
    </>
  )
}

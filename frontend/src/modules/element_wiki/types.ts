import type { ElementCategory } from '../periodic_table'

export type ElementPropertyKey =
  | 'atomicWeight'
  | 'electronegativity'
  | 'firstIonizationEnergy'
  | 'atomicRadius'

export type KnowledgeNodeType =
  | 'Element'
  | 'Ion'
  | 'Substance'
  | 'Reaction'
  | 'Phenomenon'
  | 'Concept'
  | 'Question'

export type KnowledgeEdgeType =
  | 'CONTAINS_ELEMENT'
  | 'REACTANT_IN'
  | 'PRODUCT_OF'
  | 'HAS_PHENOMENON'
  | 'RELATES_TO'
  | 'TESTS'

export interface ElementWikiProperty {
  key: ElementPropertyKey
  label: string
  status: 'available' | 'missing'
  value: number | null
  lower: number | null
  upper: number | null
  unit: string | null
  qualifier: string | null
  uncertainty: number | null
  sourceKeys: string[]
}

export interface ElementWikiSource {
  key: string
  title: string
  publisher: string | null
  url: string | null
  licenseCode: string | null
  retrievedAt: string
  fields: string[]
}

export interface KnowledgeNode {
  id: string
  type: KnowledgeNodeType
  label: string
  secondaryLabel?: string | null
  href?: string | null
  description?: string | null
}

export interface KnowledgeEdge {
  id: string
  type: KnowledgeEdgeType
  source: string
  sourceType: KnowledgeNodeType
  target: string
  targetType: KnowledgeNodeType
  label: string
}

export interface ElementWikiPage {
  identity: {
    id: string
    atomicNumber: number
    symbol: string
    nameZh: string
    nameEn: string
    status: 'confirmed' | 'predicted'
  }
  classification: {
    category: ElementCategory
    period: number
    group: number | null
    block: 's' | 'p' | 'd' | 'f'
  }
  properties: ElementWikiProperty[]
  sections: {
    ions: KnowledgeNode[]
    substances: KnowledgeNode[]
    reactions: KnowledgeNode[]
    phenomena: KnowledgeNode[]
    concepts: KnowledgeNode[]
    questions: KnowledgeNode[]
  }
  graph: {
    centerNodeId: string
    nodes: KnowledgeNode[]
    edges: KnowledgeEdge[]
    emptyReason: string | null
  }
  sources: ElementWikiSource[]
}

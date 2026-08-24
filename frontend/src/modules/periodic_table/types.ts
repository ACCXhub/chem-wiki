export type ElementCategory =
  | 'alkali-metal'
  | 'alkaline-earth-metal'
  | 'transition-metal'
  | 'post-transition-metal'
  | 'metalloid'
  | 'reactive-nonmetal'
  | 'halogen'
  | 'noble-gas'
  | 'lanthanide'
  | 'actinide'

export interface ScalarProperty {
  value: number | null
  unit: string | null
}

export interface PeriodicTableElement {
  id: string
  atomicNumber: number
  symbol: string
  nameZh: string
  nameEn: string
  category: ElementCategory
  status: 'confirmed' | 'predicted'
  layout: {
    period: number
    group: number | null
    row: number
    column: number
    block: 's' | 'p' | 'd' | 'f'
  }
  properties: {
    electronegativity: ScalarProperty
    firstIonizationEnergy: ScalarProperty
  }
}

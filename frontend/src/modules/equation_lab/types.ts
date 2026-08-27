export type EquationMode = 'molecular' | 'ionic' | 'net_ionic'

export type EquationPhase = 'aq' | 's' | 'l' | 'g'

export type EquationSuitability = 'recommended' | 'available' | 'deemphasized'

export interface CatalogSpecies {
  consolidatedId: string
  applicationId: string
  entityKind: 'ion' | 'substance'
  nameZh: string
  nameEn: string | null
  formula: string
  charge: number
  aliases: string[]
  primaryCategory: string
  tags: string[]
  defaultPriority: string
  defaultPaletteRank: number
  equationModes: Record<EquationMode, EquationSuitability>
}

export interface EquationDraftParticipant extends CatalogSpecies {
  phase: EquationPhase | null
}

export interface EquationDraft {
  mode: EquationMode
  reactants: EquationDraftParticipant[]
  products: EquationDraftParticipant[]
}

export interface CatalogSpeciesQuery {
  query?: string
  primaryCategory?: string
  equationMode: EquationMode
  limit?: number
}

export interface EquationTerm {
  formula: string
  coefficient: number
  phase: string | null
  charge: number
}

export interface ConservationRow {
  element: string
  reactants: number
  products: number
  conserved: boolean
}

export interface BalanceEquationResponse {
  state: 'balanced' | 'no_net_ionic'
  inputState: 'balanced' | 'unbalanced' | 'not_applicable'
  mode: EquationMode
  formattedEquation: string
  coefficients: number[]
  reactants: EquationTerm[]
  products: EquationTerm[]
  conservation: {
    elements: ConservationRow[]
    charge: {
      reactants: number
      products: number
      conserved: boolean
    } | null
  }
  message: string | null
  phenomenon: string | null
  redox: {
    state: 'not_inferred'
    message: string
  }
}

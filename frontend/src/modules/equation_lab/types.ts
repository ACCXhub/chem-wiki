export type EquationMode = 'molecular' | 'ionic' | 'net_ionic'

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

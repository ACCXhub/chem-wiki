import type { ReactNode } from 'react'

import type { EquationPhase } from './types'


const SUBSCRIPT_DIGITS: Record<string, string> = {
  '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
  '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
}

function chemistryFormulaText(formula: string): string {
  return formula.replace(/\d/g, (digit) => SUBSCRIPT_DIGITS[digit])
}

function chargeText(charge: number): string {
  if (charge === 0) return ''
  const magnitude = Math.abs(charge)
  return `${magnitude === 1 ? '' : magnitude}${charge > 0 ? '+' : '-'}`
}

interface ChemistryNotationProps {
  formula: string
  charge?: number
  phase?: EquationPhase | null
  coefficient?: number
}

export default function ChemistryNotation({
  formula,
  charge = 0,
  phase = null,
  coefficient,
}: ChemistryNotationProps) {
  const parts: ReactNode[] = []
  if (coefficient && coefficient !== 1) parts.push(coefficient)
  parts.push(chemistryFormulaText(formula))
  if (charge) parts.push(<sup key="charge">{chargeText(charge)}</sup>)
  if (phase) parts.push(<span key="phase" className="chem-phase">({phase})</span>)
  return <span className="chem-notation">{parts}</span>
}

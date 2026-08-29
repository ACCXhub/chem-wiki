import katex from 'katex'
import 'katex/contrib/mhchem'
import 'katex/dist/katex.min.css'

import type { EquationPhase } from './types'


function chargeExpression(charge: number): string {
  if (!charge) return ''
  const magnitude = Math.abs(charge)
  return `^{${magnitude === 1 ? '' : magnitude}${charge > 0 ? '+' : '-'}}`
}

function renderChemistry(expression: string): string {
  return katex.renderToString(`\\ce{${expression}}`, {
    output: 'htmlAndMathml',
    throwOnError: false,
    strict: 'ignore',
    trust: false,
  })
}

interface ChemistryNotationProps {
  formula: string
  charge?: number
  phase?: EquationPhase | null
  coefficient?: number | string
}

export default function ChemistryNotation({
  formula,
  charge = 0,
  phase = null,
  coefficient,
}: ChemistryNotationProps) {
  const coefficientText = coefficient && String(coefficient) !== '1' ? `${coefficient} ` : ''
  const phaseText = phase ? `(${phase})` : ''
  const expression = `${coefficientText}${formula}${chargeExpression(charge)}${phaseText}`
  return (
    <span
      className="chem-notation"
      aria-label={expression}
      dangerouslySetInnerHTML={{ __html: renderChemistry(expression) }}
    />
  )
}

export function ChemistryEquation({ expression }: { expression: string }) {
  return (
    <span
      className="chem-equation"
      aria-label={expression}
      dangerouslySetInnerHTML={{ __html: renderChemistry(expression) }}
    />
  )
}

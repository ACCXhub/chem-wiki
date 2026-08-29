import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'

import ChemistryNotation, { ChemistryEquation } from './ChemistryNotation'


test('renders coefficients, subscripts, ionic charges and phases through mhchem', () => {
  const { container } = render(
    <ChemistryNotation formula="Fe2(SO4)3" charge={2} phase="aq" coefficient={3} />,
  )

  expect(screen.getByLabelText('3 Fe2(SO4)3^{2+}(aq)')).toBeInTheDocument()
  expect(container.querySelector('.katex')).toBeInTheDocument()
  expect(container.textContent).toContain('Fe')
  expect(container.textContent).toContain('SO')
})

test.each([
  ['2H2 + O2 -> 2H2O', '→'],
  ['N2 + 3H2 <=> 2NH3', '⇌'],
])('renders equation arrows with mhchem: %s', (expression, arrow) => {
  const { container } = render(<ChemistryEquation expression={expression} />)

  expect(container.querySelector('.katex')).toBeInTheDocument()
  expect(container.textContent).toContain(arrow)
})

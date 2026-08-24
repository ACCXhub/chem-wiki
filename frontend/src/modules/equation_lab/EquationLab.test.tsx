import { fireEvent, render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'

import { EquationLabView } from './EquationLab'
import type { BalanceEquationResponse } from './types'


const result: BalanceEquationResponse = {
  state: 'balanced',
  inputState: 'unbalanced',
  mode: 'molecular',
  formattedEquation: '2H₂ + O₂ → 2H₂O',
  coefficients: [2, 1, 2],
  reactants: [
    { formula: 'H2', coefficient: 2, phase: null, charge: 0 },
    { formula: 'O2', coefficient: 1, phase: null, charge: 0 },
  ],
  products: [{ formula: 'H2O', coefficient: 2, phase: null, charge: 0 }],
  conservation: {
    elements: [
      { element: 'H', reactants: 4, products: 4, conserved: true },
      { element: 'O', reactants: 2, products: 2, conserved: true },
    ],
    charge: null,
  },
  message: null,
  phenomenon: null,
  redox: {
    state: 'not_inferred',
    message: '氧化还原解释仅接受经审核元数据，不由配平方程式推断',
  },
}

test('submits equation and presents coefficients with conservation evidence', async () => {
  const onBalance = vi.fn(() => Promise.resolve(result))
  render(<EquationLabView onBack={() => undefined} onBalance={onBalance} />)

  fireEvent.click(screen.getByRole('button', { name: '配平并验证' }))

  expect(onBalance).toHaveBeenCalledWith('H2 + O2 -> H2O', 'molecular')
  expect(await screen.findByText('2H₂ + O₂ → 2H₂O')).toBeInTheDocument()
  expect(screen.getByText('输入未配平，已求得最简整数比')).toBeInTheDocument()
  expect(screen.getAllByRole('cell', { name: '4' })).toHaveLength(2)
  expect(screen.getByText('不从配平结果推断机理')).toBeInTheDocument()
})

test('shows the approved no-net-ionic state without a fabricated product', async () => {
  const noReaction: BalanceEquationResponse = {
    ...result,
    state: 'no_net_ionic',
    inputState: 'not_applicable',
    mode: 'net_ionic',
    formattedEquation: 'Na⁺(aq) + NO₃⁻(aq)（无净离子反应）',
    products: [],
    conservation: { elements: [], charge: null },
    message: '普通水溶液中无净离子反应',
  }
  render(
    <EquationLabView
      onBack={() => undefined}
      onBalance={() => Promise.resolve(noReaction)}
    />,
  )

  fireEvent.click(screen.getByRole('button', { name: '无净反应示例' }))
  fireEvent.click(screen.getByRole('button', { name: '配平并验证' }))

  expect(await screen.findByText('普通水溶液中无净离子反应')).toBeInTheDocument()
  expect(screen.queryByText('生成物')).not.toBeInTheDocument()
})

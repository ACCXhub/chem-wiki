import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { expect, test, vi } from 'vitest'

import { EquationLabView } from './EquationLab'
import type { BalanceEquationResponse, CatalogSpecies } from './types'


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

function species(
  applicationId: string,
  nameZh: string,
  formula: string,
  charge = 0,
): CatalogSpecies {
  return {
    consolidatedId: `species:${applicationId}`,
    applicationId,
    entityKind: charge ? 'ion' : 'substance',
    nameZh,
    nameEn: null,
    formula,
    charge,
    aliases: [],
    primaryCategory: charge > 0 ? 'cation' : charge < 0 ? 'anion' : 'elemental_substance',
    tags: [],
    defaultPriority: 'core',
    defaultPaletteRank: 1,
    equationModes: {
      molecular: charge ? 'deemphasized' : 'recommended',
      ionic: charge ? 'recommended' : 'available',
      net_ionic: charge ? 'recommended' : 'available',
    },
  }
}

const molecularCatalog = [
  species('h2', '氢气', 'H2'),
  species('o2', '氧气', 'O2'),
  species('h2o', '水', 'H2O'),
]

test('composes H2 and O2 into H2O without typing a complete equation', async () => {
  const onBalance = vi.fn(() => Promise.resolve(result))
  const onSearch = vi.fn(() => Promise.resolve(molecularCatalog))
  render(<EquationLabView onBack={() => undefined} onBalance={onBalance} onSearch={onSearch} />)

  await screen.findByText('氢气')
  fireEvent.click(screen.getByRole('button', { name: '将氢气添加到反应物' }))
  fireEvent.click(screen.getByRole('button', { name: '将氧气添加到反应物' }))
  fireEvent.click(screen.getByRole('button', { name: '将水添加到生成物' }))
  fireEvent.click(screen.getByRole('button', { name: '配平并验证' }))

  expect(onBalance).toHaveBeenCalledWith('H2 + O2 -> H2O', 'molecular')
  expect(await screen.findByText('2H₂ + O₂ → 2H₂O')).toBeInTheDocument()
  expect(screen.getByText('输入未配平，已求得最简整数比')).toBeInTheDocument()
  expect(screen.getAllByRole('cell', { name: '4' })).toHaveLength(2)
})

test('combines catalog search and category with the current equation mode', async () => {
  const onSearch = vi.fn(() => Promise.resolve([
    species('sulfate', '硫酸根离子', 'SO4', -2),
  ]))
  render(<EquationLabView onBack={() => undefined} onBalance={() => Promise.resolve(result)} onSearch={onSearch} />)

  fireEvent.click(screen.getByRole('button', { name: '离子方程式' }))
  fireEvent.click(screen.getByRole('button', { name: '阴离子' }))
  fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'sulfate' } })

  await waitFor(() => expect(onSearch).toHaveBeenLastCalledWith({
    query: 'sulfate',
    primaryCategory: 'anion',
    equationMode: 'ionic',
    limit: 50,
  }, expect.any(AbortSignal)))
  const notation = document.querySelector('.species-row.kind-ion .chem-notation')
  expect(notation).toHaveTextContent('SO₄2-')
})

test('preserves invalid errors and the approved no-net-ionic result in direct input', async () => {
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
  const onBalance = vi.fn()
    .mockRejectedValueOnce(new Error('方程式没有非零守恒解'))
    .mockResolvedValueOnce(noReaction)
  render(
    <EquationLabView
      onBack={() => undefined}
      onBalance={onBalance}
      onSearch={() => Promise.resolve([])}
    />,
  )

  fireEvent.change(screen.getByLabelText('化学方程式'), { target: { value: 'H2 -> H2O' } })
  fireEvent.click(screen.getByRole('button', { name: '直接配平', hidden: true }))
  expect(await screen.findByRole('alert')).toHaveTextContent('方程式没有非零守恒解')

  fireEvent.click(screen.getByText('无净反应示例'))
  fireEvent.click(screen.getByRole('button', { name: '直接配平', hidden: true }))
  expect(await screen.findByText('普通水溶液中无净离子反应')).toBeInTheDocument()
  expect(screen.queryByText('生成物', { selector: 'th, td' })).not.toBeInTheDocument()
})

test('keeps the already-balanced result state visible', async () => {
  const balanced = { ...result, inputState: 'balanced' as const }
  render(
    <EquationLabView
      onBack={() => undefined}
      onBalance={() => Promise.resolve(balanced)}
      onSearch={() => Promise.resolve(molecularCatalog)}
    />,
  )

  await screen.findByText('氢气')
  fireEvent.click(screen.getByRole('button', { name: '将氢气添加到反应物' }))
  fireEvent.click(screen.getByRole('button', { name: '将水添加到生成物' }))
  fireEvent.click(screen.getByRole('button', { name: '配平并验证' }))
  expect(await screen.findByText('输入已经守恒')).toBeInTheDocument()
  expect(screen.getByText('不从配平结果推断机理')).toBeInTheDocument()
})

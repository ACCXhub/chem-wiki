import { fireEvent, render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'

const elements = [
  {
    id: 'h-id',
    atomicNumber: 1,
    symbol: 'H',
    nameZh: '氢',
    nameEn: 'hydrogen',
    category: 'reactive-nonmetal',
    status: 'confirmed',
    layout: { period: 1, group: 1, row: 1, column: 1, block: 's' },
    properties: {
      electronegativity: { value: 2.2, unit: 'Pauling' },
      firstIonizationEnergy: { value: 13.598, unit: 'eV' },
    },
  },
  {
    id: 'he-id',
    atomicNumber: 2,
    symbol: 'He',
    nameZh: '氦',
    nameEn: 'helium',
    category: 'noble-gas',
    status: 'confirmed',
    layout: { period: 1, group: 18, row: 1, column: 18, block: 's' },
    properties: {
      electronegativity: { value: null, unit: null },
      firstIonizationEnergy: { value: 24.587, unit: 'eV' },
    },
  },
  {
    id: 'o-id',
    atomicNumber: 8,
    symbol: 'O',
    nameZh: '氧',
    nameEn: 'oxygen',
    category: 'reactive-nonmetal',
    status: 'confirmed',
    layout: { period: 2, group: 16, row: 2, column: 16, block: 'p' },
    properties: {
      electronegativity: { value: 3.44, unit: 'Pauling' },
      firstIonizationEnergy: { value: 13.618, unit: 'eV' },
    },
  },
] as const


test('hover and keyboard focus expose a floating element inspector without a permanent panel', async () => {
  const { PeriodicTableView } = await import('./PeriodicTable')
  const onElementSelect = vi.fn()
  render(
    <PeriodicTableView
      elements={[...elements]}
      onElementSelect={onElementSelect}
    />,
  )

  expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()

  const oxygen = screen.getByRole('button', { name: '8 氧 O' })
  fireEvent.pointerEnter(oxygen, { clientX: 40, clientY: 40 })
  fireEvent.pointerMove(oxygen, { clientX: 40, clientY: 40 })
  expect(screen.getByRole('tooltip')).toHaveTextContent('氧 O')
  expect(screen.getByRole('tooltip')).toHaveStyle({ left: '56px', top: '56px' })

  fireEvent.pointerLeave(oxygen)
  expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()

  fireEvent.focus(oxygen)
  expect(screen.getByRole('tooltip')).toHaveTextContent('氧 O')
  fireEvent.click(screen.getByRole('button', { name: '2 氦 He' }))
  expect(onElementSelect).toHaveBeenCalledWith('he-id')
})

test('renders period and group coordinates plus the metal nonmetal staircase', async () => {
  const { PeriodicTableView } = await import('./PeriodicTable')
  render(<PeriodicTableView elements={[...elements]} />)

  expect(screen.getByTestId('period-label-1')).toHaveTextContent('1')
  expect(screen.getByTestId('period-label-7')).toHaveTextContent('7')
  expect(screen.getByTestId('group-label-1')).toHaveTextContent('1')
  expect(screen.getByTestId('group-label-18')).toHaveTextContent('18')
  expect(screen.getByTestId('metal-nonmetal-boundary')).toBeInTheDocument()
})


test('property modes render a persistent heatmap legend and explicit missing values', async () => {
  const { PeriodicTableView } = await import('./PeriodicTable')
  render(<PeriodicTableView elements={[...elements]} />)

  fireEvent.click(screen.getByRole('button', { name: '电负性' }))

  expect(screen.getByRole('group', { name: '图例' })).toBeInTheDocument()
  expect(screen.getByText('低')).toBeInTheDocument()
  expect(screen.getByText('高')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: '2 氦 He' })).toHaveTextContent('暂无数据')

  fireEvent.click(screen.getByRole('button', { name: '第一电离能' }))
  expect(screen.getByRole('button', { name: '1 氢 H' })).toHaveTextContent('13.598')
  expect(screen.getByText('单位：eV')).toBeInTheDocument()
})


test('search locates by Chinese name, symbol, English name, or atomic number', async () => {
  const { PeriodicTableView } = await import('./PeriodicTable')
  const onElementSelect = vi.fn()
  render(
    <PeriodicTableView
      elements={[...elements]}
      onElementSelect={onElementSelect}
    />,
  )

  const input = screen.getByRole('searchbox', { name: '搜索元素' })
  fireEvent.change(input, { target: { value: 'oxygen' } })
  fireEvent.submit(input.closest('form')!)

  expect(screen.getByRole('heading', { name: '氧 O' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: '8 氧 O' })).toHaveFocus()
  expect(onElementSelect).toHaveBeenCalledWith('o-id')

  fireEvent.change(input, { target: { value: '999' } })
  fireEvent.submit(input.closest('form')!)
  expect(screen.getByRole('status')).toHaveTextContent('未找到匹配元素')
})

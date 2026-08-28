import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, expect, test, vi } from 'vitest'

import { EquationLabView } from './EquationLab'
import type { BalanceEquationResponse, CatalogSpecies, ReactionCandidate } from './types'
import type { PeriodicTableElement } from '../periodic_table'


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
    composition: formula === 'H2O' ? { H: 2, O: 1 } : { [formula.replace(/[0-9]/g, '')]: 1 },
    aliases: [],
    chemicalClassifications: [],
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

function reactionCandidate(
  id: string,
  nameZh: string,
  product: CatalogSpecies,
  reversible = false,
): ReactionCandidate {
  return {
    consolidatedId: id,
    applicationReactionId: `application:${id}`,
    nameZh,
    materializationState: 'materialized',
    participants: [
      { role: 'reactant', coefficient: 2, speciesId: molecularCatalog[0].consolidatedId, applicationTargetId: 'h2', targetType: 'substance', nonSpeciesRef: null, nameZh: '氢气', formula: 'H2', charge: 0, phase: 'g' },
      { role: 'reactant', coefficient: 1, speciesId: molecularCatalog[1].consolidatedId, applicationTargetId: 'o2', targetType: 'substance', nonSpeciesRef: null, nameZh: '氧气', formula: 'O2', charge: 0, phase: 'g' },
      { role: 'product', coefficient: 2, speciesId: product.consolidatedId, applicationTargetId: product.applicationId, targetType: 'substance', nonSpeciesRef: null, nameZh: product.nameZh, formula: product.formula, charge: product.charge, phase: 'l' },
    ],
    equation: product.applicationId === 'h2o' ? '2H2 + O2 -> 2H2O' : `2H2 + O2 -> 2${product.formula}`,
    reversible,
    reactionTypes: ['化合反应'],
    conditions: ['点燃'],
    provenanceRefs: ['catalog:test'],
    sourcePackage: 'test',
    sourceId: id,
    orientation: 'canonical',
    matchedAnchorCount: 1,
    completionRatio: 1 / 3,
    missingParticipantCount: 2,
  }
}

beforeEach(() => window.localStorage.clear())

function material(name: string, scope = document.body) {
  return within(scope).getByRole('article', { name: `拖拽物质 ${name}` })
}

function addMaterial(name: string, side: 'reactants' | 'products', scope = document.body) {
  const block = material(name, scope)
  fireEvent.click(block)
  fireEvent.click(within(block).getByRole('button', { name: side === 'reactants' ? '放入反应物' : '放入生成物' }))
}

function dragData() {
  return { effectAllowed: '', dropEffect: '', setData: vi.fn(), setDragImage: vi.fn() }
}

test('drags H2 and O2 into reactants and H2O into products, then auto-balances', async () => {
  const onBalance = vi.fn(() => Promise.resolve(result))
  const onSearch = vi.fn(() => Promise.resolve(molecularCatalog))
  render(<EquationLabView onBack={() => undefined} onBalance={onBalance} onSearch={onSearch} />)

  await screen.findByText('氢气')
  expect(screen.getByRole('checkbox', { name: '自动配平ON' })).toBeChecked()
  const reactants = screen.getByRole('region', { name: '反应物' })
  const products = screen.getByRole('region', { name: '生成物' })
  const dataTransfer = dragData()

  fireEvent.dragStart(material('氢气'), { dataTransfer })
  fireEvent.dragOver(reactants, { dataTransfer })
  expect(reactants).toHaveClass('is-drag-target')
  fireEvent.drop(reactants, { dataTransfer })
  fireEvent.dragStart(material('氧气'), { dataTransfer })
  fireEvent.dragOver(reactants, { dataTransfer })
  fireEvent.drop(reactants, { dataTransfer })
  fireEvent.dragStart(material('水'), { dataTransfer })
  fireEvent.dragOver(products, { dataTransfer })
  fireEvent.drop(products, { dataTransfer })

  await waitFor(() => expect(onBalance).toHaveBeenCalledWith('H2 + O2 -> H2O', 'molecular'))
  await screen.findByText('输入未配平，已求得最简整数比')
  expect(screen.getByLabelText('结构化方程式草稿')).toHaveTextContent('2H₂氢气+O₂氧气+＋→2H₂O水+＋')
  expect(screen.getByLabelText('反应物空槽位')).toBeInTheDocument()
  expect(screen.getByLabelText('生成物空槽位')).toBeInTheDocument()
  expect(screen.getByText('输入未配平，已求得最简整数比')).toBeInTheDocument()
  expect(screen.getAllByRole('cell', { name: '4' })).toHaveLength(2)
})

test('converges same-side duplicates and supports participant move, removal, and undo', async () => {
  render(<EquationLabView onBack={() => undefined} onBalance={() => Promise.resolve(result)} onSearch={() => Promise.resolve(molecularCatalog)} />)

  await screen.findByText('氢气')
  addMaterial('氢气', 'reactants')
  addMaterial('氢气', 'reactants')
  addMaterial('氧气', 'reactants')
  expect(screen.getAllByLabelText('氢气，点击编辑物态，双击移除')).toHaveLength(1)

  const dataTransfer = dragData()
  const oxygen = screen.getByLabelText('氧气，点击编辑物态，双击移除')
  fireEvent.dragStart(oxygen, { dataTransfer })
  fireEvent.drop(screen.getByRole('region', { name: '生成物' }), { dataTransfer })
  expect(screen.getByRole('region', { name: '生成物' })).toHaveTextContent('氧气')
  expect(screen.getByRole('region', { name: '反应物' })).not.toHaveTextContent('氧气')

  const hydrogen = screen.getByLabelText('氢气，点击编辑物态，双击移除')
  fireEvent.doubleClick(hydrogen)
  expect(screen.queryByLabelText('氢气，点击编辑物态，双击移除')).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: '撤销' }))
  expect(await screen.findByLabelText('氢气，点击编辑物态，双击移除')).toBeInTheDocument()
})

test('keeps keyboard placement controls active inside a material block', async () => {
  render(<EquationLabView onBack={() => undefined} onBalance={() => Promise.resolve(result)} onSearch={() => Promise.resolve(molecularCatalog)} />)

  await screen.findByText('氢气')
  const hydrogen = material('氢气')
  fireEvent.keyDown(hydrogen, { key: 'Enter' })
  const placeReactant = within(hydrogen).getByRole('button', { name: '放入反应物' })
  fireEvent.keyDown(placeReactant, { key: 'Enter' })
  expect(placeReactant).toBeInTheDocument()
  fireEvent.click(placeReactant)
  expect(screen.getByRole('region', { name: '反应物' })).toHaveTextContent('氢气')
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
  const notation = document.querySelector('.species-block.kind-ion .chem-notation')
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

  fireEvent.click(screen.getByRole('button', { name: '净离子方程式' }))
  fireEvent.click(screen.getByRole('button', { name: '手动输入' }))
  fireEvent.change(screen.getByLabelText('化学方程式'), { target: { value: 'H2 -> H2O' } })
  fireEvent.click(screen.getByRole('button', { name: '直接配平' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('方程式没有非零守恒解')

  fireEvent.click(screen.getByText('无净反应示例'))
  fireEvent.click(screen.getByRole('button', { name: '直接配平' }))
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
  addMaterial('氢气', 'reactants')
  addMaterial('水', 'products')
  expect(await screen.findByText('输入已经守恒')).toBeInTheDocument()
  expect(screen.queryByText('不从配平结果推断机理')).not.toBeInTheDocument()
  expect(screen.queryByText('实时方程式')).not.toBeInTheDocument()
})

test('stops automatic balancing when disabled while preserving explicit balancing', async () => {
  const onBalance = vi.fn(() => Promise.resolve(result))
  render(<EquationLabView onBack={() => undefined} onBalance={onBalance} onSearch={() => Promise.resolve(molecularCatalog)} />)

  await screen.findByText('氢气')
  fireEvent.click(screen.getByRole('checkbox', { name: '自动配平ON' }))
  expect(screen.getByRole('checkbox', { name: '自动配平OFF' })).not.toBeChecked()
  await screen.findByRole('article', { name: '拖拽物质 氧气' })
  addMaterial('氢气', 'reactants')
  addMaterial('氧气', 'reactants')
  addMaterial('水', 'products')
  await new Promise((resolve) => window.setTimeout(resolve, 340))
  expect(onBalance).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: '配平' }))
  await waitFor(() => expect(onBalance).toHaveBeenCalledWith('H2 + O2 -> H2O', 'molecular'))
})

test('does not let an older automatic balance response replace a newer draft', async () => {
  let resolveFirst: (value: BalanceEquationResponse) => void = () => undefined
  let resolveSecond: (value: BalanceEquationResponse) => void = () => undefined
  const onBalance = vi.fn()
    .mockImplementationOnce(() => new Promise<BalanceEquationResponse>((resolve) => { resolveFirst = resolve }))
    .mockImplementationOnce(() => new Promise<BalanceEquationResponse>((resolve) => { resolveSecond = resolve }))
  render(<EquationLabView onBack={() => undefined} onBalance={onBalance} onSearch={() => Promise.resolve(molecularCatalog)} />)

  await screen.findByText('氢气')
  addMaterial('氢气', 'reactants')
  addMaterial('氧气', 'reactants')
  addMaterial('水', 'products')
  await waitFor(() => expect(onBalance).toHaveBeenCalledTimes(1))

  fireEvent.click(screen.getByLabelText('氢气，点击编辑物态，双击移除'))
  await new Promise((resolve) => window.setTimeout(resolve, 200))
  fireEvent.click(screen.getByRole('button', { name: '(g)' }))
  resolveFirst(result)
  await Promise.resolve()
  expect(document.querySelector('.participant-coefficient')).not.toBeInTheDocument()
  await waitFor(() => expect(onBalance).toHaveBeenCalledWith('H2(g) + O2 -> H2O', 'molecular'))
  resolveSecond(result)
  await waitFor(() => expect(screen.getByLabelText('结构化方程式草稿')).toHaveTextContent('2H₂'))
})

test('narrows candidates with both equation sides and auto-focuses a unique reaction', async () => {
  const peroxide = species('h2o2', '过氧化氢', 'H2O2')
  const waterReaction = reactionCandidate('reaction:water', '水的生成', molecularCatalog[2])
  const peroxideReaction = reactionCandidate('reaction:peroxide', '过氧化氢的生成', peroxide)
  const onFindCandidates = vi.fn((request: { reactantApplicationIds: string[]; productApplicationIds: string[] }) => {
    if (request.productApplicationIds.includes('h2o')) return Promise.resolve([waterReaction])
    return Promise.resolve([waterReaction, peroxideReaction])
  })
  render(<EquationLabView onBack={() => undefined} onBalance={() => Promise.resolve(result)} onSearch={() => Promise.resolve(molecularCatalog)} onFindCandidates={onFindCandidates} />)

  await screen.findByText('氢气')
  addMaterial('氢气', 'reactants')
  expect(await screen.findByRole('heading', { name: '候选反应' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: '选择反应 过氧化氢的生成' })).toBeInTheDocument()

  addMaterial('水', 'products')
  expect(await screen.findByRole('region', { name: '当前反应' })).toHaveTextContent('水的生成')
  await waitFor(() => expect(onFindCandidates).toHaveBeenLastCalledWith({
    reactantApplicationIds: ['h2'],
    productApplicationIds: ['h2o'],
  }, expect.any(AbortSignal)))
  expect(screen.getByLabelText('氧气，由当前反应补全')).toBeInTheDocument()
  expect(screen.getByText('化合反应')).toBeInTheDocument()
  expect(screen.getByText('点燃')).toBeInTheDocument()
})

test('manually promotes an alternative candidate to the stable cluster center', async () => {
  const peroxide = species('h2o2', '过氧化氢', 'H2O2')
  const candidates = [
    reactionCandidate('reaction:water', '水的生成', molecularCatalog[2]),
    reactionCandidate('reaction:peroxide', '过氧化氢的生成', peroxide),
  ]
  render(<EquationLabView onBack={() => undefined} onBalance={() => Promise.resolve(result)} onSearch={() => Promise.resolve(molecularCatalog)} onFindCandidates={() => Promise.resolve(candidates)} />)

  await screen.findByText('氢气')
  addMaterial('氢气', 'reactants')
  const alternative = await screen.findByRole('button', { name: '选择反应 过氧化氢的生成' })
  expect(alternative).toHaveClass('is-alternative')
  fireEvent.click(alternative)

  expect(screen.getByRole('button', { name: '选择反应 过氧化氢的生成' })).toHaveClass('is-central')
  expect(screen.getByRole('region', { name: '当前反应' })).toHaveTextContent('过氧化氢的生成')
  expect(screen.getByLabelText('过氧化氢，由当前反应补全')).toBeInTheDocument()
})

test('keeps direct catalog selection primary while exposing the controlled builder', async () => {
  render(
    <EquationLabView
      onBack={() => undefined}
      onBalance={() => Promise.resolve(result)}
      onSearch={() => Promise.resolve(molecularCatalog)}
    />,
  )

  await screen.findByText('氢气')
  expect(screen.getByRole('button', { name: '搜索物质' })).toHaveAttribute('aria-pressed', 'true')
  fireEvent.click(screen.getByRole('button', { name: '构建物质' }))
  expect(screen.getByRole('region', { name: '构建物质' })).toBeInTheDocument()
})

test('resolves controlled sodium and sulfate blocks to the existing catalog species and draft', async () => {
  const sodium = { ...species('sodium', '钠离子', 'Na', 1), composition: { Na: 1 } }
  const sulfate = { ...species('sulfate', '硫酸根离子', 'SO4', -2), composition: { S: 1, O: 4 } }
  const sodiumSulfate = { ...species('sodium-sulfate', '硫酸钠', 'Na2SO4'), composition: { Na: 2, S: 1, O: 4 } }
  const onSearch = vi.fn((request: { primaryCategory?: string; composition?: Record<string, number> }) => {
    if (request.primaryCategory === 'cation') return Promise.resolve([sodium])
    if (request.primaryCategory === 'anion') return Promise.resolve([sulfate])
    if (request.composition) return Promise.resolve([sodiumSulfate])
    return Promise.resolve(molecularCatalog)
  })
  render(
    <EquationLabView
      onBack={() => undefined}
      onBalance={() => Promise.resolve(result)}
      onSearch={onSearch}
      onLoadElements={() => Promise.resolve([])}
    />,
  )

  await screen.findByText('氢气')
  fireEvent.click(screen.getByRole('button', { name: '构建物质' }))
  expect(await screen.findByRole('button', { name: '添加钠离子' })).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: '添加钠离子' }))
  fireEvent.click(screen.getByRole('button', { name: '添加钠离子' }))
  fireEvent.click(screen.getByRole('button', { name: '阴离子' }))
  fireEvent.click(screen.getByRole('button', { name: '添加硫酸根离子' }))

  expect(await screen.findByText('1 个匹配')).toBeInTheDocument()
  await waitFor(() => expect(onSearch).toHaveBeenLastCalledWith({
    composition: { Na: 2, O: 4, S: 1 },
    charge: 0,
    entityKind: 'substance',
    equationMode: 'molecular',
    limit: 50,
  }, expect.any(AbortSignal)))
  const dataTransfer = dragData()
  fireEvent.dragStart(material('硫酸钠'), { dataTransfer })
  fireEvent.dragOver(screen.getByRole('region', { name: '反应物' }), { dataTransfer })
  fireEvent.drop(screen.getByRole('region', { name: '反应物' }), { dataTransfer })
  expect(screen.getByRole('region', { name: '反应物' })).toHaveTextContent('硫酸钠')
})

test('shows multiple and no controlled composition matches without synthesizing a species', async () => {
  const carbon: PeriodicTableElement = {
    id: 'carbon', atomicNumber: 6, symbol: 'C', nameZh: '碳', nameEn: 'carbon', category: 'reactive-nonmetal', status: 'confirmed' as const,
    layout: { period: 2, group: 14, row: 2, column: 14, block: 'p' as const },
    properties: { electronegativity: { value: 2.5, unit: 'Pauling' }, firstIonizationEnergy: { value: 11.2, unit: 'eV' } },
  }
  const hydrogen = { ...carbon, id: 'hydrogen', atomicNumber: 1, symbol: 'H', nameZh: '氢', nameEn: 'hydrogen' }
  const buteneOne = { ...species('butene-1', '1-丁烯', 'C4H8'), composition: { C: 4, H: 8 } }
  const buteneTwo = { ...species('butene-2', '顺-2-丁烯', 'C4H8'), composition: { C: 4, H: 8 } }
  const onSearch = vi.fn((request: { composition?: Record<string, number> }) => {
    if (request.composition?.C === 4 && request.composition.H === 8) return Promise.resolve([buteneOne, buteneTwo])
    if (request.composition) return Promise.resolve([])
    return Promise.resolve(molecularCatalog)
  })
  render(
    <EquationLabView
      onBack={() => undefined}
      onBalance={() => Promise.resolve(result)}
      onSearch={onSearch}
      onLoadElements={() => Promise.resolve([carbon, hydrogen])}
    />,
  )

  await screen.findByText('氢气')
  fireEvent.click(screen.getByRole('button', { name: '构建物质' }))
  fireEvent.click(screen.getByRole('button', { name: '元素' }))
  expect(await screen.findByRole('button', { name: '添加碳' })).toBeInTheDocument()
  for (let count = 0; count < 4; count += 1) fireEvent.click(screen.getByRole('button', { name: '添加碳' }))
  for (let count = 0; count < 8; count += 1) fireEvent.click(screen.getByRole('button', { name: '添加氢' }))
  expect(await screen.findByText('2 个匹配')).toBeInTheDocument()
  expect(screen.getByText('1-丁烯')).toBeInTheDocument()
  expect(screen.getByText('顺-2-丁烯')).toBeInTheDocument()

  fireEvent.click(screen.getByRole('button', { name: '增加氢' }))
  expect(await screen.findByText('未找到匹配物质')).toBeInTheDocument()
})

test('persists a direct palette favorite and recent use across reload', async () => {
  window.localStorage.clear()
  const first = render(
    <EquationLabView onBack={() => undefined} onBalance={() => Promise.resolve(result)} onSearch={() => Promise.resolve(molecularCatalog)} />,
  )
  await screen.findByText('氢气')
  fireEvent.click(screen.getByRole('button', { name: '收藏水' }))
  addMaterial('水', 'reactants')
  first.unmount()

  render(
    <EquationLabView onBack={() => undefined} onBalance={() => Promise.resolve(result)} onSearch={() => Promise.resolve(molecularCatalog)} />,
  )
  expect(await screen.findByRole('button', { name: '取消收藏水' })).toBeInTheDocument()
  expect(screen.queryByLabelText('最近使用')).not.toBeInTheDocument()
})

test('keeps quick species in one compact flow and hides their duplicate catalog blocks until searching', async () => {
  const view = render(
    <EquationLabView onBack={() => undefined} onBalance={() => Promise.resolve(result)} onSearch={() => Promise.resolve(molecularCatalog)} />,
  )
  await screen.findByText('氢气')
  fireEvent.click(screen.getByRole('button', { name: '收藏水' }))
  addMaterial('水', 'reactants')
  view.unmount()

  render(
    <EquationLabView onBack={() => undefined} onBalance={() => Promise.resolve(result)} onSearch={() => Promise.resolve(molecularCatalog)} />,
  )
  const quickFlow = await screen.findByRole('region', { name: '快捷物质' })
  expect(within(quickFlow).getAllByRole('article', { name: '拖拽物质 水' })).toHaveLength(1)
  expect(screen.getAllByRole('article', { name: '拖拽物质 水' })).toHaveLength(1)

  fireEvent.change(screen.getByRole('searchbox'), { target: { value: '水' } })
  await waitFor(() => expect(screen.getAllByRole('article', { name: '拖拽物质 水' })).toHaveLength(2))
})

test('toggles palette Chinese names immediately and persists the display preference', async () => {
  const first = render(
    <EquationLabView onBack={() => undefined} onBalance={() => Promise.resolve(result)} onSearch={() => Promise.resolve(molecularCatalog)} />,
  )
  await screen.findByText('氢气')
  fireEvent.click(screen.getByRole('button', { name: '隐藏中文名' }))
  expect(material('氢气')).toHaveTextContent('H₂')
  expect(material('氢气')).not.toHaveTextContent('氢气')
  first.unmount()

  render(
    <EquationLabView onBack={() => undefined} onBalance={() => Promise.resolve(result)} onSearch={() => Promise.resolve(molecularCatalog)} />,
  )
  expect(await screen.findByRole('button', { name: '显示中文名' })).toBeInTheDocument()
  await screen.findByRole('article', { name: '拖拽物质 氢气' })
  expect(material('氢气')).not.toHaveTextContent('氢气')
})

test('hydrates saved long-tail favorites and recents separately from the default catalog after reload', async () => {
  window.localStorage.clear()
  const longTail = species('long-tail', '甲苯', 'C7H8')
  const onSearch = vi.fn((request: { query?: string; applicationIds?: string[] }) => {
    if (request.query === '甲苯') return Promise.resolve([longTail])
    if (request.applicationIds) return Promise.resolve([longTail])
    return Promise.resolve(molecularCatalog)
  })
  const first = render(
    <EquationLabView onBack={() => undefined} onBalance={() => Promise.resolve(result)} onSearch={onSearch} />,
  )

  await screen.findByText('氢气')
  fireEvent.change(screen.getByRole('searchbox'), { target: { value: '甲苯' } })
  await screen.findByText('甲苯')
  fireEvent.click(screen.getByRole('button', { name: '收藏甲苯' }))
  addMaterial('甲苯', 'reactants')
  first.unmount()

  const second = render(
    <EquationLabView onBack={() => undefined} onBalance={() => Promise.resolve(result)} onSearch={onSearch} />,
  )

  const quickAccess = await screen.findByRole('region', { name: '快捷物质' })
  fireEvent.click(within(quickAccess).getByRole('button', { name: '取消收藏甲苯' }))
  expect(await within(quickAccess).findByLabelText('最近使用')).toBeInTheDocument()
  addMaterial('甲苯', 'products', quickAccess)
  expect(screen.getByRole('region', { name: '生成物' })).toHaveTextContent('甲苯')
  expect(window.localStorage.getItem('chem-wiki.equation-lab.palette-preferences.v1'))
    .toBe(JSON.stringify({ version: 1, favorites: [], recents: ['long-tail'], showChineseNames: true }))
  second.unmount()

  render(
    <EquationLabView onBack={() => undefined} onBalance={() => Promise.resolve(result)} onSearch={onSearch} />,
  )
  const reloadedQuickAccess = await screen.findByRole('region', { name: '快捷物质' })
  expect(within(reloadedQuickAccess).getByLabelText('最近使用')).toBeInTheDocument()
})

test('removes stale saved palette identities without breaking the normal catalog', async () => {
  window.localStorage.setItem(
    'chem-wiki.equation-lab.palette-preferences.v1',
    JSON.stringify({ version: 1, favorites: ['missing-species'], recents: ['missing-species'] }),
  )
  render(
    <EquationLabView
      onBack={() => undefined}
      onBalance={() => Promise.resolve(result)}
      onSearch={(request) => Promise.resolve(request.applicationIds ? [] : molecularCatalog)}
    />,
  )

  expect(await screen.findByText('氢气')).toBeInTheDocument()
  await waitFor(() => expect(window.localStorage.getItem('chem-wiki.equation-lab.palette-preferences.v1'))
    .toBe(JSON.stringify({ version: 1, favorites: [], recents: [], showChineseNames: true })))
  expect(screen.queryByRole('region', { name: '快捷物质' })).not.toBeInTheDocument()
})

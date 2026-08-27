import { expect, test } from 'vitest'

import {
  addBuilderBlock,
  adjustBuilderBlock,
  canSubmitDraft,
  clearBuilderTray,
  createDraftParticipant,
  resolveBuilderTray,
  serializeEquationDraft,
} from './composer'
import type { BuilderBlock, CatalogSpecies, EquationDraft } from './types'


function species(overrides: Partial<CatalogSpecies> = {}): CatalogSpecies {
  return {
    consolidatedId: 'species:test',
    applicationId: '00000000-0000-4000-8000-000000000001',
    entityKind: 'substance',
    nameZh: '测试物种',
    nameEn: null,
    formula: 'H2O',
    charge: 0,
    composition: { H: 2, O: 1 },
    aliases: [],
    chemicalClassifications: ['oxide'],
    primaryCategory: 'oxide',
    tags: [],
    defaultPriority: 'core',
    defaultPaletteRank: 1,
    equationModes: {
      molecular: 'recommended',
      ionic: 'deemphasized',
      net_ionic: 'deemphasized',
    },
    ...overrides,
  }
}

test('serializes catalog identities into the existing M05 equation syntax', () => {
  const silver = createDraftParticipant(species({
    applicationId: '00000000-0000-4000-8000-000000000002',
    entityKind: 'ion',
    formula: 'Ag',
    charge: 1,
  }))
  silver.phase = 'aq'
  const sulfate = createDraftParticipant(species({
    applicationId: '00000000-0000-4000-8000-000000000003',
    entityKind: 'ion',
    formula: 'SO4',
    charge: -2,
  }))
  const product = createDraftParticipant(species({ formula: 'Ag2SO4' }))
  product.phase = 's'

  expect(serializeEquationDraft({
    mode: 'ionic',
    reactants: [silver, sulfate],
    products: [product],
  })).toBe('Ag+(aq) + SO4^2- -> Ag2SO4(s)')
})

test('requires both sides except for the preserved no-net-ionic path', () => {
  const participant = createDraftParticipant(species())
  const molecular: EquationDraft = { mode: 'molecular', reactants: [participant], products: [] }
  const netIonic: EquationDraft = { ...molecular, mode: 'net_ionic' }

  expect(canSubmitDraft(molecular)).toBe(false)
  expect(canSubmitDraft(netIonic)).toBe(true)
})

test('turns controlled ion blocks into catalog resolution facts', () => {
  expect(resolveBuilderTray([
    {
      block: { id: 'ion:sodium', label: '钠离子', formula: 'Na', composition: { Na: 1 }, charge: 1, kind: 'ion' },
      count: 2,
    },
    {
      block: { id: 'ion:sulfate', label: '硫酸根', formula: 'SO4', composition: { S: 1, O: 4 }, charge: -2, kind: 'ion' },
      count: 1,
    },
  ])).toEqual({
    composition: { Na: 2, O: 4, S: 1 },
    totalCharge: 0,
    entityKind: 'substance',
  })
})

test('keeps a compact controlled tray with explicit count and removal operations', () => {
  const sodium: BuilderBlock = {
    id: 'ion:sodium', label: '钠离子', formula: 'Na', composition: { Na: 1 }, charge: 1, kind: 'ion',
  }
  const once = addBuilderBlock([], sodium)
  const twice = addBuilderBlock(once, sodium)

  expect(twice).toHaveLength(1)
  expect(twice[0].count).toBe(2)
  expect(adjustBuilderBlock(twice, sodium.id, -1)[0].count).toBe(1)
  expect(adjustBuilderBlock(once, sodium.id, -1)).toEqual([])
  expect(clearBuilderTray()).toEqual([])
})

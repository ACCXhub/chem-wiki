import { expect, test } from 'vitest'

import {
  canSubmitDraft,
  createDraftParticipant,
  serializeEquationDraft,
} from './composer'
import type { CatalogSpecies, EquationDraft } from './types'


function species(overrides: Partial<CatalogSpecies> = {}): CatalogSpecies {
  return {
    consolidatedId: 'species:test',
    applicationId: '00000000-0000-4000-8000-000000000001',
    entityKind: 'substance',
    nameZh: '测试物种',
    nameEn: null,
    formula: 'H2O',
    charge: 0,
    aliases: [],
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

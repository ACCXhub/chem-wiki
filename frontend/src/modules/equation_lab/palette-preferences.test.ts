import { expect, test } from 'vitest'

import {
  loadPalettePreferences,
  resolvePaletteSpecies,
  recordPaletteRecent,
  savePalettePreferences,
  togglePaletteFavorite,
} from './palette-preferences'
import type { CatalogSpecies } from './types'

function species(applicationId: string): CatalogSpecies {
  return {
    consolidatedId: `species:${applicationId}`,
    applicationId,
    entityKind: 'substance',
    nameZh: applicationId,
    nameEn: null,
    formula: applicationId,
    charge: 0,
    composition: { H: 2 },
    aliases: [],
    chemicalClassifications: [],
    primaryCategory: 'elemental_substance',
    tags: [],
    defaultPriority: 'core',
    defaultPaletteRank: 1,
    equationModes: { molecular: 'recommended', ionic: 'available', net_ionic: 'available' },
  }
}

test('persists identity-based favorites and recents while ignoring unsupported stored values', () => {
  const storage = new Map<string, string>()
  const localStorage = {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => storage.set(key, value),
  } as unknown as Storage
  let preferences = togglePaletteFavorite({ favorites: [], recents: [] }, 'water')
  preferences = recordPaletteRecent(preferences, 'water')
  savePalettePreferences(preferences, localStorage)
  storage.set('bad', 'invalid')

  expect(loadPalettePreferences(localStorage)).toEqual({ favorites: ['water'], recents: ['water'] })
  expect(resolvePaletteSpecies([species('hydrogen'), species('water')], preferences.favorites).map((item) => item.applicationId))
    .toEqual(['water'])
})

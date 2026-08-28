import { expect, test } from 'vitest'

import {
  loadPalettePreferences,
  resolvePaletteSpecies,
  recordPaletteRecent,
  savePalettePreferences,
  setPaletteChineseNames,
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
  let preferences = togglePaletteFavorite({ favorites: [], recents: [], showChineseNames: true }, 'water')
  preferences = recordPaletteRecent(preferences, 'water')
  preferences = setPaletteChineseNames(preferences, false)
  savePalettePreferences(preferences, localStorage)
  storage.set('bad', 'invalid')

  expect(loadPalettePreferences(localStorage)).toEqual({ favorites: ['water'], recents: ['water'], showChineseNames: false })
  expect(resolvePaletteSpecies([species('hydrogen'), species('water')], preferences.favorites).map((item) => item.applicationId))
    .toEqual(['water'])
})

test('loads legacy favorites and recents with Chinese names enabled by default', () => {
  const storage = {
    getItem: () => JSON.stringify({ version: 1, favorites: ['water'], recents: ['water'] }),
    setItem: () => undefined,
  } as unknown as Storage

  expect(loadPalettePreferences(storage)).toEqual({ favorites: ['water'], recents: ['water'], showChineseNames: true })
})

import type {
  BuilderBlock,
  BuilderResolution,
  BuilderTrayEntry,
  CatalogSpecies,
  EquationDraft,
  EquationDraftParticipant,
  EquationPhase,
} from './types'

export function addBuilderBlock(
  entries: BuilderTrayEntry[],
  block: BuilderBlock,
): BuilderTrayEntry[] {
  const existing = entries.find((entry) => entry.block.id === block.id)
  if (!existing) return [...entries, { block, count: 1 }]
  return entries.map((entry) => (
    entry.block.id === block.id ? { ...entry, count: entry.count + 1 } : entry
  ))
}

export function adjustBuilderBlock(
  entries: BuilderTrayEntry[],
  blockId: string,
  delta: -1 | 1,
): BuilderTrayEntry[] {
  return entries.flatMap((entry) => {
    if (entry.block.id !== blockId) return [entry]
    const count = entry.count + delta
    return count > 0 ? [{ ...entry, count }] : []
  })
}

export function clearBuilderTray(): BuilderTrayEntry[] {
  return []
}

export function resolveBuilderTray(entries: BuilderTrayEntry[]): BuilderResolution | null {
  if (!entries.length) return null
  const composition: Record<string, number> = {}
  let totalCharge = 0
  for (const { block, count } of entries) {
    if (count < 1) continue
    totalCharge += block.charge * count
    for (const [element, amount] of Object.entries(block.composition)) {
      composition[element] = (composition[element] ?? 0) + amount * count
    }
  }
  if (!Object.keys(composition).length) return null
  return {
    composition: Object.fromEntries(Object.entries(composition).sort(([left], [right]) => (
      left.localeCompare(right)
    ))),
    totalCharge,
    entityKind: totalCharge === 0 ? 'substance' : 'ion',
  }
}


export function createDraftParticipant(species: CatalogSpecies): EquationDraftParticipant {
  return { ...species, phase: null }
}

export function serializeParticipant(participant: EquationDraftParticipant): string {
  const magnitude = Math.abs(participant.charge)
  const charge = participant.charge === 0
    ? ''
    : `${magnitude === 1 ? '' : `^${magnitude}`}${participant.charge > 0 ? '+' : '-'}`
  const phase = participant.phase ? `(${participant.phase})` : ''
  return `${participant.formula}${charge}${phase}`
}

export function serializeEquationDraft(draft: EquationDraft): string {
  const reactants = draft.reactants.map(serializeParticipant).join(' + ')
  const products = draft.products.map(serializeParticipant).join(' + ')
  return products ? `${reactants} -> ${products}` : reactants
}

export function canSubmitDraft(draft: EquationDraft): boolean {
  return draft.reactants.length > 0
    && (draft.products.length > 0 || draft.mode === 'net_ionic')
}

export function addParticipant(
  participants: EquationDraftParticipant[],
  species: CatalogSpecies,
): EquationDraftParticipant[] {
  if (participants.some((participant) => participant.applicationId === species.applicationId)) {
    return participants
  }
  return [...participants, createDraftParticipant(species)]
}

export function moveParticipant(
  participants: EquationDraftParticipant[],
  index: number,
  direction: -1 | 1,
): EquationDraftParticipant[] {
  const target = index + direction
  if (target < 0 || target >= participants.length) return participants
  const reordered = [...participants]
  ;[reordered[index], reordered[target]] = [reordered[target], reordered[index]]
  return reordered
}

export function updateParticipantPhase(
  participants: EquationDraftParticipant[],
  applicationId: string,
  phase: EquationPhase | null,
): EquationDraftParticipant[] {
  return participants.map((participant) => (
    participant.applicationId === applicationId ? { ...participant, phase } : participant
  ))
}

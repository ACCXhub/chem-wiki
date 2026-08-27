import type {
  CatalogSpecies,
  EquationDraft,
  EquationDraftParticipant,
  EquationPhase,
} from './types'


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

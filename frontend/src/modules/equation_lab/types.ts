export type EquationMode = 'molecular' | 'ionic' | 'net_ionic'

export type EquationPhase = 'aq' | 's' | 'l' | 'g'

export type EquationSuitability = 'recommended' | 'available' | 'deemphasized'

export interface CatalogSpecies {
  consolidatedId: string
  applicationId: string
  entityKind: 'ion' | 'substance'
  nameZh: string
  nameEn: string | null
  formula: string
  charge: number
  composition: Record<string, number> | null
  aliases: string[]
  chemicalClassifications: string[]
  primaryCategory: string
  tags: string[]
  defaultPriority: string
  defaultPaletteRank: number
  equationModes: Record<EquationMode, EquationSuitability>
}

export interface EquationDraftParticipant extends CatalogSpecies {
  phase: EquationPhase | null
}

export interface EquationDraft {
  mode: EquationMode
  reactants: EquationDraftParticipant[]
  products: EquationDraftParticipant[]
}

export interface ReactionCandidateParticipant {
  role: string
  coefficient: number | string
  speciesId: string | null
  applicationTargetId: string | null
  targetType: 'ion' | 'substance' | null
  nonSpeciesRef: string | null
  nameZh: string | null
  formula: string | null
  charge: number | null
  phase: EquationPhase | null
}

export interface ReactionCandidate {
  consolidatedId: string
  applicationReactionId: string | null
  nameZh: string
  materializationState: 'materialized' | 'catalog_only'
  participants: ReactionCandidateParticipant[]
  equation: string | null
  reversible: boolean | null
  reactionTypes: string[]
  conditions: string[]
  provenanceRefs: string[]
  sourcePackage: string
  sourceId: string
  orientation: 'canonical' | 'reverse'
  matchedAnchorCount: number
  completionRatio: number
  missingParticipantCount: number
}

export interface CatalogReactionEntry {
  consolidatedId: string
  applicationReactionId: string | null
  nameZh: string
  materializationState: 'materialized' | 'catalog_only'
  participants: ReactionCandidateParticipant[]
  equation: string | null
  reversible: boolean | null
  reactionTypes: string[]
  conditions: string[]
  provenanceRefs: string[]
  sourcePackage: string
  sourceId: string
}

export interface CatalogReactionKnowledge {
  consolidatedId: string
  applicationId: string
  sourceType: 'concept' | 'phenomenon'
  displayNameZh: string
  teachingPriority: string
  contentZh: string
  relatedReactionIds: string[]
  relatedSpeciesIds: string[]
}

export interface CatalogRelatedSpecies extends CatalogSpecies {
  structureAvailable: boolean
}

export interface CatalogSourceAttribution {
  name: string
  url: string | null
}

export interface CatalogReactionDetail extends CatalogReactionEntry {
  concepts: CatalogReactionKnowledge[]
  phenomena: CatalogReactionKnowledge[]
  relatedSpecies: CatalogRelatedSpecies[]
  sources: CatalogSourceAttribution[]
}

export interface ReactionCandidateQuery {
  reactantApplicationIds: string[]
  productApplicationIds: string[]
}

export interface CatalogSpeciesQuery {
  query?: string
  applicationIds?: string[]
  primaryCategory?: string
  equationMode: EquationMode
  composition?: Record<string, number>
  charge?: number
  entityKind?: 'ion' | 'substance'
  limit?: number
}

export interface CatalogCompletionQuery {
  composition: Record<string, number>
  equationMode?: EquationMode
  entityKind?: 'ion' | 'substance'
  limit?: number
}

export interface BuilderBlock {
  id: string
  label: string
  formula: string
  composition: Record<string, number>
  charge: number
  kind: 'element' | 'ion'
}

export interface BuilderTrayEntry {
  block: BuilderBlock
  count: number
}

export interface BuilderResolution {
  composition: Record<string, number>
  totalCharge: number
  entityKind: 'ion' | 'substance'
}

export interface EquationTerm {
  formula: string
  coefficient: number
  phase: string | null
  charge: number
}

export interface ConservationRow {
  element: string
  reactants: number
  products: number
  conserved: boolean
}

export interface BalanceEquationResponse {
  state: 'balanced' | 'no_net_ionic'
  inputState: 'balanced' | 'unbalanced' | 'not_applicable'
  mode: EquationMode
  formattedEquation: string
  coefficients: number[]
  reactants: EquationTerm[]
  products: EquationTerm[]
  conservation: {
    elements: ConservationRow[]
    charge: {
      reactants: number
      products: number
      conserved: boolean
    } | null
  }
  message: string | null
  phenomenon: string | null
  redox: {
    state: 'not_inferred'
    message: string
  }
}

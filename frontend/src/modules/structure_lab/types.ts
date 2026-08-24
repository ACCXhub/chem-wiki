export type StructureInputFormat = 'smiles' | 'molblock'

export interface StructureDescriptors {
  molecularWeight: number
  exactMass: number
  heavyAtomCount: number
  hydrogenBondDonors: number
  hydrogenBondAcceptors: number
  rotatableBondCount: number
  formalCharge: number
}

export interface AtomCoordinate {
  atomIndex: number
  x: number
  y: number
}

export interface StructureDepiction {
  format: 'svg'
  svg: string
  width: number
  height: number
  atomCoordinates: AtomCoordinate[]
}

export interface StructureConformer {
  state: 'available' | 'unavailable'
  format: 'mol'
  molBlock: string | null
  reason: string | null
}

export interface FunctionalGroupDetection {
  functionalGroupId: string
  key: string
  nameZh: string
  nameEn: string
  smarts: string
  patternSource: string
  occurrences: Array<{ atomIndices: number[] }>
}

export interface AnalyzeStructureResponse {
  state: 'valid' | 'invalid' | 'unsupported'
  inputFormat: string
  structureId: string | null
  canonicalSmiles: string | null
  formula: string | null
  descriptors: StructureDescriptors | null
  depiction: StructureDepiction | null
  conformer: StructureConformer | null
  functionalGroups: FunctionalGroupDetection[]
  code: string | null
  message: string | null
}

export interface StructureEditorProps {
  value: string
  onChange: (value: string) => void
  onError?: (message: string) => void
}

export interface MoleculeViewer3DProps {
  molBlock: string
}

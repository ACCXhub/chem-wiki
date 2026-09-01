import { act, fireEvent, render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'

import { StructureLabView } from './StructureLab'
import type { AnalyzeStructureResponse, CatalogStructureExploration } from './types'


const validResult: AnalyzeStructureResponse = {
  state: 'valid',
  inputFormat: 'smiles',
  structureId: '61f642c8-cf6e-4cbf-8b29-bca13461e555',
  canonicalSmiles: 'CCO',
  formula: 'C2H6O',
  descriptors: {
    molecularWeight: 46.069,
    exactMass: 46.0419,
    heavyAtomCount: 3,
    hydrogenBondDonors: 1,
    hydrogenBondAcceptors: 1,
    rotatableBondCount: 0,
    formalCharge: 0,
  },
  depiction: {
    format: 'svg',
    svg: '<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"></svg>',
    width: 600,
    height: 420,
    atomCoordinates: [
      { atomIndex: 0, x: 100, y: 210 },
      { atomIndex: 1, x: 300, y: 210 },
      { atomIndex: 2, x: 500, y: 210 },
    ],
  },
  conformer: { state: 'available', format: 'mol', molBlock: 'ethanol V2000', reason: null },
  functionalGroups: [
    {
      functionalGroupId: '206a72f6-1c27-54c7-a74b-9907511a59dd',
      key: 'alcohol',
      nameZh: '醇羟基',
      nameEn: 'alcohol',
      smarts: '[O;H1]',
      patternSource: 'RDKit Functional_Group_Hierarchy.txt',
      occurrences: [{ atomIndices: [2] }],
    },
  ],
  structuralTeaching: null,
  code: null,
  message: null,
}

test('presents H2O as one species with switchable phase-specific learning context', async () => {
  render(
    <StructureLabView
      onBack={() => undefined}
      onAnalyze={() => Promise.resolve(validResult)}
      catalogExploration={{
        species: {
          consolidatedId: 'species:water', applicationId: 'water', entityKind: 'substance',
          nameZh: '水', nameEn: 'water', formula: 'H2O', charge: 0, composition: { H: 2, O: 1 },
          aliases: [], chemicalClassifications: [], primaryCategory: 'inorganic', tags: [],
          defaultPriority: 'core', defaultPaletteRank: 1, equationModes: {},
        },
        structure: null, knowledge: [], relatedSpecies: [], relatedReactions: [],
      }}
      phaseContext={{
        consolidatedSpeciesId: 'species:water', applicationSpeciesId: 'water',
        phaseFact: {
          standardPhase: 'l', allowedTeachingPhases: ['s', 'l', 'g'],
          thermochemistryAvailablePhases: ['l', 'g'], phaseConditions: [
            { phase: 's', thermochemistry_available_at_reference: false },
            { phase: 'l', thermochemistry_available_at_reference: true },
            { phase: 'g', thermochemistry_available_at_reference: true },
          ], referenceTemperatureK: 298.15, standardPressureBar: 1,
        },
        thermochemistry: [
          { phase: 'l', temperatureK: 298.15, standardPressureBar: 1, deltaFHKjMol: -285.828371 },
          { phase: 'g', temperatureK: 298.15, standardPressureBar: 1, deltaFHKjMol: -241.824622 },
        ],
        phaseTransitions: [
          { transition: 'fusion', fromPhase: 's', toPhase: 'l', enthalpyKjMol: 5.9954, transitionTemperatureK: 273.15 },
          { transition: 'vaporization', fromPhase: 'l', toPhase: 'g', enthalpyKjMol: 40.8779, transitionTemperatureK: 373.15 },
        ],
      }}
      EditorComponent={() => <div />}
      Viewer3DComponent={() => <div />}
    />,
  )

  expect(screen.getByText('物态')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: '液态 (l)' })).toHaveAttribute('aria-pressed', 'true')
  expect(screen.getByText('ΔfH° −285.828 kJ/mol')).toBeInTheDocument()
  expect(screen.getByText('汽化')).toBeInTheDocument()

  fireEvent.click(screen.getByRole('button', { name: '固态 (s)' }))
  expect(screen.getByText('该物态暂无参考条件下的热化学数据。')).toBeInTheDocument()

  fireEvent.click(screen.getByRole('button', { name: '气态 (g)' }))
  expect(screen.getByText('ΔfH° −241.825 kJ/mol')).toBeInTheDocument()
  expect(screen.getByText('汽化')).toBeInTheDocument()
})

test('analyzes an edited structure and links functional groups to 2D and 3D views', async () => {
  const onAnalyze = vi.fn(() => Promise.resolve(validResult))
  render(
    <StructureLabView
      onBack={() => undefined}
      onAnalyze={onAnalyze}
      EditorComponent={({ value, onChange }) => (
        <textarea aria-label="结构编辑器" value={value} onChange={(event) => onChange(event.target.value)} />
      )}
      Viewer3DComponent={({ molBlock }) => <div>3D model: {molBlock}</div>}
    />,
  )

  fireEvent.change(screen.getByRole('textbox', { name: '结构编辑器' }), {
    target: { value: 'CCO' },
  })
  fireEvent.click(screen.getByRole('button', { name: '分析结构' }))

  expect(onAnalyze).toHaveBeenCalledWith('smiles', 'CCO')
  expect(await screen.findByText('C₂H₆O')).toBeInTheDocument()
  expect(screen.getByText('46.069 g/mol')).toBeInTheDocument()
  expect(screen.getByRole('img', { name: '乙醇的二维结构' })).toBeInTheDocument()
  expect(screen.getByText('3D model: ethanol V2000')).toBeInTheDocument()

  fireEvent.mouseEnter(screen.getByRole('button', { name: /醇羟基/ }))
  expect(document.querySelector('[data-highlighted-atom="2"]')).toBeInTheDocument()
  expect(screen.queryByText('RDKit Functional_Group_Hierarchy.txt')).not.toBeInTheDocument()
  expect(screen.getByText('结构分析范围')).toBeInTheDocument()
})

test('keeps loading and unsupported chemistry states explicit', async () => {
  let resolveAnalysis!: (result: AnalyzeStructureResponse) => void
  const onAnalyze = vi.fn(() => new Promise<AnalyzeStructureResponse>((resolve) => {
    resolveAnalysis = resolve
  }))
  render(
    <StructureLabView
      onBack={() => undefined}
      onAnalyze={onAnalyze}
      EditorComponent={({ value, onChange }) => (
        <textarea aria-label="结构编辑器" value={value} onChange={(event) => onChange(event.target.value)} />
      )}
      Viewer3DComponent={() => <div>unexpected viewer</div>}
    />,
  )

  fireEvent.click(screen.getByRole('button', { name: '分析结构' }))
  expect(screen.getByRole('button', { name: '正在分析…' })).toBeDisabled()
  expect(screen.getByText('RDKit 正在验证并生成构象…')).toBeInTheDocument()

  await act(async () => resolveAnalysis({
    state: 'unsupported',
    inputFormat: 'inchi',
    structureId: null,
    canonicalSmiles: null,
    formula: null,
    descriptors: null,
    depiction: null,
    conformer: null,
    functionalGroups: [],
    structuralTeaching: null,
    code: 'unsupported_format',
    message: '当前仅支持 SMILES 与 molfile 结构输入',
  }))

  expect(screen.getByRole('alert')).toHaveTextContent('暂不支持该表示')
  expect(screen.getByRole('alert')).toHaveTextContent('当前仅支持 SMILES 与 molfile 结构输入')
  expect(screen.queryByText('unexpected viewer')).not.toBeInTheDocument()
})

test('shows a failed analysis request as a service error', async () => {
  render(
    <StructureLabView
      onBack={() => undefined}
      onAnalyze={() => Promise.reject(new Error('化学引擎暂不可用'))}
      EditorComponent={({ value, onChange }) => (
        <textarea aria-label="结构编辑器" value={value} onChange={(event) => onChange(event.target.value)} />
      )}
      Viewer3DComponent={() => <div />}
    />,
  )

  fireEvent.click(screen.getByRole('button', { name: '分析结构' }))

  expect(await screen.findByRole('alert')).toHaveTextContent('化学引擎暂不可用')
})

test('isolates a failed chemistry editor and keeps the SMILES fallback usable', () => {
  const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined)
  const BrokenEditor = () => {
    throw new Error('editor chunk failed')
  }

  render(
    <StructureLabView
      onBack={() => undefined}
      onAnalyze={() => Promise.resolve(validResult)}
      EditorComponent={BrokenEditor}
      Viewer3DComponent={() => <div />}
    />,
  )

  expect(screen.getByRole('status')).toHaveTextContent(
    '结构编辑器加载失败，可继续使用 SMILES 输入',
  )
  expect(screen.getByLabelText('SMILES')).toBeEnabled()
  consoleError.mockRestore()
})

test('presents catalog-linked ethene as a structure learning loop with its real reaction', async () => {
  const onNavigate = vi.fn()
  const etheneResult: AnalyzeStructureResponse = {
    ...validResult,
    canonicalSmiles: 'C=C',
    formula: 'C2H4',
    structuralTeaching: {
      primary: { key: 'carbon_carbon_double_bond', atomIndices: [0, 1], value: null },
      observations: [
        { key: 'sp2_hybridization', atomIndices: [0, 1], value: null },
        { key: 'trigonal_planar_geometry', atomIndices: [0, 1], value: null },
        { key: 'ideal_bond_angle', atomIndices: [0, 1], value: 120 },
        { key: 'approximately_planar_skeleton', atomIndices: [0, 1], value: null },
      ],
    },
    functionalGroups: [{
      ...validResult.functionalGroups[0],
      key: 'alkene',
      nameZh: '碳碳双键',
      nameEn: 'alkene',
    }],
  }
  const catalogExploration: CatalogStructureExploration = {
    species: {
      consolidatedId: 'species:ethene', applicationId: 'ethene', entityKind: 'substance',
      nameZh: '乙烯', nameEn: 'ethene', formula: 'C2H4', charge: 0,
      composition: { C: 2, H: 4 }, aliases: [], chemicalClassifications: ['alkene'],
      primaryCategory: 'organic', tags: [], defaultPriority: 'core', defaultPaletteRank: 1,
      equationModes: { molecular: 'recommended', ionic: 'deemphasized', netIonic: 'deemphasized' },
    },
    structure: {
      applicationSpeciesId: 'ethene', publishedStructureId: 'structure:ethene', structureScope: 'molecule',
      canonicalSmiles: 'C=C', isomericSmiles: 'C=C', molecularFormula: 'C2H4', formalCharge: 0,
    },
    knowledge: [{
      consolidatedId: 'knowledge:ethene', sourceType: 'molecular_example', displayNameZh: '乙烯', contentZh: null,
      payload: { molecular_geometry: 'planar_molecule', central_hybridization_model: 'sp2', representative_bond_angle_deg: 120 },
    }],
    relatedSpecies: [{
      consolidatedId: 'species:ethane', applicationId: 'ethane', entityKind: 'substance',
      nameZh: '乙烷', nameEn: 'ethane', formula: 'C2H6', charge: 0,
      composition: { C: 2, H: 6 }, aliases: [], chemicalClassifications: ['alkane'],
      primaryCategory: 'organic', tags: [], defaultPriority: 'core', defaultPaletteRank: 2,
      equationModes: { molecular: 'recommended', ionic: 'deemphasized', netIonic: 'deemphasized' },
      structureAvailable: true,
    }],
    relatedReactions: [{
      consolidatedId: 'reaction:ethene-hydrogenation', nameZh: '乙烯催化加氢', materializationState: 'materialized', reactionTypes: ['addition'],
      conditions: ['催化剂'], equation: 'C2H4 + H2 -> C2H6',
    }],
  }

  render(
    <StructureLabView
      onBack={() => undefined}
      onNavigate={onNavigate}
      onAnalyze={() => Promise.resolve(etheneResult)}
      initialSmiles="C=C"
      catalogExploration={catalogExploration}
      phaseContext={{
        consolidatedSpeciesId: 'species:ethene', applicationSpeciesId: 'ethene',
        phaseFact: {
          standardPhase: 'g', allowedTeachingPhases: ['g'], thermochemistryAvailablePhases: ['g'],
          phaseConditions: [{ phase: 'g', thermochemistry_available_at_reference: true }],
          referenceTemperatureK: 298.15, standardPressureBar: 1,
        },
        thermochemistry: [{ phase: 'g', temperatureK: 298.15, standardPressureBar: 1, deltaFHKjMol: 52.499701 }],
        phaseTransitions: [],
      }}
      EditorComponent={({ value, onChange }) => <textarea aria-label="结构编辑器" value={value} onChange={(event) => onChange(event.target.value)} />}
      Viewer3DComponent={() => <div>3D model</div>}
    />,
  )

  expect(await screen.findByRole('heading', { name: '乙烯' })).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'C=C' })).toBeInTheDocument()
  expect(screen.getByText('碳碳双键是烯烃的特征结构。')).toBeInTheDocument()
  expect(screen.getByText('sp² 杂化')).toBeInTheDocument()
  expect(screen.getByText('分子骨架近似平面')).toBeInTheDocument()
  expect(screen.getByText('气态 (g)')).toBeInTheDocument()
  expect(screen.queryByRole('group', { name: '可用物态' })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: '在方程实验室中查看乙烯催化加氢' }))
  expect(onNavigate).toHaveBeenCalledWith('/equation-lab?reaction=reaction%3Aethene-hydrogenation')
})

test('keeps a catalog species without an accepted structure out of the free-form result view', () => {
  const onAnalyze = vi.fn(() => Promise.resolve(validResult))
  render(
    <StructureLabView
      onBack={() => undefined}
      onAnalyze={onAnalyze}
      catalogExploration={{
        species: {
          consolidatedId: 'species:aluminium-nitrate', applicationId: 'aluminium-nitrate', entityKind: 'substance',
          nameZh: '硝酸铝', nameEn: null, formula: 'Al(NO3)3', charge: 0, composition: null, aliases: [], chemicalClassifications: ['salt'],
          primaryCategory: 'salt', tags: [], defaultPriority: 'common', defaultPaletteRank: 1,
          equationModes: { molecular: 'available', ionic: 'available', netIonic: 'available' },
        },
        structure: null, knowledge: [], relatedSpecies: [], relatedReactions: [],
      }}
      EditorComponent={() => <div>编辑器不应显示</div>}
      Viewer3DComponent={() => <div />}
    />,
  )

  expect(screen.getByRole('heading', { name: '硝酸铝' })).toBeInTheDocument()
  expect(screen.getByText('暂无可用的已确认结构')).toBeInTheDocument()
  expect(screen.getByText('暂无可用的物态信息')).toBeInTheDocument()
  expect(screen.queryByText('编辑器不应显示')).not.toBeInTheDocument()
  expect(onAnalyze).not.toHaveBeenCalled()
})

import { act, fireEvent, render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'

import { StructureLabView } from './StructureLab'
import type { AnalyzeStructureResponse } from './types'


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
  code: null,
  message: null,
}

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
  expect(screen.getByText('RDKit Functional_Group_Hierarchy.txt')).toBeInTheDocument()
  expect(screen.getByText('不构造反应，也不推断机理')).toBeInTheDocument()
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
    'Ketcher 编辑器加载失败，可继续使用 SMILES 输入',
  )
  expect(screen.getByLabelText('SMILES')).toBeEnabled()
  consoleError.mockRestore()
})

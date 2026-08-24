import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { Ketcher } from 'ketcher-core'
import { Editor, type ButtonsConfig } from 'ketcher-react'
import 'ketcher-react/dist/index.css'
import { StandaloneStructServiceProvider } from 'ketcher-standalone'

import type { StructureEditorProps } from '../types'


const M06_BUTTONS: ButtonsConfig = {
  analyse: { hidden: true },
  check: { hidden: true },
  miew: { hidden: true },
  'reaction-plus': { hidden: true },
  arrows: { hidden: true },
  'reaction-mapping-tools': { hidden: true },
  'reaction-automap': { hidden: true },
  'reaction-map': { hidden: true },
  'reaction-unmap': { hidden: true },
  sgroup: { hidden: true },
  rgroup: { hidden: true },
  'rgroup-label': { hidden: true },
  'rgroup-fragment': { hidden: true },
  'rgroup-attpoints': { hidden: true },
  'create-monomer': { hidden: true },
}


export default function KetcherEditor({ value, onChange, onError }: StructureEditorProps) {
  const provider = useMemo(() => new StandaloneStructServiceProvider(), [])
  const ketcherRef = useRef<Ketcher | null>(null)
  const onChangeRef = useRef(onChange)
  const onErrorRef = useRef(onError)
  const appliedValueRef = useRef('')
  const [ready, setReady] = useState(false)

  useEffect(() => {
    onChangeRef.current = onChange
    onErrorRef.current = onError
  }, [onChange, onError])

  const readStructure = useCallback(async () => {
    const ketcher = ketcherRef.current
    if (!ketcher) return
    try {
      const smiles = await ketcher.getSmiles()
      if (smiles && smiles !== appliedValueRef.current) {
        appliedValueRef.current = smiles
        onChangeRef.current(smiles)
      }
    } catch {
      onErrorRef.current?.('Ketcher 暂时无法导出当前结构')
    }
  }, [])

  const handleInit = useCallback((ketcher: Ketcher) => {
    ketcherRef.current = ketcher
    ketcher.changeEvent.add(readStructure)
    setReady(true)
  }, [readStructure])

  useEffect(() => {
    const ketcher = ketcherRef.current
    const normalized = value.trim()
    if (!ketcher || !ready || !normalized || normalized === appliedValueRef.current) return
    appliedValueRef.current = normalized
    void ketcher.setMolecule(normalized).catch(() => {
      onErrorRef.current?.('Ketcher 无法载入该结构文本')
    })
  }, [ready, value])

  useEffect(() => () => {
    ketcherRef.current?.changeEvent.remove(readStructure)
  }, [readStructure])

  return (
    <div className="structure-ketcher" data-ready={ready}>
      {!ready ? <p className="structure-adapter-loading">正在启动 Ketcher…</p> : null}
      <Editor
        staticResourcesUrl=""
        structServiceProvider={provider}
        onInit={handleInit}
        errorHandler={(message) => onErrorRef.current?.(message)}
        buttons={M06_BUTTONS}
        disableMacromoleculesEditor
      />
    </div>
  )
}

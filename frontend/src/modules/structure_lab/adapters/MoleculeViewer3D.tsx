import { useEffect, useRef } from 'react'
import { createViewer } from '3dmol'

import type { MoleculeViewer3DProps } from '../types'


export default function MoleculeViewer3D({ molBlock }: MoleculeViewer3DProps) {
  const hostRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const host = hostRef.current
    if (!host) return
    host.classList.remove('is-error')
    host.removeAttribute('role')
    host.replaceChildren()
    try {
      const viewer = createViewer(host, { backgroundColor: '#081713', antialias: true })
      viewer.addModel(molBlock, 'mol')
      viewer.setStyle({}, {
        stick: { radius: 0.16, colorscheme: 'Jmol' },
        sphere: { scale: 0.28, colorscheme: 'Jmol' },
      })
      viewer.zoomTo()
      viewer.render()
      viewer.zoom(1.12, 250)
      return () => {
        viewer.removeAllModels()
        viewer.clear()
        host.replaceChildren()
      }
    } catch {
      host.classList.add('is-error')
      host.setAttribute('role', 'status')
      host.textContent = '当前浏览器无法启动 3Dmol.js，二维结构仍可使用'
    }
  }, [molBlock])

  return <div ref={hostRef} className="structure-viewer-3d" aria-label="可旋转的三维分子模型" />
}

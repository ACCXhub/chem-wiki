import { Suspense, lazy, useCallback, useEffect, useState } from 'react'

import ElementWiki from '../modules/element_wiki'
import EquationLab from '../modules/equation_lab'
import PeriodicTable from '../modules/periodic_table'
import './App.css'


const StructureLab = lazy(() => import('../modules/structure_lab'))


function elementIdFromPath(pathname: string): string | null {
  const match = /^\/elements\/([^/]+)$/.exec(pathname)
  return match ? decodeURIComponent(match[1]) : null
}

function App() {
  const [pathname, setPathname] = useState(() => window.location.pathname)

  useEffect(() => {
    const handlePopState = () => setPathname(window.location.pathname)
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  const navigate = useCallback((nextPath: string) => {
    window.history.pushState(null, '', nextPath)
    setPathname(nextPath)
  }, [])

  const elementId = elementIdFromPath(pathname)
  if (pathname === '/equation-lab') {
    return <EquationLab onBack={() => navigate('/')} />
  }
  if (pathname === '/structure-lab') {
    return (
      <Suspense fallback={<main className="app-route-loading">正在打开结构实验室…</main>}>
        <StructureLab onBack={() => navigate('/')} />
      </Suspense>
    )
  }
  if (elementId) {
    return <ElementWiki elementId={elementId} onBack={() => navigate('/')} />
  }
  return (
    <>
      <nav className="lab-entry-cluster" aria-label="实验室入口">
        <button className="structure-lab-entry" type="button" onClick={() => navigate('/structure-lab')}>
          结构实验室
        </button>
        <button className="equation-lab-entry" type="button" onClick={() => navigate('/equation-lab')}>
          方程实验室
        </button>
      </nav>
      <PeriodicTable onElementSelect={(id) => navigate(`/elements/${id}`)} />
    </>
  )
}

export default App

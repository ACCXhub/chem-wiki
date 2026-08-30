import { Suspense, lazy, useCallback, useEffect, useState } from 'react'

import ElementWiki from '../modules/element_wiki'
import EquationLab from '../modules/equation_lab'
import PeriodicTable from '../modules/periodic_table'
import AppearanceControl from './AppearanceControl'
import './App.css'


const StructureLab = lazy(() => import('../modules/structure_lab'))


function elementIdFromPath(pathname: string): string | null {
  const match = /^\/elements\/([^/]+)$/.exec(pathname)
  return match ? decodeURIComponent(match[1]) : null
}

function App() {
  const [locationKey, setLocationKey] = useState(
    () => `${window.location.pathname}${window.location.search}`,
  )

  useEffect(() => {
    const handlePopState = () => setLocationKey(`${window.location.pathname}${window.location.search}`)
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  const navigate = useCallback((nextPath: string) => {
    window.history.pushState(null, '', nextPath)
    setLocationKey(nextPath)
  }, [])

  const location = new URL(locationKey, window.location.origin)
  const pathname = location.pathname
  const elementId = elementIdFromPath(pathname)
  if (pathname === '/equation-lab') {
    return (
      <>
        <div className="global-appearance"><AppearanceControl /></div>
        <EquationLab
          onBack={() => navigate('/')}
          onNavigate={navigate}
          reactionId={location.searchParams.get('reaction')}
        />
      </>
    )
  }
  if (pathname === '/structure-lab') {
    return (
      <>
        <div className="global-appearance"><AppearanceControl /></div>
        <Suspense fallback={<main className="app-route-loading">正在打开结构实验室…</main>}>
          <StructureLab onBack={() => navigate('/')} speciesId={location.searchParams.get('species')} />
        </Suspense>
      </>
    )
  }
  if (elementId) {
    return (
      <>
        <div className="global-appearance"><AppearanceControl /></div>
        <ElementWiki elementId={elementId} onBack={() => navigate('/')} onNavigate={navigate} />
      </>
    )
  }
  return (
    <>
      <nav className="lab-entry-cluster" aria-label="学习工具">
        <AppearanceControl />
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

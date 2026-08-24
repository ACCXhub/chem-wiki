import { useCallback, useEffect, useState } from 'react'

import ElementWiki from '../modules/element_wiki'
import EquationLab from '../modules/equation_lab'
import PeriodicTable from '../modules/periodic_table'


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
  if (elementId) {
    return <ElementWiki elementId={elementId} onBack={() => navigate('/')} />
  }
  return (
    <>
      <button className="equation-lab-entry" type="button" onClick={() => navigate('/equation-lab')}>
        方程实验室
      </button>
      <PeriodicTable onElementSelect={(id) => navigate(`/elements/${id}`)} />
    </>
  )
}

export default App

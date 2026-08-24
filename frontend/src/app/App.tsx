import { useCallback, useEffect, useState } from 'react'

import ElementWiki from '../modules/element_wiki'
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
  if (elementId) {
    return <ElementWiki elementId={elementId} onBack={() => navigate('/')} />
  }
  return <PeriodicTable onElementSelect={(id) => navigate(`/elements/${id}`)} />
}

export default App

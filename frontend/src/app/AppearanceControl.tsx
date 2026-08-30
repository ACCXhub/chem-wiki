import { useEffect, useState } from 'react'

import {
  applyAppearance,
  persistAppearance,
  savedAppearance,
  type AppearanceMode,
} from './appearance'

const OPTIONS: readonly { mode: AppearanceMode; label: string }[] = [
  { mode: 'light', label: '明亮' },
  { mode: 'dark', label: '深色' },
  { mode: 'system', label: '跟随系统' },
]

export default function AppearanceControl() {
  const [mode, setMode] = useState<AppearanceMode>(() => savedAppearance())
  const [isOpen, setIsOpen] = useState(false)

  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const update = () => applyAppearance(mode, document.documentElement, media.matches)
    update()
    if (mode !== 'system') return undefined
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [mode])

  function selectMode(nextMode: AppearanceMode) {
    setMode(nextMode)
    persistAppearance(nextMode)
    setIsOpen(false)
  }

  return (
    <div className="appearance-control">
      <button
        type="button"
        className="appearance-trigger"
        aria-label="切换外观"
        aria-expanded={isOpen}
        aria-controls="appearance-options"
        onClick={() => setIsOpen((open) => !open)}
      >
        <span aria-hidden="true">◐</span>
        <span>外观</span>
      </button>
      {isOpen ? (
        <div id="appearance-options" className="appearance-menu" role="menu" aria-label="外观">
          {OPTIONS.map((option) => (
            <button
              key={option.mode}
              type="button"
              role="menuitemradio"
              aria-checked={mode === option.mode}
              onClick={() => selectMode(option.mode)}
            >
              <span aria-hidden="true">{mode === option.mode ? '●' : '○'}</span>
              {option.label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  )
}

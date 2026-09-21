import { useRef } from 'react'
import { cn } from './cn'
import { useOverlay } from './useOverlay'

/**
 * Slide-over panel for mobile navigation. Focus-trapped, Esc-to-close,
 * scroll-locked (see useOverlay). `side` is 'left' or 'right'.
 */
export default function Drawer({ open, onClose, side = 'left', label = 'Drawer', className, children }) {
  const panelRef = useRef(null)
  useOverlay(open, onClose, panelRef)

  if (!open) return null

  const position = side === 'right' ? 'right-0' : 'left-0'

  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-slate-900/40" onClick={onClose} aria-hidden="true" />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={label}
        tabIndex={-1}
        className={cn(
          'absolute inset-y-0 flex w-64 max-w-[85vw] flex-col border-line bg-surface shadow-pop',
          side === 'right' ? 'border-l' : 'border-r',
          position,
          className
        )}
      >
        {children}
      </div>
    </div>
  )
}

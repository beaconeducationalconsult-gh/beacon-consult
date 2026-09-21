import { useId, useRef } from 'react'
import { cn } from './cn'
import { useOverlay } from './useOverlay'

/**
 * Generic modal dialog: backdrop, focus trap, Esc-to-close, scroll lock and
 * focus restore (see useOverlay). Labelled by `title` when provided.
 */
export default function Modal({ open, onClose, title, children, footer, size = 'md', className }) {
  const panelRef = useRef(null)
  const titleId = useId()
  useOverlay(open, onClose, panelRef)

  if (!open) return null

  const width = size === 'sm' ? 'max-w-sm' : size === 'lg' ? 'max-w-2xl' : 'max-w-md'

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-slate-900/50" onClick={onClose} aria-hidden="true" />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? titleId : undefined}
        tabIndex={-1}
        className={cn('relative w-full rounded-2xl border border-line-2 bg-surface p-6 shadow-pop', width, className)}
      >
        {title && (
          <h2 id={titleId} className="text-lg font-semibold text-heading">
            {title}
          </h2>
        )}
        <div className={cn(title && 'mt-2')}>{children}</div>
        {footer && <div className="mt-6 flex justify-end gap-3">{footer}</div>}
      </div>
    </div>
  )
}

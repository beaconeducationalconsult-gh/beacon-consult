import { createContext, useContext, useEffect, useId, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { cn } from './cn'

const MenuContext = createContext({ close() {} })

const ITEM =
  'flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-text transition-colors hover:bg-surface-2 hover:text-heading'

/**
 * Accessible dropdown menu. `trigger` is a render prop receiving
 * `{ open, toggle, ref, ariaProps }` so any element can be the trigger.
 * Closes on outside click, Escape and item activation; arrow keys move between
 * items; focus returns to the trigger on close.
 */
export default function Menu({ trigger, children, align = 'right', panelClassName }) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef(null)
  const triggerRef = useRef(null)
  const panelId = useId()

  const close = () => setOpen(false)

  useEffect(() => {
    if (!open) return
    const onPointerDown = (e) => {
      if (!rootRef.current?.contains(e.target)) close()
    }
    const onKeyDown = (e) => {
      if (e.key === 'Escape') {
        close()
        triggerRef.current?.focus()
        return
      }
      if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp' && e.key !== 'Home' && e.key !== 'End') return
      const items = [...rootRef.current.querySelectorAll('[role="menuitem"]')]
      if (!items.length) return
      e.preventDefault()
      const current = items.indexOf(document.activeElement)
      let next
      if (e.key === 'ArrowDown') next = (current + 1 + items.length) % items.length
      else if (e.key === 'ArrowUp') next = (current - 1 + items.length) % items.length
      else if (e.key === 'Home') next = 0
      else next = items.length - 1
      items[next]?.focus()
    }
    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  useEffect(() => {
    if (open) rootRef.current?.querySelector('[role="menuitem"]')?.focus()
  }, [open])

  return (
    <div ref={rootRef} className="relative">
      {trigger({
        open,
        toggle: () => setOpen((o) => !o),
        ref: triggerRef,
        ariaProps: { 'aria-haspopup': 'menu', 'aria-expanded': open, 'aria-controls': open ? panelId : undefined },
      })}
      {open && (
        <div
          id={panelId}
          role="menu"
          className={cn(
            'absolute z-40 mt-2 min-w-56 rounded-xl border border-line-2 bg-surface p-1 shadow-pop',
            align === 'right' ? 'right-0' : 'left-0',
            panelClassName
          )}
        >
          <MenuContext.Provider value={{ close }}>{children}</MenuContext.Provider>
        </div>
      )}
    </div>
  )
}

export function MenuItem({ to, href, onClick, icon, children }) {
  const { close } = useContext(MenuContext)
  const handle = (e) => {
    onClick?.(e)
    close()
  }
  if (to) return <Link to={to} role="menuitem" className={ITEM} onClick={handle}>{icon}{children}</Link>
  if (href) return <a href={href} role="menuitem" className={ITEM} onClick={handle}>{icon}{children}</a>
  return <button type="button" role="menuitem" className={ITEM} onClick={handle}>{icon}{children}</button>
}

export function MenuLabel({ children }) {
  return <p className="px-3 pb-1 pt-2 text-xs font-semibold uppercase tracking-wide text-subtle">{children}</p>
}

export function MenuDivider() {
  return <div className="my-1 h-px bg-line-2" role="separator" />
}

import { useEffect, useRef } from 'react'

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'

/**
 * Shared overlay behaviour for Modal and Drawer: locks scroll, moves focus in,
 * traps Tab within the panel, closes on Escape, and restores focus on unmount.
 * `containerRef` must point at the panel element that holds the focusables.
 */
export function useOverlay(open, onClose, containerRef) {
  const restoreTo = useRef(null)

  useEffect(() => {
    if (!open) return

    restoreTo.current = document.activeElement
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    const panel = containerRef.current
    const focusFirst = () => {
      const nodes = panel?.querySelectorAll(FOCUSABLE)
      if (nodes && nodes.length) nodes[0].focus()
      else panel?.focus()
    }
    // Focus after the panel mounts into the DOM.
    const raf = requestAnimationFrame(focusFirst)

    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.stopPropagation()
        onClose?.()
        return
      }
      if (event.key !== 'Tab' || !panel) return
      const nodes = [...panel.querySelectorAll(FOCUSABLE)].filter((el) => el.offsetParent !== null)
      if (!nodes.length) return
      const first = nodes[0]
      const last = nodes[nodes.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', onKeyDown)
    return () => {
      cancelAnimationFrame(raf)
      document.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = previousOverflow
      restoreTo.current?.focus?.()
    }
  }, [open, onClose, containerRef])
}

/** Join class names, dropping falsy values. Zero-dependency stand-in for clsx. */
export function cn(...classes) {
  return classes.filter(Boolean).join(' ')
}

import { useState } from 'react'

/*
 * Equivalent fractions and comparison, with strips (B4.1.3.1.2, B4.1.3.2.1).
 *
 * Two strips of equal length cut into different numbers of parts: line the
 * shaded parts up and "2/4 = 1/2" is something a pupil can see rather than be
 * told. The comparison underneath uses the cross-multiplication the indicator
 * expects once the pictures have made it obvious.
 */

const DENOMINATORS = [1, 2, 3, 4, 5, 6, 8, 10]

export default function FractionStripModel() {
  const [left, setLeft] = useState({ numerator: 1, denominator: 2 })
  const [right, setRight] = useState({ numerator: 2, denominator: 4 })

  const strip = (value, onChange, label, colour) => (
    <div>
      <div className="mb-1 flex items-center gap-2">
        <span className="label-caps">{label}</span>
        <input
          type="number"
          min="0"
          max={value.denominator}
          className="input w-16 py-1 text-center"
          value={value.numerator}
          onChange={(event) => onChange({ ...value, numerator: Math.max(0, Math.min(value.denominator, Number(event.target.value))) })}
          aria-label={`${label} numerator`}
        />
        <span className="text-slate-500">/</span>
        <select
          className="input w-20 py-1"
          value={value.denominator}
          onChange={(event) => {
            const denominator = Number(event.target.value)
            onChange({ denominator, numerator: Math.min(value.numerator, denominator) })
          }}
          aria-label={`${label} denominator`}
        >
          {DENOMINATORS.map((d) => <option key={d} value={d}>{d}</option>)}
        </select>
      </div>
      <div className="flex h-12 w-full overflow-hidden rounded border border-slate-300">
        {Array.from({ length: value.denominator }, (_, i) => (
          <div
            key={i}
            className="flex-1 border-r border-slate-300 last:border-r-0"
            style={{ backgroundColor: i < value.numerator ? colour : 'white' }}
          />
        ))}
      </div>
    </div>
  )

  const equal = left.numerator * right.denominator === right.numerator * left.denominator
  const leftBigger = left.numerator * right.denominator > right.numerator * left.denominator
  const simplify = ({ numerator, denominator }) => {
    const gcd = (a, b) => (b ? gcd(b, a % b) : a)
    const g = gcd(numerator, denominator) || 1
    return `${numerator / g}/${denominator / g}`
  }

  return (
    <div className="space-y-4">
      <p className="card-meta">
        Cut each strip into parts and shade some. Equivalent fractions are two different cuts that
        shade the same amount of the same length.
      </p>
      {strip(left, setLeft, 'Strip A', '#4f46e5')}
      {strip(right, setRight, 'Strip B', '#f59e0b')}

      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg bg-slate-50 p-3">
          <p className="label-caps">Which is more?</p>
          <p className="text-xl font-semibold text-slate-900">
            {left.numerator}/{left.denominator} {equal ? '=' : leftBigger ? '>' : '<'} {right.numerator}/{right.denominator}
          </p>
        </div>
        <div className="rounded-lg bg-slate-50 p-3">
          <p className="label-caps">Simplest form</p>
          <p className="text-sm text-slate-700">
            A = {simplify(left)} · B = {simplify(right)}
          </p>
        </div>
        <div className="rounded-lg bg-slate-50 p-3">
          <p className="label-caps">As decimals</p>
          <p className="text-sm text-slate-700">
            A = {(left.numerator / left.denominator).toFixed(2)} · B = {(right.numerator / right.denominator).toFixed(2)}
          </p>
        </div>
      </div>

      {equal && left.numerator !== right.numerator && (
        <p className="text-sm text-emerald-700">
          A and B are equivalent: {simplify(left)} and {simplify(right)} name the same amount.
        </p>
      )}
    </div>
  )
}

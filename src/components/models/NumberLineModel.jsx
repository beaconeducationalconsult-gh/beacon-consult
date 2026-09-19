import { useState } from 'react'

/*
 * Compare, order and round on one number line (B4.1.1.1.4, B4.1.1.1.5).
 *
 * Two markers the teacher drags; the model says which is bigger, writes the
 * sentence with `>`, `<` or `=`, and shows where each number sits relative to
 * the nearest thousand — which is exactly the hundred/thousand rounding the
 * indicator asks for.
 */

const CEILING = 10000

export default function NumberLineModel() {
  const [a, setA] = useState(3200)
  const [b, setB] = useState(7600)

  const symbol = a > b ? '>' : a < b ? '<' : '='
  const toNearest = (n, step) => Math.round(n / step) * step
  const percent = (n) => `${(n / CEILING) * 100}%`

  const marker = (value, onChange, label, colour) => (
    <div>
      <label className="label-caps" htmlFor={`nl-${label}`}>
        {label}: <span className="text-slate-900">{value.toLocaleString()}</span>
      </label>
      <input
        id={`nl-${label}`}
        type="range"
        min="0"
        max={CEILING}
        step="10"
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="w-full"
        style={{ accentColor: colour }}
      />
    </div>
  )

  return (
    <div>
      <div className="grid gap-3 sm:grid-cols-2">
        {marker(a, setA, 'A', '#4f46e5')}
        {marker(b, setB, 'B', '#f59e0b')}
      </div>

      <div className="relative mt-4 h-16">
        <div className="absolute top-6 h-0.5 w-full bg-slate-300" />
        {Array.from({ length: 11 }, (_, i) => (
          <div key={i} className="absolute top-4 text-center" style={{ left: percent(i * (CEILING / 10)) }}>
            <div className="mx-auto h-3 w-px bg-slate-400" />
            <span className="text-[10px] text-slate-500">{((i * CEILING) / 10).toLocaleString()}</span>
          </div>
        ))}
        {[{ v: a, c: '#4f46e5', label: 'A' }, { v: b, c: '#f59e0b', label: 'B' }].map(({ v, c, label }) => (
          <div key={label} className="absolute top-0 -translate-x-1/2 text-center" style={{ left: percent(v) }}>
            <span className="rounded px-1 text-xs font-semibold text-white" style={{ backgroundColor: c }}>
              {label}
            </span>
            <div className="mx-auto h-6 w-0.5" style={{ backgroundColor: c }} />
          </div>
        ))}
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg bg-slate-50 p-3">
          <p className="label-caps">Comparison</p>
          <p className="text-xl font-semibold text-slate-900">
            {a.toLocaleString()} {symbol} {b.toLocaleString()}
          </p>
          <p className="text-xs text-slate-500">
            {symbol === '=' ? 'The two numbers are equal.' : `A is ${Math.abs(a - b).toLocaleString()} ${a > b ? 'more' : 'less'} than B.`}
          </p>
        </div>
        <div className="rounded-lg bg-slate-50 p-3">
          <p className="label-caps">A rounded</p>
          <p className="text-sm text-slate-700">
            nearest ten: {toNearest(a, 10).toLocaleString()}<br />
            nearest hundred: {toNearest(a, 100).toLocaleString()}<br />
            nearest thousand: {toNearest(a, 1000).toLocaleString()}
          </p>
        </div>
        <div className="rounded-lg bg-slate-50 p-3">
          <p className="label-caps">B rounded</p>
          <p className="text-sm text-slate-700">
            nearest ten: {toNearest(b, 10).toLocaleString()}<br />
            nearest hundred: {toNearest(b, 100).toLocaleString()}<br />
            nearest thousand: {toNearest(b, 1000).toLocaleString()}
          </p>
        </div>
      </div>
    </div>
  )
}

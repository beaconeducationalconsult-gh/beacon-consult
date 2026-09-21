import { useState } from 'react'

/*
 * Factors by arranging counters (B4.1.1.3.1, B4.1.1.3.4, B4.1.1.3.6).
 *
 * A number of counters the teacher slides up and down; the model draws every
 * rectangle that uses all of them exactly once. The rows of dots *are* the
 * factor pairs, a number with a single rectangle is prime, and a square
 * rectangle is a square number — the three things the indicators ask for.
 */

const MAX = 36

function factorPairs(n) {
  const pairs = []
  for (let rows = 1; rows <= n; rows += 1) {
    if (n % rows === 0) pairs.push([rows, n / rows])
  }
  return pairs
}

export default function FactorArrayModel() {
  const [count, setCount] = useState(12)
  const pairs = factorPairs(count)
  const [rows, cols] = pairs[Math.min(pairs.length - 1, Math.floor((pairs.length - 1) / 2))] || [1, count]
  const factors = pairs.map(([r]) => r)

  return (
    <div>
      <label className="label-caps" htmlFor="fa-count">
        Counters: <span className="text-slate-900">{count}</span>
      </label>
      <input
        id="fa-count"
        type="range"
        min="2"
        max={MAX}
        value={count}
        onChange={(event) => setCount(Number(event.target.value))}
        className="w-full max-w-md"
      />

      <div className="mt-4 flex flex-wrap items-start gap-6">
        <div
          className="grid gap-1 rounded-lg bg-slate-50 p-3"
          style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}
          role="img"
          aria-label={`${count} counters arranged as ${rows} rows of ${cols}`}
        >
          {Array.from({ length: count }, (_, i) => (
            <span key={i} className="h-4 w-4 rounded-full bg-brand-600" />
          ))}
        </div>

        <div className="space-y-2 text-sm">
          <p>
            <span className="label-caps block">Rectangles</span>
            {pairs.map(([r, c]) => `${r} × ${c}`).join(', ')}
          </p>
          <p>
            <span className="label-caps block">Factors of {count}</span>
            {factors.join(', ')}
          </p>
          <p>
            <span className="label-caps block">This number is</span>
            {pairs.length === 1 ? 'prime — only one rectangle' : rows === cols ? 'a square number' : 'composite'}
          </p>
        </div>
      </div>
    </div>
  )
}

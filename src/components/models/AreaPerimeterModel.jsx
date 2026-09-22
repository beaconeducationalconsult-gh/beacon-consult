import { useState } from 'react'

/*
 * Perimeter and area on a grid (B4.3.3.1.3, B4.3.3.1.4, B4.3.3.2.1).
 *
 * A rectangle the teacher resizes: the perimeter walks the edge one unit at a
 * time, the area counts the square units inside — the two formulas the
 * indicators ask pupils to develop, rather than hand over. The fixed-perimeter
 * table underneath is the B4.3.3.1.4 question: which rectangles can you make
 * around the same fence?
 */

const UNIT = 22

export default function AreaPerimeterModel() {
  const [width, setWidth] = useState(5)
  const [height, setHeight] = useState(3)

  const perimeter = 2 * (width + height)
  const area = width * height

  const samePerimeter = Array.from({ length: Math.floor(perimeter / 2) }, (_, i) => {
    const w = i + 1
    return { width: w, height: perimeter / 2 - w }
  })

  return (
    <div>
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label className="label-caps" htmlFor="ap-w">Width: {width} cm</label>
          <input id="ap-w" type="range" min="1" max="12" value={width}
            onChange={(event) => setWidth(Number(event.target.value))} className="w-full" />
        </div>
        <div>
          <label className="label-caps" htmlFor="ap-h">Height: {height} cm</label>
          <input id="ap-h" type="range" min="1" max="12" value={height}
            onChange={(event) => setHeight(Number(event.target.value))} className="w-full" />
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-start gap-6">
        <div
          className="relative rounded border-t-2 border-l-2 border-brand-600 bg-brand-50 dark:bg-brand-500/20"
          style={{ width: width * UNIT, height: height * UNIT }}
          role="img"
          aria-label={`Rectangle ${width} cm by ${height} cm`}
        >
          {Array.from({ length: width * height }, (_, i) => (
            <span
              key={i}
              className="absolute border-r border-b border-brand-200 dark:border-brand-500/30"
              style={{
                width: UNIT, height: UNIT,
                left: (i % width) * UNIT,
                top: Math.floor(i / width) * UNIT,
              }}
            />
          ))}
        </div>

        <dl className="space-y-2 text-sm">
          <div>
            <dt className="label-caps">Perimeter</dt>
            <dd className="text-lg text-heading">
              2 × ({width} + {height}) = <strong>{perimeter} cm</strong>
            </dd>
          </div>
          <div>
            <dt className="label-caps">Area</dt>
            <dd className="text-lg text-heading">
              {width} × {height} = <strong>{area} square units</strong>
            </dd>
          </div>
          <div>
            <dt className="label-caps">Counted, not multiplied</dt>
            <dd className="text-text">
              {width} rows of {height}… that is {area} squares — the same as multiplying, which is
              the formula the class is deriving.
            </dd>
          </div>
        </dl>
      </div>

      <div className="mt-4 rounded-lg bg-surface-2 p-3">
        <p className="label-caps mb-2">Rectangles with a perimeter of {perimeter} cm</p>
        <div className="flex flex-wrap gap-2 text-sm text-text">
          {samePerimeter.map(({ width: w, height: h }) => (
            <button
              key={w}
              type="button"
              className={w === width ? 'chip-brand' : 'chip bg-surface'}
              onClick={() => { setWidth(w); setHeight(h) }}
            >
              {w} × {h} = {w * h} sq units
            </button>
          ))}
        </div>
        <p className="mt-2 text-xs text-muted">
          Every rectangle here uses the same fence. The square holds the most area.
        </p>
      </div>
    </div>
  )
}

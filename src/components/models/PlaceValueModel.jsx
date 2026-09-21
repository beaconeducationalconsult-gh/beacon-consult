import { useState } from 'react'

/*
 * Place value, the way it is taught with multi-base materials (B4.1.1.1.1).
 *
 * A six-digit frame the teacher fills digit by digit: each column shows the
 * digit's *value*, so "the 4 in 45,231" stops being a position and becomes
 * 40,000. The expanded form underneath is the sentence the syllabus asks pupils
 * to write, and the number name is there for B4.1.1.1.2.
 */

const COLUMNS = [
  ['hundred thousands', 100000],
  ['ten thousands', 10000],
  ['thousands', 1000],
  ['hundreds', 100],
  ['tens', 10],
  ['ones', 1],
]

const ONES = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine',
  'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen',
  'eighteen', 'nineteen']
const TENS = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']

function inWords(n) {
  if (n === 0) return 'zero'
  if (n < 20) return ONES[n]
  if (n < 100) return TENS[Math.floor(n / 10)] + (n % 10 ? `-${ONES[n % 10]}` : '')
  if (n < 1000) {
    return `${ONES[Math.floor(n / 100)]} hundred${n % 100 ? ` and ${inWords(n % 100)}` : ''}`
  }
  for (const [scale, word] of [[1000, 'thousand'], [1000000, 'million']]) {
    if (n < scale * 1000) {
      const rest = n % scale
      return `${inWords(Math.floor(n / scale))} ${word}${rest ? ` ${rest < 100 ? 'and ' : ''}${inWords(rest)}` : ''}`
    }
  }
  return String(n)
}

export default function PlaceValueModel() {
  const [digits, setDigits] = useState([0, 4, 5, 2, 3, 1])

  const setDigit = (index, value) =>
    setDigits((current) => current.map((d, i) => (i === index ? Math.max(0, Math.min(9, value)) : d)))

  const number = digits.reduce((total, digit, i) => total + digit * COLUMNS[i][1], 0)
  const expanded = digits
    .map((digit, i) => (digit ? `${digit} × ${COLUMNS[i][1].toLocaleString()}` : null))
    .filter(Boolean)
    .join(' + ') || '0'

  return (
    <div>
      <p className="card-meta mb-3">
        Set a digit in each column. Everything below follows — the value of each digit, the expanded
        form pupils write, and the number in words.
      </p>

      <div className="flex flex-wrap gap-2">
        {digits.map((digit, index) => (
          <div key={COLUMNS[index][0]} className="w-24">
            <label className="label-caps text-[10px]" htmlFor={`pv-${index}`}>{COLUMNS[index][0]}</label>
            <input
              id={`pv-${index}`}
              type="number"
              min="0"
              max="9"
              className="input text-center text-xl"
              value={digit}
              onChange={(event) => setDigit(index, Number(event.target.value))}
            />
            <p className="mt-1 text-center text-xs text-slate-500">
              value: {(digit * COLUMNS[index][1]).toLocaleString()}
            </p>
          </div>
        ))}
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg bg-slate-50 p-3">
          <p className="label-caps">Number</p>
          <p className="text-2xl font-semibold text-slate-900">{number.toLocaleString()}</p>
        </div>
        <div className="rounded-lg bg-slate-50 p-3 sm:col-span-2">
          <p className="label-caps">Expanded form</p>
          <p className="text-lg text-slate-800">{expanded}</p>
          <p className="mt-1 text-sm text-slate-600">In words: {inWords(number)}</p>
        </div>
      </div>
    </div>
  )
}

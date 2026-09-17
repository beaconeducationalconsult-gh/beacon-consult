/** Grade ids are KG1, KG2, B1…B9 — matching the curriculum JSON filenames. */
export const GRADES = ['KG1', 'KG2', 'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B9']

const LABELS = {
  KG1: 'KG 1',
  KG2: 'KG 2',
  B1: 'Basic 1',
  B2: 'Basic 2',
  B3: 'Basic 3',
  B4: 'Basic 4',
  B5: 'Basic 5',
  B6: 'Basic 6',
  B7: 'Basic 7',
  B8: 'Basic 8',
  B9: 'Basic 9',
}

export function gradeLabel(grade) {
  return LABELS[grade] || grade || ''
}

export function gradeBand(grade) {
  if (!grade) return ''
  if (grade.startsWith('KG')) return 'Kindergarten'
  const n = Number(String(grade).replace(/\D/g, ''))
  if (n <= 3) return 'Lower Primary'
  if (n <= 6) return 'Upper Primary'
  return 'Junior High School'
}

export const TERMS = [1, 2, 3]
export const termLabel = (term) => `Term ${term}`

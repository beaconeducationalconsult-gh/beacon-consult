// app/src/kernel/types.ts

export interface Indicator {
  code: string           // e.g. "B4.1.1.1.1"
  strand: string
  subStrand: string
  contentStandard: string
  text: string
  grade: string
  subject: string
  extra: Record<string, unknown>  // subject-specific fields
}
   
export interface GenerationRequest {
  indicator: Indicator
  grade: string
  term: number
  week: number
  schoolContext: Record<string, unknown>
  options: Record<string, unknown>
}

// ── Block types ───────────────────────────────────────────────
export interface TextBlock {
  type: 'text'
  text: string
  style: 'body' | 'heading' | 'bullet'
}

export interface TableBlock {
  type: 'table'
  headers: string[]
  rows: string[][]
}

export interface CalloutBlock {
  type: 'callout'
  label: string   // e.g. "Safety note", "Core point"
  text: string
}

export interface EquationBlock {
  type: 'equation'
  latex: string
}

export type Block = TextBlock | TableBlock | CalloutBlock | EquationBlock

export interface Section {
  title: string
  blocks: Block[]
}

export interface MaterialDoc {
  title: string
  sections: Section[]
  meta: Record<string, unknown>
}

export interface Question {
  prompt: string
  options: string[] | null   // null for open-ended
  answer: string
  difficulty: 'reinforcement' | 'core' | 'extension'
}
// app/src/kernel/SubjectModule.ts
import type { GenerationRequest, Indicator, MaterialDoc, Question } from './types'

export interface SubjectModule {
  id: string
  displayName: string
  grades: string[]
  capabilities: Set<string>

  loadIndicators(grade: string): Promise<Indicator[]>
  validate(): string[]   // returns [] if clean, list of problems otherwise
  generateLessonPlan(request: GenerationRequest): MaterialDoc
  generateSchemeOfWork(grade: string, term: number, options?: Record<string, unknown>): MaterialDoc
  generateRecordOfWork(grade: string, term: number, options?: Record<string, unknown>): MaterialDoc
  generateQuestionsDoc(indicator: Indicator, grade: string, term: number): Promise<MaterialDoc>
  generateQuestions?(indicator: Indicator, count: number): Question[]
}

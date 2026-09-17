import type { SubjectModule } from '../../kernel/SubjectModule'
import type {
  GenerationRequest,
  Indicator,
  MaterialDoc,
} from '../../kernel/types'

export class MathModule implements SubjectModule {
  id = 'math'
  displayName = 'Mathematics'
  grades = ['B4']
  capabilities = new Set(['lesson_plan', 'scheme_of_work', 'questions'])

  async loadIndicators(grade: string): Promise<Indicator[]> {
    const res = await fetch(`/curriculum/${grade.toLowerCase()}_indicators.json`)
    if (!res.ok) return []
    const raw = await res.json()
    return raw
      .filter((i: any) => i.subjectId === 'mathematics')
      .map((i: any) => ({
        code: i.code,
        strand: i.strandName,
        subStrand: i.subStrandName,
        contentStandard: i.contentStandardDescription,
        text: i.description,
        grade: i.grade,
        subject: i.subjectId,
        extra: i.extra ?? {},
      }))
  }

  validate(): string[] {
    // Grade list is hardcoded — nothing to validate at construction time.
    // Real data validation happens in loadIndicators at runtime.
    return []
  }

  generateLessonPlan(request: GenerationRequest): MaterialDoc {
    const { indicator: ind, week, options } = request
    const duration = (options.duration_minutes as number) ?? 60

    return {
      title: `Lesson Plan — ${ind.strand} — ${ind.grade} Wk ${week}`,
      sections: [
        {
          title: 'Indicator',
          blocks: [{ type: 'text', text: `${ind.code}: ${ind.text}`, style: 'body' }],
        },
        {
          title: 'Objectives',
          blocks: [
            {
              type: 'text',
              text: `By the end of the lesson, learners will be able to ${ind.text.toLowerCase()}.`,
              style: 'bullet',
            },
          ],
        },
        {
          title: 'Core Content',
          blocks: [
            { type: 'text', text: ind.contentStandard, style: 'body' },
            {
              type: 'callout',
              label: 'Sub-skill',
              text: (ind.extra.sub_skill as string) ?? 'n/a',
            },
          ],
        },
        {
          title: 'Duration',
          blocks: [{ type: 'text', text: `${duration} minutes`, style: 'body' }],
        },
      ],
      meta: { subject: ind.subject, grade: ind.grade, indicatorCode: ind.code },
    }
  }

  generateSchemeOfWork(grade: string, term: number, options?: Record<string, unknown>): MaterialDoc {
    // Indicators are async — caller must pre-load and pass via options
    const indicators = (options?.indicators as Indicator[]) ?? []
    return {
      title: `Scheme of Work — Mathematics ${grade} Term ${term}`,
      sections: [
        {
          title: 'Indicators covered',
          blocks: [
            {
              type: 'table',
              headers: ['Code', 'Strand', 'Indicator'],
              rows: indicators.map(i => [i.code, i.strand, i.text]),
            },
          ],
        },
      ],
      meta: { subject: 'math', grade, term },
    }
  }

  generateRecordOfWork(grade: string, term: number, options?: Record<string, unknown>): MaterialDoc {
    // Lessons are async — caller must pre-load and pass via options
    const lessons = (options?.lessons as any[]) ?? []
    return {
      title: `Record of Work — Mathematics ${grade} Term ${term}`,
      sections: [
        {
          title: 'Weekly Schedule',
          blocks: [
            {
              type: 'table',
              headers: ['Week', 'Day', 'Indicator', 'Session Title'],
              rows: lessons.map(l => [l.week, l.day, l.indicatorCode, l.sessionTitle]),
            },
          ],
        },
      ],
      meta: { subject: 'math', grade, term },
    }
  }

  async generateQuestionsDoc(indicator: Indicator, grade: string, term: number): Promise<MaterialDoc> {
    // In a real app, this would fetch from /curriculum/questions/math/B4.json
    // For this reference impl, we'll simulate the fetch
    const res = await fetch(`/curriculum/questions/math/${grade}.json`).catch(() => null)
    let questions: any[] = []
    if (res && res.ok) {
      const data = await res.json()
      const found = data.find((entry: any) => entry.indicatorCode === indicator.code)
      questions = found ? found.questions : []
    }

    return {
      title: `Question Bank — ${indicator.strand} — ${indicator.grade} T${term}`,
      sections: [
        {
          title: 'Indicator',
          blocks: [{ type: 'text', text: `${indicator.code}: ${indicator.text}`, style: 'body' }],
        },
        {
          title: 'Questions',
          blocks: questions.map((q, idx) => ({
            type: 'text',
            text: `${idx + 1}. ${q.prompt} ${q.options ? `(Options: ${q.options.join(', ')})` : ''}`,
            style: 'body'
          })),
        },
      ],
      meta: { subject: 'math', grade, term, indicatorCode: indicator.code },
    }
  }

  generateQuestions(indicator: Indicator, count: number): any[] {
    // This is a synchronous call as per interface, so we return placeholders
    // Actual data is handled in the async generateQuestionsDoc
    return []
  }
}

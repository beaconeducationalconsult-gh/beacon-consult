import type { SubjectModule } from '../../kernel/SubjectModule'
import type {
  GenerationRequest,
  Indicator,
  MaterialDoc,
} from '../../kernel/types'

export class GhanaianLanguageModule implements SubjectModule {
  id = 'ghanaian-language'
  displayName = 'Ghanaian Language'
  grades = ['B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B9']
  capabilities = new Set(['lesson_plan', 'scheme_of_work'])

  async loadIndicators(grade: string): Promise<Indicator[]> {
    const res = await fetch(`/curriculum/${grade.toLowerCase()}_indicators.json`)
    if (!res.ok) return []
    const raw = await res.json()
    return raw
      .filter((i: any) => i.subjectId === 'ghanaian-language')
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
              label: 'Language Focus',
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
    const indicators = (options?.indicators as Indicator[]) ?? []
    return {
      title: `Scheme of Work — Ghanaian Language ${grade} Term ${term}`,
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
      meta: { subject: 'ghanaian-language', grade, term },
    }
  }

  generateRecordOfWork(grade: string, term: number, options?: Record<string, unknown>): MaterialDoc {
    const lessons = (options?.lessons as any[]) ?? []
    return {
      title: `Record of Work — Ghanaian Language ${grade} Term ${term}`,
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
      meta: { subject: 'ghanaian-language', grade, term },
    }
  }

  async generateQuestionsDoc(indicator: Indicator, grade: string, term: number): Promise<MaterialDoc> {
    return {
      title: `Question Bank — ${indicator.strand} — ${indicator.grade} T${term}`,
      sections: [{ title: 'Questions', blocks: [{ type: 'text', text: 'Questions not yet authored for this subject.', style: 'body' }] }],
      meta: { subject: 'ghanaian-language', grade, term, indicatorCode: indicator.code },
    }
  }

  generateQuestions(indicator: Indicator, count: number): any[] {
    return []
  }
}

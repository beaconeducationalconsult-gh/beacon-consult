import { useState } from 'react'
import { registry } from '../kernel'
import { renderDocx, downloadBlob } from '../drivers/docx'
import { recordGeneration, getSchool, getUser } from './firestore'
import { useAuth } from './AuthContext'
import type { Indicator } from '../kernel/types'

type DocType = 'lesson_plan' | 'scheme_of_work' | 'record_of_work' | 'question_bank'

interface GenerateParams {
  subject: string
  grade: string
  term: number
  week?: number
  indicator?: Indicator
  docType: DocType
}

export function useGenerate() {
  const { user } = useAuth()
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function generate(params: GenerateParams) {
    setGenerating(true)
    setError(null)
    try {
      const module = registry.get(params.subject)

      // --- Resolve School Branding ---
      let schoolContext: Record<string, unknown> = {}
      if (user) {
        const userData = await getUser(user.uid)
        const schoolId = userData?.schoolId ?? user.uid
        const schoolData = await getSchool(schoolId)

        schoolContext = {
          schoolName: schoolData?.name ?? 'My School',
          teacherName: userData?.displayName ?? user.displayName ?? 'Teacher',
        }
      }

      let doc
      if (params.docType === 'lesson_plan') {
        if (!params.indicator) throw new Error('Indicator is required for lesson plans')
        if (!module.capabilities.has('lesson_plan')) throw new Error(`${params.subject} does not support lesson_plan`)

        doc = module.generateLessonPlan({
          indicator: params.indicator,
          grade: params.grade,
          term: params.term,
          week: params.week ?? 1,
          schoolContext,
          options: {},
        })
      } else if (params.docType === 'scheme_of_work') {
        if (!module.capabilities.has('scheme_of_work')) throw new Error(`${params.subject} does not support scheme_of_work`)

        const indicators = await module.loadIndicators(params.grade)
        doc = module.generateSchemeOfWork(params.grade, params.term, { indicators })
      } else if (params.docType === 'record_of_work') {
        const res = await fetch(`/curriculum/${params.grade.toLowerCase()}_schedules.json`)
        if (!res.ok) throw new Error(`No schedule data found for grade ${params.grade}`)
        const allSchedules = await res.json()
        const lessons = allSchedules.filter((l: any) => l.subjectId === params.subject)

        doc = module.generateRecordOfWork(params.grade, params.term, { lessons })
      } else if (params.docType === 'question_bank') {
        if (!module.capabilities.has('questions')) {
          throw new Error(`${params.subject} does not support question generation`)
        }

        const indicator = params.indicator
        if (!indicator) throw new Error('Indicator is required for question bank')

        doc = await module.generateQuestionsDoc(indicator, params.grade, params.term)
      } else {
        throw new Error('Unsupported document type')
      }

      const blob = await renderDocx(doc)
      const filename = `${params.subject}_${params.grade}_${params.docType}_T${params.term}.docx`
      downloadBlob(blob, filename)

      if (user) {
        const userData = await getUser(user.uid)
        const schoolId = userData?.schoolId ?? user.uid
        await recordGeneration({
          schoolId,
          userId: user.uid,
          subject: params.subject,
          grade: params.grade,
          indicatorCode: params.indicator?.code ?? 'all',
          documentType: params.docType,
          filename,
        })
      }
    } catch (e: any) {
      setError(e.message)
    } finally {
      setGenerating(false)
    }
  }

  return { generate, generating, error }
}

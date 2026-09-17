import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { registry } from '../../kernel'
import { useIndicators } from '../../services/useCurriculum'
import { useGenerate } from '../../services/useGenerate'

type DocType = 'lesson_plan' | 'scheme_of_work' | 'record_of_work'

export function GeneratePage() {
  const [searchParams] = useSearchParams()
  const { generate, generating, error } = useGenerate()

  // State for selection
  const [docType, setDocType] = useState<DocType>('lesson_plan')
  const [subject, setSubject] = useState('')
  const [grade, setGrade] = useState('')
  const [term, setTerm] = useState(1)
  const [week, setWeek] = useState(1)
  const [selectedIndicatorCode, setSelectedIndicatorCode] = useState('')

  const { indicators, loading: indicatorsLoading } = useIndicators(grade, subject)

  useEffect(() => {
    const code = searchParams.get('code')
    if (code) {
      setSelectedIndicatorCode(code)
      setDocType('lesson_plan')
    }
  }, [searchParams])

  const handleGenerate = async () => {
    const indicator = indicators.find(i => i.code === selectedIndicatorCode)

    await generate({
      subject,
      grade,
      term,
      week,
      indicator: indicator || undefined,
      docType,
    })
  }

  const loadedSubjects = registry.listLoaded()
  const currentModule = subject ? registry.get(subject) : null

  return (
    <div className="max-w-3xl mx-auto p-8">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-4">Generate Material</h1>
        <p className="text-gray-600">Configure your document and download it as a Word file.</p>
      </div>

      <div className="bg-white shadow-sm border border-gray-200 rounded-lg p-8 space-y-8">
        {/* 0. Document Type */}
        <div className="flex flex-col items-center gap-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
          <span className="text-sm font-medium text-gray-500 uppercase tracking-wider">Document Type</span>
          <div className="flex gap-2">
            {(['lesson_plan', 'scheme_of_work', 'record_of_work', 'question_bank'] as DocType[]).map(type => (
              <button
                key={type}
                onClick={() => setDocType(type)}
                className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                  docType === type
                    ? 'bg-[#1B4332] text-white shadow-md'
                    : 'bg-white text-gray-600 border border-gray-300 hover:border-[#1B4332]'
                }`}
              >
                {type === 'lesson_plan' ? 'Lesson Plan' : type === 'scheme_of_work' ? 'Scheme of Work' : type === 'record_of_work' ? 'Record of Work' : 'Question Bank'}
              </button>
            ))}
          </div>
        </div>

        {/* 1. Subject & Grade */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Subject</label>
            <select
              value={subject}
              onChange={(e) => {
                setSubject(e.target.value)
                setGrade('')
                setSelectedIndicatorCode('')
              }}
              className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#1B4332] focus:border-transparent"
            >
              <option value="">Select Subject</option>
              {loadedSubjects.map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Grade</label>
            <select
              disabled={!subject}
              value={grade}
              onChange={(e) => {
                setGrade(e.target.value)
                setSelectedIndicatorCode('')
              }}
              className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#1B4332] focus:border-transparent disabled:bg-gray-100"
            >
              <option value="">Select Grade</option>
              {currentModule?.grades.map(g => (
                <option key={g} value={g}>{g}</option>
              ))}
            </select>
          </div>
        </div>

        {/* 2. Term & Week */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Term</label>
            <select
              value={term}
              onChange={(e) => setTerm(parseInt(e.target.value))}
              className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#1B4332] focus:border-transparent"
            >
              <option value={1}>Term 1</option>
              <option value={2}>Term 2</option>
              <option value={3}>Term 3</option>
            </select>
          </div>
          {docType === 'lesson_plan' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Week</label>
              <input
                type="number"
                min="1"
                max="12"
                value={week}
                onChange={(e) => setWeek(parseInt(e.target.value))}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#1B4332] focus:border-transparent"
              />
            </div>
          )}
        </div>

        {/* 3. Indicator Selection (Only for Lesson Plan & Question Bank) */}
        {(docType === 'lesson_plan' || docType === 'question_bank') && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Indicator</label>
            <select
              disabled={!grade || indicatorsLoading}
              value={selectedIndicatorCode}
              onChange={(e) => setSelectedIndicatorCode(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#1B4332] focus:border-transparent disabled:bg-gray-100"
            >
              <option value="">{indicatorsLoading ? 'Loading...' : 'Select Indicator'}</option>
              {indicators.map(ind => (
                <option key={ind.code} value={ind.code}>
                  {ind.code} — {ind.text.substring(0, 100)}...
                </option>
              ))}
            </select>
          </div>
        )}

        {error && (
          <div className="p-4 bg-red-50 text-red-600 rounded-md text-sm">
            {error}
          </div>
        )}

        <button
          onClick={handleGenerate}
          disabled={generating || !subject || !grade || ((docType === 'lesson_plan' || docType === 'question_bank') && !selectedIndicatorCode)}
          className="w-full py-4 bg-[#1B4332] text-white font-bold rounded-md hover:bg-[#16201A] transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          {generating ? 'Generating...' : `Generate ${docType === 'lesson_plan' ? 'Lesson Plan' : docType === 'scheme_of_work' ? 'Scheme of Work' : docType === 'record_of_work' ? 'Record of Work' : 'Question Bank'}`}
        </button>
      </div>
    </div>
  )
}

import { useState } from 'react'
import { api, Question } from '../api'

export function QuestionPanel({ questions, onRefresh }: { questions: Question[]; onRefresh: () => void }) {
  const [answeringId, setAnsweringId] = useState<string | null>(null)
  const [answerText, setAnswerText] = useState('')

  const handleAnswer = async (id: string) => {
    if (!answerText.trim()) return
    await api.answerQuestion(id, answerText)
    setAnsweringId(null)
    setAnswerText('')
    onRefresh()
  }

  const handleDismiss = async (id: string) => {
    await api.dismissQuestion(id)
    onRefresh()
  }

  return (
    <div>
      <span className="text-[11px] font-semibold tracking-[0.08em] uppercase text-[var(--soma-dim)] block mb-5">
        Decision Synapses
      </span>

      {questions.length === 0 ? (
        <p className="text-[var(--soma-dim)] text-xs py-6 text-center opacity-50">
          No pending decisions.
        </p>
      ) : (
        <div className="space-y-3">
          {questions.map(q => (
            <div key={q.id} className="bg-[var(--surface-1)] border border-[var(--border-subtle)] rounded-lg p-4">
              <p className="text-[13px] text-[var(--soma)] leading-relaxed">{q.question_text}</p>
              {q.context && (
                <p className="text-[11px] text-[var(--soma-dim)] mt-2 leading-relaxed">{q.context}</p>
              )}
              <div className="flex items-center gap-2 mt-2 text-[10px] text-[var(--soma-dim)] opacity-50 font-mono">
                <span>{q.generated_by.replace('agent:', '')}</span>
                <span>&middot;</span>
                <span>{new Date(q.created_at).toLocaleDateString()}</span>
              </div>

              {answeringId === q.id ? (
                <div className="mt-3">
                  <textarea
                    value={answerText}
                    onChange={e => setAnswerText(e.target.value)}
                    placeholder="Your response..."
                    className="w-full bg-[var(--surface-0)] border border-[var(--border)] rounded px-3 py-2 text-xs text-[var(--soma)] placeholder:text-[var(--soma-dim)] placeholder:opacity-40 focus:outline-none focus:border-[var(--dendrite)] resize-none"
                    rows={3}
                    autoFocus
                  />
                  <div className="flex gap-2 mt-2">
                    <button onClick={() => handleAnswer(q.id)} className="text-[11px] px-3 py-1.5 bg-[var(--dendrite)] rounded text-white font-medium hover:opacity-90">
                      Submit
                    </button>
                    <button onClick={() => setAnsweringId(null)} className="text-[11px] px-3 py-1.5 bg-[var(--surface-2)] border border-[var(--border)] rounded text-[var(--soma-dim)] hover:text-[var(--soma)]">
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex gap-2 mt-3">
                  <button onClick={() => setAnsweringId(q.id)} className="text-[11px] px-3 py-1.5 bg-[var(--surface-2)] border border-[var(--border)] rounded text-[var(--dendrite)] hover:bg-[var(--surface-3)]">
                    Respond
                  </button>
                  <button onClick={() => handleDismiss(q.id)} className="text-[11px] px-3 py-1.5 bg-[var(--surface-2)] border border-[var(--border)] rounded text-[var(--soma-dim)] hover:text-[var(--soma)]">
                    Dismiss
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

import { useState } from 'react'
import { api, Question } from '../api'

export function QuestionPanel({
  questions,
  onRefresh,
}: {
  questions: Question[]
  onRefresh: () => void
}) {
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
      <h2 className="text-lg font-semibold text-white mb-4">
        Questions for Joseph
      </h2>
      <div className="space-y-3">
        {questions.length === 0 && (
          <p className="text-gray-500 text-sm py-4 text-center">
            No pending questions. Run agents to generate them.
          </p>
        )}
        {questions.map((q) => (
          <div
            key={q.id}
            className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4"
          >
            <p className="text-sm text-white font-medium">{q.question_text}</p>
            {q.context && (
              <p className="text-xs text-gray-400 mt-1">{q.context}</p>
            )}
            <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
              <span>{q.generated_by}</span>
              <span>·</span>
              <span>{new Date(q.created_at).toLocaleDateString()}</span>
            </div>

            {answeringId === q.id ? (
              <div className="mt-3">
                <textarea
                  value={answerText}
                  onChange={(e) => setAnswerText(e.target.value)}
                  placeholder="Type your answer..."
                  className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 resize-none"
                  rows={3}
                  autoFocus
                />
                <div className="flex gap-2 mt-2">
                  <button
                    onClick={() => handleAnswer(q.id)}
                    className="text-xs px-3 py-1.5 bg-blue-600 rounded hover:bg-blue-500 text-white"
                  >
                    Submit
                  </button>
                  <button
                    onClick={() => setAnsweringId(null)}
                    className="text-xs px-3 py-1.5 bg-gray-700 rounded hover:bg-gray-600 text-gray-300"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex gap-2 mt-3">
                <button
                  onClick={() => setAnsweringId(q.id)}
                  className="text-xs px-3 py-1.5 bg-blue-600/20 border border-blue-500/30 rounded hover:bg-blue-600/30 text-blue-400"
                >
                  Answer
                </button>
                <button
                  onClick={() => handleDismiss(q.id)}
                  className="text-xs px-3 py-1.5 bg-gray-700/50 border border-gray-600/30 rounded hover:bg-gray-700 text-gray-400"
                >
                  Dismiss
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

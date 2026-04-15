import { useEffect, useState } from 'react'
import { api, SkillInfo } from '../api'

export function SkillSidebar() {
  const [skills, setSkills] = useState<SkillInfo[]>([])
  const [executing, setExecuting] = useState<string | null>(null)
  const [result, setResult] = useState<string | null>(null)

  useEffect(() => {
    api.skills().then(setSkills).catch(console.error)
  }, [])

  const handleExecute = async (skill: SkillInfo) => {
    setExecuting(skill.id)
    setResult(null)
    try {
      const res = await api.executeSkill(skill.id) as { output_text?: string; status: string }
      setResult(res.output_text || `Status: ${res.status}`)
    } catch (e) {
      setResult(e instanceof Error ? e.message : 'Execution failed')
    } finally {
      setExecuting(null)
    }
  }

  return (
    <div>
      <h2 className="text-lg font-semibold text-white mb-4">Skills</h2>
      <div className="space-y-2">
        {skills.map((skill) => (
          <div
            key={skill.id}
            className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-3"
          >
            <div className="flex items-center justify-between">
              <div className="min-w-0 flex-1">
                <span className="text-sm font-medium text-white">
                  {skill.display_name}
                </span>
                <p className="text-xs text-gray-400 mt-0.5 line-clamp-2">
                  {skill.description}
                </p>
              </div>
              <button
                onClick={() => handleExecute(skill)}
                disabled={executing === skill.id}
                className="ml-3 text-xs px-3 py-1.5 bg-emerald-600/20 border border-emerald-500/30 rounded hover:bg-emerald-600/30 text-emerald-400 disabled:opacity-50 flex-shrink-0"
              >
                {executing === skill.id ? '...' : 'Run'}
              </button>
            </div>
            {skill.execution_count > 0 && (
              <span className="text-xs text-gray-600 mt-1 inline-block">
                Ran {skill.execution_count}x
              </span>
            )}
          </div>
        ))}
      </div>

      {result && (
        <div className="mt-4 bg-gray-900 border border-gray-700 rounded-lg p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-gray-400">
              Skill Output
            </span>
            <button
              onClick={() => setResult(null)}
              className="text-xs text-gray-500 hover:text-gray-300"
            >
              Close
            </button>
          </div>
          <pre className="text-xs text-gray-300 whitespace-pre-wrap max-h-60 overflow-y-auto">
            {result}
          </pre>
        </div>
      )}
    </div>
  )
}

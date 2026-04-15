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
      <span className="text-[11px] font-semibold tracking-[0.08em] uppercase text-[var(--soma-dim)] block mb-5">
        Skill Pathways
      </span>

      <div className="space-y-1">
        {skills.map(skill => (
          <div
            key={skill.id}
            className="flex items-center justify-between px-3 py-2.5 rounded-md hover:bg-[var(--surface-1)] transition-colors group"
          >
            <div className="min-w-0 flex-1">
              <span className="text-[13px] text-[var(--soma)]">{skill.display_name}</span>
              <p className="text-[11px] text-[var(--soma-dim)] opacity-60 mt-0.5 line-clamp-1">
                {skill.description}
              </p>
            </div>
            <button
              onClick={() => handleExecute(skill)}
              disabled={executing === skill.id}
              className="ml-3 text-[11px] px-2.5 py-1 border border-[var(--border)] rounded text-[var(--axon)] opacity-0 group-hover:opacity-100 hover:bg-[var(--surface-2)] disabled:opacity-30 transition-opacity flex-shrink-0"
            >
              {executing === skill.id ? '...' : 'Run'}
            </button>
          </div>
        ))}
      </div>

      {result && (
        <div className="mt-4 bg-[var(--surface-1)] border border-[var(--border-subtle)] rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-mono text-[var(--soma-dim)]">OUTPUT</span>
            <button onClick={() => setResult(null)} className="text-[10px] text-[var(--soma-dim)] hover:text-[var(--soma)]">
              close
            </button>
          </div>
          <pre className="text-[12px] font-mono text-[var(--soma)] whitespace-pre-wrap max-h-48 overflow-y-auto leading-relaxed">
            {result}
          </pre>
        </div>
      )}
    </div>
  )
}

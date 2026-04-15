import { useEffect, useState } from 'react'
import { api, SkillInfo } from '../api'

interface SkillRun {
  skill: SkillInfo
  output: string
  status: 'running' | 'done' | 'error'
  time?: number
}

const INPUT_FIELDS: Record<string, { key: string; placeholder: string }[]> = {
  summarize_context: [{ key: 'topic', placeholder: 'Topic to summarize (or leave blank for overview)...' }],
  decision_brief: [{ key: 'topic', placeholder: 'Decision topic...' }],
  draft_message: [
    { key: 'recipient', placeholder: 'Recipient name...' },
    { key: 'intent', placeholder: 'Message intent...' },
  ],
}

export function SkillSidebar() {
  const [skills, setSkills] = useState<SkillInfo[]>([])
  const [runs, setRuns] = useState<SkillRun[]>([])
  const [executing, setExecuting] = useState<string | null>(null)
  const [inputs, setInputs] = useState<Record<string, string>>({})

  useEffect(() => {
    api.skills().then(setSkills).catch(console.error)
  }, [])

  const handleExecute = async (skill: SkillInfo) => {
    setExecuting(skill.id)

    // Add a "running" entry at the top
    const runEntry: SkillRun = { skill, output: '', status: 'running' }
    setRuns(prev => [runEntry, ...prev.slice(0, 4)]) // Keep last 5

    try {
      const res = (await api.executeSkill(skill.id, inputs)) as {
        output_text?: string
        status: string
        duration_ms?: number
      }
      setRuns(prev => {
        const updated = [...prev]
        const idx = updated.findIndex(r => r.skill.id === skill.id && r.status === 'running')
        if (idx >= 0) {
          updated[idx] = {
            skill,
            output: res.output_text || `Status: ${res.status}`,
            status: 'done',
            time: res.duration_ms,
          }
        }
        return updated
      })
    } catch (e) {
      setRuns(prev => {
        const updated = [...prev]
        const idx = updated.findIndex(r => r.skill.id === skill.id && r.status === 'running')
        if (idx >= 0) {
          updated[idx] = {
            skill,
            output: e instanceof Error ? e.message : 'Failed',
            status: 'error',
          }
        }
        return updated
      })
    } finally {
      setExecuting(null)
      setInputs({})
    }
  }

  const setInput = (key: string, value: string) => {
    setInputs(prev => ({ ...prev, [key]: value }))
  }

  return (
    <div className="flex flex-col h-full">
      <span className="text-[11px] font-semibold tracking-[0.08em] uppercase text-[var(--soma-dim)] block mb-4">
        Skill Pathways
      </span>

      {/* Skill list */}
      <div className="space-y-1 mb-5">
        {skills.map(skill => {
          const fields = INPUT_FIELDS[skill.name]
          return (
            <div key={skill.id}>
              <div className="flex items-center justify-between px-3 py-2 rounded-md hover:bg-[var(--surface-1)] transition-colors group">
                <div className="min-w-0 flex-1">
                  <span className="text-[13px] text-[var(--soma)]">{skill.display_name}</span>
                  {skill.execution_count > 0 && (
                    <span className="font-mono text-[10px] text-[var(--soma-dim)] opacity-40 ml-2">
                      x{skill.execution_count}
                    </span>
                  )}
                </div>
                <button
                  onClick={() => handleExecute(skill)}
                  disabled={executing !== null}
                  className="ml-3 text-[11px] px-2.5 py-1 border border-[var(--border)] rounded text-[var(--axon)] opacity-0 group-hover:opacity-100 hover:bg-[var(--surface-2)] disabled:opacity-30 transition-opacity flex-shrink-0"
                >
                  {executing === skill.id ? '...' : 'Run'}
                </button>
              </div>
              {/* Input fields for skills that need them */}
              {fields && (
                <div className="px-3 pb-2 space-y-1.5">
                  {fields.map(f => (
                    <input
                      key={f.key}
                      value={inputs[f.key] || ''}
                      onChange={e => setInput(f.key, e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && handleExecute(skill)}
                      placeholder={f.placeholder}
                      className="w-full bg-[var(--surface-0)] border border-[var(--border-subtle)] rounded px-2.5 py-1.5 text-[11px] text-[var(--soma)] placeholder:text-[var(--soma-dim)] placeholder:opacity-40 focus:outline-none focus:border-[var(--dendrite)]"
                    />
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Output panel — live document view */}
      {runs.length > 0 && (
        <div className="flex-1 min-h-0">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-mono text-[var(--soma-dim)]">OUTPUT</span>
            <button
              onClick={() => setRuns([])}
              className="text-[10px] text-[var(--soma-dim)] hover:text-[var(--soma)]"
            >
              clear
            </button>
          </div>
          <div className="space-y-3 max-h-[60vh] overflow-y-auto">
            {runs.map((run, i) => (
              <div
                key={`${run.skill.id}-${i}`}
                className="bg-[var(--surface-1)] border border-[var(--border-subtle)] rounded-lg overflow-hidden"
              >
                {/* Run header */}
                <div className="flex items-center justify-between px-3 py-2 border-b border-[var(--border-subtle)]">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-1.5 h-1.5 rounded-full"
                      style={{
                        backgroundColor:
                          run.status === 'running' ? 'var(--myelin)' :
                          run.status === 'error' ? 'var(--inhibit)' : 'var(--axon)',
                      }}
                    />
                    <span className="text-[11px] text-[var(--soma)]">{run.skill.display_name}</span>
                  </div>
                  {run.time && (
                    <span className="font-mono text-[10px] text-[var(--soma-dim)] opacity-50">
                      {run.time}ms
                    </span>
                  )}
                </div>

                {/* Output body — rendered as document */}
                <div className="px-4 py-3 skill-output">
                  {run.status === 'running' ? (
                    <span className="text-[12px] text-[var(--soma-dim)]">Querying cortex...</span>
                  ) : (
                    <div className="text-[12px] text-[var(--soma)] leading-relaxed whitespace-pre-wrap">
                      {renderMarkdown(run.output)}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

/** Lightweight markdown-to-JSX renderer for skill output */
function renderMarkdown(text: string) {
  const lines = text.split('\n')
  const elements: JSX.Element[] = []

  lines.forEach((line, i) => {
    const trimmed = line.trimStart()

    if (trimmed.startsWith('## ')) {
      elements.push(
        <h2 key={i} className="text-[14px] font-semibold text-white mt-3 mb-2">
          {trimmed.slice(3)}
        </h2>
      )
    } else if (trimmed.startsWith('### ')) {
      elements.push(
        <h3 key={i} className="text-[12px] font-semibold text-[var(--dendrite)] mt-3 mb-1 uppercase tracking-wider">
          {trimmed.slice(4)}
        </h3>
      )
    } else if (trimmed.startsWith('> ')) {
      elements.push(
        <blockquote key={i} className="border-l-2 border-[var(--surface-3)] pl-3 text-[11px] text-[var(--soma-dim)] my-1 leading-relaxed">
          {renderInline(trimmed.slice(2))}
        </blockquote>
      )
    } else if (trimmed.startsWith('- ')) {
      elements.push(
        <div key={i} className="flex gap-2 my-0.5">
          <span className="text-[var(--soma-dim)] mt-px">·</span>
          <span className="text-[12px]">{renderInline(trimmed.slice(2))}</span>
        </div>
      )
    } else if (trimmed.startsWith('---')) {
      elements.push(
        <div key={i} className="h-px bg-[var(--border-subtle)] my-3" />
      )
    } else if (trimmed.startsWith('1.') || trimmed.startsWith('2.') || trimmed.startsWith('3.')) {
      const num = trimmed.split('.')[0]
      const rest = trimmed.slice(trimmed.indexOf('.') + 2)
      elements.push(
        <div key={i} className="flex gap-2 my-0.5">
          <span className="font-mono text-[10px] text-[var(--soma-dim)] w-4">{num}.</span>
          <span className="text-[12px]">{renderInline(rest)}</span>
        </div>
      )
    } else if (trimmed === '') {
      elements.push(<div key={i} className="h-1" />)
    } else {
      elements.push(
        <p key={i} className="text-[12px] my-0.5">{renderInline(trimmed)}</p>
      )
    }
  })

  return <>{elements}</>
}

/** Render inline bold/code */
function renderInline(text: string) {
  // Bold: **text**
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={i} className="text-white font-medium">{part.slice(2, -2)}</strong>
        }
        // Inline code: `text`
        const codeParts = part.split(/(`[^`]+`)/g)
        return codeParts.map((cp, j) => {
          if (cp.startsWith('`') && cp.endsWith('`')) {
            return (
              <code key={`${i}-${j}`} className="font-mono text-[11px] bg-[var(--surface-3)] px-1 py-0.5 rounded text-[var(--axon)]">
                {cp.slice(1, -1)}
              </code>
            )
          }
          return <span key={`${i}-${j}`}>{cp}</span>
        })
      })}
    </>
  )
}

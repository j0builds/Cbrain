import { useState } from 'react'
import { api, Task } from '../api'

const urgencyColor: Record<string, string> = {
  critical: 'var(--inhibit)',
  high: 'var(--myelin)',
  normal: 'var(--axon)',
  low: 'var(--soma-dim)',
}

export function TaskList({ tasks, onRefresh }: { tasks: Task[]; onRefresh: () => void }) {
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [copied, setCopied] = useState<string | null>(null)
  const [showAdd, setShowAdd] = useState(false)
  const [newTitle, setNewTitle] = useState('')

  const handleAdd = async () => {
    if (!newTitle.trim()) return
    await api.createTask({ title: newTitle })
    setNewTitle('')
    setShowAdd(false)
    onRefresh()
  }

  const handleToggle = async (task: Task) => {
    await api.updateTask(task.id, { status: task.status === 'done' ? 'open' : 'done' })
    onRefresh()
  }

  const handleCopy = (task: Task) => {
    if (task.claude_prompt) {
      navigator.clipboard.writeText(task.claude_prompt)
      setCopied(task.id)
      setTimeout(() => setCopied(null), 2000)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <span className="text-[11px] font-semibold tracking-[0.08em] uppercase text-[var(--soma-dim)]">
          Task Cortex
        </span>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="text-[11px] px-2.5 py-1 bg-[var(--surface-2)] border border-[var(--border)] rounded text-[var(--soma-dim)] hover:text-[var(--soma)] hover:bg-[var(--surface-3)]"
        >
          + New
        </button>
      </div>

      {showAdd && (
        <div className="mb-4 flex gap-2">
          <input
            value={newTitle}
            onChange={e => setNewTitle(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleAdd()}
            placeholder="Signal description..."
            className="flex-1 bg-[var(--surface-0)] border border-[var(--border)] rounded px-3 py-2 text-xs text-[var(--soma)] placeholder:text-[var(--soma-dim)] placeholder:opacity-40 focus:outline-none focus:border-[var(--dendrite)]"
            autoFocus
          />
          <button onClick={handleAdd} className="text-xs px-3 py-2 bg-[var(--dendrite)] rounded text-white font-medium hover:opacity-90">
            Add
          </button>
        </div>
      )}

      {tasks.length === 0 ? (
        <p className="text-[var(--soma-dim)] text-xs py-8 text-center opacity-50">
          No active signals. Hit Extract Tasks to populate.
        </p>
      ) : (
        <div className="space-y-1">
          {tasks.map(task => {
            const isExpanded = expandedId === task.id
            const scoreColor = task.importance_score >= 60 ? 'var(--inhibit)' :
              task.importance_score >= 40 ? 'var(--myelin)' :
              task.importance_score >= 25 ? 'var(--axon)' : 'var(--soma-dim)'

            return (
              <div key={task.id}>
                {/* Task row */}
                <div
                  className={`flex items-start gap-3 px-3 py-2.5 rounded-md cursor-pointer transition-colors ${
                    isExpanded ? 'bg-[var(--surface-2)]' : 'hover:bg-[var(--surface-1)]'
                  }`}
                  onClick={() => setExpandedId(isExpanded ? null : task.id)}
                >
                  {/* Score indicator */}
                  <div className="flex flex-col items-center gap-0.5 mt-0.5 flex-shrink-0 w-7">
                    <span className="font-mono text-[11px] font-semibold" style={{ color: scoreColor }}>
                      {task.importance_score}
                    </span>
                    <div className="w-5 h-0.5 rounded-full bg-[var(--surface-3)] overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${task.importance_score}%`,
                          backgroundColor: scoreColor,
                        }}
                      />
                    </div>
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className={`text-[13px] leading-tight ${task.status === 'done' ? 'line-through opacity-40' : 'text-[var(--soma)]'}`}>
                        {task.title}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="font-mono text-[10px]" style={{ color: urgencyColor[task.urgency] }}>
                        {task.urgency.toUpperCase()}
                      </span>
                      <span className="text-[10px] text-[var(--soma-dim)] opacity-40">
                        {task.source.replace('brain:', '')}
                      </span>
                      {task.priority_reason && (
                        <span className="text-[10px] text-[var(--soma-dim)] opacity-50 truncate max-w-[200px]">
                          {task.priority_reason.replace(/^Score \d+: /, '')}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Chevron */}
                  <span className="text-[10px] text-[var(--soma-dim)] opacity-30 mt-1">
                    {isExpanded ? '▼' : '▸'}
                  </span>
                </div>

                {/* Expanded detail */}
                {isExpanded && (
                  <div className="ml-10 mr-2 mb-3 bg-[var(--surface-1)] border border-[var(--border-subtle)] rounded-lg overflow-hidden">
                    {/* Description */}
                    {task.description && (
                      <div className="px-4 py-3 border-b border-[var(--border-subtle)]">
                        <span className="text-[10px] font-mono text-[var(--soma-dim)] opacity-50 block mb-1.5">CONTEXT</span>
                        <p className="text-[12px] text-[var(--soma)] leading-relaxed whitespace-pre-wrap">
                          {task.description}
                        </p>
                      </div>
                    )}

                    {/* Instructions */}
                    {task.instructions && (
                      <div className="px-4 py-3 border-b border-[var(--border-subtle)]">
                        <span className="text-[10px] font-mono text-[var(--soma-dim)] opacity-50 block mb-1.5">INSTRUCTIONS</span>
                        <div className="text-[12px] text-[var(--soma)] leading-relaxed">
                          {task.instructions.split('\n').map((line, i) => (
                            <div key={i} className={line.startsWith('Note:') ? 'mt-2 text-[var(--myelin)] text-[11px]' : 'my-0.5'}>
                              {line}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Claude prompt */}
                    {task.claude_prompt && (
                      <div className="px-4 py-3">
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-[10px] font-mono text-[var(--soma-dim)] opacity-50">CLAUDE PROMPT</span>
                          <button
                            onClick={e => { e.stopPropagation(); handleCopy(task) }}
                            className="text-[10px] px-2 py-0.5 border border-[var(--border)] rounded text-[var(--dendrite)] hover:bg-[var(--surface-2)]"
                          >
                            {copied === task.id ? 'Copied' : 'Copy'}
                          </button>
                        </div>
                        <pre className="text-[11px] font-mono text-[var(--soma-dim)] leading-relaxed whitespace-pre-wrap bg-[var(--surface-0)] rounded p-3 max-h-48 overflow-y-auto">
                          {task.claude_prompt}
                        </pre>
                      </div>
                    )}

                    {/* Actions */}
                    <div className="px-4 py-2 border-t border-[var(--border-subtle)] flex gap-2">
                      <button
                        onClick={e => { e.stopPropagation(); handleToggle(task) }}
                        className="text-[11px] px-3 py-1 bg-[var(--surface-2)] border border-[var(--border)] rounded text-[var(--axon)] hover:bg-[var(--surface-3)]"
                      >
                        {task.status === 'done' ? 'Reopen' : 'Complete'}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

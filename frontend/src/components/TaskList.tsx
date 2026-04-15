import { useState } from 'react'
import { api, Task } from '../api'

const urgencyMap: Record<string, { label: string; color: string }> = {
  critical: { label: 'CRIT', color: 'var(--inhibit)' },
  high: { label: 'HIGH', color: 'var(--myelin)' },
  normal: { label: 'NORM', color: 'var(--soma-dim)' },
  low: { label: 'LOW', color: 'var(--soma-dim)' },
}

export function TaskList({ tasks, onRefresh }: { tasks: Task[]; onRefresh: () => void }) {
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
            className="flex-1 membrane-input px-3 py-2 text-xs bg-[var(--surface-1)] border border-[var(--border)] rounded text-[var(--soma)] placeholder:text-[var(--soma-dim)] placeholder:opacity-40 focus:outline-none focus:border-[var(--dendrite)]"
            autoFocus
          />
          <button onClick={handleAdd} className="text-xs px-3 py-2 bg-[var(--dendrite)] rounded text-white font-medium hover:opacity-90">
            Add
          </button>
        </div>
      )}

      {tasks.length === 0 ? (
        <p className="text-[var(--soma-dim)] text-xs py-8 text-center opacity-50">
          No active signals. Sync to populate.
        </p>
      ) : (
        <div className="space-y-1">
          {tasks.map((task, i) => {
            const u = urgencyMap[task.urgency] || urgencyMap.normal
            return (
              <div
                key={task.id}
                className="group flex items-start gap-3 px-3 py-2.5 rounded-md hover:bg-[var(--surface-1)] transition-colors"
              >
                <button
                  onClick={() => handleToggle(task)}
                  className="mt-0.5 w-4 h-4 rounded-sm border border-[var(--border)] flex items-center justify-center text-[10px] text-transparent hover:border-[var(--axon)] hover:text-[var(--axon)] flex-shrink-0"
                  style={task.status === 'done' ? { borderColor: 'var(--axon)', color: 'var(--axon)' } : {}}
                >
                  {task.status === 'done' ? '✓' : ''}
                </button>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={`text-[13px] leading-tight ${task.status === 'done' ? 'line-through text-[var(--soma-dim)] opacity-50' : 'text-[var(--soma)]'}`}>
                      {task.title}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="font-mono text-[10px]" style={{ color: u.color }}>{u.label}</span>
                    {task.priority <= 10 && (
                      <span className="font-mono text-[10px] text-[var(--dendrite)]">P{task.priority}</span>
                    )}
                    {task.blocker && (
                      <span className="text-[10px] text-[var(--inhibit)]">blocked</span>
                    )}
                    {task.priority_reason && (
                      <span className="text-[10px] text-[var(--soma-dim)] opacity-60 truncate max-w-[180px]">
                        {task.priority_reason}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

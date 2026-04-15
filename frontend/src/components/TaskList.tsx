import { useState } from 'react'
import { api, Task } from '../api'

const urgencyColors: Record<string, string> = {
  critical: 'bg-red-500/20 text-red-400 border-red-500/30',
  high: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  normal: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  low: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
}

const statusIcons: Record<string, string> = {
  open: '○',
  in_progress: '◐',
  blocked: '✕',
  done: '●',
}

export function TaskList({
  tasks,
  onRefresh,
}: {
  tasks: Task[]
  onRefresh: () => void
}) {
  const [showAdd, setShowAdd] = useState(false)
  const [newTitle, setNewTitle] = useState('')

  const handleAdd = async () => {
    if (!newTitle.trim()) return
    await api.createTask({ title: newTitle })
    setNewTitle('')
    setShowAdd(false)
    onRefresh()
  }

  const handleStatusChange = async (task: Task, status: string) => {
    await api.updateTask(task.id, { status })
    onRefresh()
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white">CEO Task List</h2>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="text-sm px-3 py-1 rounded bg-blue-600 hover:bg-blue-500 text-white"
        >
          + Add
        </button>
      </div>

      {showAdd && (
        <div className="mb-4 flex gap-2">
          <input
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
            placeholder="Task title..."
            className="flex-1 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
            autoFocus
          />
          <button
            onClick={handleAdd}
            className="px-3 py-2 bg-blue-600 rounded text-sm hover:bg-blue-500"
          >
            Save
          </button>
        </div>
      )}

      <div className="space-y-2">
        {tasks.length === 0 && (
          <p className="text-gray-500 text-sm py-4 text-center">
            No open tasks. Sync from Notion or add one manually.
          </p>
        )}
        {tasks.map((task) => (
          <div
            key={task.id}
            className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-3 hover:border-gray-600 transition-colors"
          >
            <div className="flex items-start gap-3">
              <button
                onClick={() =>
                  handleStatusChange(
                    task,
                    task.status === 'done' ? 'open' : 'done'
                  )
                }
                className="mt-0.5 text-gray-400 hover:text-green-400 transition-colors"
                title={task.status}
              >
                {statusIcons[task.status] || '○'}
              </button>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-white truncate">
                    {task.title}
                  </span>
                  <span
                    className={`text-xs px-1.5 py-0.5 rounded border ${urgencyColors[task.urgency]}`}
                  >
                    {task.urgency}
                  </span>
                </div>
                {task.priority_reason && (
                  <p className="text-xs text-gray-400 mt-1">
                    {task.priority_reason}
                  </p>
                )}
                {task.blocker && (
                  <p className="text-xs text-red-400 mt-1">
                    Blocked: {task.blocker}
                  </p>
                )}
                <div className="flex items-center gap-3 mt-2">
                  <span className="text-xs text-gray-500">
                    P{task.priority}
                  </span>
                  <span className="text-xs text-gray-600">{task.source}</span>
                  {task.due_date && (
                    <span className="text-xs text-yellow-500">
                      Due: {new Date(task.due_date).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

import { AgentStatus } from './components/AgentStatus'
import { ContextSearch } from './components/ContextSearch'
import { QuestionPanel } from './components/QuestionPanel'
import { SkillSidebar } from './components/SkillSidebar'
import { SyncBar } from './components/SyncBar'
import { TaskList } from './components/TaskList'
import { TimelineView } from './components/TimelineView'
import { useDashboard } from './hooks/useDashboard'

export default function App() {
  const { data, loading, error, refresh } = useDashboard()

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-gray-400 text-lg">Loading C-Brain...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 text-lg mb-2">Connection Error</p>
          <p className="text-gray-500 text-sm">{error}</p>
          <button
            onClick={refresh}
            className="mt-4 px-4 py-2 bg-blue-600 rounded text-sm hover:bg-blue-500 text-white"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  const d = data!

  const totalTasks = Object.values(d.task_counts).reduce(
    (a, b) => a + b,
    0
  )

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-bold text-white tracking-tight">
              C-Brain
            </h1>
            <span className="text-xs bg-blue-600/20 text-blue-400 px-2 py-0.5 rounded border border-blue-500/30">
              MVP
            </span>
            <span className="text-xs text-gray-500">
              {totalTasks} tasks · {d.questions.length} questions pending
            </span>
          </div>
          <SyncBar onRefresh={refresh} />
        </div>

        {/* Search */}
        <div className="mt-4">
          <ContextSearch />
        </div>
      </header>

      {/* Main grid */}
      <main className="grid grid-cols-1 lg:grid-cols-3 gap-6 p-6">
        {/* Left column — Tasks */}
        <div className="lg:col-span-1">
          <TaskList tasks={d.tasks} onRefresh={refresh} />
        </div>

        {/* Center column — Questions + Timeline */}
        <div className="lg:col-span-1 space-y-8">
          <QuestionPanel questions={d.questions} onRefresh={refresh} />
          <TimelineView events={d.timeline} />
        </div>

        {/* Right column — Skills + Agents */}
        <div className="lg:col-span-1 space-y-8">
          <SkillSidebar />
          <AgentStatus agents={d.agents} onRefresh={refresh} />
        </div>
      </main>
    </div>
  )
}

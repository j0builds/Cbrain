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
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-[var(--soma-dim)] text-sm tracking-wide">Initializing cortex...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-[var(--inhibit)] text-sm mb-3">Signal lost</p>
          <p className="text-[var(--soma-dim)] text-xs mb-4">{error}</p>
          <button onClick={refresh} className="text-xs px-4 py-2 bg-[var(--surface-2)] border border-[var(--border)] rounded-md text-[var(--soma)] hover:bg-[var(--surface-3)]">
            Reconnect
          </button>
        </div>
      </div>
    )
  }

  const d = data!
  const openCount = d.tasks.filter(t => t.status !== 'done').length

  return (
    <div className="min-h-screen">
      {/* ── Header ── */}
      <header className="border-b border-[var(--border-subtle)] px-8 py-5">
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-5">
            <div className="flex items-center gap-2.5">
              <div className="w-2 h-2 rounded-full bg-[var(--axon)]" />
              <h1 className="text-base font-semibold text-white tracking-tight">C-Brain</h1>
            </div>
            <div className="h-4 w-px bg-[var(--border)]" />
            <span className="text-xs text-[var(--soma-dim)] font-mono">
              {openCount} active signals &middot; {d.questions.length} pending
            </span>
          </div>
          <SyncBar onRefresh={refresh} />
        </div>
        <ContextSearch />
      </header>

      {/* ── Grid ── */}
      <main className="grid grid-cols-1 lg:grid-cols-12 gap-px bg-[var(--border-subtle)]">
        {/* Left — Tasks */}
        <div className="lg:col-span-4 bg-[var(--surface-0)] p-6">
          <TaskList tasks={d.tasks} onRefresh={refresh} />
        </div>

        {/* Center — Questions + Timeline */}
        <div className="lg:col-span-4 bg-[var(--surface-0)] p-6 space-y-8">
          <QuestionPanel questions={d.questions} onRefresh={refresh} />
          <div className="h-px bg-[var(--border-subtle)]" />
          <TimelineView events={d.timeline} />
        </div>

        {/* Right — Skills + Agents */}
        <div className="lg:col-span-4 bg-[var(--surface-0)] p-6 space-y-8">
          <SkillSidebar />
          <div className="h-px bg-[var(--border-subtle)]" />
          <AgentStatus agents={d.agents} onRefresh={refresh} />
        </div>
      </main>
    </div>
  )
}

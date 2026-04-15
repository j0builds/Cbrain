import { useState } from 'react'
import { AgentStatus as AgentStatusType, api } from '../api'

const AGENTS: Record<string, string> = {
  consolidator: 'Consolidator',
  enricher: 'Enricher',
  prioritizer: 'Prioritizer',
  question_generator: 'Questions',
}

export function AgentStatus({ agents, onRefresh }: { agents: AgentStatusType[]; onRefresh: () => void }) {
  const [triggering, setTriggering] = useState<string | null>(null)

  const handleTrigger = async (name: string) => {
    setTriggering(name)
    try {
      await api.triggerAgent(name)
      onRefresh()
    } catch (e) {
      console.error(e)
    } finally {
      setTriggering(null)
    }
  }

  return (
    <div>
      <span className="text-[11px] font-semibold tracking-[0.08em] uppercase text-[var(--soma-dim)] block mb-5">
        Autonomous Agents
      </span>

      <div className="space-y-1">
        {Object.entries(AGENTS).map(([name, label]) => {
          const agent = agents.find(a => a.agent_name === name)
          const statusColor = !agent ? 'var(--soma-dim)' :
            agent.status === 'completed' ? 'var(--axon)' :
            agent.status === 'failed' ? 'var(--inhibit)' : 'var(--myelin)'

          return (
            <div
              key={name}
              className="flex items-center justify-between px-3 py-2.5 rounded-md hover:bg-[var(--surface-1)] transition-colors group"
            >
              <div className="flex items-center gap-3">
                <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: statusColor }} />
                <div>
                  <span className="text-[13px] text-[var(--soma)]">{label}</span>
                  {agent ? (
                    <span className="font-mono text-[10px] text-[var(--soma-dim)] opacity-50 ml-2">
                      {new Date(agent.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  ) : (
                    <span className="font-mono text-[10px] text-[var(--soma-dim)] opacity-30 ml-2">idle</span>
                  )}
                </div>
              </div>
              <button
                onClick={() => handleTrigger(name)}
                disabled={triggering === name}
                className="text-[11px] px-2 py-1 border border-[var(--border)] rounded text-[var(--soma-dim)] opacity-0 group-hover:opacity-100 hover:text-[var(--soma)] hover:bg-[var(--surface-2)] disabled:opacity-30 transition-opacity"
              >
                {triggering === name ? '...' : 'trigger'}
              </button>
            </div>
          )
        })}
      </div>
    </div>
  )
}

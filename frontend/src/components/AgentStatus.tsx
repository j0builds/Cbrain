import { useState } from 'react'
import { AgentStatus as AgentStatusType, api } from '../api'

const AGENT_LABELS: Record<string, string> = {
  consolidator: 'Consolidator',
  enricher: 'Enricher',
  prioritizer: 'Prioritizer',
  question_generator: 'Questions',
}

export function AgentStatus({
  agents,
  onRefresh,
}: {
  agents: AgentStatusType[]
  onRefresh: () => void
}) {
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

  const agentNames = ['consolidator', 'enricher', 'prioritizer', 'question_generator']

  return (
    <div>
      <h2 className="text-lg font-semibold text-white mb-4">Agents</h2>
      <div className="space-y-2">
        {agentNames.map((name) => {
          const agent = agents.find((a) => a.agent_name === name)
          return (
            <div
              key={name}
              className="flex items-center justify-between bg-gray-800/50 border border-gray-700/50 rounded-lg px-3 py-2"
            >
              <div>
                <span className="text-sm text-white">
                  {AGENT_LABELS[name] || name}
                </span>
                {agent ? (
                  <div className="flex items-center gap-2 mt-0.5">
                    <span
                      className={`text-xs ${
                        agent.status === 'completed'
                          ? 'text-green-400'
                          : agent.status === 'failed'
                            ? 'text-red-400'
                            : 'text-yellow-400'
                      }`}
                    >
                      {agent.status === 'completed' ? '✓' : agent.status === 'failed' ? '✕' : '◐'}
                    </span>
                    <span className="text-xs text-gray-500">
                      {new Date(agent.started_at).toLocaleTimeString()}
                    </span>
                  </div>
                ) : (
                  <p className="text-xs text-gray-600">Never run</p>
                )}
              </div>
              <button
                onClick={() => handleTrigger(name)}
                disabled={triggering === name}
                className="text-xs px-2 py-1 bg-gray-700 rounded hover:bg-gray-600 text-gray-300 disabled:opacity-50"
              >
                {triggering === name ? '...' : '▶'}
              </button>
            </div>
          )
        })}
      </div>
    </div>
  )
}

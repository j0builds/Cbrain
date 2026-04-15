import { TimelineEvent } from '../api'

const typeColors: Record<string, string> = {
  sync: 'text-blue-400',
  task_created: 'text-green-400',
  enrichment: 'text-purple-400',
  consolidation: 'text-yellow-400',
  created: 'text-emerald-400',
  updated: 'text-orange-400',
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

export function TimelineView({ events }: { events: TimelineEvent[] }) {
  return (
    <div>
      <h2 className="text-lg font-semibold text-white mb-4">Timeline</h2>
      <div className="space-y-2">
        {events.length === 0 && (
          <p className="text-gray-500 text-sm py-4 text-center">
            No events yet. Sync data or run agents to populate.
          </p>
        )}
        {events.map((event) => (
          <div
            key={event.id}
            className="flex items-start gap-3 py-2 border-b border-gray-800/50 last:border-0"
          >
            <span className="text-xs text-gray-500 w-16 flex-shrink-0 pt-0.5">
              {timeAgo(event.created_at)}
            </span>
            <div className="min-w-0">
              <p className="text-sm text-gray-300">{event.summary}</p>
              <div className="flex items-center gap-2 mt-0.5">
                <span
                  className={`text-xs ${typeColors[event.event_type] || 'text-gray-500'}`}
                >
                  {event.event_type}
                </span>
                {event.actor && (
                  <span className="text-xs text-gray-600">{event.actor}</span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

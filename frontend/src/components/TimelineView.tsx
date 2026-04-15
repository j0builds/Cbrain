import { TimelineEvent } from '../api'

const typeColor: Record<string, string> = {
  sync: 'var(--axon)',
  task_created: 'var(--dendrite)',
  enrichment: 'var(--myelin)',
  consolidation: 'var(--myelin)',
  created: 'var(--axon)',
  updated: 'var(--dendrite)',
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'now'
  if (mins < 60) return `${mins}m`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h`
  return `${Math.floor(hours / 24)}d`
}

export function TimelineView({ events }: { events: TimelineEvent[] }) {
  return (
    <div>
      <span className="text-[11px] font-semibold tracking-[0.08em] uppercase text-[var(--soma-dim)] block mb-5">
        Signal History
      </span>

      {events.length === 0 ? (
        <p className="text-[var(--soma-dim)] text-xs py-6 text-center opacity-50">No signals recorded.</p>
      ) : (
        <div className="space-y-0">
          {events.map(event => (
            <div key={event.id} className="flex items-start gap-3 py-2">
              <span className="font-mono text-[10px] text-[var(--soma-dim)] opacity-50 w-8 text-right flex-shrink-0 pt-px">
                {timeAgo(event.created_at)}
              </span>
              <div
                className="w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0"
                style={{ backgroundColor: typeColor[event.event_type] || 'var(--soma-dim)' }}
              />
              <div className="min-w-0">
                <p className="text-[12px] text-[var(--soma)] leading-snug">{event.summary}</p>
                <span className="font-mono text-[10px] text-[var(--soma-dim)] opacity-40">
                  {event.event_type}{event.actor ? ` / ${event.actor}` : ''}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

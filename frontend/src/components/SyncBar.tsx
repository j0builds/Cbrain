import { useState } from 'react'
import { api } from '../api'

type SyncType = 'notion' | 'memory' | 'jopedia' | 'extract'

export function SyncBar({ onRefresh }: { onRefresh: () => void }) {
  const [syncing, setSyncing] = useState<string | null>(null)
  const [lastResult, setLastResult] = useState<string | null>(null)

  const handleSync = async (type: SyncType) => {
    setSyncing(type)
    setLastResult(null)
    try {
      let res: Record<string, unknown>
      if (type === 'notion') res = await api.syncNotion() as Record<string, unknown>
      else if (type === 'jopedia') res = await api.syncJopedia() as Record<string, unknown>
      else if (type === 'extract') res = await api.extractTasks() as Record<string, unknown>
      else res = await api.syncMemory() as Record<string, unknown>

      const parts = Object.entries(res)
        .filter(([k]) => !k.startsWith('error'))
        .map(([k, v]) => `${k}: ${v}`)
      setLastResult(parts.join(' | ') || 'done')
      if (res.error) setLastResult(String(res.error))
      onRefresh()
    } catch (e) {
      setLastResult(e instanceof Error ? e.message : 'failed')
    } finally {
      setSyncing(null)
    }
  }

  return (
    <div className="flex items-center gap-2 flex-wrap">
      {lastResult && (
        <span className="font-mono text-[10px] text-[var(--axon)] mr-1">{lastResult}</span>
      )}
      <button
        onClick={() => handleSync('extract')}
        disabled={syncing !== null}
        className="text-[11px] px-3 py-1.5 bg-[var(--dendrite)] rounded text-white font-medium hover:opacity-90 disabled:opacity-30"
      >
        {syncing === 'extract' ? 'Extracting...' : 'Extract Tasks'}
      </button>
      <button
        onClick={() => handleSync('jopedia')}
        disabled={syncing !== null}
        className="text-[11px] px-3 py-1.5 bg-[var(--surface-2)] border border-[var(--border)] rounded text-[var(--soma-dim)] hover:text-[var(--soma)] hover:bg-[var(--surface-3)] disabled:opacity-30"
      >
        {syncing === 'jopedia' ? 'Ingesting...' : 'Jopedia'}
      </button>
      <button
        onClick={() => handleSync('notion')}
        disabled={syncing !== null}
        className="text-[11px] px-3 py-1.5 bg-[var(--surface-2)] border border-[var(--border)] rounded text-[var(--soma-dim)] hover:text-[var(--soma)] hover:bg-[var(--surface-3)] disabled:opacity-30"
      >
        {syncing === 'notion' ? 'Syncing...' : 'Notion'}
      </button>
      <button
        onClick={() => handleSync('memory')}
        disabled={syncing !== null}
        className="text-[11px] px-3 py-1.5 bg-[var(--surface-2)] border border-[var(--border)] rounded text-[var(--soma-dim)] hover:text-[var(--soma)] hover:bg-[var(--surface-3)] disabled:opacity-30"
      >
        {syncing === 'memory' ? 'Syncing...' : 'Memory'}
      </button>
    </div>
  )
}

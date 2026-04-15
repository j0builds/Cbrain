import { useState } from 'react'
import { api } from '../api'

export function SyncBar({ onRefresh }: { onRefresh: () => void }) {
  const [syncing, setSyncing] = useState<string | null>(null)
  const [lastResult, setLastResult] = useState<string | null>(null)

  const handleSync = async (type: 'notion' | 'memory' | 'jopedia') => {
    setSyncing(type)
    setLastResult(null)
    try {
      let res: Record<string, unknown>
      if (type === 'notion') res = await api.syncNotion() as Record<string, unknown>
      else if (type === 'jopedia') res = await api.syncJopedia() as Record<string, unknown>
      else res = await api.syncMemory() as Record<string, unknown>

      const parts = Object.entries(res)
        .filter(([k]) => !k.startsWith('error'))
        .map(([k, v]) => `${v}`)
      setLastResult(parts.join(', ') || 'done')
      if (res.error) setLastResult(String(res.error))
      onRefresh()
    } catch (e) {
      setLastResult(e instanceof Error ? e.message : 'failed')
    } finally {
      setSyncing(null)
    }
  }

  return (
    <div className="flex items-center gap-2">
      {lastResult && (
        <span className="font-mono text-[10px] text-[var(--soma-dim)] opacity-60 mr-1">{lastResult}</span>
      )}
      <button
        onClick={() => handleSync('jopedia')}
        disabled={syncing !== null}
        className="text-[11px] px-3 py-1.5 bg-[var(--surface-2)] border border-[var(--border)] rounded text-[var(--dendrite)] hover:bg-[var(--surface-3)] disabled:opacity-30"
      >
        {syncing === 'jopedia' ? 'Ingesting...' : 'Ingest Jopedia'}
      </button>
      <button
        onClick={() => handleSync('notion')}
        disabled={syncing !== null}
        className="text-[11px] px-3 py-1.5 bg-[var(--surface-2)] border border-[var(--border)] rounded text-[var(--soma-dim)] hover:text-[var(--soma)] hover:bg-[var(--surface-3)] disabled:opacity-30"
      >
        {syncing === 'notion' ? 'Syncing...' : 'Sync Notion'}
      </button>
      <button
        onClick={() => handleSync('memory')}
        disabled={syncing !== null}
        className="text-[11px] px-3 py-1.5 bg-[var(--surface-2)] border border-[var(--border)] rounded text-[var(--soma-dim)] hover:text-[var(--soma)] hover:bg-[var(--surface-3)] disabled:opacity-30"
      >
        {syncing === 'memory' ? 'Syncing...' : 'Sync Memory'}
      </button>
    </div>
  )
}

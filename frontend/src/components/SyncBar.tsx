import { useState } from 'react'
import { api } from '../api'

export function SyncBar({ onRefresh }: { onRefresh: () => void }) {
  const [syncing, setSyncing] = useState<string | null>(null)

  const handleSync = async (type: 'notion' | 'memory') => {
    setSyncing(type)
    try {
      if (type === 'notion') {
        await api.syncNotion()
      } else {
        await api.syncMemory()
      }
      onRefresh()
    } catch (e) {
      console.error(e)
    } finally {
      setSyncing(null)
    }
  }

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={() => handleSync('notion')}
        disabled={syncing !== null}
        className="text-xs px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg hover:bg-gray-700 text-gray-300 disabled:opacity-50"
      >
        {syncing === 'notion' ? 'Syncing...' : 'Sync Notion'}
      </button>
      <button
        onClick={() => handleSync('memory')}
        disabled={syncing !== null}
        className="text-xs px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg hover:bg-gray-700 text-gray-300 disabled:opacity-50"
      >
        {syncing === 'memory' ? 'Syncing...' : 'Sync Memory'}
      </button>
    </div>
  )
}

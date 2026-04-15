import { useState } from 'react'
import { api } from '../api'

interface SearchResult {
  id: string
  title: string
  body: string
  entry_type: string
  importance_tier: string
  score: number
}

const tierColor: Record<string, string> = {
  critical: 'var(--inhibit)',
  high: 'var(--myelin)',
  medium: 'var(--dendrite)',
  low: 'var(--soma-dim)',
}

export function ContextSearch() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [searching, setSearching] = useState(false)

  const handleSearch = async () => {
    if (!query.trim()) return
    setSearching(true)
    try {
      const data = (await api.searchContext(query)) as SearchResult[]
      setResults(data)
    } catch (e) {
      console.error(e)
    } finally {
      setSearching(false)
    }
  }

  return (
    <div>
      <div className="flex gap-2">
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSearch()}
          placeholder="Query the cortex..."
          className="flex-1 bg-[var(--surface-1)] border border-[var(--border)] rounded-md px-4 py-2 text-[13px] text-[var(--soma)] placeholder:text-[var(--soma-dim)] placeholder:opacity-40 focus:outline-none focus:border-[var(--dendrite)]"
        />
        <button
          onClick={handleSearch}
          disabled={searching}
          className="px-4 py-2 bg-[var(--surface-2)] border border-[var(--border)] rounded-md text-[13px] text-[var(--soma-dim)] hover:text-[var(--soma)] hover:bg-[var(--surface-3)] disabled:opacity-30"
        >
          {searching ? '...' : 'Search'}
        </button>
      </div>

      {results.length > 0 && (
        <div className="mt-3 bg-[var(--surface-1)] border border-[var(--border-subtle)] rounded-lg divide-y divide-[var(--border-subtle)]">
          {results.slice(0, 8).map(r => (
            <div key={r.id} className="px-4 py-3">
              <div className="flex items-center gap-2">
                <span className="text-[13px] text-[var(--soma)] font-medium">{r.title}</span>
                <span className="font-mono text-[10px] text-[var(--soma-dim)] opacity-50">{r.entry_type}</span>
                <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: tierColor[r.importance_tier] || 'var(--soma-dim)' }} />
              </div>
              <p className="text-[11px] text-[var(--soma-dim)] mt-1 line-clamp-2 leading-relaxed">{r.body}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

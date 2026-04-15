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

  const tierColors: Record<string, string> = {
    critical: 'text-red-400',
    high: 'text-orange-400',
    medium: 'text-yellow-400',
    low: 'text-gray-400',
  }

  return (
    <div>
      <div className="flex gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          placeholder="Search brain..."
          className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
        />
        <button
          onClick={handleSearch}
          disabled={searching}
          className="px-4 py-2 bg-blue-600 rounded-lg text-sm hover:bg-blue-500 text-white disabled:opacity-50"
        >
          {searching ? '...' : 'Search'}
        </button>
      </div>

      {results.length > 0 && (
        <div className="mt-4 space-y-2">
          {results.map((r) => (
            <div
              key={r.id}
              className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-3"
            >
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-white">
                  {r.title}
                </span>
                <span className="text-xs bg-gray-700 px-1.5 py-0.5 rounded text-gray-400">
                  {r.entry_type}
                </span>
                <span
                  className={`text-xs ${tierColors[r.importance_tier]}`}
                >
                  {r.importance_tier}
                </span>
              </div>
              <p className="text-xs text-gray-400 mt-1 line-clamp-2">
                {r.body}
              </p>
              <span className="text-xs text-gray-600 mt-1 inline-block">
                Score: {r.score.toFixed(4)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

const BASE = '/api/v1'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export interface Task {
  id: string
  title: string
  description: string | null
  priority: number
  priority_reason: string | null
  urgency: string
  status: string
  blocker: string | null
  source: string
  due_date: string | null
  created_at: string
  updated_at: string
}

export interface Question {
  id: string
  question_text: string
  context: string | null
  generated_by: string
  priority: number
  status: string
  created_at: string
}

export interface TimelineEvent {
  id: string
  event_type: string
  summary: string
  source: string
  actor: string | null
  created_at: string
}

export interface AgentStatus {
  agent_name: string
  status: string
  started_at: string
  completed_at: string | null
  summary: string | null
}

export interface SkillInfo {
  id: string
  name: string
  display_name: string
  description: string
  execution_count: number
  last_executed_at: string | null
}

export interface Dashboard {
  tasks: Task[]
  questions: Question[]
  timeline: TimelineEvent[]
  agents: AgentStatus[]
  task_counts: Record<string, number>
}

export const api = {
  dashboard: () => request<Dashboard>('/dashboard'),
  tasks: (status?: string) => request<Task[]>(`/tasks${status ? `?status=${status}` : ''}`),
  createTask: (data: { title: string; description?: string; urgency?: string }) =>
    request<{ id: string }>('/tasks', { method: 'POST', body: JSON.stringify(data) }),
  updateTask: (id: string, data: Partial<Task>) =>
    request(`/tasks/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  questions: () => request<Question[]>('/questions'),
  answerQuestion: (id: string, answer_text: string) =>
    request(`/questions/${id}/answer`, { method: 'POST', body: JSON.stringify({ answer_text }) }),
  dismissQuestion: (id: string) =>
    request(`/questions/${id}/dismiss`, { method: 'POST' }),
  skills: () => request<SkillInfo[]>('/skills'),
  executeSkill: (id: string, input_data: Record<string, unknown> = {}) =>
    request(`/skills/${id}/execute`, { method: 'POST', body: JSON.stringify({ input_data }) }),
  searchContext: (q: string) => request(`/context/search?q=${encodeURIComponent(q)}`),
  agentStatus: () => request<Record<string, { last_run: AgentStatus | null }>>('/agents/status'),
  triggerAgent: (name: string) =>
    request(`/agents/${name}/trigger`, { method: 'POST' }),
  syncNotion: () => request('/sync/notion', { method: 'POST' }),
  syncMemory: () => request('/sync/memory', { method: 'POST' }),
}

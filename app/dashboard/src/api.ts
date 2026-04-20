import axios from 'axios'
import type {
  AuthResponse, Project, Contact, ApiKey, ApiKeyCreated,
  UserProfile, ConversationRecord, StatsOverview,
  DailyConversation, ProjectUsage,
  AccountConfig, AccountConfigCreate, PromptsUpdate,
} from './types'

export const api = axios.create({ baseURL: '/api/v1' })

// Interceptors are wired in main.ts after stores are created (avoids circular imports)

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authLogin = (email: string, password: string) =>
  api.post<AuthResponse>('/auth/login', { email, password })

export const authRegister = (email: string, password: string, name: string) =>
  api.post<AuthResponse>('/auth/register', { email, password, name })

export const authRefresh = (refresh_token: string) =>
  api.post<AuthResponse>('/auth/refresh', { refresh_token })

export const authResetPassword = (email: string) =>
  api.post('/auth/reset-password', { email })

export const authUpdatePassword = (access_token: string, password: string) =>
  api.post('/auth/update-password', { access_token, password })

export const authVerifyOtp = (email: string, token: string) =>
  api.post<AuthResponse>('/auth/verify-otp', { email, token })

export const authResendOtp = (email: string) =>
  api.post('/auth/resend-otp', { email })

// ── Projects ──────────────────────────────────────────────────────────────────
export const getProjects = () => api.get<Project[]>('/projects')

export const createProject = (name: string, description: string | null) =>
  api.post<Project>('/projects', { name, description })

export const updateProject = (id: string, name: string) =>
  api.patch<Project>(`/projects/${id}`, { name })

export const deleteProject = (id: string) => api.delete(`/projects/${id}`)

// ── API Keys ──────────────────────────────────────────────────────────────────
export const getProjectKeys = (pid: string) =>
  api.get<ApiKey[]>(`/projects/${pid}/keys`)

export const createProjectKey = (pid: string, name: string) =>
  api.post<ApiKeyCreated>(`/projects/${pid}/keys`, { name })

export const deleteProjectKey = (pid: string, keyId: string) =>
  api.delete(`/projects/${pid}/keys/${keyId}`)

// ── Contacts ──────────────────────────────────────────────────────────────────
export const getContacts = (pid: string) =>
  api.get<Contact[]>(`/projects/${pid}/contacts`)

export const deleteContact = (pid: string, cid: string) =>
  api.delete(`/projects/${pid}/contacts/${cid}/contact`)

// ── Profiles ──────────────────────────────────────────────────────────────────
export const getProfile = (pid: string, cid: string) =>
  api.get<UserProfile>(`/projects/${pid}/contacts/${cid}/profile`)

export const deleteProfile = (pid: string, cid: string) =>
  api.delete(`/projects/${pid}/contacts/${cid}/profile`)

export const extractSync = (pid: string, cid: string, force: boolean) =>
  api.post(`/projects/${pid}/contacts/${cid}/profile/extract/sync?force=${force}`)

export const compressProfile = (pid: string, cid: string) =>
  api.post(`/projects/${pid}/contacts/${cid}/profile/compress`)

export const exportContactProfile = (pid: string, cid: string) =>
  api.get(`/projects/${pid}/contacts/${cid}/profile/export`, { responseType: 'blob' })

export const exportAllProfiles = (pid: string) =>
  api.get(`/projects/${pid}/profiles/export`, { responseType: 'blob' })

// ── Conversations ─────────────────────────────────────────────────────────────
export const getConversations = (pid: string, cid: string) =>
  api.get<ConversationRecord[]>(`/projects/${pid}/contacts/${cid}/conversations?limit=100`)

export const deleteConversations = (pid: string, cid: string) =>
  api.delete(`/projects/${pid}/contacts/${cid}/conversations`)

// ── Config ────────────────────────────────────────────────────────────────────
export const getConfig = () => api.get<AccountConfig>('/config')

export const saveConfig = (data: AccountConfigCreate) =>
  api.put<AccountConfig>('/config', data)

export const updatePrompts = (data: PromptsUpdate) =>
  api.patch<AccountConfig>('/config/prompts', data)

export const regeneratePrompts = (comment?: string) =>
  api.post<AccountConfig>('/config/regenerate', { comment: comment ?? null })

export const deleteConfig = () => api.delete('/config')

// ── Stats ─────────────────────────────────────────────────────────────────────
export const getStatsOverview = () => api.get<StatsOverview>('/stats/overview')

export const getDailyConversations = () =>
  api.get<DailyConversation[]>('/stats/conversations/daily')

export const getUsageStats = () => api.get<ProjectUsage[]>('/stats/usage')

// ── Helpers ───────────────────────────────────────────────────────────────────
export function downloadBlob(blob: Blob, defaultFilename: string, contentDisposition?: string | null) {
  const match = contentDisposition?.match(/filename="([^"]+)"/)
  const filename = match?.[1] ?? defaultFilename
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export function fmtTokens(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
  return String(n)
}

export function timeAgo(iso: string | null): string {
  if (!iso) return '—'
  const d = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (d < 60) return 'just now'
  if (d < 3600) return `${Math.floor(d / 60)}m ago`
  if (d < 86400) return `${Math.floor(d / 3600)}h ago`
  return `${Math.floor(d / 86400)}d ago`
}

export function fmt(iso: string | null): string {
  return iso ? new Date(iso).toLocaleString() : '—'
}

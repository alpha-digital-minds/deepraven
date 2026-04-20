export interface Personal {
  name: string | null
  gender: string | null
  phone: string | null
  company: string | null
  role: string | null
  location: string | null
  delivery_address: string | null
}

export interface Preferences {
  communication_style: string | null
  best_contact_channel: string | null
  languages: string[]
}

export interface Sales {
  buying_persona: string | null
  pain_points: string[]
  objections_raised: string[]
  buying_triggers: string[]
  current_needs: string[]
  budget_range: string | null
  purchase_history: string[]
}

export interface Relationship {
  status: string | null
  last_contact_date: string | null
  personal_details: string[]
}

export interface Relative {
  relation: string
  name: string | null
  age: string | null
  gender: string | null
  preferences: string[]
  sizes: Record<string, string>
  notes: string | null
}

export interface UserProfile {
  personal: Personal
  preferences: Preferences
  sales: Sales
  relationship: Relationship
  relatives: Relative[]
  created_at: string | null
  updated_at: string | null
}

export interface Project {
  id: string
  name: string
  description: string | null
  created_at: string
}

export interface Contact {
  id: string
  external_id: string
  name: string | null
  company: string | null
  total_conversations: number
  unprocessed_count: number
  extraction_status: string
  last_contact_date: string | null
}

export interface ApiKey {
  id: string
  name: string
  prefix: string
  created_at: string
  last_used_at: string | null
  revoked_at: string | null
}

export interface ApiKeyCreated extends ApiKey {
  key: string
}

export interface Message {
  role: 'user' | 'assistant'
  content: string
}

export interface ConversationRecord {
  id: string
  messages: Message[]
  processed: boolean
  timestamp: string
}

export interface StatsOverview {
  projects: number
  contacts: number
  conversations: number
  total_tokens: number
}

export interface DailyConversation {
  date: string
  count: number
}

export interface ProjectUsage {
  project_name: string
  calls: number
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
}

export interface AuthResponse {
  access_token: string
  refresh_token: string | null
}

export interface AccountConfigCreate {
  profile_schema: Record<string, unknown>
  purpose_industry: string
  purpose_agent_type: string
  purpose_description: string
}

export interface AccountConfig extends AccountConfigCreate {
  id: string
  account_id: string
  prompt_extractor: string
  prompt_reviewer: string
  prompt_compressor: string
  created_at: string
  updated_at: string
}

export interface PromptsUpdate {
  prompt_extractor?: string
  prompt_reviewer?: string
  prompt_compressor?: string
}

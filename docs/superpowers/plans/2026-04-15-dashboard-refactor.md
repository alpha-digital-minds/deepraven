# Dashboard Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the monolithic 1995-line `app/static/dashboard.html` with a Vite + Vue 3 + TypeScript SFC app with URL-based navigation, Pinia stores, Vue Router, and Axios.

**Architecture:** Vite project lives in `app/dashboard/src/`, builds to `app/static/dist/`. FastAPI mounts `dist/` as a static directory and serves `index.html` for all `/dashboard/*` routes. The built `dist/` is committed so deployment needs no Node.js.

**Tech Stack:** Vite 5, Vue 3 (Composition API + `<script setup>`), TypeScript, Pinia, Vue Router 4, Axios, Chart.js 4

---

## File Map

| Action | Path | Purpose |
|---|---|---|
| Create | `app/dashboard/package.json` | npm dependencies |
| Create | `app/dashboard/vite.config.ts` | Vite config, base `/dashboard/`, outDir `../../static/dist` |
| Create | `app/dashboard/tsconfig.json` | TypeScript config |
| Create | `app/dashboard/index.html` | Vite HTML entry point |
| Create | `app/dashboard/src/main.ts` | App bootstrap |
| Create | `app/dashboard/src/App.vue` | Root component |
| Create | `app/dashboard/src/style.css` | Global CSS (migrated from dashboard.html) |
| Create | `app/dashboard/src/types.ts` | TypeScript interfaces |
| Create | `app/dashboard/src/api.ts` | Axios instance + all typed API calls |
| Create | `app/dashboard/src/router.ts` | Vue Router + auth guard |
| Create | `app/dashboard/src/composables/useToast.ts` | Toast state |
| Create | `app/dashboard/src/stores/auth.ts` | Auth store (JWT, login, logout) |
| Create | `app/dashboard/src/stores/app.ts` | App store (projects, contacts) |
| Create | `app/dashboard/src/components/ToastNotification.vue` | Toast UI |
| Create | `app/dashboard/src/components/AppHeader.vue` | Top bar + project switcher |
| Create | `app/dashboard/src/components/AppLayout.vue` | Authenticated shell |
| Create | `app/dashboard/src/components/LoginScreen.vue` | All auth forms |
| Create | `app/dashboard/src/components/HomeDashboard.vue` | Stats overview |
| Create | `app/dashboard/src/components/ContactSidebar.vue` | Contact list |
| Create | `app/dashboard/src/components/ProjectPanel.vue` | Project management shell |
| Create | `app/dashboard/src/components/ProjectKeysTab.vue` | API key CRUD |
| Create | `app/dashboard/src/components/ProjectIntegrationTab.vue` | Code snippets |
| Create | `app/dashboard/src/components/ProjectSettingsTab.vue` | Rename/delete project |
| Create | `app/dashboard/src/components/ContactDetail.vue` | Contact detail shell |
| Create | `app/dashboard/src/components/ProfileTab.vue` | Structured profile |
| Create | `app/dashboard/src/components/ConversationsTab.vue` | Conversation history |
| Modify | `app/main.py` | Serve dist/ instead of dashboard.html |
| Create | `app/static/dist/` | Vite build output (committed) |

---

### Task 1: Scaffold the Vite project

**Files:**
- Create: `app/dashboard/package.json`
- Create: `app/dashboard/vite.config.ts`
- Create: `app/dashboard/tsconfig.json`
- Create: `app/dashboard/index.html`

- [ ] **Step 1: Create package.json**

Create `app/dashboard/package.json`:

```json
{
  "name": "deepraven-dashboard",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "axios": "^1.7.2",
    "chart.js": "^4.4.3",
    "pinia": "^2.1.7",
    "vue": "^3.4.27",
    "vue-router": "^4.3.2"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.4",
    "typescript": "^5.2.2",
    "vite": "^5.2.0",
    "vue-tsc": "^2.0.11"
  }
}
```

- [ ] **Step 2: Create vite.config.ts**

Create `app/dashboard/vite.config.ts`:

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  base: '/dashboard/',
  build: {
    outDir: resolve(__dirname, '../../static/dist'),
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/api': 'http://localhost:5100',
      '/assets': 'http://localhost:5100',
    },
  },
})
```

- [ ] **Step 3: Create tsconfig.json**

Create `app/dashboard/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "module": "ESNext",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "preserve",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src/**/*.ts", "src/**/*.d.ts", "src/**/*.tsx", "src/**/*.vue"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 4: Create tsconfig.node.json**

Create `app/dashboard/tsconfig.node.json`:

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 5: Create index.html**

Create `app/dashboard/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>DeepRaven Dashboard</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

- [ ] **Step 6: Add node_modules to .gitignore**

Add to the repo's `.gitignore`:

```
app/dashboard/node_modules/
```

- [ ] **Step 7: Install dependencies**

```bash
cd app/dashboard
npm install
```

Expected: `node_modules/` created, no errors.

- [ ] **Step 8: Commit**

```bash
cd ../..
git add app/dashboard/ .gitignore
git commit -m "feat: scaffold Vite + Vue 3 + TS dashboard project"
```

---

### Task 2: Types, global CSS, and API layer

**Files:**
- Create: `app/dashboard/src/types.ts`
- Create: `app/dashboard/src/style.css`
- Create: `app/dashboard/src/api.ts`
- Create: `app/dashboard/src/composables/useToast.ts`

- [ ] **Step 1: Create types.ts**

Create `app/dashboard/src/types.ts`:

```typescript
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
```

- [ ] **Step 2: Create style.css**

Create `app/dashboard/src/style.css`. Copy the full CSS content from lines 9–511 of `app/static/dashboard.html` (everything inside the `<style>` tag). Then append these additional rules at the end:

```css
/* Vue Router */
a.router-link-active,
a.router-link-exact-active { text-decoration: none; }
```

- [ ] **Step 3: Create useToast.ts**

Create `app/dashboard/src/composables/useToast.ts`:

```typescript
import { reactive } from 'vue'

export interface Toast {
  id: number
  message: string
  type: 'info' | 'success' | 'error'
}

const toasts = reactive<Toast[]>([])
let _id = 0

export function useToast() {
  function toast(message: string, type: Toast['type'] = 'info', duration = 3500) {
    const id = ++_id
    toasts.push({ id, message, type })
    setTimeout(() => {
      const idx = toasts.findIndex(t => t.id === id)
      if (idx !== -1) toasts.splice(idx, 1)
    }, duration)
  }
  return { toasts, toast }
}
```

- [ ] **Step 4: Create api.ts**

Create `app/dashboard/src/api.ts`:

```typescript
import axios from 'axios'
import type {
  AuthResponse, Project, Contact, ApiKey, ApiKeyCreated,
  UserProfile, ConversationRecord, StatsOverview,
  DailyConversation, ProjectUsage,
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
```

- [ ] **Step 5: Commit**

```bash
git add app/dashboard/src/
git commit -m "feat: add types, CSS, API layer, and toast composable"
```

---

### Task 3: Pinia stores and router

**Files:**
- Create: `app/dashboard/src/stores/auth.ts`
- Create: `app/dashboard/src/stores/app.ts`
- Create: `app/dashboard/src/router.ts`

- [ ] **Step 1: Create auth store**

Create `app/dashboard/src/stores/auth.ts`:

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('dr_jwt'))
  const refreshToken = ref<string | null>(localStorage.getItem('dr_refresh'))
  const email = ref<string>(localStorage.getItem('dr_email') || '')

  const isAuthenticated = computed(() => !!token.value)

  function setTokens(access: string, refresh: string | null) {
    token.value = access
    if (refresh) refreshToken.value = refresh
    localStorage.setItem('dr_jwt', access)
    if (refresh) localStorage.setItem('dr_refresh', refresh)
  }

  function setEmail(e: string) {
    email.value = e
    localStorage.setItem('dr_email', e)
  }

  function logout() {
    token.value = null
    refreshToken.value = null
    email.value = ''
    localStorage.removeItem('dr_jwt')
    localStorage.removeItem('dr_refresh')
    localStorage.removeItem('dr_email')
  }

  return { token, refreshToken, email, isAuthenticated, setTokens, setEmail, logout }
})
```

- [ ] **Step 2: Create app store**

Create `app/dashboard/src/stores/app.ts`:

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Project, Contact } from '../types'

export const useAppStore = defineStore('app', () => {
  const projects = ref<Project[]>([])
  const contacts = ref<Contact[]>([])
  const contactsRefreshKey = ref(0)

  function setProjects(p: Project[]) { projects.value = p }
  function setContacts(c: Contact[]) { contacts.value = c }
  function refreshContacts() { contactsRefreshKey.value++ }

  return { projects, contacts, contactsRefreshKey, setProjects, setContacts, refreshContacts }
})
```

- [ ] **Step 3: Create router**

Create `app/dashboard/src/router.ts`:

```typescript
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from './stores/auth'

const router = createRouter({
  history: createWebHistory('/dashboard/'),
  linkActiveClass: 'active',
  linkExactActiveClass: 'active',
  routes: [
    {
      path: '/login',
      component: () => import('./components/LoginScreen.vue'),
    },
    {
      path: '/',
      component: () => import('./components/AppLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        { path: '', component: () => import('./components/HomeDashboard.vue') },
        { path: 'projects/:projectId', component: () => import('./components/ProjectPanel.vue') },
        {
          path: 'projects/:projectId/contacts/:contactId',
          component: () => import('./components/ContactDetail.vue'),
        },
      ],
    },
  ],
})

router.beforeEach(to => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.path === '/login' && auth.isAuthenticated) {
    return { path: '/' }
  }
})

export default router
```

- [ ] **Step 4: Commit**

```bash
git add app/dashboard/src/
git commit -m "feat: add Pinia stores and Vue Router"
```

---

### Task 4: App shell (main.ts, App.vue, ToastNotification.vue)

**Files:**
- Create: `app/dashboard/src/main.ts`
- Create: `app/dashboard/src/App.vue`
- Create: `app/dashboard/src/components/ToastNotification.vue`

- [ ] **Step 1: Create main.ts**

Create `app/dashboard/src/main.ts`:

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { api } from './api'
import { useAuthStore } from './stores/auth'
import './style.css'

const pinia = createPinia()
const app = createApp(App)
app.use(pinia)
app.use(router)

// Wire Axios interceptors after Pinia is active
let _refreshPromise: Promise<void> | null = null

api.interceptors.request.use(config => {
  const auth = useAuthStore()
  if (auth.token) config.headers.Authorization = `Bearer ${auth.token}`
  return config
})

api.interceptors.response.use(
  res => res,
  async error => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const auth = useAuthStore()
      if (auth.refreshToken) {
        if (!_refreshPromise) {
          _refreshPromise = api
            .post('/auth/refresh', { refresh_token: auth.refreshToken }, { _retry: true } as never)
            .then(r => auth.setTokens(r.data.access_token, r.data.refresh_token))
            .catch(() => { auth.logout(); router.push('/login') })
            .finally(() => { _refreshPromise = null })
        }
        await _refreshPromise
        if (auth.token) {
          original.headers.Authorization = `Bearer ${auth.token}`
          return api(original)
        }
      } else {
        auth.logout()
        router.push('/login')
      }
    }
    return Promise.reject(error)
  },
)

app.mount('#app')
```

- [ ] **Step 2: Create App.vue**

Create `app/dashboard/src/App.vue`:

```vue
<template>
  <RouterView />
  <ToastNotification />
</template>

<script setup lang="ts">
import ToastNotification from './components/ToastNotification.vue'
</script>
```

- [ ] **Step 3: Create ToastNotification.vue**

Create `app/dashboard/src/components/ToastNotification.vue`:

```vue
<template>
  <div id="toasts">
    <div
      v-for="t in toasts"
      :key="t.id"
      :class="`toast toast-${t.type}`"
    >{{ t.message }}</div>
  </div>
</template>

<script setup lang="ts">
import { useToast } from '../composables/useToast'
const { toasts } = useToast()
</script>
```

- [ ] **Step 4: Verify dev server starts**

```bash
cd app/dashboard
npm run dev
```

Expected: Vite starts at `http://localhost:5173`. Browser shows blank page (no components yet). No TypeScript errors.

- [ ] **Step 5: Commit**

```bash
cd ../..
git add app/dashboard/src/
git commit -m "feat: add app shell, main.ts, Axios interceptors"
```

---

### Task 5: AppHeader and AppLayout

**Files:**
- Create: `app/dashboard/src/components/AppHeader.vue`
- Create: `app/dashboard/src/components/AppLayout.vue`

- [ ] **Step 1: Create AppHeader.vue**

Create `app/dashboard/src/components/AppHeader.vue`:

```vue
<template>
  <header>
    <RouterLink to="/">
      <img class="logo" src="/assets/logo.png" alt="DeepRaven" />
    </RouterLink>
    <h1>DeepRaven</h1>
    <div class="spacer" />

    <!-- Project picker -->
    <div class="proj-picker" id="proj-picker">
      <div class="proj-dropdown" id="proj-dropdown" :class="{ open: dropdownOpen }">
        <button class="proj-picker-btn" @click.stop="dropdownOpen = !dropdownOpen">
          <span id="proj-picker-label">{{ selectedProject?.name ?? 'Select a project' }}</span>
          <span class="proj-dd-arrow">▾</span>
        </button>
        <div class="proj-dd-menu">
          <div
            v-for="p in appStore.projects"
            :key="p.id"
            class="proj-dd-item"
            :class="{ active: p.id === route.params.projectId }"
            @click="selectProject(p.id)"
          >{{ p.name }}</div>
          <div class="proj-dd-divider" />
          <div class="proj-dd-item proj-dd-new" @click="showCreateModal = true">+ New Project</div>
        </div>
      </div>
    </div>

    <div class="account-info" id="account-info">
      <span>{{ authStore.email }}</span>
      <button class="btn-sm" @click="doLogout">Sign out</button>
    </div>
  </header>

  <!-- New project modal -->
  <Teleport to="body">
    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal">
        <h3>New Project</h3>
        <div class="form-group">
          <label>Project Name</label>
          <input v-model="newProjectName" type="text" placeholder="e.g. Sales Team EU" style="width:100%;padding:9px 12px;border:1px solid var(--border);border-radius:7px;font-size:14px;outline:none" />
        </div>
        <div class="form-group">
          <label>Description (optional)</label>
          <input v-model="newProjectDesc" type="text" placeholder="What is this project for?" style="width:100%;padding:9px 12px;border:1px solid var(--border);border-radius:7px;font-size:14px;outline:none" />
        </div>
        <div class="modal-actions">
          <button class="btn-sm" @click="showCreateModal = false">Cancel</button>
          <button class="btn-sm primary" :disabled="creating" @click="doCreateProject">
            {{ creating ? 'Creating…' : 'Create Project' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useAppStore } from '../stores/app'
import { createProject, getProjects } from '../api'
import { useToast } from '../composables/useToast'

const authStore = useAuthStore()
const appStore = useAppStore()
const router = useRouter()
const route = useRoute()
const { toast } = useToast()

const dropdownOpen = ref(false)
const showCreateModal = ref(false)
const newProjectName = ref('')
const newProjectDesc = ref('')
const creating = ref(false)

const selectedProject = computed(() =>
  appStore.projects.find(p => p.id === route.params.projectId)
)

function closeDropdown() { dropdownOpen.value = false }
onMounted(() => document.addEventListener('click', closeDropdown))
onUnmounted(() => document.removeEventListener('click', closeDropdown))

async function selectProject(id: string) {
  dropdownOpen.value = false
  await router.push(`/projects/${id}`)
}

async function doCreateProject() {
  if (!newProjectName.value.trim()) { toast('Project name is required', 'error'); return }
  creating.value = true
  try {
    await createProject(newProjectName.value.trim(), newProjectDesc.value.trim() || null)
    const res = await getProjects()
    appStore.setProjects(res.data)
    showCreateModal.value = false
    newProjectName.value = ''
    newProjectDesc.value = ''
    toast('Project created!', 'success')
  } catch {
    toast('Failed to create project', 'error')
  } finally {
    creating.value = false
  }
}

function doLogout() {
  authStore.logout()
  router.push('/login')
}
</script>
```

- [ ] **Step 2: Create AppLayout.vue**

Create `app/dashboard/src/components/AppLayout.vue`:

```vue
<template>
  <AppHeader />
  <div id="app-layout" class="visible">
    <ContactSidebar />
    <main id="main">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import AppHeader from './AppHeader.vue'
import ContactSidebar from './ContactSidebar.vue'
import { getProjects } from '../api'
import { useAppStore } from '../stores/app'

const appStore = useAppStore()

onMounted(async () => {
  try {
    const res = await getProjects()
    appStore.setProjects(res.data)
  } catch { /* auth errors handled by interceptor */ }
})
</script>
```

- [ ] **Step 3: Commit**

```bash
git add app/dashboard/src/
git commit -m "feat: add AppHeader and AppLayout components"
```

---

### Task 6: LoginScreen

**Files:**
- Create: `app/dashboard/src/components/LoginScreen.vue`

- [ ] **Step 1: Create LoginScreen.vue**

Create `app/dashboard/src/components/LoginScreen.vue`:

```vue
<template>
  <div id="login-screen">
    <div class="login-card">
      <div class="login-logo">
        <img src="/assets/logo.png" alt="DeepRaven" />
      </div>
      <h2 id="auth-title">{{ title }}</h2>
      <p class="sub" id="auth-sub">{{ subtitle }}</p>

      <!-- Name (register only) -->
      <div v-if="mode === 'register'" class="form-group">
        <label>Name</label>
        <input v-model="name" type="text" placeholder="Your name" />
      </div>

      <!-- Email -->
      <div v-if="mode !== 'reset' && mode !== 'otp'" class="form-group">
        <label>Email</label>
        <input v-model="email" type="email" placeholder="you@example.com" @keydown.enter="submit" />
      </div>

      <!-- Password -->
      <div v-if="mode === 'login' || mode === 'register' || mode === 'reset'" class="form-group" id="password-group">
        <label id="password-label">{{ mode === 'reset' ? 'New Password' : 'Password' }}</label>
        <input v-model="password" type="password" placeholder="••••••••" @keydown.enter="submit" />
      </div>

      <!-- Confirm password (reset only) -->
      <div v-if="mode === 'reset'" class="form-group">
        <label>Confirm Password</label>
        <input v-model="confirmPassword" type="password" placeholder="••••••••" @keydown.enter="submit" />
      </div>

      <!-- Forgot link (login only) -->
      <div v-if="mode === 'login'" class="forgot-link">
        <a @click="mode = 'forgot'">Forgot password?</a>
      </div>

      <!-- OTP input -->
      <div v-if="mode === 'otp'" class="form-group">
        <label>6-digit code</label>
        <input v-model="otp" type="text" maxlength="6" placeholder="123456" @keydown.enter="submit" />
      </div>

      <p v-if="errorMsg" class="login-error">{{ errorMsg }}</p>
      <p v-if="okMsg" class="login-ok">{{ okMsg }}</p>

      <button class="login-btn" :disabled="loading" @click="submit">
        {{ btnLabel }}
      </button>

      <!-- Resend OTP -->
      <div v-if="mode === 'otp'" style="text-align:center;margin-top:12px;font-size:13px;color:var(--muted)">
        Didn't get a code? <a style="color:var(--primary);cursor:pointer" @click="doResendOtp">Resend</a>
      </div>

      <!-- Switch between login / register / forgot -->
      <div v-if="mode !== 'reset' && mode !== 'otp'" class="login-switch">
        <template v-if="mode === 'login'">
          Don't have an account? <a @click="mode = 'register'">Sign up</a>
        </template>
        <template v-else-if="mode === 'register'">
          Already have an account? <a @click="mode = 'login'">Sign in</a>
        </template>
        <template v-else-if="mode === 'forgot'">
          Remember your password? <a @click="mode = 'login'">Sign in</a>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import {
  authLogin, authRegister, authResetPassword,
  authUpdatePassword, authVerifyOtp, authResendOtp,
} from '../api'

type Mode = 'login' | 'register' | 'forgot' | 'otp' | 'reset'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const mode = ref<Mode>('login')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const name = ref('')
const otp = ref('')
const otpEmail = ref('')
const recoveryToken = ref<string | null>(null)
const loading = ref(false)
const errorMsg = ref('')
const okMsg = ref('')

const title = computed(() => ({
  login: 'Welcome back',
  register: 'Create account',
  forgot: 'Reset password',
  otp: 'Check your email',
  reset: 'Set new password',
}[mode.value]))

const subtitle = computed(() => ({
  login: 'Sign in to your account',
  register: 'Start your free account',
  forgot: "Enter your email and we'll send a reset link.",
  otp: `We sent a 6-digit code to ${otpEmail.value}`,
  reset: 'Enter your new password below.',
}[mode.value]))

const btnLabel = computed(() => {
  if (loading.value) return { login: 'Signing in…', register: 'Creating…', forgot: 'Sending…', otp: 'Verifying…', reset: 'Updating…' }[mode.value]
  return { login: 'Sign in', register: 'Create account', forgot: 'Send reset link', otp: 'Verify', reset: 'Update password' }[mode.value]
})

onMounted(() => {
  // Handle password reset link: /dashboard/login#type=recovery&access_token=...
  const hash = new URLSearchParams(window.location.hash.replace(/^#/, ''))
  if (hash.get('type') === 'recovery' && hash.get('access_token')) {
    recoveryToken.value = hash.get('access_token')
    mode.value = 'reset'
    history.replaceState(null, '', '/dashboard/login')
    return
  }
  // Handle ?confirmed=1 from email confirmation redirect
  if (route.query.confirmed === '1') {
    okMsg.value = 'Email confirmed! You can now sign in.'
    history.replaceState(null, '', '/dashboard/login')
  }
})

function clearMessages() { errorMsg.value = ''; okMsg.value = '' }

async function submit() {
  clearMessages()
  loading.value = true
  try {
    if (mode.value === 'login') {
      if (!email.value || !password.value) { errorMsg.value = 'Email and password are required'; return }
      const res = await authLogin(email.value, password.value)
      authStore.setTokens(res.data.access_token, res.data.refresh_token)
      authStore.setEmail(email.value)
      const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
      router.push(redirect)

    } else if (mode.value === 'register') {
      if (!email.value || !password.value) { errorMsg.value = 'Email and password are required'; return }
      const res = await authRegister(email.value, password.value, name.value || email.value)
      if (!res.data.access_token) {
        otpEmail.value = email.value
        mode.value = 'otp'
        return
      }
      authStore.setTokens(res.data.access_token, res.data.refresh_token)
      authStore.setEmail(email.value)
      router.push('/')

    } else if (mode.value === 'forgot') {
      if (!email.value) { errorMsg.value = 'Email is required'; return }
      await authResetPassword(email.value)
      okMsg.value = 'Reset link sent! Check your inbox.'

    } else if (mode.value === 'otp') {
      if (otp.value.length !== 6) { errorMsg.value = 'Enter the 6-digit code from your email'; return }
      const res = await authVerifyOtp(otpEmail.value, otp.value)
      authStore.setTokens(res.data.access_token, res.data.refresh_token)
      authStore.setEmail(otpEmail.value)
      router.push('/')

    } else if (mode.value === 'reset') {
      if (!password.value) { errorMsg.value = 'Password is required'; return }
      if (password.value !== confirmPassword.value) { errorMsg.value = 'Passwords do not match'; return }
      if (password.value.length < 6) { errorMsg.value = 'Password must be at least 6 characters'; return }
      await authUpdatePassword(recoveryToken.value!, password.value)
      okMsg.value = 'Password updated! Signing you in…'
      authStore.setTokens(recoveryToken.value!, null)
      setTimeout(() => router.push('/'), 1500)
    }
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    errorMsg.value = msg ?? 'Something went wrong'
  } finally {
    loading.value = false
  }
}

async function doResendOtp() {
  clearMessages()
  try {
    await authResendOtp(otpEmail.value)
    okMsg.value = 'Code resent! Check your inbox.'
  } catch {
    errorMsg.value = 'Failed to resend code'
  }
}
</script>
```

- [ ] **Step 2: Commit**

```bash
git add app/dashboard/src/
git commit -m "feat: add LoginScreen with all auth modes"
```

---

### Task 7: HomeDashboard

**Files:**
- Create: `app/dashboard/src/components/HomeDashboard.vue`

- [ ] **Step 1: Create HomeDashboard.vue**

Create `app/dashboard/src/components/HomeDashboard.vue`:

```vue
<template>
  <div class="home-panel">
    <div class="home-title">Overview</div>
    <div class="home-sub">Welcome back, {{ authStore.email }}</div>

    <div class="stat-cards">
      <div v-if="loading" v-for="i in 4" :key="i" class="stat-card">
        <div class="sc-label" style="background:#f1f5f9;width:60%;height:10px;border-radius:4px" />
        <div class="sc-value" style="background:#f1f5f9;width:40%;height:28px;border-radius:4px;margin-top:8px" />
      </div>
      <template v-else>
        <div class="stat-card sc-blue">
          <div class="sc-label">Projects</div>
          <div class="sc-value">{{ stats?.projects ?? 0 }}</div>
          <div class="sc-sub">active projects</div>
        </div>
        <div class="stat-card sc-green">
          <div class="sc-label">Contacts</div>
          <div class="sc-value">{{ (stats?.contacts ?? 0).toLocaleString() }}</div>
          <div class="sc-sub">tracked contacts</div>
        </div>
        <div class="stat-card sc-amber">
          <div class="sc-label">Conversations</div>
          <div class="sc-value">{{ (stats?.conversations ?? 0).toLocaleString() }}</div>
          <div class="sc-sub">total ingested</div>
        </div>
        <div class="stat-card sc-purple">
          <div class="sc-label">LLM Tokens</div>
          <div class="sc-value">{{ fmtTokens(stats?.total_tokens ?? 0) }}</div>
          <div class="sc-sub">tokens consumed</div>
        </div>
      </template>
    </div>

    <div class="home-section">
      <div class="home-section-title">💬 Conversations — last 30 days</div>
      <div class="chart-card">
        <canvas ref="chartCanvas" height="90" />
      </div>
    </div>

    <div class="home-section">
      <div class="home-section-title">⚡ LLM Usage by Project</div>
      <div class="chart-card" style="padding:0;overflow:hidden">
        <div style="padding:16px 22px">
          <p v-if="loading" style="color:var(--muted);font-size:13px">Loading…</p>
          <p v-else-if="!usage.length" style="color:var(--muted);font-size:13px">
            No LLM usage recorded yet. Usage is logged when profiles are extracted.
          </p>
          <table v-else class="usage-table">
            <thead>
              <tr>
                <th>Project</th><th>Calls</th><th>Prompt</th>
                <th>Completion</th><th>Total tokens</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in usage" :key="r.project_name">
                <td><span class="proj-name">{{ r.project_name }}</span></td>
                <td>{{ Number(r.calls).toLocaleString() }}</td>
                <td>{{ fmtTokens(Number(r.prompt_tokens)) }}</td>
                <td>{{ fmtTokens(Number(r.completion_tokens)) }}</td>
                <td>
                  <div class="usage-bar-wrap">
                    <div class="usage-bar">
                      <div class="usage-bar-fill" :style="{ width: usagePct(r) + '%' }" />
                    </div>
                    <span style="min-width:42px">{{ fmtTokens(Number(r.total_tokens)) }}</span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import {
  Chart, CategoryScale, LinearScale, BarElement, Tooltip,
} from 'chart.js'
import { useAuthStore } from '../stores/auth'
import { getStatsOverview, getDailyConversations, getUsageStats, fmtTokens } from '../api'
import type { StatsOverview, ProjectUsage } from '../types'

Chart.register(CategoryScale, LinearScale, BarElement, Tooltip)

const authStore = useAuthStore()
const chartCanvas = ref<HTMLCanvasElement | null>(null)
const loading = ref(true)
const stats = ref<StatsOverview | null>(null)
const usage = ref<ProjectUsage[]>([])
let chart: Chart | null = null

const maxTokens = ref(1)
function usagePct(r: ProjectUsage) {
  return Math.round((Number(r.total_tokens) / maxTokens.value) * 100)
}

onMounted(async () => {
  try {
    const [sRes, dRes, uRes] = await Promise.all([
      getStatsOverview(),
      getDailyConversations(),
      getUsageStats(),
    ])
    stats.value = sRes.data
    usage.value = uRes.data
    maxTokens.value = Math.max(...uRes.data.map(r => Number(r.total_tokens)), 1)
    renderChart(dRes.data)
  } catch { /* interceptor handles 401 */ } finally {
    loading.value = false
  }
})

onUnmounted(() => { chart?.destroy() })

function renderChart(daily: { date: string; count: number }[]) {
  if (!chartCanvas.value) return
  const today = new Date()
  const map: Record<string, number> = {}
  daily.forEach(r => { map[r.date] = Number(r.count) })
  const labels: string[] = []
  const data: number[] = []
  for (let i = 29; i >= 0; i--) {
    const d = new Date(today)
    d.setDate(d.getDate() - i)
    const key = d.toISOString().slice(0, 10)
    labels.push(key.slice(5))
    data.push(map[key] || 0)
  }
  chart?.destroy()
  chart = new Chart(chartCanvas.value, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Conversations',
        data,
        backgroundColor: 'rgba(99,102,241,.2)',
        borderColor: '#6366f1',
        borderWidth: 1.5,
        borderRadius: 3,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { font: { size: 10 }, maxRotation: 45 }, grid: { display: false } },
        y: { beginAtZero: true, ticks: { precision: 0, font: { size: 10 } }, grid: { color: '#f1f5f9' } },
      },
    },
  })
}
</script>
```

- [ ] **Step 2: Commit**

```bash
git add app/dashboard/src/
git commit -m "feat: add HomeDashboard with stats and chart"
```

---

### Task 8: ContactSidebar

**Files:**
- Create: `app/dashboard/src/components/ContactSidebar.vue`

- [ ] **Step 1: Create ContactSidebar.vue**

Create `app/dashboard/src/components/ContactSidebar.vue`:

```vue
<template>
  <div class="sidebar">
    <div class="sidebar-header">
      <span class="contacts-label">{{ projectId ? 'Contacts' : 'Contacts' }}</span>
      <input
        v-if="projectId"
        v-model="search"
        class="contact-search"
        placeholder="Search…"
        @input="filterContacts"
      />
    </div>

    <!-- Project nav (keys / integration / settings) -->
    <div v-if="projectId" class="sidebar-proj-nav" id="sidebar-proj-nav">
      <RouterLink :to="`/projects/${projectId}`" class="spn-item" id="spn-keys">
        🔑 API Keys
      </RouterLink>
      <RouterLink :to="`/projects/${projectId}?tab=integration`" class="spn-item" id="spn-integration">
        🔗 Integration
      </RouterLink>
      <RouterLink :to="`/projects/${projectId}?tab=settings`" class="spn-item" id="spn-settings">
        ⚙ Settings
      </RouterLink>
    </div>

    <div id="contacts-list" class="contacts-list">
      <div v-if="!projectId" style="padding:16px;text-align:center;color:#94a3b8;font-size:13px">
        Select a project
      </div>
      <div v-else-if="loadingContacts" style="padding:16px;text-align:center">
        <span class="spin" style="width:20px;height:20px;border-width:2px" />
      </div>
      <div v-else-if="!filtered.length" style="padding:16px;text-align:center;color:#94a3b8;font-size:13px">
        No contacts yet
      </div>
      <div
        v-for="c in filtered"
        :key="c.id"
        class="contact-card"
        :class="{ active: c.id === contactId }"
        @click="router.push(`/projects/${projectId}/contacts/${c.id}`)"
      >
        <div class="cc-name">{{ c.name || c.external_id }}</div>
        <div class="cc-id">{{ c.external_id }}</div>
        <div class="cc-badges">
          <span v-if="c.company" class="badge b-gray">{{ c.company }}</span>
          <span class="badge b-gray">💬 {{ c.total_conversations }}</span>
          <span v-if="c.unprocessed_count > 0" class="badge b-amber">⚡ {{ c.unprocessed_count }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getContacts } from '../api'
import { useAppStore } from '../stores/app'
import type { Contact } from '../types'

const router = useRouter()
const route = useRoute()
const appStore = useAppStore()

const search = ref('')
const loadingContacts = ref(false)
const allContacts = ref<Contact[]>([])

const projectId = computed(() => route.params.projectId as string | undefined)
const contactId = computed(() => route.params.contactId as string | undefined)

const filtered = computed(() => {
  const q = search.value.toLowerCase()
  if (!q) return allContacts.value
  return allContacts.value.filter(c =>
    c.external_id.toLowerCase().includes(q) ||
    (c.name ?? '').toLowerCase().includes(q) ||
    (c.company ?? '').toLowerCase().includes(q)
  )
})

function filterContacts() { /* reactivity handles it */ }

async function loadContacts(pid: string) {
  loadingContacts.value = true
  try {
    const res = await getContacts(pid)
    allContacts.value = res.data
    appStore.setContacts(res.data)
  } catch { allContacts.value = [] } finally {
    loadingContacts.value = false
  }
}

watch(projectId, pid => {
  if (pid) { search.value = ''; loadContacts(pid) }
  else allContacts.value = []
}, { immediate: true })

// Refresh when appStore signals (e.g. after extract)
watch(() => appStore.contactsRefreshKey, () => {
  if (projectId.value) loadContacts(projectId.value)
})

// Auto-refresh every 15 seconds
let timer: ReturnType<typeof setInterval> | null = null
onMounted(() => {
  timer = setInterval(() => {
    if (projectId.value) loadContacts(projectId.value)
  }, 15_000)
})
onUnmounted(() => { if (timer) clearInterval(timer) })
</script>
```

- [ ] **Step 2: Commit**

```bash
git add app/dashboard/src/
git commit -m "feat: add ContactSidebar with auto-refresh"
```

---

### Task 9: ProjectPanel (Keys, Integration, Settings tabs)

**Files:**
- Create: `app/dashboard/src/components/ProjectPanel.vue`
- Create: `app/dashboard/src/components/ProjectKeysTab.vue`
- Create: `app/dashboard/src/components/ProjectIntegrationTab.vue`
- Create: `app/dashboard/src/components/ProjectSettingsTab.vue`

- [ ] **Step 1: Create ProjectPanel.vue**

Create `app/dashboard/src/components/ProjectPanel.vue`:

```vue
<template>
  <div v-if="project" class="project-overview">
    <div class="po-header">
      <div class="po-title">{{ project.name }}</div>
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
        <span style="font-size:11px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.05em">Project ID</span>
        <span style="font-family:monospace;font-size:12px;background:#f1f5f9;padding:2px 8px;border-radius:4px;user-select:all">{{ projectId }}</span>
        <button class="copy-btn" style="padding:2px 8px;font-size:11px" @click="copyText(projectId, $event)">Copy</button>
        <button class="btn-sm" style="margin-left:8px" @click="doExportAll">↓ Export All Profiles</button>
      </div>
      <div class="tabs">
        <div class="tab" :class="{ active: activeTab === 'keys' }" @click="activeTab = 'keys'">API Keys</div>
        <div class="tab" :class="{ active: activeTab === 'integration' }" @click="activeTab = 'integration'">Integration</div>
        <div class="tab" :class="{ active: activeTab === 'settings' }" @click="activeTab = 'settings'">Settings</div>
      </div>
    </div>
    <div class="po-body">
      <ProjectKeysTab v-if="activeTab === 'keys'" :project-id="projectId" />
      <ProjectIntegrationTab v-else-if="activeTab === 'integration'" :project-id="projectId" />
      <ProjectSettingsTab v-else-if="activeTab === 'settings'" :project-id="projectId" :project-name="project.name" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '../stores/app'
import { exportAllProfiles, downloadBlob } from '../api'
import { useToast } from '../composables/useToast'
import ProjectKeysTab from './ProjectKeysTab.vue'
import ProjectIntegrationTab from './ProjectIntegrationTab.vue'
import ProjectSettingsTab from './ProjectSettingsTab.vue'

const route = useRoute()
const appStore = useAppStore()
const { toast } = useToast()

const projectId = computed(() => route.params.projectId as string)
const project = computed(() => appStore.projects.find(p => p.id === projectId.value))
const activeTab = ref<'keys' | 'integration' | 'settings'>('keys')

// Switch tab from query param (used by sidebar links)
watch(() => route.query.tab, tab => {
  if (tab === 'integration' || tab === 'settings') activeTab.value = tab
  else activeTab.value = 'keys'
}, { immediate: true })

function copyText(text: string, event: MouseEvent) {
  const btn = event.currentTarget as HTMLButtonElement
  navigator.clipboard.writeText(text).then(() => {
    const orig = btn.textContent!
    btn.textContent = 'Copied!'
    btn.style.cssText = 'background:var(--primary);color:white;border-color:var(--primary)'
    setTimeout(() => { btn.textContent = orig; btn.style.cssText = '' }, 1600)
  }).catch(() => toast('Copy failed', 'error'))
}

async function doExportAll() {
  toast('Preparing export…', 'info')
  try {
    const res = await exportAllProfiles(projectId.value)
    downloadBlob(res.data, 'profiles.json', res.headers['content-disposition'])
    toast('All profiles exported', 'success')
  } catch { toast('Export failed', 'error') }
}
</script>
```

- [ ] **Step 2: Create ProjectKeysTab.vue**

Create `app/dashboard/src/components/ProjectKeysTab.vue`:

```vue
<template>
  <div class="po-section">
    <div class="po-section-title">API Keys</div>
    <div v-if="loadingKeys" style="padding:8px 0">Loading…</div>
    <div v-else-if="!keys.length" style="color:var(--muted);font-size:13px">
      No API keys yet — create your first key below.
    </div>
    <template v-else>
      <div v-for="k in keys" :key="k.id" class="key-row" :class="{ 'key-revoked': k.revoked_at }">
        <div style="flex:1;min-width:0">
          <div class="key-name">{{ k.name }}</div>
          <div class="key-meta">
            Created {{ fmt(k.created_at) }}
            <template v-if="k.last_used_at"> · Last used {{ timeAgo(k.last_used_at) }}</template>
            <template v-if="k.revoked_at"> · Revoked</template>
            <template v-else> · Key shown once at creation</template>
          </div>
        </div>
        <div style="display:flex;gap:6px;flex-shrink:0">
          <button v-if="!k.revoked_at" class="btn-sm danger" @click="doRevoke(k.id)">Revoke</button>
        </div>
      </div>
      <p style="font-size:12px;color:var(--muted);margin-top:12px;padding-top:10px;border-top:1px solid var(--border)">
        API key values are only shown once at creation and cannot be retrieved again.
      </p>
    </template>
  </div>

  <div class="po-section">
    <div class="po-section-title">Create New Key</div>
    <div class="inline-form">
      <input v-model="newKeyName" type="text" placeholder="Key name (e.g. Production, Staging)" />
      <button class="btn-sm primary" :disabled="creating" @click="doCreate">+ Create Key</button>
    </div>
    <div v-if="newKeyValue" class="new-key-reveal">
      <div class="nkr-title">
        <span>Key created — copy it now, it will never be shown again</span>
        <button class="btn-sm" @click="newKeyValue = ''">Dismiss</button>
      </div>
      <div class="new-key-val">
        <code>{{ newKeyValue }}</code>
        <button class="copy-btn" @click="copyKey">Copy</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getProjectKeys, createProjectKey, deleteProjectKey, fmt, timeAgo } from '../api'
import { useToast } from '../composables/useToast'
import type { ApiKey } from '../types'

const props = defineProps<{ projectId: string }>()
const { toast } = useToast()

const keys = ref<ApiKey[]>([])
const loadingKeys = ref(true)
const newKeyName = ref('')
const newKeyValue = ref('')
const creating = ref(false)

onMounted(() => loadKeys())

async function loadKeys() {
  loadingKeys.value = true
  try {
    const res = await getProjectKeys(props.projectId)
    keys.value = res.data
  } catch { toast('Failed to load keys', 'error') } finally { loadingKeys.value = false }
}

async function doCreate() {
  if (!newKeyName.value.trim()) { toast('Key name is required', 'error'); return }
  creating.value = true
  try {
    const res = await createProjectKey(props.projectId, newKeyName.value.trim())
    newKeyValue.value = res.data.key
    newKeyName.value = ''
    await loadKeys()
  } catch { toast('Failed to create key', 'error') } finally { creating.value = false }
}

async function doRevoke(keyId: string) {
  if (!confirm('Revoke this API key? Any integrations using it will stop working.')) return
  try {
    await deleteProjectKey(props.projectId, keyId)
    toast('Key revoked', 'success')
    await loadKeys()
  } catch { toast('Failed to revoke key', 'error') }
}

function copyKey() {
  navigator.clipboard.writeText(newKeyValue.value).then(() => toast('Copied!', 'success'))
}
</script>
```

- [ ] **Step 3: Create ProjectIntegrationTab.vue**

Create `app/dashboard/src/components/ProjectIntegrationTab.vue`:

```vue
<template>
  <div class="po-section">
    <div class="po-section-title">Project Details</div>
    <div class="info-row">
      <div><div class="info-label">Project ID</div><div class="info-val">{{ projectId }}</div></div>
      <button class="copy-btn" @click="copy(projectId)">Copy</button>
    </div>
    <div class="info-row">
      <div><div class="info-label">API Base URL</div><div class="info-val">{{ base }}</div></div>
      <button class="copy-btn" @click="copy(base)">Copy</button>
    </div>
  </div>

  <div class="po-section">
    <div class="po-section-title">Quick Start</div>
    <p style="font-size:13px;color:var(--muted);margin-bottom:14px">
      Create an API key in the <strong>API Keys</strong> tab and use it as your bearer token.
      Use any stable string as <code style="background:#f1f5f9;padding:1px 5px;border-radius:3px">CONTACT_ID</code>
      (email, CRM ID, etc.) — DeepRaven creates the contact automatically on first use.
    </p>
    <div style="margin-bottom:8px;font-size:13px;font-weight:600">Send a conversation</div>
    <div class="snippet-tabs">
      <div
        v-for="l in langs" :key="l"
        class="snippet-tab"
        :class="{ active: activeLang === l }"
        @click="activeLang = l"
      >{{ l }}</div>
    </div>
    <pre class="code-block">{{ snippets[activeLang].send }}</pre>
    <div style="margin-bottom:8px;font-size:13px;font-weight:600">Retrieve profile</div>
    <pre class="code-block">{{ snippets[activeLang].get }}</pre>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useToast } from '../composables/useToast'

const props = defineProps<{ projectId: string }>()
const { toast } = useToast()

const base = `${window.location.origin}/api/v1`
const langs = ['curl', 'python', 'node'] as const
type Lang = typeof langs[number]
const activeLang = ref<Lang>('curl')

const snippets = computed<Record<Lang, { send: string; get: string }>>(() => ({
  curl: {
    send: `curl -X POST ${base}/projects/${props.projectId}/contacts/CONTACT_ID/conversations \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"messages":[{"role":"user","content":"I am interested in your product."},{"role":"assistant","content":"Great! Tell me more about your needs."}]}'`,
    get: `curl ${base}/projects/${props.projectId}/contacts/CONTACT_ID/profile \\
  -H "Authorization: Bearer YOUR_API_KEY"`,
  },
  python: {
    send: `import requests\n\nAPI_KEY    = "YOUR_API_KEY"\nBASE_URL   = "${base}"\nPROJECT_ID = "${props.projectId}"\nCONTACT_ID = "your-contact-id"\n\nrequests.post(\n    f"{BASE_URL}/projects/{PROJECT_ID}/contacts/{CONTACT_ID}/conversations",\n    headers={"Authorization": f"Bearer {API_KEY}"},\n    json={"messages": [{"role": "user", "content": "I need a gift under $200"}]},\n)`,
    get: `resp = requests.get(\n    f"{BASE_URL}/projects/{PROJECT_ID}/contacts/{CONTACT_ID}/profile",\n    headers={"Authorization": f"Bearer {API_KEY}"},\n)\nprint(resp.json()["personal"]["name"])`,
  },
  node: {
    send: `const BASE_URL = "${base}";\nconst PROJECT_ID = "${props.projectId}";\nconst API_KEY = "YOUR_API_KEY";\nconst CONTACT_ID = "your-contact-id";\n\nawait fetch(\`\${BASE_URL}/projects/\${PROJECT_ID}/contacts/\${CONTACT_ID}/conversations\`, {\n  method: "POST",\n  headers: { "Authorization": \`Bearer \${API_KEY}\`, "Content-Type": "application/json" },\n  body: JSON.stringify({ messages: [{ role: "user", content: "I need a gift under $200" }] }),\n});`,
    get: `const res = await fetch(\n  \`\${BASE_URL}/projects/\${PROJECT_ID}/contacts/\${CONTACT_ID}/profile\`,\n  { headers: { Authorization: \`Bearer \${API_KEY}\` } }\n);\nconst p = await res.json();\nconsole.log(p.personal.name, p.sales.pain_points);`,
  },
}))

function copy(text: string) {
  navigator.clipboard.writeText(text).then(() => toast('Copied!', 'success'))
}
</script>
```

- [ ] **Step 4: Create ProjectSettingsTab.vue**

Create `app/dashboard/src/components/ProjectSettingsTab.vue`:

```vue
<template>
  <div class="po-section">
    <div class="po-section-title">Project Name</div>
    <div class="inline-form">
      <input v-model="name" type="text" placeholder="Project name" />
      <button class="btn-sm primary" :disabled="saving" @click="doRename">
        {{ saving ? 'Saving…' : 'Save' }}
      </button>
    </div>
  </div>
  <div class="po-section">
    <div class="po-section-title">Danger Zone</div>
    <div class="danger-box">
      <p>Deleting a project permanently removes all contacts, conversations, and profiles. This cannot be undone.</p>
      <button class="btn-sm danger" @click="doDelete">Delete this project</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { updateProject, deleteProject, getProjects } from '../api'
import { useAppStore } from '../stores/app'
import { useToast } from '../composables/useToast'

const props = defineProps<{ projectId: string; projectName: string }>()
const router = useRouter()
const appStore = useAppStore()
const { toast } = useToast()

const name = ref(props.projectName)
const saving = ref(false)

async function doRename() {
  if (!name.value.trim()) return
  saving.value = true
  try {
    await updateProject(props.projectId, name.value.trim())
    const res = await getProjects()
    appStore.setProjects(res.data)
    toast('Project renamed', 'success')
  } catch { toast('Failed to rename project', 'error') } finally { saving.value = false }
}

async function doDelete() {
  if (!confirm('Delete this project and ALL its data? This cannot be undone.')) return
  try {
    await deleteProject(props.projectId)
    const res = await getProjects()
    appStore.setProjects(res.data)
    toast('Project deleted', 'success')
    router.push('/')
  } catch { toast('Failed to delete project', 'error') }
}
</script>
```

- [ ] **Step 5: Commit**

```bash
git add app/dashboard/src/
git commit -m "feat: add ProjectPanel with Keys, Integration, Settings tabs"
```

---

### Task 10: ContactDetail, ProfileTab, ConversationsTab

**Files:**
- Create: `app/dashboard/src/components/ContactDetail.vue`
- Create: `app/dashboard/src/components/ProfileTab.vue`
- Create: `app/dashboard/src/components/ConversationsTab.vue`

- [ ] **Step 1: Create ContactDetail.vue**

Create `app/dashboard/src/components/ContactDetail.vue`:

```vue
<template>
  <div v-if="loading" class="empty-state">
    <span class="spin" style="width:36px;height:36px;border-width:3px" />
  </div>
  <div v-else-if="profile" style="display:flex;flex-direction:column;height:100%;overflow:hidden">
    <div class="detail-header">
      <div class="dh-top">
        <div>
          <div class="dh-name">{{ profile.personal.name || contact?.external_id || contactId }}</div>
          <div class="dh-id">{{ contact?.external_id || contactId }}</div>
          <div class="dh-meta">
            <span class="badge b-green">● idle</span>
            <span>Updated {{ timeAgo(profile.updated_at) }}</span>
            <span>💬 {{ conversations.length }} conversations</span>
          </div>
        </div>
        <div class="dh-actions">
          <button class="btn-sm" @click="reload">↻ Refresh</button>
          <button class="btn-sm primary" :disabled="extracting" @click="doExtract(false)">
            {{ extracting ? '…' : '⚡ Extract New' }}
          </button>
          <button class="btn-sm" :disabled="extracting" @click="doExtract(true)">↺ Force</button>
          <button class="btn-sm" @click="doCompress">⊘ Compress</button>
          <button class="btn-sm" @click="doExport">↓ Export</button>
        </div>
      </div>
      <div class="tabs">
        <div class="tab" :class="{ active: activeTab === 'profile' }" @click="activeTab = 'profile'">Profile</div>
        <div class="tab" :class="{ active: activeTab === 'conversations' }" @click="activeTab = 'conversations'">
          Conversations&nbsp;<span class="badge b-gray">{{ conversations.length }}</span>
        </div>
      </div>
    </div>
    <div class="tab-content">
      <ProfileTab v-if="activeTab === 'profile'" :profile="profile" :project-id="projectId" :contact-id="contactId" @reload="reload" />
      <ConversationsTab v-else :conversations="conversations" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  getProfile, getConversations, extractSync, compressProfile,
  exportContactProfile, downloadBlob, timeAgo,
} from '../api'
import { useAppStore } from '../stores/app'
import { useToast } from '../composables/useToast'
import type { UserProfile, ConversationRecord } from '../types'
import ProfileTab from './ProfileTab.vue'
import ConversationsTab from './ConversationsTab.vue'

const route = useRoute()
const appStore = useAppStore()
const { toast } = useToast()

const projectId = computed(() => route.params.projectId as string)
const contactId = computed(() => route.params.contactId as string)
const contact = computed(() => appStore.contacts.find(c => c.id === contactId.value))

const loading = ref(true)
const extracting = ref(false)
const activeTab = ref<'profile' | 'conversations'>('profile')
const profile = ref<UserProfile | null>(null)
const conversations = ref<ConversationRecord[]>([])

async function load() {
  loading.value = true
  try {
    const [pRes, cRes] = await Promise.all([
      getProfile(projectId.value, contactId.value),
      getConversations(projectId.value, contactId.value),
    ])
    profile.value = pRes.data
    conversations.value = cRes.data
  } catch { toast('Failed to load contact', 'error') } finally { loading.value = false }
}

watch([projectId, contactId], load, { immediate: true })

async function reload() {
  await load()
  appStore.refreshContacts()
  toast('Profile refreshed', 'success')
}

async function doExtract(force: boolean) {
  toast(force ? 'Force re-extracting…' : 'Extracting new conversations…', 'info')
  extracting.value = true
  try {
    await extractSync(projectId.value, contactId.value, force)
    toast('Extraction completed!', 'success')
    await load()
    appStore.refreshContacts()
  } catch (err: unknown) {
    const status = (err as { response?: { status?: number } })?.response?.status
    if (status === 404) toast('No conversations to process', 'error')
    else if (status === 409) toast('Extraction already running', 'error')
    else toast('Extraction failed', 'error')
  } finally { extracting.value = false }
}

async function doCompress() {
  try {
    await compressProfile(projectId.value, contactId.value)
    toast('Profile compressed', 'success')
    await load()
  } catch { toast('Compress failed', 'error') }
}

async function doExport() {
  try {
    const res = await exportContactProfile(projectId.value, contactId.value)
    downloadBlob(res.data, 'profile.json', res.headers['content-disposition'])
    toast('Profile exported', 'success')
  } catch { toast('Export failed', 'error') }
}
</script>
```

- [ ] **Step 2: Create ProfileTab.vue**

Create `app/dashboard/src/components/ProfileTab.vue`:

```vue
<template>
  <div class="profile-grid">
    <div class="persona-card">
      <div class="persona-label">Buying Persona</div>
      <div v-if="profile.sales.buying_persona" class="persona-text">{{ profile.sales.buying_persona }}</div>
      <div v-else class="persona-empty">No buying persona yet — run extraction after conversations are added.</div>
    </div>

    <div class="pcard">
      <div class="pcard-title">Personal</div>
      <ProfileRow label="Name" :value="profile.personal.name" />
      <ProfileRow label="Gender" :value="profile.personal.gender" />
      <ProfileRow label="Phone" :value="profile.personal.phone" />
      <ProfileRow label="Location" :value="profile.personal.location" />
      <ProfileRow label="Company" :value="profile.personal.company" />
      <ProfileRow label="Role" :value="profile.personal.role" />
      <div v-if="profile.personal.delivery_address" class="field col">
        <span class="fl">Delivery address</span>
        <span style="font-size:12px;color:#cbd5e1">{{ profile.personal.delivery_address }}</span>
      </div>
    </div>

    <div class="pcard">
      <div class="pcard-title">Preferences</div>
      <ProfileRow label="Comm. style" :value="profile.preferences.communication_style" />
      <ProfileRow label="Best channel" :value="profile.preferences.best_contact_channel" />
      <div class="field col">
        <span class="fl">Languages</span>
        <TagList :items="profile.preferences.languages" />
      </div>
    </div>

    <!-- Relatives -->
    <div v-if="profile.relatives.length" class="pcard">
      <div class="pcard-title">Relatives &amp; Family</div>
      <div v-for="r in profile.relatives" :key="r.relation + (r.name ?? '')" class="relative-item">
        <div class="relative-relation">{{ [r.relation, r.name].filter(Boolean).join(' — ') }}</div>
        <div class="relative-attrs">
          <span v-if="r.age" class="relative-attr">Age {{ r.age }}</span>
          <span v-if="r.gender" class="relative-attr">{{ r.gender }}</span>
          <span v-for="pref in r.preferences" :key="pref" class="relative-attr">{{ pref }}</span>
          <span v-for="(val, key) in r.sizes" :key="key" class="relative-attr size-attr">{{ key }}: {{ val }}</span>
        </div>
        <div v-if="r.notes" class="relative-notes">{{ r.notes }}</div>
      </div>
    </div>

    <div class="pcard">
      <div class="pcard-title">Current Needs</div>
      <div class="field col"><span class="fl" /><TagList :items="profile.sales.current_needs" /></div>
    </div>

    <div class="pcard">
      <div class="pcard-title">Relationship</div>
      <ProfileRow label="Status" :value="profile.relationship.status" />
      <ProfileRow label="Last contact" :value="profile.relationship.last_contact_date" />
      <div class="field col">
        <span class="fl">Details</span>
        <TagList :items="profile.relationship.personal_details" />
      </div>
    </div>

    <div class="pcard">
      <div class="pcard-title">Sales Intelligence</div>
      <div class="field col"><span class="fl">Buying triggers</span><TagList :items="profile.sales.buying_triggers" /></div>
      <div class="field col"><span class="fl">Pain points</span><TagList :items="profile.sales.pain_points" /></div>
      <div class="field col"><span class="fl">Objections</span><TagList :items="profile.sales.objections_raised" /></div>
      <ProfileRow label="Budget" :value="profile.sales.budget_range" />
      <div v-if="profile.sales.purchase_history.length" class="field col">
        <span class="fl">Purchase history</span>
        <TagList :items="profile.sales.purchase_history" />
      </div>
    </div>

    <div style="grid-column:1/-1;font-size:11px;color:#94a3b8;padding:2px 0">
      Created {{ fmt(profile.created_at) }} · Updated {{ fmt(profile.updated_at) }}
    </div>

    <!-- GDPR -->
    <div class="gdpr-section">
      <div class="gdpr-title">Data &amp; Privacy (GDPR)</div>
      <div class="gdpr-actions">
        <button class="btn-danger" @click="eraseConversations">Erase Conversations</button>
        <button class="btn-danger" @click="eraseProfile">Erase Profile Data</button>
        <button class="btn-danger destructive" @click="deleteContactAction">Delete Contact</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { deleteConversations, deleteProfile, deleteContact, fmt } from '../api'
import { useToast } from '../composables/useToast'
import type { UserProfile } from '../types'

// Inline sub-components
const ProfileRow = {
  props: ['label', 'value'],
  template: `<div class="field"><span class="fl">{{ label }}</span><span class="fv" :class="{ empty: !value }">{{ value || '—' }}</span></div>`,
}
const TagList = {
  props: ['items'],
  template: `<div v-if="items && items.length" class="tag-list"><span v-for="t in items" :key="t" class="tag">{{ t }}</span></div><span v-else class="fv empty">none yet</span>`,
}

const props = defineProps<{ profile: UserProfile; projectId: string; contactId: string }>()
const emit = defineEmits<{ (e: 'reload'): void }>()
const router = useRouter()
const { toast } = useToast()

async function eraseConversations() {
  if (!confirm('Erase all conversation history for this contact? This cannot be undone.')) return
  try {
    await deleteConversations(props.projectId, props.contactId)
    toast('Conversation history erased', 'success')
    emit('reload')
  } catch { toast('Failed', 'error') }
}

async function eraseProfile() {
  if (!confirm('Erase all extracted profile data for this contact? This cannot be undone.')) return
  try {
    await deleteProfile(props.projectId, props.contactId)
    toast('Profile data erased', 'success')
    emit('reload')
  } catch { toast('Failed', 'error') }
}

async function deleteContactAction() {
  if (!confirm('Permanently delete this contact and ALL their data? This cannot be undone.')) return
  if (!confirm('Are you sure? This will delete conversations, profile, and the contact record.')) return
  try {
    await deleteContact(props.projectId, props.contactId)
    toast('Contact deleted', 'success')
    router.push(`/projects/${props.projectId}`)
  } catch { toast('Failed', 'error') }
}
</script>
```

- [ ] **Step 3: Create ConversationsTab.vue**

Create `app/dashboard/src/components/ConversationsTab.vue`:

```vue
<template>
  <div v-if="!conversations.length" style="text-align:center;padding:48px;color:#94a3b8">
    No conversations yet
  </div>
  <div v-else>
    <div
      v-for="rec in [...conversations].reverse()"
      :key="rec.id"
      class="convo-card"
      :class="rec.processed ? 'is-processed' : 'is-unprocessed'"
    >
      <div class="convo-header">
        <span>{{ fmt(rec.timestamp) }}</span>
        <span>{{ rec.messages.length }} msg{{ rec.messages.length !== 1 ? 's' : '' }}</span>
        <span class="spacer" />
        <span v-if="rec.processed" class="badge b-green">✓ Processed</span>
        <span v-else class="badge b-amber">⏳ Pending extraction</span>
      </div>
      <div class="convo-msgs">
        <div v-for="(m, i) in rec.messages" :key="i" class="msg" :class="`msg-${m.role}`">
          <div class="msg-role">{{ m.role }}</div>
          {{ m.content }}
          <div>
            <span v-if="rec.processed" class="msg-status msg-status-ok">✓ in profile</span>
            <span v-else class="msg-status msg-status-pending">⏳ pending</span>
          </div>
        </div>
      </div>
      <div v-if="!rec.processed" class="convo-pending">
        ⏳ Not yet extracted into the profile — will be processed automatically
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { fmt } from '../api'
import type { ConversationRecord } from '../types'

defineProps<{ conversations: ConversationRecord[] }>()
</script>
```

- [ ] **Step 4: Commit**

```bash
git add app/dashboard/src/
git commit -m "feat: add ContactDetail, ProfileTab, ConversationsTab"
```

---

### Task 11: Update FastAPI to serve the new dashboard

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Update main.py**

Open `app/main.py`. Replace the existing dashboard route and related code with the following.

Remove this line at the top:
```python
_DASHBOARD_HTML = (Path(__file__).parent / "static" / "dashboard.html").read_text()
```

Add this import at the top with the other FastAPI imports:
```python
from fastapi.staticfiles import StaticFiles
```

Replace:
```python
@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard() -> HTMLResponse:
    return HTMLResponse(content=_DASHBOARD_HTML)
```

With:
```python
@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
@app.get("/dashboard/{path:path}", response_class=HTMLResponse, include_in_schema=False)
async def dashboard(path: str = "") -> HTMLResponse:
    dist_index = Path(__file__).parent / "static" / "dist" / "index.html"
    return HTMLResponse(content=dist_index.read_text())
```

Then add this **after** all `app.include_router(...)` calls and **after** the route definitions (but before the health endpoint works fine too — just must be last mount):

```python
# Serve Vite-built assets (JS, CSS, images)
_dist = Path(__file__).parent / "static" / "dist"
if _dist.exists():
    app.mount("/dashboard/assets", StaticFiles(directory=str(_dist / "assets")), name="dashboard-assets")
```

- [ ] **Step 2: Verify main.py imports are clean**

```bash
cd /path/to/deepraven
source venv/bin/activate
REDIS_URL=redis://localhost:6379 SUPABASE_URL=https://placeholder.supabase.co SUPABASE_SECRET_KEY=placeholder GROQ_API_KEY=placeholder python -c "from app.main import app; print('OK')"
```

Expected: `OK` with no import errors.

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat: update FastAPI to serve Vite dist for dashboard"
```

---

### Task 12: Build and commit dist

**Files:**
- Create: `app/static/dist/` (build output, committed)

- [ ] **Step 1: Build the dashboard**

```bash
cd app/dashboard
npm run build
```

Expected:
```
vite v5.x.x building for production...
✓ N modules transformed.
dist/index.html        x.xx kB
dist/assets/index-[hash].js    xxx kB
dist/assets/index-[hash].css   xx kB
✓ built in xxxms
```

No TypeScript errors. Output lands in `app/static/dist/`.

- [ ] **Step 2: Add dist to git (not gitignored)**

Verify `app/static/dist/` is NOT in `.gitignore`. If it is, remove the entry.

```bash
git check-ignore -v app/static/dist/
```

Expected: no output (meaning it's not ignored).

- [ ] **Step 3: Start the server and verify**

```bash
cd ../..
source venv/bin/activate
./start.sh
```

Open `http://localhost:5100/dashboard` in a browser.

Expected:
- Login screen appears
- Logging in works
- Navigating to a project shows `/dashboard/projects/:id` in the URL
- Opening a contact shows `/dashboard/projects/:id/contacts/:cid`
- Browser back button works
- Refreshing the page at a deep URL (e.g. `/dashboard/projects/abc`) reloads correctly

- [ ] **Step 4: Commit dist and finalize**

```bash
git add app/static/dist/
git commit -m "feat: add Vite build output for dashboard"
```

- [ ] **Step 5: Final cleanup commit**

Optionally archive the old file (do not delete yet until you've verified the new dashboard is fully working):

```bash
git mv app/static/dashboard.html app/static/dashboard.html.bak
git commit -m "chore: archive old monolithic dashboard.html"
```

Once the new dashboard is verified working in production, delete the backup:

```bash
git rm app/static/dashboard.html.bak
git commit -m "chore: remove old monolithic dashboard"
```

---

## Self-Review

**Spec coverage:**
- ✅ Vite + Vue 3 + TS project in `app/dashboard/`
- ✅ Build output to `app/static/dist/` (committed)
- ✅ Vue Router with history mode, base `/dashboard/`
- ✅ Routes: `/`, `/login`, `/projects/:id`, `/projects/:id/contacts/:cid`
- ✅ Auth guard in router
- ✅ Pinia stores: auth + app
- ✅ Axios with interceptors (attach JWT, handle 401 + refresh)
- ✅ All auth modes: login, register, forgot, OTP, reset
- ✅ Boot logic: recovery hash, confirmed query param
- ✅ HomeDashboard: stats cards, Chart.js bar chart, usage table
- ✅ ContactSidebar: contact list, search, 15s auto-refresh
- ✅ ProjectPanel: keys tab, integration tab (curl/python/node snippets), settings tab
- ✅ ContactDetail: profile tab, conversations tab
- ✅ All actions: extract, force-extract, compress, export (single + all), GDPR erase/delete
- ✅ FastAPI updated to serve dist/
- ✅ `compressProfile` bug fixed (wrong URL and undefined functions in original)

**Type consistency:** All API functions return types matching `types.ts`. All component props reference the same interfaces.

**No placeholders:** All code blocks are complete implementations.

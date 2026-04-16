# Dashboard Refactor — Design Spec

**Date:** 2026-04-15
**Status:** Approved
**Scope:** Replace the monolithic `app/static/dashboard.html` (1995 lines) with a Vite + Vue 3 + TypeScript SFC app with URL-based navigation

---

## Overview

The current dashboard is a single 1995-line HTML file mixing CSS, HTML, and vanilla JS DOM manipulation. It has no structure, no type safety, and is hard to maintain or extend. This refactor replaces it with a proper Vite + Vue 3 + TypeScript application using Single File Components, Vue Router, Pinia, and Axios — preserving all existing functionality.

---

## Repo Structure

```
app/
├── dashboard/                    ← Vue source (dev only, not served)
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html                ← Vite entry point
│   └── src/
│       ├── main.ts               ← Vue app bootstrap
│       ├── App.vue               ← Root component (router-view + toast)
│       ├── router.ts             ← Vue Router config + auth guard
│       ├── api.ts                ← Axios instance + all typed API calls
│       ├── types.ts              ← TypeScript interfaces (mirrors app/models.py)
│       ├── stores/
│       │   ├── auth.ts           ← useAuthStore (JWT, account info, login/logout)
│       │   └── app.ts            ← useAppStore (selected project, contacts cache)
│       ├── composables/
│       │   └── useToast.ts       ← Toast notification state + trigger
│       └── components/
│           ├── AppHeader.vue     ← Top bar: logo, account info, logout
│           ├── ToastNotification.vue
│           ├── LoginScreen.vue   ← Login / register / forgot / OTP forms
│           ├── HomeDashboard.vue ← Stats cards + conversations chart + usage table
│           ├── ContactSidebar.vue← Contact list, search, unprocessed badge
│           ├── AppLayout.vue     ← Sidebar + main panel shell (shown when authed)
│           ├── ContactDetail.vue ← Profile tab + Conversations tab
│           ├── ProfileTab.vue    ← Structured profile card layout
│           ├── ConversationsTab.vue ← Conversation history with badges
│           ├── ProjectPanel.vue  ← Project management shell
│           ├── ProjectKeysTab.vue← API key list + create + revoke
│           ├── ProjectIntegrationTab.vue ← Integration code snippets
│           └── ProjectSettingsTab.vue    ← Rename / delete project
└── static/
    └── dist/                     ← Vite build output (committed to repo)
        ├── index.html
        └── assets/
            ├── index-[hash].js
            └── index-[hash].css
```

---

## Routing

Vue Router in **history mode** with base `/dashboard/`.

| Route | Component | Description |
|---|---|---|
| `/dashboard/login` | `LoginScreen` | Auth forms — redirects to `/dashboard/` on success |
| `/dashboard/` | `HomeDashboard` | Stats overview (requires auth) |
| `/dashboard/projects/:projectId` | `ProjectPanel` | Keys / Integration / Settings tabs |
| `/dashboard/projects/:projectId/contacts/:contactId` | `ContactDetail` | Profile / Conversations tabs |

**Auth guard:** `router.beforeEach` checks `useAuthStore().isAuthenticated`. Unauthenticated access to any route except `/dashboard/login` redirects to login. After login, user is redirected back to the original route.

FastAPI serves `/dashboard` and all `/dashboard/*` sub-paths to `dist/index.html` so Vue Router handles all client-side navigation.

---

## State Management (Pinia)

### `useAuthStore`
```typescript
{
  token: string | null       // JWT — persisted to localStorage
  account: Account | null    // { id, email }
  isAuthenticated: boolean
  login(email, password): Promise<void>
  logout(): void
}
```

### `useAppStore`
```typescript
{
  projects: Project[]
  selectedProject: Project | null
  contacts: Contact[]
  loadProjects(): Promise<void>
  loadContacts(projectId: string): Promise<void>
}
```

---

## API Layer

**`api.ts`** creates a single Axios instance:
- `baseURL` set to `/api/v1`
- Request interceptor: attaches `Authorization: Bearer <token>` from `useAuthStore`
- Response interceptor: on 401, calls `authStore.logout()` and redirects to `/dashboard/login`

All API calls are exported as typed async functions:

```typescript
export const getProfile = (pid: string, cid: string): Promise<UserProfile> =>
  api.get(`/projects/${pid}/contacts/${cid}/profile`).then(r => r.data)

export const createConversation = (pid: string, cid: string, body: ConversationCreate): Promise<void> =>
  api.post(`/projects/${pid}/contacts/${cid}/conversations`, body)
```

No raw `axios.get(...)` calls anywhere outside `api.ts`.

---

## TypeScript Types (`types.ts`)

Mirrors the Pydantic models in `app/models.py`:

```typescript
interface Personal { name: string | null; company: string | null; role: string | null; location: string | null; delivery_address: string | null }
interface Preferences { communication_style: string | null; best_contact_channel: string | null; languages: string[] }
interface Sales { buying_persona: string | null; pain_points: string[]; objections_raised: string[]; buying_triggers: string[]; current_needs: string[]; budget_range: string | null; purchase_history: string[] }
interface Relationship { status: string | null; last_contact_date: string | null; personal_details: string[] }
interface Relative { relation: string; age: string | null; preferences: string[] }
interface UserProfile { personal: Personal; preferences: Preferences; sales: Sales; relationship: Relationship; relatives: Relative[] }

interface Project { id: string; name: string; created_at: string }
interface Contact { id: string; external_id: string; conversation_count: number; unprocessed_count: number; extraction_status: string; last_contact_date: string | null }
interface ApiKey { id: string; name: string; prefix: string; created_at: string }
interface ConversationRecord { id: string; messages: Message[]; processed: boolean; created_at: string }
interface Message { role: 'user' | 'assistant'; content: string }
```

---

## FastAPI Changes

`app/main.py` — two small changes:

1. Mount `app/static/dist/assets` as a static directory at `/dashboard/assets`
2. Add a catch-all route that serves `app/static/dist/index.html` for `/dashboard` and all `/dashboard/{path:path}` sub-routes (so Vue Router history mode works)

The existing `/dashboard` route is replaced by this catch-all.

---

## Build & Dev Workflow

```bash
# Development (hot reload at http://localhost:5173)
cd app/dashboard
npm install
npm run dev

# Production build (outputs to app/static/dist/)
npm run build
```

`vite.config.ts` sets `build.outDir` to `../../static/dist` and `base` to `/dashboard/`.

The built `dist/` is committed to the repo. Deployment requires no Node.js — FastAPI serves the pre-built static files directly.

`.gitignore` gets `app/dashboard/node_modules/` added; `app/static/dist/` is NOT ignored (committed).

---

## Component Responsibilities

| Component | What it does |
|---|---|
| `App.vue` | Root: `<router-view>` + `<ToastNotification>` |
| `AppLayout.vue` | Authenticated shell: `AppHeader` + `ContactSidebar` + `<router-view>` for main panel |
| `LoginScreen.vue` | All auth forms: login, register, forgot password, OTP verify, reset password |
| `HomeDashboard.vue` | Fetches stats, renders stat cards, Chart.js conversations chart, usage table |
| `ContactSidebar.vue` | Lists contacts for selected project, search filter, auto-refresh every 15s |
| `ContactDetail.vue` | Loads profile + conversations, renders Profile/Conversations tabs |
| `ProfileTab.vue` | Renders `UserProfile` as card layout; Extract / Force Re-extract buttons |
| `ConversationsTab.vue` | Lists conversations with processed/unprocessed badges |
| `ProjectPanel.vue` | Project management shell with Keys / Integration / Settings tabs |
| `ProjectKeysTab.vue` | Lists API keys, create key (shows raw key once), revoke key |
| `ProjectIntegrationTab.vue` | Code snippet showing how to call the API with this project's key |
| `ProjectSettingsTab.vue` | Rename project, delete project |
| `AppHeader.vue` | Logo, project switcher dropdown, account email, logout button |
| `ToastNotification.vue` | Success/error/info toasts triggered via `useToast` composable |

---

## Out of Scope

- New dashboard features (this is a refactor only — same functionality)
- Dark mode
- Testing (no test suite configured for this project)
- CI/CD for the frontend build step

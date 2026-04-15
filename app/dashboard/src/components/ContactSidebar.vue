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

    <!-- Project nav sticky at bottom -->
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

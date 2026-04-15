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

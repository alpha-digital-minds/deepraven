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

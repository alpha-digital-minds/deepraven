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

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

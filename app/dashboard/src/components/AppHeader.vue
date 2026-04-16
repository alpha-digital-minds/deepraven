<template>
  <header>
    <RouterLink to="/">
      <img class="logo" :src="'/assets/logo.png'" alt="DeepRaven" />
    </RouterLink>
    <h1>DeepRaven</h1>
    <div class="spacer" />

    <!-- Project picker -->
    <div class="proj-picker" id="proj-picker">
      <button class="proj-picker-btn" @click.stop="dropdownOpen = !dropdownOpen">
        <span id="proj-picker-label">{{ selectedProject?.name ?? 'Select a project' }}</span>
        <span class="proj-dd-arrow">▾</span>
      </button>
      <div class="proj-dropdown" id="proj-dropdown" :class="{ open: dropdownOpen }">
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

<template>
  <AppHeader />
  <div id="app-layout" class="visible" :class="{ 'no-sidebar': isConfigRoute }">
    <ContactSidebar v-if="!isConfigRoute" />
    <main id="main">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from './AppHeader.vue'
import ContactSidebar from './ContactSidebar.vue'
import { getProjects } from '../api'
import { useAppStore } from '../stores/app'

const route = useRoute()
const isConfigRoute = computed(() => route.path === '/configuration')

const appStore = useAppStore()

onMounted(async () => {
  try {
    const res = await getProjects()
    appStore.setProjects(res.data)
  } catch { /* auth errors handled by interceptor */ }
})
</script>

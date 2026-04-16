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

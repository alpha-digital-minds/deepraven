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

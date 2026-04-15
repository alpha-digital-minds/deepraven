<template>
  <div v-if="!conversations.length" style="text-align:center;padding:48px;color:#94a3b8">
    No conversations yet
  </div>
  <div v-else>
    <div
      v-for="rec in [...conversations].reverse()"
      :key="rec.id"
      class="convo-card"
      :class="rec.processed ? 'is-processed' : 'is-unprocessed'"
    >
      <div class="convo-header">
        <span>{{ fmt(rec.timestamp) }}</span>
        <span>{{ rec.messages.length }} msg{{ rec.messages.length !== 1 ? 's' : '' }}</span>
        <span class="spacer" />
        <span v-if="rec.processed" class="badge b-green">✓ Processed</span>
        <span v-else class="badge b-amber">⏳ Pending extraction</span>
      </div>
      <div class="convo-msgs">
        <div v-for="(m, i) in rec.messages" :key="i" class="msg" :class="`msg-${m.role}`">
          <div class="msg-role">{{ m.role }}</div>
          {{ m.content }}
          <div>
            <span v-if="rec.processed" class="msg-status msg-status-ok">✓ in profile</span>
            <span v-else class="msg-status msg-status-pending">⏳ pending</span>
          </div>
        </div>
      </div>
      <div v-if="!rec.processed" class="convo-pending">
        ⏳ Not yet extracted into the profile — will be processed automatically
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { fmt } from '../api'
import type { ConversationRecord } from '../types'

defineProps<{ conversations: ConversationRecord[] }>()
</script>

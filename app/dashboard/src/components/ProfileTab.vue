<template>
  <div class="profile-grid">
    <div class="persona-card">
      <div class="persona-label">Buying Persona</div>
      <div v-if="profile.sales.buying_persona" class="persona-text">{{ profile.sales.buying_persona }}</div>
      <div v-else class="persona-empty">No buying persona yet — run extraction after conversations are added.</div>
    </div>

    <div class="pcard">
      <div class="pcard-title">Personal</div>
      <ProfileRow label="Name" :value="profile.personal.name" />
      <ProfileRow label="Gender" :value="profile.personal.gender" />
      <ProfileRow label="Phone" :value="profile.personal.phone" />
      <ProfileRow label="Location" :value="profile.personal.location" />
      <ProfileRow label="Company" :value="profile.personal.company" />
      <ProfileRow label="Role" :value="profile.personal.role" />
      <div v-if="profile.personal.delivery_address" class="field col">
        <span class="fl">Delivery address</span>
        <span style="font-size:12px;color:#cbd5e1">{{ profile.personal.delivery_address }}</span>
      </div>
    </div>

    <div class="pcard">
      <div class="pcard-title">Preferences</div>
      <ProfileRow label="Comm. style" :value="profile.preferences.communication_style" />
      <ProfileRow label="Best channel" :value="profile.preferences.best_contact_channel" />
      <div class="field col">
        <span class="fl">Languages</span>
        <TagList :items="profile.preferences.languages" />
      </div>
    </div>

    <!-- Relatives -->
    <div v-if="profile.relatives.length" class="pcard">
      <div class="pcard-title">Relatives &amp; Family</div>
      <div v-for="r in profile.relatives" :key="r.relation + (r.name ?? '')" class="relative-item">
        <div class="relative-relation">{{ [r.relation, r.name].filter(Boolean).join(' — ') }}</div>
        <div class="relative-attrs">
          <span v-if="r.age" class="relative-attr">Age {{ r.age }}</span>
          <span v-if="r.gender" class="relative-attr">{{ r.gender }}</span>
          <span v-for="pref in r.preferences" :key="pref" class="relative-attr">{{ pref }}</span>
          <span v-for="(val, key) in r.sizes" :key="key" class="relative-attr size-attr">{{ key }}: {{ val }}</span>
        </div>
        <div v-if="r.notes" class="relative-notes">{{ r.notes }}</div>
      </div>
    </div>

    <div class="pcard">
      <div class="pcard-title">Current Needs</div>
      <div class="field col"><span class="fl" /><TagList :items="profile.sales.current_needs" /></div>
    </div>

    <div class="pcard">
      <div class="pcard-title">Relationship</div>
      <ProfileRow label="Status" :value="profile.relationship.status" />
      <ProfileRow label="Last contact" :value="profile.relationship.last_contact_date" />
      <div class="field col">
        <span class="fl">Details</span>
        <TagList :items="profile.relationship.personal_details" />
      </div>
    </div>

    <div class="pcard">
      <div class="pcard-title">Sales Intelligence</div>
      <div class="field col"><span class="fl">Buying triggers</span><TagList :items="profile.sales.buying_triggers" /></div>
      <div class="field col"><span class="fl">Pain points</span><TagList :items="profile.sales.pain_points" /></div>
      <div class="field col"><span class="fl">Objections</span><TagList :items="profile.sales.objections_raised" /></div>
      <ProfileRow label="Budget" :value="profile.sales.budget_range" />
      <div v-if="profile.sales.purchase_history.length" class="field col">
        <span class="fl">Purchase history</span>
        <TagList :items="profile.sales.purchase_history" />
      </div>
    </div>

    <div style="grid-column:1/-1;font-size:11px;color:#94a3b8;padding:2px 0">
      Created {{ fmt(profile.created_at) }} · Updated {{ fmt(profile.updated_at) }}
    </div>

    <!-- GDPR -->
    <div class="gdpr-section">
      <div class="gdpr-title">Data &amp; Privacy (GDPR)</div>
      <div class="gdpr-actions">
        <button class="btn-danger" @click="eraseConversations">Erase Conversations</button>
        <button class="btn-danger" @click="eraseProfile">Erase Profile Data</button>
        <button class="btn-danger destructive" @click="deleteContactAction">Delete Contact</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { h } from 'vue'
import { useRouter } from 'vue-router'
import { deleteConversations, deleteProfile, deleteContact, fmt } from '../api'
import { useToast } from '../composables/useToast'
import type { UserProfile } from '../types'

// Inline sub-components using render functions (no template compiler needed)
const ProfileRow = {
  props: ['label', 'value'],
  setup(props: { label: string; value: string | null | undefined }) {
    return () => h('div', { class: 'field' }, [
      h('span', { class: 'fl' }, props.label),
      h('span', { class: ['fv', !props.value ? 'empty' : ''] }, props.value || '—'),
    ])
  },
}
const TagList = {
  props: ['items'],
  setup(props: { items: string[] | null | undefined }) {
    return () => {
      const items = props.items
      if (items && items.length) {
        return h('div', { class: 'tag-list' }, items.map(t => h('span', { class: 'tag', key: t }, t)))
      }
      return h('span', { class: 'fv empty' }, 'none yet')
    }
  },
}

const props = defineProps<{ profile: UserProfile; projectId: string; contactId: string }>()
const emit = defineEmits<{ (e: 'reload'): void }>()
const router = useRouter()
const { toast } = useToast()

async function eraseConversations() {
  if (!confirm('Erase all conversation history for this contact? This cannot be undone.')) return
  try {
    await deleteConversations(props.projectId, props.contactId)
    toast('Conversation history erased', 'success')
    emit('reload')
  } catch { toast('Failed', 'error') }
}

async function eraseProfile() {
  if (!confirm('Erase all extracted profile data for this contact? This cannot be undone.')) return
  try {
    await deleteProfile(props.projectId, props.contactId)
    toast('Profile data erased', 'success')
    emit('reload')
  } catch { toast('Failed', 'error') }
}

async function deleteContactAction() {
  if (!confirm('Permanently delete this contact and ALL their data? This cannot be undone.')) return
  if (!confirm('Are you sure? This will delete conversations, profile, and the contact record.')) return
  try {
    await deleteContact(props.projectId, props.contactId)
    toast('Contact deleted', 'success')
    router.push(`/projects/${props.projectId}`)
  } catch { toast('Failed', 'error') }
}
</script>

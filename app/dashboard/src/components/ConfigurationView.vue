<template>
  <div class="config-view">
    <div class="config-header">
      <h2>Configuration</h2>
      <p class="config-subtitle">Define your data model and use-case context. DeepRaven will generate custom extraction prompts tailored to your schema.</p>
    </div>

    <!-- Purpose Section -->
    <div class="config-card">
      <h3>Purpose</h3>
      <p class="card-hint">Describe what your AI agent does — this shapes how prompts are generated</p>
      <div class="purpose-row">
        <div class="form-field">
          <label>Industry</label>
          <input v-model="form.purpose_industry" type="text" placeholder="e.g. Luxury Retail" />
        </div>
        <div class="form-field">
          <label>Agent Type</label>
          <input v-model="form.purpose_agent_type" type="text" placeholder="e.g. Sales Agent" />
        </div>
      </div>
      <div class="form-field">
        <label>Description</label>
        <textarea
          v-model="form.purpose_description"
          rows="3"
          placeholder="e.g. Track purchase intent, preferences, and upsell signals for watch retail customers"
        />
      </div>
    </div>

    <!-- Schema Section -->
    <div class="config-card">
      <h3>Schema</h3>
      <p class="card-hint">Define the JSON data model for contact profiles — the LLM will extract data into this structure</p>
      <textarea
        v-model="schemaText"
        class="schema-editor"
        rows="10"
        spellcheck="false"
        placeholder='{&#10;  "customer_tier": "",&#10;  "preferred_brands": [],&#10;  "budget_range": ""&#10;}'
        @input="validateSchema"
      />
      <div class="schema-status" :class="schemaValid ? 'valid' : 'invalid'">
        {{ schemaValid ? '✓ Valid JSON' : '✗ Invalid JSON' }}
      </div>
    </div>

    <!-- Save button -->
    <div class="save-row">
      <button
        class="btn-primary"
        :disabled="saving || !schemaValid || !formComplete"
        @click="doSave"
      >
        {{ saving ? 'Generating…' : 'Save & Generate Prompts' }}
      </button>
    </div>

    <!-- Generated Prompts Section -->
    <div class="config-card prompts-card">
      <div class="prompts-header">
        <div>
          <h3>Generated Prompts</h3>
          <p class="card-hint">
            <span v-if="config">Auto-generated from your schema and purpose. You can edit them directly.</span>
            <span v-else>Save your schema and purpose above to generate prompts.</span>
          </p>
        </div>
        <div v-if="config" class="regen-row">
          <input
            v-model="regenComment"
            type="text"
            class="regen-input"
            placeholder="Optional: guide the regeneration…"
          />
          <button class="btn-secondary" :disabled="regenerating" @click="doRegenerate">
            {{ regenerating ? 'Regenerating…' : '↺ Regenerate' }}
          </button>
        </div>
      </div>

      <!-- Prompt tabs -->
      <div class="prompt-tabs">
        <button
          v-for="tab in promptTabs"
          :key="tab.key"
          class="prompt-tab"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >{{ tab.label }}</button>
      </div>

      <div v-if="!config" class="prompts-empty">
        No prompts generated yet. Fill in your purpose and schema above, then click "Save &amp; Generate Prompts".
      </div>
      <div v-else class="prompt-editor-wrap">
        <textarea
          v-model="promptDrafts[activeTab]"
          class="prompt-editor"
          rows="8"
          spellcheck="false"
        />
        <div class="prompt-actions">
          <button
            class="btn-secondary"
            :disabled="savingPrompts"
            @click="doSavePrompts"
          >
            {{ savingPrompts ? 'Saving…' : 'Save Edits' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Danger Zone -->
    <div v-if="config" class="config-card danger-card">
      <h3>Danger Zone</h3>
      <p class="card-hint">Remove your custom configuration. The extraction pipeline will fall back to built-in defaults.</p>
      <button class="btn-danger" :disabled="deleting" @click="doDelete">
        {{ deleting ? 'Removing…' : 'Remove Configuration' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { getConfig, saveConfig, updatePrompts, regeneratePrompts, deleteConfig } from '../api'
import { useToast } from '../composables/useToast'
import type { AccountConfig } from '../types'

const { toast } = useToast()

const config = ref<AccountConfig | null>(null)
const saving = ref(false)
const savingPrompts = ref(false)
const regenerating = ref(false)
const deleting = ref(false)
const regenComment = ref('')
const activeTab = ref<'prompt_extractor' | 'prompt_reviewer' | 'prompt_compressor'>('prompt_extractor')

const promptTabs = [
  { key: 'prompt_extractor' as const, label: 'Extractor' },
  { key: 'prompt_reviewer' as const, label: 'Reviewer' },
  { key: 'prompt_compressor' as const, label: 'Compressor' },
]

const promptDrafts = reactive({
  prompt_extractor: '',
  prompt_reviewer: '',
  prompt_compressor: '',
})

const form = reactive({
  purpose_industry: '',
  purpose_agent_type: '',
  purpose_description: '',
})

const schemaText = ref('{\n  \n}')
const schemaValid = ref(true)

const formComplete = computed(() =>
  form.purpose_industry.trim() &&
  form.purpose_agent_type.trim() &&
  form.purpose_description.trim() &&
  schemaText.value.trim()
)

function validateSchema() {
  try {
    JSON.parse(schemaText.value)
    schemaValid.value = true
  } catch {
    schemaValid.value = false
  }
}

function applyConfig(c: AccountConfig) {
  config.value = c
  form.purpose_industry = c.purpose_industry
  form.purpose_agent_type = c.purpose_agent_type
  form.purpose_description = c.purpose_description
  schemaText.value = JSON.stringify(c.profile_schema, null, 2)
  schemaValid.value = true
  promptDrafts.prompt_extractor = c.prompt_extractor
  promptDrafts.prompt_reviewer = c.prompt_reviewer
  promptDrafts.prompt_compressor = c.prompt_compressor
}

onMounted(async () => {
  try {
    const res = await getConfig()
    applyConfig(res.data)
  } catch (e: any) {
    if (e?.response?.status !== 404) {
      toast('Failed to load configuration', 'error')
    }
  }
})

async function doSave() {
  validateSchema()
  if (!schemaValid.value) { toast('Fix JSON schema before saving', 'error'); return }
  saving.value = true
  try {
    const res = await saveConfig({
      profile_schema: JSON.parse(schemaText.value),
      purpose_industry: form.purpose_industry.trim(),
      purpose_agent_type: form.purpose_agent_type.trim(),
      purpose_description: form.purpose_description.trim(),
    })
    applyConfig(res.data)
    toast('Configuration saved and prompts generated', 'success')
  } catch (e: any) {
    const detail = e?.response?.data?.detail ?? 'Failed to save configuration'
    toast(detail, 'error')
  } finally {
    saving.value = false
  }
}

async function doSavePrompts() {
  savingPrompts.value = true
  try {
    const res = await updatePrompts({ [activeTab.value]: promptDrafts[activeTab.value] })
    applyConfig(res.data)
    toast('Prompt saved', 'success')
  } catch {
    toast('Failed to save prompt', 'error')
  } finally {
    savingPrompts.value = false
  }
}

async function doRegenerate() {
  if (config.value && (promptDrafts.prompt_extractor !== config.value.prompt_extractor ||
    promptDrafts.prompt_reviewer !== config.value.prompt_reviewer ||
    promptDrafts.prompt_compressor !== config.value.prompt_compressor)) {
    if (!confirm('Regenerating will overwrite your manual edits. Continue?')) return
  }
  regenerating.value = true
  try {
    const res = await regeneratePrompts(regenComment.value.trim() || undefined)
    applyConfig(res.data)
    regenComment.value = ''
    toast('Prompts regenerated', 'success')
  } catch (e: any) {
    const detail = e?.response?.data?.detail ?? 'Failed to regenerate prompts'
    toast(detail, 'error')
  } finally {
    regenerating.value = false
  }
}

async function doDelete() {
  if (!confirm('Remove your custom configuration? The pipeline will fall back to built-in defaults.')) return
  deleting.value = true
  try {
    await deleteConfig()
    config.value = null
    form.purpose_industry = ''
    form.purpose_agent_type = ''
    form.purpose_description = ''
    schemaText.value = '{\n  \n}'
    promptDrafts.prompt_extractor = ''
    promptDrafts.prompt_reviewer = ''
    promptDrafts.prompt_compressor = ''
    toast('Configuration removed', 'success')
  } catch {
    toast('Failed to remove configuration', 'error')
  } finally {
    deleting.value = false
  }
}
</script>

<style scoped>
.config-view {
  padding: 24px;
  max-width: 860px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.config-header h2 {
  margin: 0 0 6px;
  font-size: 20px;
}

.config-subtitle {
  margin: 0;
  font-size: 13px;
  color: var(--muted, #888);
}

.config-card {
  background: var(--surface, #1a1a1a);
  border: 1px solid var(--border, #333);
  border-radius: 10px;
  padding: 20px;
}

.config-card h3 {
  margin: 0 0 4px;
  font-size: 15px;
}

.card-hint {
  margin: 0 0 14px;
  font-size: 12px;
  color: var(--muted, #888);
}

.purpose-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.purpose-row .form-field {
  flex: 1;
  min-width: 160px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.form-field label {
  font-size: 12px;
  color: var(--muted, #888);
  font-weight: 500;
}

.form-field input,
.form-field textarea {
  padding: 8px 10px;
  border: 1px solid var(--border, #333);
  border-radius: 6px;
  background: var(--bg, #111);
  color: var(--text, #eee);
  font-size: 13px;
  font-family: inherit;
  resize: vertical;
  outline: none;
  transition: border-color 0.15s;
}

.form-field input:focus,
.form-field textarea:focus {
  border-color: var(--accent, #6366f1);
}

.schema-editor {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border, #333);
  border-radius: 6px;
  background: var(--bg, #111);
  color: var(--text, #eee);
  font-family: monospace;
  font-size: 13px;
  resize: vertical;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.15s;
}

.schema-editor:focus {
  border-color: var(--accent, #6366f1);
}

.schema-status {
  margin-top: 6px;
  font-size: 11px;
}

.schema-status.valid { color: #4ade80; }
.schema-status.invalid { color: #f87171; }

.save-row {
  display: flex;
  justify-content: flex-end;
}

.btn-primary {
  padding: 10px 24px;
  background: var(--accent, #6366f1);
  color: #fff;
  border: none;
  border-radius: 7px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
}

.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-secondary {
  padding: 7px 14px;
  background: var(--surface, #1a1a1a);
  color: var(--text, #eee);
  border: 1px solid var(--border, #333);
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  transition: border-color 0.15s;
}

.btn-secondary:hover { border-color: var(--accent, #6366f1); }
.btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-danger {
  padding: 8px 18px;
  background: transparent;
  color: #f87171;
  border: 1px solid #f87171;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s;
}

.btn-danger:hover { background: rgba(248, 113, 113, 0.1); }
.btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }

.prompts-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}

.regen-row {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.regen-input {
  padding: 7px 10px;
  border: 1px solid var(--border, #333);
  border-radius: 6px;
  background: var(--bg, #111);
  color: var(--text, #eee);
  font-size: 12px;
  min-width: 220px;
  outline: none;
}

.regen-input:focus { border-color: var(--accent, #6366f1); }

.prompt-tabs {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--border, #333);
  margin-bottom: 12px;
}

.prompt-tab {
  padding: 8px 16px;
  font-size: 12px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  color: var(--muted, #888);
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
}

.prompt-tab.active {
  color: var(--accent, #6366f1);
  border-bottom-color: var(--accent, #6366f1);
  font-weight: 600;
}

.prompt-editor {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border, #333);
  border-radius: 6px;
  background: var(--bg, #111);
  color: var(--text, #eee);
  font-size: 13px;
  font-family: inherit;
  resize: vertical;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.15s;
}

.prompt-editor:focus { border-color: var(--accent, #6366f1); }

.prompt-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}

.prompts-empty {
  padding: 20px;
  text-align: center;
  color: var(--muted, #888);
  font-size: 13px;
  background: var(--bg, #111);
  border: 1px dashed var(--border, #333);
  border-radius: 6px;
}

.danger-card {
  border-color: rgba(248, 113, 113, 0.3);
}
</style>

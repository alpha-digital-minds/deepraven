<template>
  <div class="po-section">
    <div class="po-section-title">Project Details</div>
    <div class="info-row">
      <div><div class="info-label">Project ID</div><div class="info-val">{{ projectId }}</div></div>
      <button class="copy-btn" @click="copy(projectId)">Copy</button>
    </div>
    <div class="info-row">
      <div><div class="info-label">API Base URL</div><div class="info-val">{{ base }}</div></div>
      <button class="copy-btn" @click="copy(base)">Copy</button>
    </div>
  </div>

  <div class="po-section">
    <div class="po-section-title">Quick Start</div>
    <p style="font-size:13px;color:var(--muted);margin-bottom:14px">
      Create an API key in the <strong>API Keys</strong> tab and use it as your bearer token.
      Use any stable string as <code style="background:#f1f5f9;padding:1px 5px;border-radius:3px">CONTACT_ID</code>
      (email, CRM ID, etc.) — DeepRaven creates the contact automatically on first use.
    </p>
    <div style="margin-bottom:8px;font-size:13px;font-weight:600">Send a conversation</div>
    <div class="snippet-tabs">
      <div
        v-for="l in langs" :key="l"
        class="snippet-tab"
        :class="{ active: activeLang === l }"
        @click="activeLang = l"
      >{{ l }}</div>
    </div>
    <pre class="code-block">{{ snippets[activeLang].send }}</pre>
    <div style="margin-bottom:8px;font-size:13px;font-weight:600">Retrieve profile</div>
    <pre class="code-block">{{ snippets[activeLang].get }}</pre>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useToast } from '../composables/useToast'

const props = defineProps<{ projectId: string }>()
const { toast } = useToast()

const base = `${window.location.origin}/api/v1`
const langs = ['curl', 'python', 'node'] as const
type Lang = typeof langs[number]
const activeLang = ref<Lang>('curl')

const snippets = computed<Record<Lang, { send: string; get: string }>>(() => ({
  curl: {
    send: `curl -X POST ${base}/projects/${props.projectId}/contacts/CONTACT_ID/conversations \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"messages":[{"role":"user","content":"I am interested in your product."},{"role":"assistant","content":"Great! Tell me more about your needs."}]}'`,
    get: `curl ${base}/projects/${props.projectId}/contacts/CONTACT_ID/profile \\
  -H "Authorization: Bearer YOUR_API_KEY"`,
  },
  python: {
    send: `import requests\n\nAPI_KEY    = "YOUR_API_KEY"\nBASE_URL   = "${base}"\nPROJECT_ID = "${props.projectId}"\nCONTACT_ID = "your-contact-id"\n\nrequests.post(\n    f"{BASE_URL}/projects/{PROJECT_ID}/contacts/{CONTACT_ID}/conversations",\n    headers={"Authorization": f"Bearer {API_KEY}"},\n    json={"messages": [{"role": "user", "content": "I need a gift under $200"}]},\n)`,
    get: `resp = requests.get(\n    f"{BASE_URL}/projects/{PROJECT_ID}/contacts/{CONTACT_ID}/profile",\n    headers={"Authorization": f"Bearer {API_KEY}"},\n)\nprint(resp.json()["personal"]["name"])`,
  },
  node: {
    send: `const BASE_URL = "${base}";\nconst PROJECT_ID = "${props.projectId}";\nconst API_KEY = "YOUR_API_KEY";\nconst CONTACT_ID = "your-contact-id";\n\nawait fetch(\`\${BASE_URL}/projects/\${PROJECT_ID}/contacts/\${CONTACT_ID}/conversations\`, {\n  method: "POST",\n  headers: { "Authorization": \`Bearer \${API_KEY}\`, "Content-Type": "application/json" },\n  body: JSON.stringify({ messages: [{ role: "user", content: "I need a gift under $200" }] }),\n});`,
    get: `const res = await fetch(\n  \`\${BASE_URL}/projects/\${PROJECT_ID}/contacts/\${CONTACT_ID}/profile\`,\n  { headers: { Authorization: \`Bearer \${API_KEY}\` } }\n);\nconst p = await res.json();\nconsole.log(p.personal.name, p.sales.pain_points);`,
  },
}))

function copy(text: string) {
  navigator.clipboard.writeText(text).then(() => toast('Copied!', 'success'))
}
</script>

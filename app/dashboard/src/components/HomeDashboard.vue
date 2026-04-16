<template>
  <div class="home-panel">
    <div class="home-title">Overview</div>
    <div class="home-sub">Welcome back, {{ authStore.email }}</div>

    <div class="stat-cards">
      <div v-if="loading" v-for="i in 4" :key="i" class="stat-card">
        <div class="sc-label" style="background:#f1f5f9;width:60%;height:10px;border-radius:4px" />
        <div class="sc-value" style="background:#f1f5f9;width:40%;height:28px;border-radius:4px;margin-top:8px" />
      </div>
      <template v-else>
        <div class="stat-card sc-blue">
          <div class="sc-label">Projects</div>
          <div class="sc-value">{{ stats?.projects ?? 0 }}</div>
          <div class="sc-sub">active projects</div>
        </div>
        <div class="stat-card sc-green">
          <div class="sc-label">Contacts</div>
          <div class="sc-value">{{ (stats?.contacts ?? 0).toLocaleString() }}</div>
          <div class="sc-sub">tracked contacts</div>
        </div>
        <div class="stat-card sc-amber">
          <div class="sc-label">Conversations</div>
          <div class="sc-value">{{ (stats?.conversations ?? 0).toLocaleString() }}</div>
          <div class="sc-sub">total ingested</div>
        </div>
        <div class="stat-card sc-purple">
          <div class="sc-label">LLM Tokens</div>
          <div class="sc-value">{{ fmtTokens(stats?.total_tokens ?? 0) }}</div>
          <div class="sc-sub">tokens consumed</div>
        </div>
      </template>
    </div>

    <div class="home-section">
      <div class="home-section-title">💬 Conversations — last 30 days</div>
      <div class="chart-card">
        <canvas ref="chartCanvas" height="90" />
      </div>
    </div>

    <div class="home-section">
      <div class="home-section-title">⚡ LLM Usage by Project</div>
      <div class="chart-card" style="padding:0;overflow:hidden">
        <div style="padding:16px 22px">
          <p v-if="loading" style="color:var(--muted);font-size:13px">Loading…</p>
          <p v-else-if="!usage.length" style="color:var(--muted);font-size:13px">
            No LLM usage recorded yet. Usage is logged when profiles are extracted.
          </p>
          <table v-else class="usage-table">
            <thead>
              <tr>
                <th>Project</th><th>Calls</th><th>Prompt</th>
                <th>Completion</th><th>Total tokens</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in usage" :key="r.project_name">
                <td><span class="proj-name">{{ r.project_name }}</span></td>
                <td>{{ Number(r.calls).toLocaleString() }}</td>
                <td>{{ fmtTokens(Number(r.prompt_tokens)) }}</td>
                <td>{{ fmtTokens(Number(r.completion_tokens)) }}</td>
                <td>
                  <div class="usage-bar-wrap">
                    <div class="usage-bar">
                      <div class="usage-bar-fill" :style="{ width: usagePct(r) + '%' }" />
                    </div>
                    <span style="min-width:42px">{{ fmtTokens(Number(r.total_tokens)) }}</span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import {
  Chart, BarController, CategoryScale, LinearScale, BarElement, Tooltip,
} from 'chart.js'
import { useAuthStore } from '../stores/auth'
import { getStatsOverview, getDailyConversations, getUsageStats, fmtTokens } from '../api'
import type { StatsOverview, ProjectUsage } from '../types'

Chart.register(BarController, CategoryScale, LinearScale, BarElement, Tooltip)

const authStore = useAuthStore()
const chartCanvas = ref<HTMLCanvasElement | null>(null)
const loading = ref(true)
const stats = ref<StatsOverview | null>(null)
const usage = ref<ProjectUsage[]>([])
let chart: Chart | null = null

const maxTokens = ref(1)
function usagePct(r: ProjectUsage) {
  return Math.round((Number(r.total_tokens) / maxTokens.value) * 100)
}

onMounted(async () => {
  try {
    const [sRes, dRes, uRes] = await Promise.all([
      getStatsOverview(),
      getDailyConversations(),
      getUsageStats(),
    ])
    stats.value = sRes.data
    usage.value = uRes.data
    maxTokens.value = Math.max(...uRes.data.map(r => Number(r.total_tokens)), 1)
    renderChart(dRes.data)
  } catch { /* interceptor handles 401 */ } finally {
    loading.value = false
  }
})

onUnmounted(() => { chart?.destroy() })

function renderChart(daily: { date: string; count: number }[]) {
  if (!chartCanvas.value) return
  const today = new Date()
  const map: Record<string, number> = {}
  daily.forEach(r => { map[r.date] = Number(r.count) })
  const labels: string[] = []
  const data: number[] = []
  for (let i = 29; i >= 0; i--) {
    const d = new Date(today)
    d.setDate(d.getDate() - i)
    const key = d.toISOString().slice(0, 10)
    labels.push(key.slice(5))
    data.push(map[key] || 0)
  }
  chart?.destroy()
  chart = new Chart(chartCanvas.value, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Conversations',
        data,
        backgroundColor: 'rgba(99,102,241,.2)',
        borderColor: '#6366f1',
        borderWidth: 1.5,
        borderRadius: 3,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { font: { size: 10 }, maxRotation: 45 }, grid: { display: false } },
        y: { beginAtZero: true, ticks: { precision: 0, font: { size: 10 } }, grid: { color: '#f1f5f9' } },
      },
    },
  })
}
</script>

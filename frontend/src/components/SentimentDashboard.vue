<template>
  <div class="sentiment-dashboard">
    <div class="dash-header">
      <span class="section-label">04 / Sentiment Dashboard</span>
      <div class="header-actions">
        <button class="btn-refresh" @click="loadData" :disabled="loading">
          {{ loading ? 'Analyzing...' : '↻ Refresh' }}
        </button>
        <button class="btn-refresh" @click="exportJSON" :disabled="!data" title="Export raw JSON">
          ↓ JSON
        </button>
        <button class="btn-refresh" @click="exportCSV" :disabled="!data" title="Export timeline as CSV">
          ↓ CSV
        </button>
      </div>
    </div>

    <div v-if="loading && !data" class="loading-state">
      <div class="loading-msg">Running sentiment analysis across all three scenarios...</div>
      <div class="loading-hint">This may take a minute (LLM classification in progress)</div>
    </div>

    <div v-else-if="error" class="error-state">
      {{ error }}
    </div>

    <div v-else-if="data">
      <!-- Scenario tabs -->
      <div class="scenario-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="tab-btn"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >{{ tab.label }}</button>
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'compare' }"
          @click="activeTab = 'compare'; loadComparison()"
        >A vs B vs C</button>
      </div>

      <!-- Single-scenario view -->
      <div v-if="activeTab !== 'compare'" class="scenario-view">
        <div v-if="currentScenario" class="scenario-content">
          <!-- Overall Sentiment Score -->
          <div class="panel-row">
            <div class="panel sentiment-panel">
              <div class="panel-title">Overall Sentiment</div>
              <div class="sentiment-gauge">
                <div class="gauge-bar">
                  <div
                    class="gauge-positive"
                    :style="{ width: currentScenario.overall.positive_pct + '%' }"
                  />
                  <div
                    class="gauge-neutral"
                    :style="{ width: currentScenario.overall.neutral_pct + '%' }"
                  />
                  <div
                    class="gauge-negative"
                    :style="{ width: currentScenario.overall.negative_pct + '%' }"
                  />
                </div>
                <div class="gauge-labels">
                  <span class="label-positive">{{ currentScenario.overall.positive_pct }}% Positive</span>
                  <span class="label-neutral">{{ currentScenario.overall.neutral_pct }}% Neutral</span>
                  <span class="label-negative">{{ currentScenario.overall.negative_pct }}% Negative</span>
                </div>
                <div class="avg-score">
                  Avg score: <strong>{{ currentScenario.overall.avg_score > 0 ? '+' : '' }}{{ currentScenario.overall.avg_score }}</strong>
                  <span v-if="currentScenario.overall.weighted_avg_score !== undefined">
                    · Weighted: <strong>{{ currentScenario.overall.weighted_avg_score > 0 ? '+' : '' }}{{ currentScenario.overall.weighted_avg_score }}</strong>
                  </span>
                  · {{ currentScenario.total_posts_analyzed }} posts analyzed
                </div>
                <div v-if="currentScenario.overall.nps_score !== undefined" class="nps-score">
                  NPS: <strong :class="currentScenario.overall.nps_score >= 0 ? 'score-pos' : 'score-neg'">{{ currentScenario.overall.nps_score > 0 ? '+' : '' }}{{ currentScenario.overall.nps_score }}</strong>
                  <span class="nps-hint">{{ npsLabel(currentScenario.overall.nps_score) }}</span>
                </div>
              </div>
            </div>

            <!-- Faction Breakdown -->
            <div class="panel faction-panel">
              <div class="panel-title">Faction Breakdown</div>
              <div class="factions">
                <div v-for="f in factionItems" :key="f.key" class="faction-row">
                  <span class="faction-label">{{ f.label }}</span>
                  <div class="faction-bar-wrap">
                    <div class="faction-bar" :class="'faction-' + f.key" :style="{ width: (currentScenario.factions[f.pct_key] || 0) + '%' }" />
                  </div>
                  <span class="faction-pct">{{ currentScenario.factions[f.pct_key] || 0 }}%</span>
                  <span class="faction-count">({{ currentScenario.factions[f.count_key] || 0 }})</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Timeline Chart -->
          <div class="panel timeline-panel">
            <div class="panel-title">Sentiment Timeline</div>
            <div class="timeline-chart">
              <div v-if="!currentScenario.timeline.length" class="chart-empty">No timeline data yet</div>
              <div v-else class="chart-svg-wrap">
                <svg :viewBox="`0 0 ${chartW} ${chartH}`" class="chart-svg">
                  <!-- Zero line -->
                  <line :x1="chartPad" :y1="zeroY" :x2="chartW - chartPad" :y2="zeroY" stroke="#e0e0e0" stroke-width="1" />
                  <!-- Positive/Negative regions -->
                  <rect :x="chartPad" :y="chartPad" :width="chartW - chartPad * 2" :height="zeroY - chartPad" fill="#f9fffe" />
                  <rect :x="chartPad" :y="zeroY" :width="chartW - chartPad * 2" :height="chartH - chartPad - zeroY" fill="#fff9f9" />
                  <!-- Weighted avg line (dashed, behind main line) -->
                  <polyline v-if="weightedTimelinePoints" :points="weightedTimelinePoints" fill="none" stroke="#ff6b00" stroke-width="1.5" stroke-dasharray="4,3" opacity="0.6" />
                  <!-- Score line -->
                  <polyline :points="timelinePoints" fill="none" stroke="#111" stroke-width="2" />
                  <!-- Event injection markers -->
                  <template v-for="marker in eventMarkerCoords" :key="'evt-'+marker.round">
                    <line
                      :x1="marker.x" :y1="chartPad"
                      :x2="marker.x" :y2="chartH - chartPad"
                      :stroke="marker.color" stroke-width="1" stroke-dasharray="4,3"
                    />
                    <text :x="marker.x" :y="chartPad - 4" text-anchor="middle" :font-size="7" :fill="marker.color">
                      {{ marker.label }}
                    </text>
                  </template>
                  <!-- Data points -->
                  <circle
                    v-for="(pt, i) in timelineCoords"
                    :key="i"
                    :cx="pt.x"
                    :cy="pt.y"
                    r="3"
                    fill="#111"
                  />
                  <!-- Y axis labels -->
                  <text :x="chartPad - 4" :y="chartPad + 4" text-anchor="end" font-size="9" fill="#888">+1</text>
                  <text :x="chartPad - 4" :y="zeroY + 4" text-anchor="end" font-size="9" fill="#888">0</text>
                  <text :x="chartPad - 4" :y="chartH - chartPad + 4" text-anchor="end" font-size="9" fill="#888">-1</text>
                  <!-- X axis (round numbers) -->
                  <text
                    v-for="(pt, i) in timelineCoords"
                    :key="'lbl'+i"
                    :x="pt.x"
                    :y="chartH - chartPad + 14"
                    text-anchor="middle"
                    font-size="8"
                    fill="#888"
                  >{{ currentScenario.timeline[i].round_num }}</text>
                </svg>
                <div class="timeline-legend-inline">
                  <span class="legend-raw">— Raw avg</span>
                  <span class="legend-weighted">-- Weighted avg</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Velocity Sparkline -->
          <div v-if="velocityData.length > 1" class="panel velocity-panel">
            <div class="panel-title">Sentiment Velocity (Rate of Change)</div>
            <div class="velocity-bars">
              <div v-for="(v, i) in velocityData" :key="i" class="vel-bar-col">
                <div class="vel-bar-wrap">
                  <div
                    class="vel-bar"
                    :class="v.val >= 0 ? 'vel-up' : 'vel-down'"
                    :style="{ height: Math.min(Math.abs(v.val) * 200, 100) + '%', [v.val >= 0 ? 'bottom' : 'top']: '50%' }"
                  />
                  <div class="vel-zero" />
                </div>
                <span class="vel-label">{{ v.round }}</span>
              </div>
            </div>
          </div>

          <!-- Top Objections + Persona Heatmap -->
          <div class="panel-row">
            <div class="panel objections-panel">
              <div class="panel-title">Top Objections</div>
              <div v-if="!currentScenario.top_objections.length" class="empty-msg">No significant objections detected</div>
              <div v-for="(obj, i) in currentScenario.top_objections" :key="i" class="objection-row">
                <span class="obj-rank">{{ i + 1 }}</span>
                <div class="obj-content">
                  <div class="obj-theme">{{ obj.theme }}</div>
                  <div v-if="obj.example" class="obj-example">"{{ obj.example }}"</div>
                </div>
                <span v-if="obj.count" class="obj-count">~{{ obj.count }}</span>
              </div>
            </div>

            <!-- Topic Breakdown -->
            <div v-if="currentScenario.topic_breakdown?.overall && Object.keys(currentScenario.topic_breakdown.overall).length" class="panel topic-panel">
              <div class="panel-title">Topic Breakdown</div>
              <div v-for="(count, topic) in currentScenario.topic_breakdown.overall" :key="topic" class="topic-row">
                <span class="topic-name">{{ topic }}</span>
                <div class="topic-bar-wrap">
                  <div class="topic-bar" :style="{ width: (count / maxTopicCount * 100) + '%' }" />
                </div>
                <span class="topic-count">{{ count }}</span>
              </div>
            </div>
          </div>

          <div class="panel-row">
            <div class="panel heatmap-panel">
              <div class="panel-title">Persona Heatmap</div>
              <div v-if="!Object.keys(currentScenario.persona_heatmap || {}).length" class="empty-msg">No heatmap data yet</div>
              <div v-for="(score, arch) in currentScenario.persona_heatmap" :key="arch" class="heatmap-row">
                <span class="heatmap-arch">{{ formatArchName(arch) }}</span>
                <div class="heatmap-bar-wrap">
                  <div
                    class="heatmap-bar"
                    :class="score >= 0 ? 'bar-positive' : 'bar-negative'"
                    :style="{ width: Math.abs(score) * 100 + '%', marginLeft: score >= 0 ? '50%' : (50 + score * 50) + '%' }"
                  />
                  <div class="heatmap-zero" />
                </div>
                <span class="heatmap-score" :class="score >= 0 ? 'score-pos' : 'score-neg'">
                  {{ score >= 0 ? '+' : '' }}{{ score }}
                </span>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="no-data">No data available for this scenario yet</div>
      </div>

      <!-- Comparison view -->
      <div v-else class="compare-view">
        <div v-if="loadingCompare" class="loading-state">Loading comparison data...</div>
        <div v-else-if="compareData" class="compare-content">
          <div class="panel timeline-panel">
            <div class="panel-title">Scenario Comparison — Sentiment Score by Round</div>
            <div class="timeline-chart">
              <svg :viewBox="`0 0 ${chartW} ${chartH}`" class="chart-svg">
                <line :x1="chartPad" :y1="zeroY" :x2="chartW - chartPad" :y2="zeroY" stroke="#e0e0e0" stroke-width="1" />
                <polyline :points="comparePoints('a')" fill="none" stroke="#111" stroke-width="2" />
                <polyline :points="comparePoints('b')" fill="none" stroke="#ff6b00" stroke-width="2" stroke-dasharray="6,3" />
                <polyline :points="comparePoints('c')" fill="none" stroke="#cc0000" stroke-width="2" stroke-dasharray="3,3" />
              </svg>
            </div>
            <div class="compare-legend">
              <span class="legend-a">— Scenario A (Baseline)</span>
              <span class="legend-b">-- Scenario B (Competitive)</span>
              <span class="legend-c">··· Scenario C (Crisis)</span>
            </div>
          </div>

          <!-- Side-by-side overall stats -->
          <div class="compare-stats">
            <div v-for="(scenario_key, label) in { 'Scenario A': 'a', 'Scenario B': 'b', 'Scenario C': 'c' }" :key="scenario_key" class="compare-stat-col">
              <div class="stat-label">{{ label }}</div>
              <div v-if="compareData.details && compareData.details[scenario_key]">
                <div class="stat-score">{{ compareData.details[scenario_key].overall.avg_score >= 0 ? '+' : '' }}{{ compareData.details[scenario_key].overall.avg_score }}</div>
                <div class="stat-row">Advocates: {{ compareData.details[scenario_key].factions.advocates_pct }}%</div>
                <div class="stat-row">Detractors: {{ compareData.details[scenario_key].factions.detractors_pct }}%</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Navigation -->
    <div class="dash-actions">
      <button class="btn-back" @click="$emit('back')">← Back to Scenarios</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { getCampaignSentiment, compareScenarios } from '../api/sentiment.js'

const props = defineProps({
  campaignId: { type: String, required: true }
})

defineEmits(['back'])

const loading = ref(false)
const loadingCompare = ref(false)
let autoRetryTimer = null
const error = ref(null)
const data = ref(null)
const compareData = ref(null)
const activeTab = ref('a')

const chartW = 600
const chartH = 140
const chartPad = 32
const zeroY = computed(() => chartPad + (chartH - chartPad * 2) / 2)

const tabs = [
  { key: 'a', label: 'Scenario A' },
  { key: 'b', label: 'Scenario B' },
  { key: 'c', label: 'Scenario C' },
]

const factionItems = [
  { key: 'advocates', label: 'Advocates', pct_key: 'advocates_pct', count_key: 'advocates' },
  { key: 'neutral', label: 'Neutral', pct_key: 'neutral_pct', count_key: 'neutral' },
  { key: 'detractors', label: 'Detractors', pct_key: 'detractors_pct', count_key: 'detractors' },
  { key: 'churned', label: 'Churned', pct_key: 'churned_pct', count_key: 'churned' },
]

const currentScenario = computed(() => {
  if (!data.value) return null
  return data.value[`scenario_${activeTab.value}`]
})

const timelineCoords = computed(() => {
  const tl = currentScenario.value?.timeline || []
  if (!tl.length) return []
  const n = tl.length
  const xStep = (chartW - chartPad * 2) / Math.max(n - 1, 1)
  return tl.map((pt, i) => ({
    x: chartPad + i * xStep,
    y: zeroY.value - pt.avg_score * (chartH - chartPad * 2) / 2,
  }))
})

const timelinePoints = computed(() =>
  timelineCoords.value.map(p => `${p.x},${p.y}`).join(' ')
)

const comparePoints = (scenario) => {
  if (!compareData.value) return ''
  const scores = compareData.value[`scenario_${scenario}`] || []
  const rounds = compareData.value.rounds || []
  if (!scores.length || !rounds.length) return ''
  const n = rounds.length
  const xStep = (chartW - chartPad * 2) / Math.max(n - 1, 1)
  return scores
    .map((s, i) => {
      if (s === null || s === undefined) return null
      const x = chartPad + i * xStep
      const y = zeroY.value - s * (chartH - chartPad * 2) / 2
      return `${x},${y}`
    })
    .filter(Boolean)
    .join(' ')
}

const weightedTimelineCoords = computed(() => {
  const tl = currentScenario.value?.timeline || []
  if (!tl.length) return []
  const n = tl.length
  const xStep = (chartW - chartPad * 2) / Math.max(n - 1, 1)
  return tl
    .map((pt, i) => pt.weighted_avg_score !== undefined ? {
      x: chartPad + i * xStep,
      y: zeroY.value - pt.weighted_avg_score * (chartH - chartPad * 2) / 2,
    } : null)
    .filter(Boolean)
})

const weightedTimelinePoints = computed(() =>
  weightedTimelineCoords.value.map(p => `${p.x},${p.y}`).join(' ')
)

const velocityData = computed(() => {
  const tl = currentScenario.value?.timeline || []
  return tl
    .filter(pt => pt.velocity !== undefined)
    .map(pt => ({ round: pt.round_num, val: pt.velocity }))
})

const maxTopicCount = computed(() => {
  const topics = currentScenario.value?.topic_breakdown?.overall || {}
  const vals = Object.values(topics)
  return vals.length ? Math.max(...vals) : 1
})

const npsLabel = (score) => {
  if (score >= 50) return '(Excellent)'
  if (score >= 0) return '(Good)'
  if (score >= -50) return '(Needs work)'
  return '(Critical)'
}

const formatArchName = (key) =>
  key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())

const eventMarkers = ref(null)

const eventMarkerCoords = computed(() => {
  if (!eventMarkers.value || !currentScenario.value?.timeline?.length) return []
  const tl = currentScenario.value.timeline
  const n = tl.length
  if (!n) return []
  const xStep = (chartW - chartPad * 2) / Math.max(n - 1, 1)
  const markers = []

  const bRound = eventMarkers.value.scenario_b_inject_round
  const cRound = eventMarkers.value.scenario_c_inject_round

  // Only show markers relevant to current scenario tab
  if (activeTab.value === 'b' && bRound) {
    const idx = tl.findIndex(pt => pt.round_num >= bRound)
    if (idx >= 0) {
      markers.push({ round: bRound, x: chartPad + idx * xStep, color: '#ff6b00', label: 'Competitive' })
    }
  }
  if (activeTab.value === 'c' && cRound) {
    const idx = tl.findIndex(pt => pt.round_num >= cRound)
    if (idx >= 0) {
      markers.push({ round: cRound, x: chartPad + idx * xStep, color: '#cc0000', label: 'Crisis' })
    }
  }
  return markers
})

const exportJSON = () => {
  if (!data.value) return
  const blob = new Blob([JSON.stringify(data.value, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `sentiment_${props.campaignId}.json`
  a.click()
  URL.revokeObjectURL(url)
}

const exportCSV = () => {
  if (!currentScenario.value?.timeline?.length) return
  const tl = currentScenario.value.timeline
  const headers = ['round', 'avg_score', 'weighted_avg_score', 'velocity', 'positive', 'neutral', 'negative']
  const rows = tl.map(pt =>
    [pt.round_num, pt.avg_score, pt.weighted_avg_score || '', pt.velocity || '', pt.positive, pt.neutral, pt.negative].join(',')
  )
  const csv = [headers.join(','), ...rows].join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `sentiment_${activeTab.value}_${props.campaignId}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

const _hasData = (res) => {
  return res && (res.scenario_a?.total_posts_analyzed > 0 ||
                 res.scenario_b?.total_posts_analyzed > 0 ||
                 res.scenario_c?.total_posts_analyzed > 0)
}

const loadData = async () => {
  loading.value = true
  error.value = null
  try {
    const res = await getCampaignSentiment(props.campaignId)
    data.value = res
    if (res.event_markers) {
      eventMarkers.value = res.event_markers
    }
    // Auto-retry every 30 s while the simulation hasn't produced posts yet
    if (!_hasData(res)) {
      if (!autoRetryTimer) {
        autoRetryTimer = setInterval(async () => {
          try {
            const r = await getCampaignSentiment(props.campaignId)
            data.value = r
            if (r.event_markers) eventMarkers.value = r.event_markers
            if (_hasData(r)) {
              clearInterval(autoRetryTimer)
              autoRetryTimer = null
            }
          } catch {
            // keep retrying silently
          }
        }, 30000)
      }
    } else {
      if (autoRetryTimer) {
        clearInterval(autoRetryTimer)
        autoRetryTimer = null
      }
    }
  } catch (e) {
    error.value = e?.response?.data?.error || e?.message || 'Failed to load sentiment data'
  } finally {
    loading.value = false
  }
}

const loadComparison = async () => {
  if (compareData.value) return
  loadingCompare.value = true
  try {
    const res = await compareScenarios(props.campaignId)
    compareData.value = res.comparison
  } catch (e) {
    console.error('Compare failed:', e)
  } finally {
    loadingCompare.value = false
  }
}

onMounted(loadData)
onUnmounted(() => { if (autoRetryTimer) clearInterval(autoRetryTimer) })
</script>

<style scoped>
.sentiment-dashboard { font-family: 'JetBrains Mono', monospace; color: #111; }
.dash-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 12px;
  border-bottom: 1px solid #111;
  margin-bottom: 20px;
}
.section-label { font-size: 13px; font-weight: 600; }
.header-actions { display: flex; gap: 10px; }
.btn-refresh {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  border: 1px solid #111;
  background: #fff;
  color: #111;
  padding: 6px 14px;
  cursor: pointer;
}
.btn-refresh:hover:not(:disabled) { background: #f5f5f5; }
.btn-refresh:disabled { opacity: 0.5; }
.loading-state, .error-state {
  padding: 30px 0;
  font-size: 13px;
  color: #888;
  text-align: center;
}
.loading-hint { font-size: 11px; color: #bbb; margin-top: 6px; }
.error-state { color: #cc0000; }
.scenario-tabs {
  display: flex;
  gap: 0;
  border-bottom: 1px solid #e0e0e0;
  margin-bottom: 20px;
}
.tab-btn {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  padding: 8px 20px;
  border: 1px solid transparent;
  border-bottom: none;
  background: none;
  cursor: pointer;
  color: #888;
  margin-bottom: -1px;
}
.tab-btn.active {
  border: 1px solid #e0e0e0;
  border-bottom: 1px solid #fff;
  color: #111;
  background: #fff;
  font-weight: 600;
}
.panel-row { display: flex; gap: 14px; margin-bottom: 14px; }
.panel {
  border: 1px solid #e0e0e0;
  padding: 14px;
  flex: 1;
}
.panel-title {
  font-size: 11px;
  font-weight: 600;
  color: #888;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 12px;
}
/* Sentiment gauge */
.gauge-bar {
  height: 14px;
  display: flex;
  margin-bottom: 6px;
  border: 1px solid #e0e0e0;
}
.gauge-positive { background: #00a651; }
.gauge-neutral { background: #e0e0e0; }
.gauge-negative { background: #cc0000; }
.gauge-labels {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  margin-bottom: 6px;
}
.label-positive { color: #00a651; }
.label-neutral { color: #888; }
.label-negative { color: #cc0000; }
.avg-score { font-size: 11px; color: #555; }
.nps-score { font-size: 12px; color: #555; margin-top: 6px; }
.nps-score strong { font-size: 16px; }
.nps-hint { font-size: 10px; color: #999; margin-left: 4px; }
/* Factions */
.faction-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 12px;
}
.faction-label { min-width: 80px; color: #555; }
.faction-bar-wrap { flex: 1; height: 8px; background: #f0f0f0; }
.faction-bar { height: 100%; }
.faction-advocates { background: #00a651; }
.faction-neutral { background: #bbb; }
.faction-detractors { background: #ff4444; }
.faction-churned { background: #e0e0e0; }
.faction-pct { min-width: 36px; text-align: right; font-weight: 600; }
.faction-count { color: #888; min-width: 40px; }
/* Timeline */
.timeline-panel { margin-bottom: 14px; }
.chart-svg-wrap { overflow: hidden; }
.chart-svg { width: 100%; height: 140px; }
.chart-empty { font-size: 12px; color: #bbb; padding: 20px 0; text-align: center; }
.timeline-legend-inline { display: flex; gap: 16px; font-size: 10px; color: #888; margin-top: 4px; }
.legend-raw { color: #111; }
.legend-weighted { color: #ff6b00; }
/* Velocity */
.velocity-panel { margin-bottom: 14px; }
.velocity-bars { display: flex; gap: 2px; align-items: flex-end; height: 50px; }
.vel-bar-col { flex: 1; display: flex; flex-direction: column; align-items: center; }
.vel-bar-wrap { width: 100%; height: 40px; position: relative; }
.vel-bar { position: absolute; width: 100%; }
.vel-up { background: #00a651; }
.vel-down { background: #cc0000; }
.vel-zero { position: absolute; top: 50%; width: 100%; height: 1px; background: #e0e0e0; }
.vel-label { font-size: 7px; color: #bbb; margin-top: 2px; }
/* Objections */
.objection-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid #f5f5f5;
}
.obj-rank { font-size: 18px; font-weight: 700; color: #e0e0e0; min-width: 20px; }
.obj-content { flex: 1; }
.obj-theme { font-size: 12px; font-weight: 600; margin-bottom: 2px; }
.obj-example { font-size: 11px; color: #888; font-style: italic; }
.obj-count { font-size: 11px; color: #888; min-width: 40px; text-align: right; }
.empty-msg { font-size: 12px; color: #bbb; }
/* Topics */
.topic-row { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; font-size: 11px; }
.topic-name { min-width: 80px; color: #555; text-transform: capitalize; }
.topic-bar-wrap { flex: 1; height: 8px; background: #f5f5f5; }
.topic-bar { height: 100%; background: #555; }
.topic-count { min-width: 30px; text-align: right; color: #888; }
/* Persona Heatmap */
.heatmap-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 11px;
}
.heatmap-arch { min-width: 120px; color: #555; }
.heatmap-bar-wrap {
  flex: 1;
  height: 8px;
  background: #f5f5f5;
  position: relative;
}
.heatmap-zero {
  position: absolute;
  left: 50%;
  top: 0;
  height: 100%;
  width: 1px;
  background: #ccc;
}
.heatmap-bar {
  position: absolute;
  height: 100%;
}
.bar-positive { background: #00a651; }
.bar-negative { background: #cc0000; }
.heatmap-score { min-width: 50px; text-align: right; font-weight: 600; }
.score-pos { color: #00a651; }
.score-neg { color: #cc0000; }
/* Compare */
.compare-legend {
  display: flex;
  gap: 20px;
  font-size: 11px;
  margin-top: 8px;
  color: #555;
}
.legend-a { color: #111; }
.legend-b { color: #ff6b00; }
.legend-c { color: #cc0000; }
.compare-stats {
  display: flex;
  gap: 14px;
  margin-top: 14px;
}
.compare-stat-col {
  flex: 1;
  border: 1px solid #e0e0e0;
  padding: 14px;
}
.stat-label { font-size: 11px; font-weight: 600; color: #888; margin-bottom: 8px; }
.stat-score { font-size: 28px; font-weight: 700; margin-bottom: 8px; }
.stat-row { font-size: 11px; color: #555; margin-bottom: 3px; }
.no-data { font-size: 13px; color: #bbb; padding: 20px 0; }
.dash-actions { margin-top: 20px; }
.btn-back {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  padding: 10px 24px;
  cursor: pointer;
  border: 1px solid #111;
  background: #fff;
  color: #111;
}
.btn-back:hover { background: #f5f5f5; }
</style>

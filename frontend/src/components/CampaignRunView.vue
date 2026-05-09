<template>
  <div class="campaign-run">
    <div class="run-header">
      <span class="section-label">03 / Scenario Runner</span>
      <span class="section-meta" :class="statusClass">{{ statusLabel }}</span>
    </div>

    <!-- Three scenario columns -->
    <div class="scenarios-grid">
      <div
        v-for="(scenario, key) in scenarios"
        :key="key"
        class="scenario-col"
        :class="{ active: scenario.runner_status === 'running', done: isDone(scenario.runner_status) }"
      >
        <div class="scenario-header">
          <span class="scenario-id">{{ scenario.label }}</span>
          <span class="scenario-status-dot" :class="dotClass(scenario.runner_status)">■</span>
        </div>
        <div class="scenario-desc">{{ scenario.description }}</div>

        <!-- Progress bar -->
        <div class="progress-bar">
          <div
            class="progress-fill"
            :style="{ width: progressPct(scenario) + '%' }"
          />
        </div>
        <div class="progress-label">
          Round {{ scenario.current_round || 0 }} / {{ scenario.total_rounds || maxRounds }}
        </div>

        <!-- Event marker -->
        <div v-if="key === 'b' && campaign.scenario_b_injected" class="event-badge event-b">
          Competitive event injected at round {{ scenarioInjectRoundB }}
        </div>
        <div v-if="key === 'c' && campaign.scenario_c_injected" class="event-badge event-c">
          Crisis event injected at round {{ scenarioInjectRoundC }}
        </div>

        <!-- Status text -->
        <div class="scenario-status-text">{{ statusText(scenario.runner_status) }}</div>
      </div>
    </div>

    <!-- Manual Injection Panel -->
    <div class="gods-eye-panel">
      <div class="gods-eye-header">
        <span class="gods-eye-label">◇ Manual event injection</span>
        <span class="gods-eye-hint">Inject a real-time market event into a running scenario</span>
      </div>
      <div class="inject-controls">
        <select v-model="injectScenario" class="inject-select">
          <option value="b">Scenario B — Competitive</option>
          <option value="c">Scenario C — Crisis</option>
        </select>
        <textarea
          v-model="injectPrompt"
          class="inject-textarea"
          placeholder="Describe the event in natural language (e.g. 'A major security vulnerability was just disclosed...')"
          rows="2"
        />
        <button
          class="inject-btn"
          @click="handleInject"
          :disabled="injecting || !injectPrompt.trim()"
        >{{ injecting ? 'Injecting...' : 'Inject Event →' }}</button>
      </div>
      <div v-if="injectMessage" class="inject-message" :class="{ error: injectError }">
        {{ injectMessage }}
      </div>
    </div>

    <!-- Action Feed (recent actions across all scenarios) -->
    <div class="action-feed">
      <div class="feed-header">Recent Actions</div>
      <div v-if="recentActions.length === 0" class="feed-empty">Waiting for simulation to start...</div>
      <div v-for="(action, idx) in recentActions.slice(0, 12)" :key="idx" class="feed-item">
        <span class="feed-scenario">{{ action.scenario }}</span>
        <span class="feed-agent">{{ action.agent_name }}</span>
        <span class="feed-action">{{ action.action_type }}</span>
        <span class="feed-round">R{{ action.round_num }}</span>
      </div>
    </div>

    <!-- Navigation -->
    <div class="run-actions">
      <button class="btn-back" @click="$emit('back')">← Back</button>
      <button
        class="btn-next"
        @click="$emit('next')"
        :disabled="campaign.status !== 'completed' && campaign.status !== 'running'"
      >
        {{ campaign.status === 'completed' ? 'View Dashboard →' : 'Go to Dashboard →' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { getCampaign, injectEvent } from '../api/sentiment.js'

const props = defineProps({
  campaignId: { type: String, required: true },
  maxRounds: { type: Number, default: 20 },
})

const emit = defineEmits(['back', 'next'])

const campaign = ref({})
const scenarios = ref({
  a: { label: 'Scenario A — Baseline', description: 'Normal launch, no disruptions', runner_status: 'idle', current_round: 0, total_rounds: 0 },
  b: { label: 'Scenario B — Competitive', description: 'Competitive event injected mid-run', runner_status: 'idle', current_round: 0, total_rounds: 0 },
  c: { label: 'Scenario C — Crisis', description: 'Crisis event injected late in the run', runner_status: 'idle', current_round: 0, total_rounds: 0 },
})
const recentActions = ref([])
const injectScenario = ref('b')
const injectPrompt = ref('')
const injecting = ref(false)
const injectMessage = ref('')
const injectError = ref(false)

let pollInterval = null

const scenarioInjectRoundB = computed(() => campaign.value.scenario_b_inject_round || 7)
const scenarioInjectRoundC = computed(() => campaign.value.scenario_c_inject_round || 14)

const statusLabel = computed(() => {
  const s = campaign.value.status
  if (s === 'running') return '● Running'
  if (s === 'completed') return '✓ Completed'
  if (s === 'failed') return '✗ Failed'
  if (s === 'ready') return '◎ Ready'
  return '○ ' + (s || 'Unknown')
})

const statusClass = computed(() => ({
  'status-running': campaign.value.status === 'running',
  'status-done': campaign.value.status === 'completed',
  'status-error': campaign.value.status === 'failed',
}))

const progressPct = (scenario) => {
  if (!scenario.total_rounds) return 0
  return Math.round((scenario.current_round / scenario.total_rounds) * 100)
}

const dotClass = (status) => ({
  'dot-running': status === 'running' || status === 'starting',
  'dot-done': status === 'completed' || status === 'stopped',
  'dot-error': status === 'failed',
  'dot-idle': status === 'idle' || status === 'unknown',
})

const isDone = (status) => ['completed', 'stopped'].includes(status)

const statusText = (status) => {
  const map = {
    idle: 'Waiting...',
    starting: 'Starting...',
    running: 'Running',
    paused: 'Paused',
    stopping: 'Stopping...',
    stopped: 'Stopped',
    completed: 'Completed ✓',
    failed: 'Failed ✗',
    unknown: '—',
  }
  return map[status] || status || '—'
}

const fetchStatus = async () => {
  try {
    const res = await getCampaign(props.campaignId)
    campaign.value = res.campaign || {}
    const sa = res.scenario_a || {}
    const sb = res.scenario_b || {}
    const sc = res.scenario_c || {}
    scenarios.value.a = { ...scenarios.value.a, ...sa }
    scenarios.value.b = {
      ...scenarios.value.b,
      description: `Competitive event at round ${campaign.value.scenario_b_inject_round || scenarioInjectRoundB.value}`,
      ...sb,
    }
    scenarios.value.c = {
      ...scenarios.value.c,
      description: `Crisis event at round ${campaign.value.scenario_c_inject_round || scenarioInjectRoundC.value}`,
      ...sc,
    }

    // Collect recent actions
    const actions = []
    for (const [key, s] of Object.entries({ a: sa, b: sb, c: sc })) {
      if (s.recent_actions) {
        s.recent_actions.forEach(a => actions.push({ ...a, scenario: `S${key.toUpperCase()}` }))
      }
    }
    recentActions.value = actions
      .sort((a, b) => (b.round_num || 0) - (a.round_num || 0))
  } catch (e) {
    console.error('Failed to fetch campaign status:', e)
  }
}

const handleInject = async () => {
  injecting.value = true
  injectMessage.value = ''
  injectError.value = false
  try {
    await injectEvent(props.campaignId, {
      scenario: injectScenario.value,
      custom_prompt: injectPrompt.value,
    })
    injectMessage.value = `Event injected into Scenario ${injectScenario.value.toUpperCase()} successfully`
    injectPrompt.value = ''
    await fetchStatus()
  } catch (e) {
    injectError.value = true
    injectMessage.value = e?.response?.data?.error || e?.message || 'Injection failed'
  } finally {
    injecting.value = false
  }
}

onMounted(() => {
  fetchStatus()
  pollInterval = setInterval(fetchStatus, 8000)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})
</script>

<style scoped>
.campaign-run { font-family: 'JetBrains Mono', monospace; color: #111; }
.run-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 12px;
  border-bottom: 1px solid #111;
  margin-bottom: 20px;
}
.section-label { font-size: 13px; font-weight: 600; }
.section-meta { font-size: 12px; font-weight: 600; }
.status-running { color: #ff6b00; }
.status-done { color: #00a651; }
.status-error { color: #cc0000; }
.scenarios-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 24px;
}
.scenario-col {
  border: 1px solid #e0e0e0;
  padding: 14px;
  transition: border-color 0.2s;
}
.scenario-col.active { border-color: #ff6b00; }
.scenario-col.done { border-color: #ccc; opacity: 0.85; }
.scenario-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}
.scenario-id { font-size: 12px; font-weight: 700; }
.scenario-status-dot { font-size: 10px; }
.dot-running { color: #ff6b00; }
.dot-done { color: #00a651; }
.dot-error { color: #cc0000; }
.dot-idle { color: #ccc; }
.scenario-desc { font-size: 10px; color: #888; margin-bottom: 10px; }
.progress-bar {
  height: 3px;
  background: #e0e0e0;
  margin-bottom: 4px;
}
.progress-fill { height: 100%; background: #111; transition: width 0.5s; }
.progress-label { font-size: 10px; color: #888; margin-bottom: 6px; }
.event-badge {
  font-size: 10px;
  padding: 3px 8px;
  margin-bottom: 4px;
  display: inline-block;
}
.event-b { background: #fff3e0; color: #e65100; border: 1px solid #ffcc80; }
.event-c { background: #fce4ec; color: #b71c1c; border: 1px solid #f48fb1; }
.scenario-status-text { font-size: 11px; color: #666; margin-top: 4px; }
.gods-eye-panel {
  border: 1px solid #111;
  padding: 16px;
  margin-bottom: 20px;
}
.gods-eye-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 12px;
}
.gods-eye-label { font-size: 12px; font-weight: 700; }
.gods-eye-hint { font-size: 10px; color: #888; }
.inject-controls { display: flex; gap: 10px; align-items: flex-start; }
.inject-select {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  border: 1px solid #bbb;
  padding: 6px 10px;
  background: #fff;
  flex-shrink: 0;
  height: 60px;
}
.inject-textarea {
  flex: 1;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  border: 1px solid #bbb;
  padding: 6px 10px;
  resize: none;
  color: #111;
  outline: none;
}
.inject-textarea:focus { border-color: #111; }
.inject-btn {
  background: #111;
  color: #fff;
  border: none;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  padding: 8px 16px;
  cursor: pointer;
  flex-shrink: 0;
  height: 60px;
}
.inject-btn:hover:not(:disabled) { background: #333; }
.inject-btn:disabled { opacity: 0.5; cursor: default; }
.inject-message { font-size: 11px; color: #00a651; margin-top: 8px; }
.inject-message.error { color: #cc0000; }
.action-feed {
  border: 1px solid #e0e0e0;
  padding: 12px;
  margin-bottom: 20px;
  max-height: 200px;
  overflow-y: auto;
}
.feed-header { font-size: 11px; font-weight: 600; color: #888; margin-bottom: 8px; text-transform: uppercase; }
.feed-empty { font-size: 11px; color: #bbb; }
.feed-item {
  display: flex;
  gap: 10px;
  font-size: 11px;
  padding: 3px 0;
  border-bottom: 1px solid #f5f5f5;
}
.feed-scenario { min-width: 32px; color: #888; }
.feed-agent { min-width: 130px; color: #333; }
.feed-action { flex: 1; color: #111; }
.feed-round { color: #888; }
.run-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.btn-back, .btn-next {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  padding: 10px 24px;
  cursor: pointer;
  border: 1px solid #111;
}
.btn-back { background: #fff; color: #111; }
.btn-next { background: #111; color: #fff; }
.btn-back:hover { background: #f5f5f5; }
.btn-next:hover:not(:disabled) { background: #333; }
.btn-next:disabled { opacity: 0.4; cursor: default; }
</style>

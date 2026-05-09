<template>
  <div class="sentiment-view">
    <header class="workspace-topbar">
      <router-link to="/" class="workspace-brand">Sentiment Simulator</router-link>
      <div class="workspace-meta">Launch workflow · parallel scenario runner</div>
    </header>

    <main class="workspace-shell">
      <section class="workspace-hero">
        <div>
          <span class="hero-kicker">Product launch forecasting</span>
          <h1>Model the market before you ship.</h1>
          <p>
            Build a product brief, review the generated audience, prepare scenario inputs in the background,
            and monitor three parallel launch conditions from one dashboard.
          </p>
        </div>
        <div class="hero-status-card">
          <span class="status-label">Current state</span>
          <strong>{{ currentStepLabel }}</strong>
          <p>{{ currentStatusSummary }}</p>
        </div>
      </section>

      <section class="step-progress">
        <div
          v-for="(step, idx) in steps"
          :key="step"
          class="step-item"
          :class="{ active: currentStep === idx, done: currentStep > idx }"
        >
          <span class="step-num">{{ String(idx + 1).padStart(2, '0') }}</span>
          <span class="step-name">{{ step }}</span>
        </div>
      </section>

      <section class="step-content">
        <div v-if="currentStep === 0" class="surface-card">
          <SeedTemplateForm @submit="handleSeedSubmit" />
        </div>

        <div v-else-if="currentStep === 1" class="surface-card">
          <ArchetypeReview
            :totalAgents="seedData.total_agents"
            :graphBuilding="buildingGraph"
            @back="currentStep = 0"
            @next="handleArchetypeConfirm"
          />

          <div v-if="buildingGraph" class="status-panel">
            <div class="status-panel-header">
              <span>Graph preparation</span>
              <span>{{ Math.round(graphBuildPct) }}%</span>
            </div>
            <div class="status-bar">
              <div class="status-fill" :style="{ width: `${graphBuildPct}%` }" />
            </div>
            <div class="status-message">{{ graphBuildMsg }}</div>
          </div>

          <div v-if="buildError" class="error-banner">{{ buildError }}</div>

          <div v-if="graphData && !buildingGraph" class="graph-panel">
            <button class="graph-toggle" @click="showGraph = !showGraph">
              {{ showGraph ? 'Hide' : 'Show' }} knowledge graph preview
            </button>
            <div v-if="showGraph" class="graph-frame">
              <GraphPanel :graphData="graphData" />
            </div>
          </div>
        </div>

        <div v-else-if="currentStep === 2" class="surface-card">
          <div v-if="preparingCampaign" class="prepare-state">
            <div class="prepare-card">
              <span class="prepare-label">Preparing scenarios</span>
              <h2>Building the runnable launch model in the background.</h2>
              <p>
                The backend is generating archetype agents and simulation configuration for baseline,
                competitive, and crisis scenarios. This preparation step is asynchronous and safe to poll.
              </p>

              <div class="status-panel compact">
                <div class="status-panel-header">
                  <span>{{ prepareStatus }}</span>
                  <span>{{ prepareProgress }}%</span>
                </div>
                <div class="status-bar">
                  <div class="status-fill accent" :style="{ width: `${prepareProgress}%` }" />
                </div>
                <div class="status-message">Task {{ prepareTaskId || 'pending' }} · {{ prepareElapsed }}s elapsed</div>
              </div>
            </div>
          </div>

          <template v-else>
            <CampaignRunView
              v-if="campaignId"
              :campaignId="campaignId"
              :maxRounds="seedData.max_rounds || 20"
              @back="currentStep = 1"
              @next="goToDashboard"
            />
            <div v-else class="error-banner">
              No active campaign. Go back to step 1 and complete the archetype review.
            </div>
          </template>
        </div>

        <div v-else-if="currentStep === 3" class="surface-card">
          <SentimentDashboard v-if="campaignId" :campaignId="campaignId" @back="currentStep = 2" />
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import SeedTemplateForm from '../components/SeedTemplateForm.vue'
import ArchetypeReview from '../components/ArchetypeReview.vue'
import CampaignRunView from '../components/CampaignRunView.vue'
import SentimentDashboard from '../components/SentimentDashboard.vue'
import GraphPanel from '../components/GraphPanel.vue'
import { buildGraph, generateOntology, getGraphData, getTaskStatus } from '../api/graph.js'
import {
  createCampaign,
  getCampaign,
  getCampaignPrepareStatus,
  prepareCampaign,
  previewSeed,
  startCampaign,
} from '../api/sentiment.js'

const props = defineProps({
  campaignId: { type: String, default: '' },
})

const steps = ['Product seed', 'Population review', 'Scenario runner', 'Dashboard']
const currentStep = ref(0)

const seedData = ref({})
const projectId = ref('')
const graphId = ref('')
const campaignId = ref('')

const SESSION_KEY = 'sentiment_simulator_launch_state'

const buildingGraph = ref(false)
const graphBuildPct = ref(0)
const graphBuildMsg = ref('')
const buildError = ref('')
const graphData = ref(null)
const showGraph = ref(false)

const preparingCampaign = ref(false)
const prepareProgress = ref(0)
const prepareStatus = ref('Waiting for task start')
const prepareTaskId = ref('')
const prepareElapsed = ref(0)

let prepareTimer = null

const currentStepLabel = computed(() => steps[currentStep.value] || 'Campaign runner')
const currentStatusSummary = computed(() => {
  if (preparingCampaign.value) {
    return 'Scenario preparation is running asynchronously. The runner will start automatically when preparation completes.'
  }
  if (buildingGraph.value) {
    return 'Knowledge graph construction is in progress.'
  }
  if (currentStep.value === 3) {
    return 'Sentiment analysis is available from the dashboard and comparison view.'
  }
  return 'The sentiment launch path is the only public workflow in this frontend build.'
})

const saveState = () => {
  try {
    sessionStorage.setItem(
      SESSION_KEY,
      JSON.stringify({
        currentStep: currentStep.value,
        seedData: seedData.value,
        projectId: projectId.value,
        graphId: graphId.value,
        campaignId: campaignId.value,
        prepareTaskId: prepareTaskId.value,
        preparingCampaign: preparingCampaign.value,
      }),
    )
  } catch {
    // Ignore session storage failures.
  }
}

const clearState = () => {
  try {
    sessionStorage.removeItem(SESSION_KEY)
  } catch {
    // Ignore session storage failures.
  }
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

const startPrepareClock = () => {
  if (prepareTimer) {
    clearInterval(prepareTimer)
  }
  prepareTimer = setInterval(() => {
    prepareElapsed.value += 1
  }, 1000)
}

const stopPrepareClock = () => {
  if (prepareTimer) {
    clearInterval(prepareTimer)
    prepareTimer = null
  }
}

const goToDashboard = () => {
  currentStep.value = 3
  saveState()
}

const pollTask = async (taskId, onProgress) => {
  for (let attempt = 0; attempt < 240; attempt += 1) {
    await sleep(5000)
    try {
      const res = await getTaskStatus(taskId)
      const task = res.data || res
      onProgress(task.progress || 0, task.message || task.status || '')
      if (task.status === 'completed') return task
      if (task.status === 'failed') throw new Error(task.message || 'Task failed')
    } catch (error) {
      if (error.message === 'Task failed') throw error
    }
  }

  const res = await getTaskStatus(taskId)
  const task = res.data || res
  if (task.status === 'completed') return task
  throw new Error('Task timed out after 20 minutes')
}

const pollCampaignPreparation = async (taskId) => {
  prepareTaskId.value = taskId
  preparingCampaign.value = true
  prepareProgress.value = 0
  prepareElapsed.value = 0
  prepareStatus.value = 'Preparing scenario inputs'
  startPrepareClock()
  saveState()

  for (let attempt = 0; attempt < 300; attempt += 1) {
    await sleep(2500)
    const res = await getCampaignPrepareStatus(campaignId.value, taskId)
    const task = res.task || {}
    const campaign = res.campaign || {}

    prepareProgress.value = task.progress || campaign.prepare_progress || 0
    prepareStatus.value = task.message || campaign.prepare_message || 'Preparing scenario inputs'
    saveState()

    if (task.status === 'completed') {
      return task
    }

    if (task.status === 'failed') {
      throw new Error(task.error || task.message || campaign.error || 'Scenario preparation failed')
    }
  }

  throw new Error('Scenario preparation timed out after 12.5 minutes')
}

const launchCampaignRunner = async () => {
  const startRes = await startCampaign(campaignId.value, {
    platform: 'parallel',
    max_rounds: seedData.value.max_rounds || 20,
  })

  if (!startRes.success) {
    throw new Error(startRes.error || 'Campaign start failed')
  }

  preparingCampaign.value = false
  prepareProgress.value = 100
  prepareStatus.value = 'Scenario preparation complete'
  stopPrepareClock()
  currentStep.value = 2
  saveState()
}

const resumeCampaignIfNeeded = async () => {
  if (!campaignId.value) return

  const res = await getCampaign(campaignId.value)
  const campaign = res.campaign || {}

  if (campaign.status === 'preparing') {
    currentStep.value = 2
    prepareTaskId.value = campaign.prepare_task_id || prepareTaskId.value
    await pollCampaignPreparation(prepareTaskId.value)
    await launchCampaignRunner()
    return
  }

  if (campaign.status === 'ready') {
    currentStep.value = 2
    await launchCampaignRunner()
    return
  }

  if (campaign.status === 'running' || campaign.status === 'completed') {
    preparingCampaign.value = false
    stopPrepareClock()
    currentStep.value = campaign.status === 'completed' ? 3 : 2
    saveState()
  }
}

const handleSeedSubmit = async (data) => {
  clearState()
  seedData.value = data
  buildError.value = ''
  buildingGraph.value = true
  graphBuildPct.value = 0
  graphBuildMsg.value = 'Generating ontology from the product brief'
  graphData.value = null
  showGraph.value = false
  currentStep.value = 1
  saveState()

  try {
    const previewRes = await previewSeed(data)
    const markdownText = previewRes.markdown
    const simulationRequirement = previewRes.simulation_requirement

    const briefBlob = new Blob([markdownText], { type: 'text/markdown' })
    const briefFile = new File([briefBlob], `${data.product_name || 'product'}_brief.md`, {
      type: 'text/markdown',
    })

    const formData = new FormData()
    formData.append('files', briefFile)
    formData.append('simulation_requirement', simulationRequirement)
    formData.append('project_name', data.product_name || 'Product Sentiment Campaign')

    graphBuildPct.value = 20
    graphBuildMsg.value = 'Analyzing the brief with the ontology generator'

    const ontologyRes = await generateOntology(formData)
    if (!ontologyRes.success) {
      throw new Error(ontologyRes.data?.error || ontologyRes.error || 'Ontology generation failed')
    }

    projectId.value = ontologyRes.data.project_id
    graphBuildPct.value = 50
    graphBuildMsg.value = 'Creating the knowledge graph in Zep'

    const buildRes = await buildGraph({ project_id: projectId.value })
    if (!buildRes.success) {
      throw new Error(buildRes.data?.error || buildRes.error || 'Graph build failed')
    }

    const buildTaskId = buildRes.data.task_id
    const buildTask = await pollTask(buildTaskId, (progress, message) => {
      graphBuildPct.value = Math.min(100, 50 + progress * 0.5)
      graphBuildMsg.value = message
    })

    graphId.value = buildTask?.result?.graph_id || ''
    graphBuildPct.value = 100
    graphBuildMsg.value = 'Knowledge graph ready'
    buildingGraph.value = false
    saveState()

    if (graphId.value) {
      const graphRes = await getGraphData(graphId.value)
      if (graphRes.success) {
        graphData.value = graphRes.data?.graph || graphRes.data
      }
    }
  } catch (error) {
    buildingGraph.value = false
    buildError.value = error?.response?.data?.error || error?.message || 'Graph build failed'
  }
}

const handleArchetypeConfirm = async () => {
  if (buildingGraph.value) {
    buildError.value = 'The knowledge graph is still being built. Please wait.'
    return
  }
  if (!graphId.value) {
    buildError.value = 'The graph is still being prepared. Wait for the task to finish.'
    return
  }

  buildError.value = ''
  currentStep.value = 2
  saveState()

  try {
    const createRes = await createCampaign({
      project_id: projectId.value,
      graph_id: graphId.value,
      seed_data: seedData.value,
      competitive_event_weights: seedData.value.competitive_event_weights,
      crisis_event_weights: seedData.value.crisis_event_weights,
      total_agents: seedData.value.total_agents || 50,
    })

    if (!createRes.success) {
      throw new Error(createRes.error || 'Campaign creation failed')
    }

    campaignId.value = createRes.campaign.campaign_id
    saveState()

    const prepareRes = await prepareCampaign(campaignId.value)
    const taskId = prepareRes.task_id || prepareRes.task?.task_id
    if (!taskId) {
      throw new Error('Preparation task did not return a task_id')
    }

    await pollCampaignPreparation(taskId)
    await launchCampaignRunner()
  } catch (error) {
    stopPrepareClock()
    preparingCampaign.value = false
    buildError.value = error?.response?.data?.error || error?.message || 'Campaign setup failed'
    currentStep.value = 1
    saveState()
  }
}

onMounted(async () => {
  if (props.campaignId) {
    campaignId.value = props.campaignId
    currentStep.value = 3
    saveState()
    return
  }

  try {
    const saved = sessionStorage.getItem(SESSION_KEY)
    if (saved) {
      const state = JSON.parse(saved)
      seedData.value = state.seedData || {}
      projectId.value = state.projectId || ''
      graphId.value = state.graphId || ''
      campaignId.value = state.campaignId || ''
      prepareTaskId.value = state.prepareTaskId || ''
      currentStep.value = state.currentStep || 0
      preparingCampaign.value = Boolean(state.preparingCampaign)

      if (currentStep.value === 1 && graphId.value) {
        try {
          const graphRes = await getGraphData(graphId.value)
          if (graphRes.success) {
            graphData.value = graphRes.data?.graph || graphRes.data
          }
        } catch {
          // Graph preview is optional on restore.
        }
      }

      if (campaignId.value && currentStep.value >= 2) {
        await resumeCampaignIfNeeded()
      }
    }
  } catch {
    // Ignore session restore failures.
  }
})
</script>

<style scoped>
.sentiment-view {
  min-height: 100vh;
  color: #1f1712;
  background:
    radial-gradient(circle at top left, rgba(224, 120, 55, 0.16), transparent 26%),
    radial-gradient(circle at bottom right, rgba(44, 91, 79, 0.16), transparent 26%),
    linear-gradient(180deg, #fcfaf6 0%, #f5eee5 100%);
}

.workspace-topbar,
.workspace-shell {
  max-width: 1180px;
  margin: 0 auto;
  padding-left: 24px;
  padding-right: 24px;
}

.workspace-topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 28px;
}

.workspace-brand {
  color: inherit;
  text-decoration: none;
  font-size: 1.05rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.workspace-meta {
  color: #6c6056;
  font-size: 0.9rem;
}

.workspace-shell {
  padding-top: 28px;
  padding-bottom: 56px;
}

.workspace-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(260px, 0.8fr);
  gap: 18px;
  margin-bottom: 18px;
}

.workspace-hero > div,
.surface-card,
.step-progress {
  border: 1px solid rgba(31, 23, 18, 0.12);
  border-radius: 28px;
  background: rgba(255, 253, 250, 0.78);
  backdrop-filter: blur(14px);
  box-shadow: 0 18px 48px rgba(52, 32, 20, 0.06);
}

.workspace-hero > div {
  padding: 24px;
}

.hero-kicker,
.status-label,
.prepare-label {
  display: inline-flex;
  margin-bottom: 14px;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(208, 90, 43, 0.12);
  color: #c85b2e;
  font-size: 0.74rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.workspace-hero h1,
.prepare-card h2 {
  font-size: clamp(2rem, 6vw, 3.8rem);
  line-height: 0.95;
  letter-spacing: -0.05em;
  margin-bottom: 14px;
}

.workspace-hero p,
.hero-status-card p,
.prepare-card p {
  color: #6c6056;
  line-height: 1.7;
}

.hero-status-card {
  display: grid;
  align-content: start;
}

.hero-status-card strong {
  font-size: 1.45rem;
  line-height: 1.2;
  margin-bottom: 10px;
}

.step-progress {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 18px;
  padding: 16px;
}

.step-item {
  display: grid;
  gap: 6px;
  padding: 14px;
  border-radius: 18px;
  border: 1px solid transparent;
  color: #9d8d80;
}

.step-item.active {
  border-color: rgba(31, 23, 18, 0.12);
  background: rgba(255, 255, 255, 0.72);
  color: #1f1712;
}

.step-item.done {
  color: #2a6257;
  background: rgba(42, 98, 87, 0.08);
}

.step-num {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.12em;
}

.step-name {
  font-size: 0.95rem;
  font-weight: 600;
}

.surface-card {
  padding: 24px;
  overflow: visible;
}

.status-panel,
.prepare-card {
  border: 1px solid rgba(31, 23, 18, 0.08);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.74);
}

.status-panel {
  margin-top: 20px;
  padding: 16px;
}

.status-panel.compact {
  margin-top: 24px;
}

.status-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  font-size: 0.92rem;
  font-weight: 600;
}

.status-bar {
  height: 8px;
  margin-top: 12px;
  border-radius: 999px;
  background: rgba(31, 23, 18, 0.08);
  overflow: hidden;
}

.status-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #1f1712 0%, #6c6056 100%);
  transition: width 0.35s ease;
}

.status-fill.accent {
  background: linear-gradient(90deg, #c85b2e 0%, #de8c4f 100%);
}

.status-message {
  margin-top: 10px;
  color: #6c6056;
  font-size: 0.92rem;
}

.error-banner {
  margin-top: 16px;
  padding: 14px 16px;
  border-radius: 18px;
  border: 1px solid rgba(173, 54, 33, 0.18);
  background: rgba(249, 225, 219, 0.72);
  color: #8b2d1c;
}

.graph-panel {
  margin-top: 24px;
}

.graph-toggle {
  min-height: 44px;
  padding: 0 16px;
  border-radius: 999px;
  border: 1px solid rgba(31, 23, 18, 0.12);
  background: rgba(255, 255, 255, 0.76);
  cursor: pointer;
}

.graph-frame {
  margin-top: 16px;
  height: 420px;
  border-radius: 22px;
  overflow: hidden;
  border: 1px solid rgba(31, 23, 18, 0.12);
}

.prepare-state {
  display: grid;
  place-items: center;
  min-height: 340px;
}

.prepare-card {
  width: min(680px, 100%);
  padding: 28px;
}

.prepare-card h2 {
  font-size: clamp(1.9rem, 5vw, 3rem);
}

@media (max-width: 900px) {
  .workspace-topbar {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .workspace-hero,
  .step-progress {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .workspace-topbar,
  .workspace-shell {
    padding-left: 16px;
    padding-right: 16px;
  }

  .surface-card {
    padding: 18px;
  }

  .prepare-card {
    padding: 22px;
  }
}
</style>

import service from './index'

// ── Seed Template ─────────────────────────────────────────────────────────────

export const validateSeed = (seedData) =>
  service.post('/api/sentiment/seed/validate', seedData)

export const previewSeed = (seedData) =>
  service.post('/api/sentiment/seed/preview', seedData)

export const getArchetypes = () =>
  service.get('/api/sentiment/archetypes')

// ── Campaign Lifecycle ────────────────────────────────────────────────────────

/**
 * Create a campaign (provisions 3 simulation IDs).
 * @param {Object} data - { project_id, graph_id, seed_data, competitive_event_type?, crisis_event_type?, total_agents? }
 */
export const createCampaign = (data) =>
  service.post('/api/sentiment/campaign/create', data)

/**
 * Start asynchronous preparation for all three scenarios.
 */
export const prepareCampaign = (campaignId) =>
  service.post(`/api/sentiment/campaign/${campaignId}/prepare`)

/**
 * Poll campaign preparation status.
 * @param {string} campaignId
 * @param {string} taskId
 */
export const getCampaignPrepareStatus = (campaignId, taskId) =>
  service.get(`/api/sentiment/campaign/${campaignId}/prepare/status`, {
    params: taskId ? { task_id: taskId } : undefined,
  })

/**
 * Start the campaign (launches background parallel simulation runners).
 * @param {string} campaignId
 * @param {Object} options - { platform?, max_rounds? }
 */
export const startCampaign = (campaignId, options = {}) =>
  service.post(`/api/sentiment/campaign/${campaignId}/start`, options)

/**
 * Get aggregated campaign status + all three scenario run states.
 */
export const getCampaign = (campaignId) =>
  service.get(`/api/sentiment/campaign/${campaignId}`)

/**
 * List all campaigns.
 */
export const listCampaigns = () =>
  service.get('/api/sentiment/campaign')

/**
 * Delete a campaign and its simulation data.
 */
export const deleteCampaign = (campaignId) =>
  service.delete(`/api/sentiment/campaign/${campaignId}`)

/**
 * Inject a God's Eye event into a running scenario.
 * @param {string} campaignId
 * @param {Object} data - { scenario: 'b'|'c', event_type?, custom_prompt? }
 */
export const injectEvent = (campaignId, data) =>
  service.post(`/api/sentiment/campaign/${campaignId}/inject`, data)

// ── Sentiment Analysis ────────────────────────────────────────────────────────

/**
 * Run full sentiment analysis on all three scenarios.
 * Returns { scenario_a, scenario_b, scenario_c } sentiment objects.
 */
export const getCampaignSentiment = (campaignId) =>
  service.get(`/api/sentiment/campaign/${campaignId}/sentiment`)

/**
 * Return per-round scores for A/B/C on unified round axis (for overlay chart).
 */
export const compareScenarios = (campaignId) =>
  service.get(`/api/sentiment/campaign/${campaignId}/compare`)

/**
 * Live sentiment for a single simulation (polls during running state).
 */
export const getLiveSentiment = (simulationId) =>
  service.get(`/api/sentiment/sim/${simulationId}/live`)

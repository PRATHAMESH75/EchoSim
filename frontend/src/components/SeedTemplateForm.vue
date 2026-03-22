<template>
  <div class="seed-form">
    <div class="form-header">
      <span class="section-label">&gt;_ 01 / Product Seed</span>
      <span class="section-meta">7-dimension brief</span>
    </div>

    <!-- Section 1: Product Identity -->
    <div class="form-section">
      <div class="section-title">01 / Product Identity</div>
      <div class="field-row">
        <div class="field">
          <label>Product Name <span class="required">*</span></label>
          <input v-model="form.product_name" type="text" placeholder="e.g. FinTrack" class="input" />
        </div>
        <div class="field">
          <label>Category <span class="required">*</span></label>
          <input v-model="form.product_category" type="text" placeholder="e.g. SaaS / Mobile App" class="input" />
        </div>
      </div>
      <div class="field">
        <label>Tagline <span class="required">*</span></label>
        <input v-model="form.tagline" type="text" placeholder="One-line value proposition" class="input" />
      </div>
      <div class="field">
        <label>Target Market <span class="required">*</span></label>
        <input v-model="form.target_market" type="text" placeholder="e.g. Freelancers in India aged 25-40" class="input" />
      </div>
    </div>

    <!-- Section 2: Core Features -->
    <div class="form-section">
      <div class="section-title">02 / Core Features</div>
      <div v-for="(feature, idx) in form.core_features" :key="idx" class="feature-row">
        <span class="feature-num">{{ idx + 1 }}</span>
        <input v-model="feature.name" type="text" placeholder="Feature name" class="input feature-name" />
        <input v-model="feature.description" type="text" placeholder="Brief description (optional)" class="input feature-desc" />
        <button class="btn-icon" @click="removeFeature(idx)" :disabled="form.core_features.length <= 1">×</button>
      </div>
      <button class="btn-add" @click="addFeature" :disabled="form.core_features.length >= 10">+ Add feature</button>
    </div>

    <!-- Section 3: Pricing Model -->
    <div class="form-section">
      <div class="section-title">03 / Pricing Model</div>
      <div v-for="(tier, idx) in form.pricing_tiers" :key="idx" class="pricing-row">
        <input v-model="tier.name" type="text" placeholder="Tier name (e.g. Free)" class="input tier-name" />
        <input v-model="tier.price" type="text" placeholder="Price (e.g. $0 / ₹499/mo)" class="input tier-price" />
        <input v-model="tier.description" type="text" placeholder="Tier description (optional)" class="input tier-desc" />
        <button class="btn-icon" @click="removePricingTier(idx)" :disabled="form.pricing_tiers.length <= 1">×</button>
      </div>
      <button class="btn-add" @click="addPricingTier">+ Add tier</button>
      <div class="field-row" style="margin-top: 12px;">
        <div class="field">
          <label>Trial Policy</label>
          <select v-model="form.trial_policy" class="input">
            <option value="">Select...</option>
            <option value="Free trial (14 days)">Free trial (14 days)</option>
            <option value="Free trial (30 days)">Free trial (30 days)</option>
            <option value="Freemium tier available">Freemium tier available</option>
            <option value="No free trial">No free trial</option>
            <option value="Money-back guarantee">Money-back guarantee</option>
          </select>
        </div>
        <div class="field">
          <label>Billing Cycle</label>
          <select v-model="form.billing_cycle" class="input">
            <option value="">Select...</option>
            <option value="Monthly only">Monthly only</option>
            <option value="Monthly and annual (discount)">Monthly and annual (discount)</option>
            <option value="Annual only">Annual only</option>
            <option value="One-time purchase">One-time purchase</option>
            <option value="Usage-based">Usage-based</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Section 4: Competitive Context -->
    <div class="form-section">
      <div class="section-title">04 / Competitive Context</div>
      <div v-for="(comp, idx) in form.competitors" :key="idx" class="comp-row">
        <span class="comp-num">{{ idx + 1 }}</span>
        <input v-model="comp.name" type="text" placeholder="Competitor name" class="input comp-name" />
        <input v-model="comp.strength" type="text" placeholder="Their strength" class="input comp-strength" />
        <input v-model="comp.gap" type="text" placeholder="Their gap / your advantage" class="input comp-gap" />
        <button class="btn-icon" @click="removeCompetitor(idx)" :disabled="form.competitors.length <= 1">×</button>
      </div>
      <button class="btn-add" @click="addCompetitor" :disabled="form.competitors.length >= 5">+ Add competitor</button>
    </div>

    <!-- Section 5: Target Persona -->
    <div class="form-section">
      <div class="section-title">05 / Target Persona</div>
      <div class="field-row">
        <div class="field">
          <label>Age Range</label>
          <input v-model="form.target_persona.age_range" type="text" placeholder="e.g. 25-40" class="input" />
        </div>
        <div class="field">
          <label>Income Level</label>
          <select v-model="form.target_persona.income_level" class="input">
            <option value="">Select...</option>
            <option value="Low income">Low income</option>
            <option value="Middle income">Middle income</option>
            <option value="High income">High income</option>
            <option value="Enterprise / B2B">Enterprise / B2B</option>
          </select>
        </div>
      </div>
      <div class="field">
        <label>Pain Points</label>
        <textarea v-model="form.target_persona.pain_points" placeholder="Describe the key pain points your product solves..." class="textarea" rows="2" />
      </div>
      <div class="field">
        <label>Buying Triggers</label>
        <input v-model="form.target_persona.buying_triggers" type="text" placeholder="e.g. Looking for automation, just started freelancing" class="input" />
      </div>
    </div>

    <!-- Section 6: Launch Channel -->
    <div class="form-section">
      <div class="section-title">06 / Launch Channel</div>
      <div class="channel-options">
        <label v-for="opt in launchChannelOptions" :key="opt.value" class="radio-option" :class="{ selected: form.launch_channel === opt.value }">
          <input type="radio" v-model="form.launch_channel" :value="opt.value" />
          {{ opt.label }}
        </label>
      </div>
      <div class="field" style="margin-top: 12px;">
        <label>Additional notes (optional)</label>
        <input v-model="form.launch_channel_notes" type="text" placeholder="e.g. Coordinating with 3 tech newsletters" class="input" />
      </div>
    </div>

    <!-- Section 7: Known Risks -->
    <div class="form-section">
      <div class="section-title">07 / Known Risks</div>
      <div v-for="(risk, idx) in form.known_risks" :key="idx" class="risk-row">
        <input v-model="form.known_risks[idx]" type="text" placeholder="e.g. Pricing may feel steep for solo users" class="input" />
        <button class="btn-icon" @click="removeRisk(idx)" :disabled="form.known_risks.length <= 1">×</button>
      </div>
      <button class="btn-add" @click="addRisk">+ Add risk</button>
    </div>

    <!-- Simulation Config -->
    <div class="form-section">
      <div class="section-title">Simulation Config</div>
      <div class="field-row">
        <div class="field">
          <label>Total Agents</label>
          <select v-model.number="form.total_agents" class="input">
            <option :value="50">50 agents — quick test (~$2)</option>
            <option :value="120">120 agents — decision-quality (sweet spot)</option>
            <option :value="200">200 agents — high-confidence (~$8)</option>
            <option :value="500">500 agents — deep (~$20)</option>
          </select>
        </div>
        <div class="field">
          <label>Simulation Rounds (per scenario)</label>
          <select v-model.number="form.max_rounds" class="input">
            <option :value="10">10 rounds</option>
            <option :value="20">20 rounds</option>
            <option :value="30">30 rounds</option>
            <option :value="50">50 rounds</option>
            <option :value="75">75 rounds</option>
          </select>
        </div>
      </div>
      <!-- Competitive event weights (Scenario B) -->
      <div class="form-section" style="margin-top:16px; border:none; padding-bottom:0;">
        <div class="section-title" style="margin-bottom:10px;">Competitive Events — Scenario B (round 7)</div>
        <div class="weight-hint">Assign weights to each event. Higher weight = injected to more influential agents first. Total auto-normalizes to 100%.</div>
        <div class="weight-row" v-for="(evt, key) in competitiveEventLabels" :key="key">
          <span class="weight-label">{{ evt }}</span>
          <input
            type="number" min="0" max="100" step="5"
            v-model.number="form.competitive_event_weights[key]"
            class="weight-input"
            @input="clampWeight('competitive_event_weights', key)"
          />
          <span class="weight-pct">{{ normalizedWeight('competitive_event_weights', key) }}%</span>
          <div class="weight-bar-wrap">
            <div class="weight-bar-fill" :style="{ width: normalizedWeight('competitive_event_weights', key) + '%' }"></div>
          </div>
        </div>
      </div>

      <!-- Crisis event weights (Scenario C) -->
      <div class="form-section" style="margin-top:16px; border:none; padding-bottom:0;">
        <div class="section-title" style="margin-bottom:10px;">Crisis Events — Scenario C (round 14)</div>
        <div class="weight-hint">Assign weights to each event. Higher weight = injected to more influential agents first. Total auto-normalizes to 100%.</div>
        <div class="weight-row" v-for="(evt, key) in crisisEventLabels" :key="key">
          <span class="weight-label">{{ evt }}</span>
          <input
            type="number" min="0" max="100" step="5"
            v-model.number="form.crisis_event_weights[key]"
            class="weight-input"
            @input="clampWeight('crisis_event_weights', key)"
          />
          <span class="weight-pct">{{ normalizedWeight('crisis_event_weights', key) }}%</span>
          <div class="weight-bar-wrap">
            <div class="weight-bar-fill" :style="{ width: normalizedWeight('crisis_event_weights', key) + '%' }"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Validation errors -->
    <div v-if="validationErrors.length" class="error-box">
      <div v-for="err in validationErrors" :key="err" class="error-item">⚠ {{ err }}</div>
    </div>

    <!-- Submit -->
    <div class="form-actions">
      <button class="btn-submit" @click="handleSubmit" :disabled="loading">
        {{ loading ? 'Validating...' : 'Continue →' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { validateSeed } from '../api/sentiment.js'

const emit = defineEmits(['submit'])

const loading = ref(false)
const validationErrors = ref([])

const launchChannelOptions = [
  { value: 'product_hunt', label: 'Product Hunt' },
  { value: 'app_store', label: 'App Store' },
  { value: 'direct_sales', label: 'Direct Sales' },
  { value: 'social_media', label: 'Social Media' },
  { value: 'press', label: 'Press / Media' },
  { value: 'word_of_mouth', label: 'Word of Mouth' },
]

const competitiveEventLabels = {
  price_drop: 'Competitor drops price 30%',
  feature_match: 'Competitor matches key feature',
  comparison_campaign: 'Aggressive comparison campaign',
}

const crisisEventLabels = {
  security_breach: 'Critical security breach',
  harsh_review: 'Prominent harsh review (2/5 stars)',
  misleading_comparison: 'Misleading benchmark claims go viral',
}

const clampWeight = (field, key) => {
  const val = form[field][key]
  form[field][key] = Math.max(0, Math.min(100, isNaN(val) ? 0 : val))
}

const normalizedWeight = (field, key) => {
  const weights = form[field]
  const total = Object.values(weights).reduce((s, v) => s + (Number(v) || 0), 0)
  if (total <= 0) return 0
  return Math.round((Number(weights[key] || 0) / total) * 100)
}

const form = reactive({
  product_name: '',
  product_category: '',
  tagline: '',
  target_market: '',
  core_features: [
    { name: '', description: '' },
  ],
  pricing_tiers: [
    { name: '', price: '', description: '' },
  ],
  trial_policy: '',
  billing_cycle: '',
  competitors: [
    { name: '', strength: '', gap: '' },
  ],
  target_persona: {
    age_range: '',
    income_level: '',
    pain_points: '',
    buying_triggers: '',
  },
  launch_channel: '',
  launch_channel_notes: '',
  known_risks: [''],
  total_agents: 50,
  max_rounds: 20,
  competitive_event_weights: { price_drop: 33, feature_match: 34, comparison_campaign: 33 },
  crisis_event_weights: { security_breach: 40, harsh_review: 30, misleading_comparison: 30 },
})

const addFeature = () => {
  if (form.core_features.length < 10) form.core_features.push({ name: '', description: '' })
}
const removeFeature = (idx) => {
  if (form.core_features.length > 1) form.core_features.splice(idx, 1)
}
const addPricingTier = () => form.pricing_tiers.push({ name: '', price: '', description: '' })
const removePricingTier = (idx) => {
  if (form.pricing_tiers.length > 1) form.pricing_tiers.splice(idx, 1)
}
const addCompetitor = () => {
  if (form.competitors.length < 5) form.competitors.push({ name: '', strength: '', gap: '' })
}
const removeCompetitor = (idx) => {
  if (form.competitors.length > 1) form.competitors.splice(idx, 1)
}
const addRisk = () => form.known_risks.push('')
const removeRisk = (idx) => {
  if (form.known_risks.length > 1) form.known_risks.splice(idx, 1)
}

const handleSubmit = async () => {
  validationErrors.value = []
  loading.value = true
  try {
    const res = await validateSeed(form)
    if (!res.valid) {
      validationErrors.value = res.errors || ['Validation failed']
      return
    }
    emit('submit', { ...form })
  } catch (err) {
    validationErrors.value = [err?.response?.data?.error || 'Validation request failed']
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.seed-form {
  font-family: 'JetBrains Mono', monospace;
  color: #111;
  max-width: 780px;
}
.form-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 12px;
  border-bottom: 1px solid #111;
}
.section-label { font-size: 13px; font-weight: 600; letter-spacing: 0.05em; }
.section-meta { font-size: 11px; color: #666; }
.form-section {
  margin-bottom: 28px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e0e0e0;
}
.section-title {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: #888;
  margin-bottom: 14px;
  text-transform: uppercase;
}
.field { display: flex; flex-direction: column; gap: 5px; flex: 1; }
.field label { font-size: 11px; color: #555; letter-spacing: 0.04em; }
.field-row { display: flex; gap: 14px; margin-bottom: 10px; }
.required { color: #ff6b00; }
.input, .textarea {
  background: #fff;
  border: 1px solid #bbb;
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  padding: 8px 10px;
  color: #111;
  outline: none;
  transition: border-color 0.15s;
  width: 100%;
  box-sizing: border-box;
}
.input:focus, .textarea:focus { border-color: #111; }
.textarea { resize: vertical; }
.feature-row, .pricing-row, .comp-row, .risk-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.feature-num, .comp-num { font-size: 11px; color: #888; min-width: 16px; }
.feature-name { flex: 1; }
.feature-desc { flex: 2; }
.tier-name { flex: 1; }
.tier-price { flex: 1; }
.tier-desc { flex: 2; }
.comp-name { flex: 1; }
.comp-strength { flex: 1.5; }
.comp-gap { flex: 1.5; }
.btn-icon {
  background: none;
  border: 1px solid #bbb;
  color: #666;
  cursor: pointer;
  width: 26px;
  height: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
}
.btn-icon:hover:not(:disabled) { border-color: #111; color: #111; }
.btn-icon:disabled { opacity: 0.3; cursor: default; }
.btn-add {
  background: none;
  border: 1px dashed #bbb;
  color: #666;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  padding: 6px 14px;
  cursor: pointer;
  margin-top: 4px;
}
.btn-add:hover:not(:disabled) { border-color: #111; color: #111; }
.btn-add:disabled { opacity: 0.3; cursor: default; }
.channel-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.radio-option {
  display: flex;
  align-items: center;
  gap: 6px;
  border: 1px solid #bbb;
  padding: 6px 12px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}
.radio-option input { display: none; }
.radio-option.selected { border-color: #111; background: #111; color: #fff; }
.radio-option:hover:not(.selected) { border-color: #888; }
.error-box {
  border: 1px solid #ff4444;
  background: #fff5f5;
  padding: 12px 16px;
  margin-bottom: 16px;
}
.error-item { font-size: 12px; color: #cc0000; margin-bottom: 4px; }
.form-actions { display: flex; justify-content: flex-end; }
.btn-submit {
  background: #111;
  color: #fff;
  border: none;
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  padding: 12px 32px;
  cursor: pointer;
  letter-spacing: 0.05em;
  transition: background 0.15s;
}
.btn-submit:hover:not(:disabled) { background: #333; }
.btn-submit:disabled { opacity: 0.5; cursor: default; }
.weight-hint {
  font-size: 10px;
  color: #888;
  margin-bottom: 10px;
  line-height: 1.5;
}
.weight-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.weight-label {
  font-size: 11px;
  color: #333;
  width: 240px;
  flex-shrink: 0;
}
.weight-input {
  width: 60px;
  padding: 4px 6px;
  border: 1px solid #ccc;
  font-size: 12px;
  font-family: 'JetBrains Mono', monospace;
  text-align: right;
}
.weight-pct {
  font-size: 11px;
  color: #555;
  width: 36px;
  text-align: right;
  flex-shrink: 0;
}
.weight-bar-wrap {
  flex: 1;
  height: 6px;
  background: #e8e8e8;
  border-radius: 0;
  overflow: hidden;
}
.weight-bar-fill {
  height: 100%;
  background: #111;
  transition: width 0.2s;
}
</style>

<template>
  <div class="archetype-review">
    <div class="review-header">
      <span class="section-label">02 / Consumer Population</span>
      <span class="section-meta">{{ archetypes.length }} archetypes · {{ totalAgents }} agents</span>
    </div>
    <p class="review-desc">
      These predefined consumer archetypes represent the market your product will encounter.
      Each archetype models a distinct behavioral segment with its own decision patterns and influence dynamics.
    </p>

    <div v-if="loading" class="loading">Loading archetypes...</div>

    <div v-else class="archetype-grid">
      <div v-for="arch in archetypes" :key="arch.key" class="archetype-card">
        <div class="card-header">
          <span class="arch-name">{{ arch.name }}</span>
          <span class="arch-pct">{{ (arch.population_pct * 100).toFixed(0) }}%</span>
        </div>
        <div class="pop-bar">
          <div class="pop-fill" :style="{ width: (arch.population_pct * 100) + '%' }" />
        </div>
        <div class="attr-grid">
          <div class="attr">
            <span class="attr-label">Risk</span>
            <span class="attr-val" :class="riskClass(arch.risk_tolerance)">{{ arch.risk_tolerance }}</span>
          </div>
          <div class="attr">
            <span class="attr-label">Price</span>
            <span class="attr-val" :class="priceClass(arch.price_sensitivity)">{{ arch.price_sensitivity }}</span>
          </div>
          <div class="attr">
            <span class="attr-label">Influence</span>
            <span class="attr-val" :class="influenceClass(arch.social_influence)">{{ arch.social_influence }}</span>
          </div>
          <div class="attr">
            <span class="attr-label">Loyalty</span>
            <span class="attr-val">{{ arch.brand_loyalty }}</span>
          </div>
        </div>
        <div class="trigger">
          <span class="trigger-label">Trigger:</span>
          {{ arch.decision_trigger }}
        </div>
      </div>
    </div>

    <div class="review-actions">
      <button class="btn-back" @click="$emit('back')">← Back</button>
      <button class="btn-next" @click="$emit('next')">Confirm population →</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getArchetypes } from '../api/sentiment.js'

const props = defineProps({
  totalAgents: { type: Number, default: 50 }
})

defineEmits(['back', 'next'])

const archetypes = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await getArchetypes()
    archetypes.value = res.archetypes || []
  } catch (e) {
    console.error('Failed to load archetypes:', e)
  } finally {
    loading.value = false
  }
})

const riskClass = (val) => ({
  'val-high': val === 'high',
  'val-medium': val === 'medium',
  'val-low': val === 'low' || val === 'very_low',
})
const priceClass = (val) => ({
  'val-high': val === 'very_high',
  'val-medium': val === 'high' || val === 'medium',
  'val-low': val === 'low',
})
const influenceClass = (val) => ({
  'val-high': val === 'very_high' || val === 'high',
  'val-medium': val === 'medium',
  'val-low': val === 'low',
})
</script>

<style scoped>
.archetype-review { font-family: 'JetBrains Mono', monospace; color: #111; }
.review-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 12px;
  border-bottom: 1px solid #111;
  margin-bottom: 16px;
}
.section-label { font-size: 13px; font-weight: 600; }
.section-meta { font-size: 11px; color: #666; }
.review-desc { font-size: 12px; color: #555; margin-bottom: 20px; line-height: 1.6; }
.loading { font-size: 12px; color: #888; padding: 20px 0; }
.archetype-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 28px;
  overflow: visible;
}
.archetype-card {
  border: 1px solid #e0e0e0;
  padding: 14px;
  background: #fff;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 8px;
}
.arch-name { font-size: 13px; font-weight: 600; }
.arch-pct { font-size: 18px; font-weight: 700; color: #111; }
.pop-bar {
  height: 3px;
  background: #e0e0e0;
  margin-bottom: 10px;
}
.pop-fill { height: 100%; background: #111; }
.attr-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px 8px;
  margin-bottom: 8px;
}
.attr { display: flex; justify-content: space-between; align-items: center; }
.attr-label { font-size: 10px; color: #888; text-transform: uppercase; letter-spacing: 0.04em; }
.attr-val { font-size: 10px; font-weight: 600; }
.val-high { color: #ff6b00; }
.val-medium { color: #888; }
.val-low { color: #bbb; }
.trigger { font-size: 10px; color: #666; line-height: 1.4; border-top: 1px solid #f0f0f0; padding-top: 8px; }
.trigger-label { font-weight: 600; color: #888; }
.review-actions {
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
.btn-next:hover { background: #333; }
</style>

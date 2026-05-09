<template>
  <div class="launch-home">
    <div class="ambient ambient-left" />
    <div class="ambient ambient-right" />

    <header class="topbar">
      <div class="brand-block">
        <span class="brand-kicker">Launch-ready workflow</span>
        <span class="brand-name">Sentiment Simulator</span>
      </div>
      <router-link to="/sentiment" class="topbar-link">Open Workspace</router-link>
    </header>

    <main class="page-shell">
      <section class="hero-card">
        <div class="hero-copy">
          <span class="eyebrow">Product sentiment forecasting</span>
          <h1>Pressure-test a launch before the market does.</h1>
          <p class="hero-text">
            Turn a product brief into a structured knowledge graph, generate a population of consumer archetypes,
            run three parallel launch scenarios, and compare how sentiment moves round by round.
          </p>
          <div class="hero-actions">
            <router-link to="/sentiment" class="btn-primary">Start a Campaign</router-link>
            <a href="#workflow" class="btn-secondary">See the Workflow</a>
          </div>
          <div class="hero-metrics">
            <div class="metric">
              <span class="metric-value">3</span>
              <span class="metric-label">parallel scenarios</span>
            </div>
            <div class="metric">
              <span class="metric-value">19</span>
              <span class="metric-label">consumer archetypes</span>
            </div>
            <div class="metric">
              <span class="metric-value">4</span>
              <span class="metric-label">operator steps</span>
            </div>
          </div>
        </div>

        <div class="hero-panel">
          <div class="hero-panel-header">
            <span>Launch surface</span>
            <span>v1</span>
          </div>
          <div class="signal-grid">
            <div v-for="signal in signals" :key="signal.label" class="signal-card">
              <span class="signal-label">{{ signal.label }}</span>
              <strong>{{ signal.value }}</strong>
              <p>{{ signal.note }}</p>
            </div>
          </div>
        </div>
      </section>

      <section id="workflow" class="workflow-grid">
        <article v-for="step in workflow" :key="step.number" class="workflow-card">
          <span class="workflow-number">{{ step.number }}</span>
          <h2>{{ step.title }}</h2>
          <p>{{ step.description }}</p>
        </article>
      </section>

      <section class="focus-strip">
        <div>
          <span class="strip-label">Launch stance</span>
          <h3>One product path, not two unfinished ones.</h3>
        </div>
        <p>
          The public app now routes directly into the sentiment workflow. Legacy graph, simulation, and report screens
          stay backend-capable but are no longer part of the shipped frontend surface.
        </p>
      </section>
    </main>
  </div>
</template>

<script setup>
const workflow = [
  {
    number: '01',
    title: 'Brief the product',
    description: 'Capture the launch context, pricing, target segment, channels, competitors, and risk assumptions in one structured form.',
  },
  {
    number: '02',
    title: 'Review the population',
    description: 'Inspect the generated archetype mix before preparation begins so the market model is explicit instead of implied.',
  },
  {
    number: '03',
    title: 'Run scenarios in parallel',
    description: 'Execute baseline, competitive, and crisis scenarios together so timing and sentiment shifts stay comparable.',
  },
  {
    number: '04',
    title: 'Read the dashboard',
    description: 'Compare sentiment, objections, archetype heatmaps, faction movement, and round-by-round divergence with cached refreshes.',
  },
]

const signals = [
  {
    label: 'Preparation',
    value: 'Async',
    note: 'Long-running setup is handled as a tracked background task instead of a blocking request.',
  },
  {
    label: 'Analysis',
    value: 'Cached',
    note: 'Sentiment results are reused until simulation action logs change, which keeps dashboard refreshes fast.',
  },
  {
    label: 'Deployment',
    value: 'Single origin',
    note: 'The production image builds the frontend once and serves the launch surface from the backend process.',
  },
]
</script>

<style scoped>
.launch-home {
  --bg: #f7f1e7;
  --panel: rgba(255, 251, 246, 0.82);
  --ink: #1e1813;
  --muted: #65584e;
  --line: rgba(30, 24, 19, 0.12);
  --accent: #d05a2b;
  --accent-soft: rgba(208, 90, 43, 0.12);
  min-height: 100vh;
  position: relative;
  overflow: hidden;
  color: var(--ink);
  background:
    radial-gradient(circle at 12% 18%, rgba(208, 90, 43, 0.18), transparent 26%),
    radial-gradient(circle at 85% 12%, rgba(39, 102, 88, 0.16), transparent 24%),
    linear-gradient(180deg, #fbf8f2 0%, var(--bg) 100%);
}

.ambient {
  position: absolute;
  border-radius: 999px;
  filter: blur(60px);
  opacity: 0.5;
  pointer-events: none;
}

.ambient-left {
  inset: 120px auto auto -80px;
  width: 240px;
  height: 240px;
  background: rgba(208, 90, 43, 0.2);
}

.ambient-right {
  inset: auto -100px 120px auto;
  width: 280px;
  height: 280px;
  background: rgba(39, 102, 88, 0.18);
}

.topbar,
.page-shell {
  position: relative;
  z-index: 1;
}

.topbar {
  max-width: 1220px;
  margin: 0 auto;
  padding: 28px 24px 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.brand-block {
  display: grid;
  gap: 4px;
}

.brand-kicker {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.18em;
  color: var(--muted);
}

.brand-name {
  font-size: 1.15rem;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.topbar-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border: 1px solid var(--line);
  border-radius: 999px;
  text-decoration: none;
  color: var(--ink);
  background: rgba(255, 255, 255, 0.45);
  transition: transform 0.2s ease, background 0.2s ease;
}

.topbar-link:hover {
  transform: translateY(-1px);
  background: rgba(255, 255, 255, 0.7);
}

.page-shell {
  max-width: 1220px;
  margin: 0 auto;
  padding: 28px 24px 72px;
  display: grid;
  gap: 28px;
}

.hero-card {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.8fr);
  gap: 24px;
  padding: 32px;
  border: 1px solid var(--line);
  border-radius: 28px;
  background: var(--panel);
  box-shadow: 0 24px 80px rgba(37, 27, 20, 0.08);
  backdrop-filter: blur(16px);
}

.eyebrow,
.strip-label {
  display: inline-flex;
  margin-bottom: 16px;
  padding: 8px 12px;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent);
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.hero-copy h1 {
  max-width: 12ch;
  font-size: clamp(2.8rem, 7vw, 5.3rem);
  line-height: 0.95;
  letter-spacing: -0.05em;
  margin-bottom: 18px;
}

.hero-text {
  max-width: 60ch;
  color: var(--muted);
  font-size: 1.02rem;
  line-height: 1.7;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 28px;
}

.btn-primary,
.btn-secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 48px;
  padding: 0 20px;
  border-radius: 999px;
  text-decoration: none;
  font-weight: 600;
  transition: transform 0.2s ease, background 0.2s ease, color 0.2s ease;
}

.btn-primary {
  background: var(--ink);
  color: #f8f4ed;
}

.btn-secondary {
  border: 1px solid var(--line);
  color: var(--ink);
  background: rgba(255, 255, 255, 0.55);
}

.btn-primary:hover,
.btn-secondary:hover {
  transform: translateY(-1px);
}

.hero-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-top: 28px;
}

.metric {
  padding: 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.68);
  border: 1px solid var(--line);
}

.metric-value {
  display: block;
  font-size: 1.5rem;
  font-weight: 700;
}

.metric-label {
  display: block;
  margin-top: 6px;
  color: var(--muted);
  font-size: 0.92rem;
}

.hero-panel {
  display: grid;
  gap: 16px;
  padding: 20px;
  border-radius: 22px;
  background: rgba(26, 22, 19, 0.94);
  color: #fbf6ee;
}

.hero-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: rgba(251, 246, 238, 0.72);
  font-size: 0.86rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
}

.signal-grid {
  display: grid;
  gap: 14px;
}

.signal-card {
  padding: 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.signal-label {
  display: block;
  color: rgba(251, 246, 238, 0.62);
  font-size: 0.74rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.signal-card strong {
  display: block;
  margin-top: 8px;
  font-size: 1.15rem;
}

.signal-card p {
  margin-top: 8px;
  color: rgba(251, 246, 238, 0.72);
  line-height: 1.6;
}

.workflow-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.workflow-card,
.focus-strip {
  border: 1px solid var(--line);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.62);
  backdrop-filter: blur(10px);
}

.workflow-card {
  padding: 22px;
}

.workflow-number {
  display: inline-flex;
  margin-bottom: 18px;
  color: var(--accent);
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.14em;
}

.workflow-card h2 {
  font-size: 1.18rem;
  margin-bottom: 10px;
}

.workflow-card p,
.focus-strip p {
  color: var(--muted);
  line-height: 1.65;
}

.focus-strip {
  display: grid;
  grid-template-columns: minmax(0, 0.85fr) minmax(0, 1.15fr);
  gap: 24px;
  padding: 26px;
  align-items: center;
}

.focus-strip h3 {
  font-size: clamp(1.6rem, 4vw, 2.5rem);
  line-height: 1.05;
}

@media (max-width: 1024px) {
  .hero-card,
  .focus-strip,
  .workflow-grid {
    grid-template-columns: 1fr 1fr;
  }

  .hero-card {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .topbar {
    padding-top: 20px;
    flex-direction: column;
    align-items: flex-start;
    gap: 14px;
  }

  .page-shell {
    padding-bottom: 48px;
  }

  .hero-card {
    padding: 24px;
  }

  .hero-metrics,
  .workflow-grid,
  .focus-strip {
    grid-template-columns: 1fr;
  }

  .hero-copy h1 {
    max-width: none;
    font-size: clamp(2.4rem, 15vw, 4rem);
  }
}
</style>

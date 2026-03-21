# Product Executive Summary

Sentiment Simulator is the launch product in the MiroFish repository. Its core idea is to help product teams pressure-test a launch before the real market reacts. Instead of waiting for launch-day feedback, the product turns a structured product brief into a simulated market, runs multiple scenarios in parallel, and returns a dashboard that shows how sentiment, objections, and audience factions evolve over time.

## Executive view

At a leadership level, the product answers one question: "How might the market react if we launch this product under normal, competitive, and adverse conditions?"

The current release is optimized around a single end-to-end workflow:

1. Define the product seed.
2. Review the generated audience population.
3. Run three launch scenarios in parallel.
4. Compare outcomes in a sentiment dashboard.

This makes the product easier to explain, easier to operate, and more aligned with a launch decision workflow than a broad but fragmented simulation platform.

## Core business problem

Most launch planning still depends on static assumptions, fragmented customer research, and delayed real-world feedback. Teams often know the product story they want to tell, but they do not have a reliable way to stress-test that story against pricing pressure, competitor moves, or trust-damaging events before launch.

Sentiment Simulator addresses that gap by giving teams a structured pre-launch decision environment. It is designed to surface likely objections, identify fragile audience segments, and expose where sentiment can swing quickly under pressure.

## Product thesis

The product thesis is that launch risk can be modeled earlier and more concretely when three things are combined:

- a structured product brief instead of unstructured brainstorming
- a synthetic but segmented market population instead of a generic audience
- scenario comparison instead of a single linear simulation

In the current implementation, all three scenarios share the same brief-derived graph and the same archetype population. That design choice is important because it keeps scenario comparison fair. The baseline, competitive, and crisis runs diverge because of event timing and event type, not because the underlying audience changed.

## What makes the product unique

Sentiment Simulator is not just a sentiment dashboard and not just a simulator. Its uniqueness comes from how the workflow is connected end to end.

### 1. Structured launch input

The system starts from a structured seed that captures product name, category, tagline, target market, core features, pricing, competitors, persona assumptions, launch channel, and known risks. This is more disciplined than a free-form prompt and gives the platform a repeatable input model for launch planning.

### 2. Archetype-driven audience modeling

The audience is expanded into predefined consumer archetypes rather than treated as a single average buyer. The current system includes segments such as early adopters, budget buyers, skeptics, enterprise buyers, power users, privacy-cautious users, and viral amplifiers. This allows the product to model disagreement, influence spread, and asymmetric reactions across different parts of the market.

### 3. Parallel scenario comparison

The product does not run a single simulation and call it forecasting. It runs three scenarios in parallel:

1. Baseline launch
2. Competitive pressure
3. Crisis response

That makes the output more useful for decision-making because teams can compare how sentiment changes under different conditions while holding the product and audience constant.

### 4. Actionable sentiment analytics

The analysis layer goes beyond positive versus negative sentiment. The dashboard is designed to report sentiment mix, weighted average score, an NPS-like score, round-by-round movement, faction breakdowns, top objections, persona heatmaps, topic breakdowns, and anomaly detection. This creates a more operational view of launch risk than a simple scorecard.

### 5. Launch-focused scope

The repository contains broader backend capabilities, but the public product surface is intentionally narrowed to the sentiment workflow. That focus is a strategic advantage in the current release because it keeps the product aligned with one high-value job: helping teams evaluate a launch before shipping.

## Why this matters to executives

For executives, the product is valuable because it shifts launch planning from opinion-led discussion toward evidence-shaped scenario review. It can help answer:

- Which audience segments become advocates or detractors first?
- Which objections appear consistently across scenarios?
- How fragile is pricing or positioning under competitive pressure?
- Does a crisis event create a temporary dip or a structural trust collapse?
- Which launch assumptions deserve mitigation before release?

In practical terms, the system is most useful as a pre-launch strategy and communication tool. It gives product, marketing, and leadership teams a shared artifact for discussing risk, messaging, and readiness.

## Current release boundaries

The current release should be understood as a launch decision-support product, not a full market intelligence platform.

- It focuses on simulated sentiment before or during controlled launch evaluation.
- It uses predefined archetypes and scenario injection rather than live market ingestion.
- It emphasizes one coherent public workflow instead of exposing every backend capability.
- It keeps long-running preparation asynchronous and sentiment analysis cached so the operator experience stays manageable.

These boundaries are strengths for the current stage because they keep the product clear, opinionated, and operationally simpler.

## Bottom line

Sentiment Simulator is best understood as a launch forecasting and stress-testing product. Its core value is not just generating synthetic discussion. Its value is helping teams compare likely market reactions across multiple scenarios, understand which segments drive those reactions, and make better launch decisions before the real market imposes the cost of being wrong.

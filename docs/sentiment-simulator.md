# Sentiment Simulator

Sentiment Simulator is the launch product in this repository.

## Scenario model

- Scenario A: baseline launch
- Scenario B: competitive pressure injection
- Scenario C: crisis injection

All three scenarios share the same brief-derived graph and archetype population. They diverge only through event timing and follow-up reactions.

## Preparation model

Preparation is a background job that generates archetype-driven simulation inputs for all three scenarios. The frontend receives a `task_id` immediately and polls until preparation completes.

## Analysis model

Sentiment analysis reads simulation action logs and returns:

- overall sentiment mix
- weighted average score
- NPS-like score
- round timeline
- faction breakdown
- top objections
- persona heatmap
- topic breakdown
- anomaly detection

## What changed for launch

- preparation moved from a blocking request to an async task
- sentiment results are cached and invalidated when action logs change
- the UI copy and docs now describe scenario execution as parallel
- the public frontend no longer exposes the legacy report path

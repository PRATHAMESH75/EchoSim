# Product Overview

## Product definition

Sentiment Simulator is a launch-focused product workflow that converts a structured product brief into a runnable market model. The system is built for product teams that want to evaluate messaging, pricing, competitive posture, and launch risk before shipping.

At a high level, the product does four things:

1. Captures a structured description of the product and market context.
2. Translates that input into a shared model for simulation.
3. Runs three comparable market scenarios in parallel.
4. Analyzes the resulting discussions through a sentiment dashboard.

## Core idea of the product

The core idea is simple: a launch should be tested as a market system, not just as a feature checklist.

Most internal launch reviews over-index on what the team built and under-index on how different market segments will interpret price, value, trust, novelty, switching cost, and competitive response. Sentiment Simulator closes that gap by treating launch planning as a simulation problem. It models how different audience types react, influence each other, and change sentiment over multiple rounds of discussion.

This makes the product especially useful when a team needs to answer questions such as:

- Is the value proposition strong enough for skeptical buyers?
- Does the pricing survive a competitor price cut?
- Which segments are most likely to amplify praise or criticism?
- Will a trust event cause a short-term controversy or long-term churn?

## How the workflow works

### 1. Product seed

The workflow begins with a structured product seed. The current seed model includes product basics, core features, pricing tiers, competitors, target persona information, launch channel, and known risks. The backend turns this input into:

- a markdown document used by the graph pipeline
- a simulation requirement used for scenario generation

This is important because it makes the product more repeatable than free-form prompting. Teams can compare launches using the same input structure instead of inventing a new brief format each time.

### 2. Knowledge graph generation

The product brief is then passed through the graph pipeline so the launch can be represented as a structured set of entities and relationships. In product terms, this graph acts as the shared context layer for the campaign. It gives all scenarios the same factual base and helps keep the simulation grounded in the same launch story.

### 3. Archetype population review

After the graph is built, the system expands the market into an archetype-driven population. The current implementation uses predefined archetypes with different levels of risk tolerance, price sensitivity, social influence, sentiment momentum, and churn behavior.

Examples include:

- Early Adopter
- Budget Buyer
- Skeptic
- Enterprise Buyer
- Power User
- Privacy Cautious
- Viral Amplifier
- Domain Expert
- Support Seeker

This is one of the product's strongest ideas. It avoids the unrealistic assumption that "the market" reacts as one uniform group. Instead, the system models a mixed audience with different triggers, writing styles, influence weights, and tolerance for friction.

### 4. Asynchronous preparation

Campaign preparation is handled as a background task. The frontend receives a task ID immediately and polls for progress until preparation is complete.

That design matters operationally. Preparation is long-running because it has to provision multiple scenarios and generate the audience population. Making this step asynchronous keeps the operator workflow responsive and makes the system more production-friendly.

### 5. Parallel scenario execution

The current release runs three scenarios in parallel:

1. Scenario A: baseline launch
2. Scenario B: competitive pressure
3. Scenario C: crisis stress test

The competitive and crisis scenarios are not separate products or entirely separate populations. They reuse the same brief-derived context and audience, then diverge when event prompts are injected. In the current implementation, the competitive event is injected at round 7 and the crisis event at round 14.

This is a meaningful differentiator. Because the scenarios share the same starting conditions, teams can compare outcomes more confidently and isolate the effect of the disruptive event.

### 6. Sentiment dashboard

Once the campaign is running, the product analyzes generated actions and surfaces a richer set of signals than a simple sentiment score. The current analytics layer includes:

- overall sentiment mix
- weighted average sentiment
- an NPS-like score
- round-by-round sentiment timeline
- faction breakdowns such as advocates, detractors, neutral users, and churned users
- top objections from negative discussion
- persona heatmaps by archetype
- topic breakdowns
- anomaly detection for sudden sentiment shifts

The dashboard is also designed for practical reuse. Sentiment analysis is cached and automatically invalidated when simulation action logs change, which reduces unnecessary recalculation and keeps repeated reads fast.

## Product uniqueness in detail

### A. It combines forecasting and comparison

Many internal tools can summarize reactions after the fact. Fewer tools are designed to compare likely reactions before launch across multiple controlled scenarios. Sentiment Simulator is more useful than a single-run simulator because the comparison model is built into the product definition.

### B. It models audience heterogeneity explicitly

The archetype system is not cosmetic. Each archetype carries its own bias, influence weight, activity level, memory decay, and churn threshold. That means the product does not just generate different voices stylistically; it attempts to produce different strategic behaviors across segments.

### C. It connects operator flow to analysis output

The launch input, simulation setup, scenario execution, and dashboard all sit on one public product path. That coherence matters. It reduces the distance between "what we told the system about the launch" and "what the system tells us about likely reactions."

### D. It is opinionated about scope

The current frontend is intentionally narrowed to the sentiment simulator path. Legacy graph, simulation, report, and interaction capabilities remain backend-capable, but they are not treated as the main public product surface. That product discipline makes the release easier to understand and closer to a real operator workflow.

## Who the product is for

Based on the current implementation, the primary users are:

- product teams planning a launch
- growth or marketing teams refining positioning and pricing narratives
- founders or leaders evaluating launch risk
- operators who need a structured way to compare baseline versus stressed market reactions

The product is most defensible when used before launch, before a pricing change, before a major campaign, or before a risky product announcement.

## Where the product creates value

The product creates value in three layers.

First, it improves clarity. Teams must express the launch in a structured way instead of relying on vague positioning language.

Second, it improves comparison. Teams can see how the same product story performs under normal and adverse conditions.

Third, it improves prioritization. The dashboard highlights which objections, archetypes, and sentiment changes deserve attention before launch.

## Current strengths

- Clear launch-specific workflow rather than a broad experimental surface
- Parallel scenario design that improves comparability
- Archetype-driven segmentation that adds strategic depth
- Background preparation and cached analysis that improve usability
- Dashboard outputs that are richer than a single sentiment score

## Current boundaries and assumptions

The current product also has clear boundaries, and they are worth stating directly.

- It is a simulated market model, not live production telemetry.
- It uses predefined archetypes rather than continuously learned customer segments.
- It is strongest for launch planning and scenario review, not for post-launch BI or CRM reporting.
- Its public UX is intentionally narrowed to the sentiment workflow, even though the backend contains broader capabilities.

These are not defects by default. They are part of the product's present positioning. The system is designed to be focused, interpretable, and operationally coherent rather than broad and loosely connected.

## Summary

Sentiment Simulator's core idea is to make launch strategy testable before the market reacts. Its uniqueness comes from linking structured product input, archetype-based audience modeling, parallel scenario execution, and actionable sentiment analysis into one workflow. In its current form, it is best positioned as a pre-launch decision product for teams that want sharper insight into market reaction, messaging resilience, and launch risk.

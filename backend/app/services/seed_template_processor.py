"""
Seed Template Processor for Product Sentiment Simulator

Converts a structured 7-dimension product brief into:
1. A markdown document for the existing ontology/graph pipeline
2. A simulation_requirement string for SimulationConfigGenerator
3. Validation of required fields
"""

from typing import Dict, Any, List


REQUIRED_FIELDS = ["product_name", "product_category", "tagline", "target_market"]

LAUNCH_CHANNEL_LABELS = {
    "product_hunt": "Product Hunt",
    "app_store": "App Store / Play Store",
    "direct_sales": "Direct Sales / Outbound",
    "social_media": "Social Media (Twitter/LinkedIn)",
    "press": "Press / Media Coverage",
    "word_of_mouth": "Word of Mouth / Referral",
    "other": "Other",
}


def validate_seed(seed_data: Dict[str, Any]) -> List[str]:
    """
    Validate the seed template form data.
    Returns a list of error strings (empty list means valid).
    """
    errors: List[str] = []
    for field in REQUIRED_FIELDS:
        if not seed_data.get(field, "").strip():
            errors.append(f"'{field}' is required")

    features = seed_data.get("core_features", [])
    if len(features) < 1:
        errors.append("At least one core feature is required")

    pricing_tiers = seed_data.get("pricing_tiers", [])
    if len(pricing_tiers) < 1:
        errors.append("At least one pricing tier is required")

    return errors


def _feature_name(f) -> str:
    if isinstance(f, dict):
        return f.get("name", "")
    return str(f)


def _feature_desc(f) -> str:
    if isinstance(f, dict):
        return f.get("description", "")
    return ""


def generate_markdown(seed_data: Dict[str, Any]) -> str:
    """
    Render seed_data into a rich narrative document suited for LLM agent simulation.
    Prose-first format — bullet lists are minimal. Agents parse natural language better
    than structured data, and richer context sustains multi-round, multi-agent debates.
    """
    product_name = seed_data.get("product_name", "Unknown Product")
    product_category = seed_data.get("product_category", "Software")
    tagline = seed_data.get("tagline", "")
    target_market = seed_data.get("target_market", "")

    core_features = seed_data.get("core_features", [])
    pricing_tiers = seed_data.get("pricing_tiers", [])
    competitors = seed_data.get("competitors", [])
    target_persona = seed_data.get("target_persona", {})
    launch_channel = seed_data.get("launch_channel", "other")
    known_risks = seed_data.get("known_risks", [])
    trial_policy = seed_data.get("trial_policy", "")
    billing_cycle = seed_data.get("billing_cycle", "")
    channel_notes = seed_data.get("launch_channel_notes", "")
    channel_label = LAUNCH_CHANNEL_LABELS.get(launch_channel, launch_channel)

    lines = []

    # ── Header ──────────────────────────────────────────────────────────────
    lines.append(f"# {product_name}")
    lines.append(f"**{product_category}**")
    if tagline:
        lines.append(f"\n> {tagline}")
    lines.append("")

    # ── What this product is ────────────────────────────────────────────────
    lines.append("## What Is This Product")
    intro = (
        f"{product_name} is a {product_category}."
    )
    if target_market:
        intro += (
            f" It is built for {target_market}."
        )
    if tagline:
        intro += f' The product is positioned around a single promise: "{tagline}".'
    lines.append(intro)
    lines.append("")

    # ── Core Features — narrative ───────────────────────────────────────────
    lines.append("## Core Capabilities")
    if core_features:
        feature_prose_parts = []
        for f in core_features:
            name = _feature_name(f)
            desc = _feature_desc(f)
            if name and desc:
                feature_prose_parts.append(f"**{name}** — {desc}")
            elif name:
                feature_prose_parts.append(f"**{name}**")
        if feature_prose_parts:
            lines.append(
                f"{product_name} ships with {len(core_features)} core capabilities:\n"
            )
            for part in feature_prose_parts:
                lines.append(f"- {part}")
    else:
        lines.append("No features specified.")
    lines.append("")

    # ── Pricing — detailed ─────────────────────────────────────────────────
    lines.append("## Pricing and Access")
    if pricing_tiers:
        tier_summaries = []
        for tier in pricing_tiers:
            if isinstance(tier, dict):
                t_name = tier.get("name", "Tier")
                t_price = tier.get("price", "")
                t_desc = tier.get("description", "")
                summary = f"**{t_name}** at {t_price}" if t_price else f"**{t_name}**"
                if t_desc:
                    summary += f" — {t_desc}"
                tier_summaries.append(summary)
            else:
                tier_summaries.append(str(tier))
        pricing_prose = (
            f"{product_name} uses a tiered pricing model with {len(pricing_tiers)} tier(s): "
            + "; ".join(tier_summaries) + "."
        )
        lines.append(pricing_prose)

    pricing_notes = []
    if trial_policy:
        pricing_notes.append(f"Trial policy: {trial_policy}.")
    if billing_cycle:
        pricing_notes.append(f"Billing: {billing_cycle}.")
    if pricing_notes:
        lines.append(" ".join(pricing_notes))
    lines.append("")

    # ── Competitive Landscape — narrative ──────────────────────────────────
    lines.append("## Competitive Landscape")
    if competitors:
        lines.append(
            f"{product_name} enters a market with {len(competitors)} established player(s). "
            "Here is how each compares:\n"
        )
        for comp in competitors:
            if isinstance(comp, dict):
                c_name = comp.get("name", "")
                c_strength = comp.get("strength", "")
                c_gap = comp.get("gap", "")
                entry = f"**{c_name}**"
                if c_strength:
                    entry += f" — Known for: {c_strength}."
                if c_gap:
                    entry += f" Gap: {c_gap}."
                lines.append(f"- {entry}")
            else:
                lines.append(f"- {comp}")
    else:
        lines.append("No competitive context provided.")
    lines.append("")

    # ── Target Persona — rich prose ─────────────────────────────────────────
    lines.append("## Who This Is For")
    persona_parts = []
    if isinstance(target_persona, dict):
        age_range = target_persona.get("age_range", "")
        income = target_persona.get("income_level", "")
        psychographics = target_persona.get("psychographics", [])
        pain_points = target_persona.get("pain_points", "")
        buying_triggers = target_persona.get("buying_triggers", "")

        if target_market:
            persona_parts.append(target_market)
        if age_range:
            persona_parts.append(f"Core age range: {age_range}.")
        if income:
            persona_parts.append(f"Income level: {income}.")
        if psychographics:
            tags = psychographics if isinstance(psychographics, str) else ", ".join(psychographics)
            persona_parts.append(f"Psychographic profile: {tags}.")
        if pain_points:
            persona_parts.append(
                f"The pain this product addresses: {pain_points}"
            )
        if buying_triggers:
            persona_parts.append(
                f"These users are typically moved to act when: {buying_triggers}"
            )
    elif isinstance(target_persona, str) and target_persona:
        persona_parts.append(target_persona)

    if persona_parts:
        lines.append(" ".join(persona_parts))
    else:
        lines.append("No persona information provided.")
    lines.append("")

    # ── Launch Strategy ─────────────────────────────────────────────────────
    lines.append("## Launch Strategy")
    launch_prose = f"The product is launching primarily via **{channel_label}**."
    if channel_notes:
        launch_prose += f" {channel_notes}"
    lines.append(launch_prose)
    lines.append("")

    # ── Known Risks — deliberate negative signals ───────────────────────────
    lines.append("## Known Risks and Vulnerabilities")
    if known_risks:
        lines.append(
            f"The team has identified {len(known_risks)} risk(s) that may shape "
            "market reception. These are real concerns that agents should debate, "
            "amplify, or dismiss based on their persona:\n"
        )
        for risk in known_risks:
            risk_str = risk if isinstance(risk, str) else risk.get("description", "")
            if risk_str.strip():
                lines.append(f"- {risk_str}")
    else:
        lines.append("No specific risks identified.")
    lines.append("")

    # ── Simulation Framing ──────────────────────────────────────────────────
    lines.append("## Simulation Context")
    all_feature_names = [_feature_name(f) for f in core_features if _feature_name(f)]
    comp_names = []
    for c in competitors:
        n = c.get("name", "") if isinstance(c, dict) else str(c)
        if n:
            comp_names.append(n)

    framing = (
        f"{product_name} is launching into the {product_category} space. "
        f"It is competing directly with {', '.join(comp_names) if comp_names else 'existing solutions'}. "
    )
    if all_feature_names:
        framing += (
            f"Its differentiated capabilities — {', '.join(all_feature_names)} — "
            "are the primary drivers of interest, objection, and debate among prospective users. "
        )
    if known_risks:
        risk_list = [r if isinstance(r, str) else r.get("description", "") for r in known_risks]
        risk_list = [r for r in risk_list if r.strip()]
        framing += (
            f"The most contentious open questions are: {'; '.join(risk_list[:5])}. "
        )
    framing += (
        "Agents should form opinions grounded in their persona type, discuss the product "
        "openly on simulated social feeds, influence each other, and evolve their stance "
        "across rounds based on what they read and hear."
    )
    lines.append(framing)
    lines.append("")

    return "\n".join(lines)


def generate_simulation_requirement(seed_data: Dict[str, Any]) -> str:
    """
    Generate a rich natural language simulation_requirement string from seed data.
    Uses ALL features, ALL competitors, and ALL risks — not truncated subsets.
    Designed for high-round, high-agent-count simulations where agents need
    enough textual surface area to sustain diverse, non-repetitive debate.
    """
    product_name = seed_data.get("product_name", "the product")
    product_category = seed_data.get("product_category", "software")
    target_market = seed_data.get("target_market", "general consumers")
    tagline = seed_data.get("tagline", "")
    known_risks = seed_data.get("known_risks", [])
    competitors = seed_data.get("competitors", [])
    pricing_tiers = seed_data.get("pricing_tiers", [])
    launch_channel = seed_data.get("launch_channel", "social media")
    channel_label = LAUNCH_CHANNEL_LABELS.get(launch_channel, launch_channel)
    trial_policy = seed_data.get("trial_policy", "")
    billing_cycle = seed_data.get("billing_cycle", "")
    target_persona = seed_data.get("target_persona", {})

    # All features
    core_features = seed_data.get("core_features", [])
    feature_parts = []
    for f in core_features:
        name = _feature_name(f)
        desc = _feature_desc(f)
        if name and desc:
            feature_parts.append(f"{name} ({desc})")
        elif name:
            feature_parts.append(name)
    feature_str = "; ".join(feature_parts) if feature_parts else "its core features"

    # All competitors with context
    comp_parts = []
    for c in competitors:
        if isinstance(c, dict):
            c_name = c.get("name", "")
            c_strength = c.get("strength", "")
            c_gap = c.get("gap", "")
            entry = c_name
            if c_strength:
                entry += f" (strong in: {c_strength}"
                if c_gap:
                    entry += f"; gap: {c_gap}"
                entry += ")"
            elif c_gap:
                entry += f" (gap: {c_gap})"
            comp_parts.append(entry)
        elif c:
            comp_parts.append(str(c))
    comp_str = "; ".join(comp_parts) if comp_parts else "existing solutions"

    # All risks
    risk_parts = []
    for r in known_risks:
        r_str = r if isinstance(r, str) else r.get("description", "")
        if r_str.strip():
            risk_parts.append(r_str)

    # Pricing summary
    pricing_parts = []
    for tier in pricing_tiers:
        if isinstance(tier, dict):
            t_name = tier.get("name", "")
            t_price = tier.get("price", "")
            t_desc = tier.get("description", "")
            entry = f"{t_name} at {t_price}" if t_price else t_name
            if t_desc:
                entry += f" ({t_desc})"
            pricing_parts.append(entry)
        elif tier:
            pricing_parts.append(str(tier))
    pricing_str = "; ".join(pricing_parts) if pricing_parts else "undisclosed pricing"

    # Persona detail
    persona_str = ""
    if isinstance(target_persona, dict):
        pain = target_persona.get("pain_points", "")
        triggers = target_persona.get("buying_triggers", "")
        age = target_persona.get("age_range", "")
        if pain:
            persona_str += f" Their core pain: {pain}."
        if triggers:
            persona_str += f" Buying triggers: {triggers}."
        if age:
            persona_str += f" Age range: {age}."
    elif isinstance(target_persona, str) and target_persona:
        persona_str = f" Persona detail: {target_persona}."

    # Build the requirement
    req = (
        f"Simulate the full market reception to the launch of {product_name}, "
        f"a {product_category} targeting {target_market}."
    )
    if tagline:
        req += f' Core promise: "{tagline}".'
    req += (
        f"\n\nPRICING: {pricing_str}."
    )
    if trial_policy:
        req += f" {trial_policy}."
    if billing_cycle:
        req += f" {billing_cycle}."
    req += (
        f"\n\nFEATURES ({len(core_features)} total): {feature_str}."
        f"\n\nCOMPETITORS ({len(comp_parts)} total): {comp_str}."
        f"\n\nLAUNCH CHANNEL: {channel_label}."
    )
    req += f"\n\nTARGET MARKET: {target_market}.{persona_str}"

    if risk_parts:
        req += (
            f"\n\nKNOWN RISKS ({len(risk_parts)} identified — agents should probe these): "
            + "; ".join(risk_parts) + "."
        )

    req += (
        "\n\nSIMULATION INSTRUCTIONS: Agents must form independent opinions grounded in "
        "their assigned persona. Discussions should cover: (1) value proposition vs. "
        f"competitors like {comp_str[:80]}; "
        "(2) pricing fairness — whether each tier represents good value; "
        "(3) feature depth — does it solve the stated pain points; "
        "(4) trust and credibility signals — privacy, AI reliability, single-developer risk; "
        "(5) switching cost from existing tools; "
        "(6) social proof dynamics — who gets influenced by early adopter enthusiasm. "
        "Agents should change their stance over rounds as they see peer opinions, "
        "not simply repeat their initial position. Minority opinions must be given "
        "room to surface and potentially shift the conversation."
    )

    return req.strip()

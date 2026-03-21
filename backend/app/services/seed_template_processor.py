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


def generate_markdown(seed_data: Dict[str, Any]) -> str:
    """
    Render seed_data dict into a structured markdown document.
    This markdown is sent to the existing ontology + graph building pipeline unchanged.
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

    lines = []
    lines.append(f"# {product_name}")
    lines.append(f"\n**Category:** {product_category}")
    if tagline:
        lines.append(f"\n**Tagline:** {tagline}")
    if target_market:
        lines.append(f"\n**Target Market:** {target_market}")
    lines.append("")

    # Core Features
    lines.append("## Core Features")
    if core_features:
        for i, feature in enumerate(core_features, 1):
            if isinstance(feature, dict):
                name = feature.get("name", "")
                desc = feature.get("description", "")
                lines.append(f"{i}. **{name}** — {desc}" if desc else f"{i}. {name}")
            else:
                lines.append(f"{i}. {feature}")
    else:
        lines.append("No features specified.")
    lines.append("")

    # Pricing Model
    lines.append("## Pricing Model")
    if pricing_tiers:
        for tier in pricing_tiers:
            if isinstance(tier, dict):
                tier_name = tier.get("name", "Tier")
                price = tier.get("price", "")
                description = tier.get("description", "")
                lines.append(f"- **{tier_name}**: {price}")
                if description:
                    lines.append(f"  {description}")
            else:
                lines.append(f"- {tier}")
    trial_policy = seed_data.get("trial_policy", "")
    billing_cycle = seed_data.get("billing_cycle", "")
    if trial_policy:
        lines.append(f"\n**Trial Policy:** {trial_policy}")
    if billing_cycle:
        lines.append(f"**Billing:** {billing_cycle}")
    lines.append("")

    # Competitive Context
    lines.append("## Competitive Context")
    if competitors:
        for comp in competitors:
            if isinstance(comp, dict):
                comp_name = comp.get("name", "")
                strength = comp.get("strength", "")
                gap = comp.get("gap", "")
                lines.append(f"- **{comp_name}**")
                if strength:
                    lines.append(f"  - Strength: {strength}")
                if gap:
                    lines.append(f"  - Gap: {gap}")
            else:
                lines.append(f"- {comp}")
    else:
        lines.append("No competitors specified.")
    lines.append("")

    # Target Persona
    lines.append("## Target Persona")
    if isinstance(target_persona, dict):
        age_range = target_persona.get("age_range", "")
        income = target_persona.get("income_level", "")
        psychographics = target_persona.get("psychographics", [])
        pain_points = target_persona.get("pain_points", "")
        buying_triggers = target_persona.get("buying_triggers", "")

        if age_range:
            lines.append(f"- **Age Range:** {age_range}")
        if income:
            lines.append(f"- **Income Level:** {income}")
        if psychographics:
            tags = psychographics if isinstance(psychographics, str) else ", ".join(psychographics)
            lines.append(f"- **Psychographics:** {tags}")
        if pain_points:
            lines.append(f"- **Pain Points:** {pain_points}")
        if buying_triggers:
            lines.append(f"- **Buying Triggers:** {buying_triggers}")
    elif isinstance(target_persona, str) and target_persona:
        lines.append(target_persona)
    lines.append("")

    # Launch Channel
    lines.append("## Launch Channel")
    channel_label = LAUNCH_CHANNEL_LABELS.get(launch_channel, launch_channel)
    lines.append(f"Primary launch channel: **{channel_label}**")
    channel_notes = seed_data.get("launch_channel_notes", "")
    if channel_notes:
        lines.append(f"\n{channel_notes}")
    lines.append("")

    # Known Risks
    lines.append("## Known Risks")
    if known_risks:
        for risk in known_risks:
            if isinstance(risk, str) and risk.strip():
                lines.append(f"- {risk}")
    else:
        lines.append("No specific risks identified.")
    lines.append("")

    # Product Overview Summary (for LLM context quality)
    lines.append("## Product Overview Summary")
    feature_list = []
    for f in core_features[:3]:
        if isinstance(f, dict):
            feature_list.append(f.get("name", ""))
        else:
            feature_list.append(str(f))
    feature_summary = ", ".join(feature_list) if feature_list else "multiple features"

    lines.append(
        f"{product_name} is a {product_category} targeting {target_market}. "
        f"It offers {feature_summary}. "
        f"It is entering a market with {len(competitors)} known competitor(s). "
        f"The primary launch channel is {channel_label}."
    )
    if known_risks:
        risk_summary = "; ".join(
            r if isinstance(r, str) else r.get("description", "")
            for r in known_risks[:3]
        )
        lines.append(f"Known risks include: {risk_summary}.")

    return "\n".join(lines)


def generate_simulation_requirement(seed_data: Dict[str, Any]) -> str:
    """
    Generate a natural language simulation_requirement string from seed data.
    This is passed to SimulationConfigGenerator as context for agent behavior generation.
    """
    product_name = seed_data.get("product_name", "the product")
    product_category = seed_data.get("product_category", "software")
    target_market = seed_data.get("target_market", "general consumers")
    tagline = seed_data.get("tagline", "")
    known_risks = seed_data.get("known_risks", [])
    competitors = seed_data.get("competitors", [])
    launch_channel = seed_data.get("launch_channel", "social media")
    channel_label = LAUNCH_CHANNEL_LABELS.get(launch_channel, launch_channel)

    core_features = seed_data.get("core_features", [])
    feature_names = []
    for f in core_features[:3]:
        if isinstance(f, dict):
            feature_names.append(f.get("name", ""))
        else:
            feature_names.append(str(f))
    feature_str = ", ".join(feature_names) if feature_names else "its core features"

    comp_names = []
    for c in competitors[:2]:
        if isinstance(c, dict):
            comp_names.append(c.get("name", ""))
        else:
            comp_names.append(str(c))
    comp_str = " and ".join(comp_names) if comp_names else "existing solutions"

    risk_str = ""
    if known_risks:
        risks = []
        for r in known_risks[:2]:
            risks.append(r if isinstance(r, str) else r.get("description", ""))
        risk_str = f" Key concerns include: {'; '.join(risks)}."

    requirement = (
        f"Simulate market sentiment and consumer reactions to the launch of {product_name}, "
        f"a {product_category} targeting {target_market}. "
    )
    if tagline:
        requirement += f'The product is positioned as: "{tagline}". '
    requirement += (
        f"Key features: {feature_str}. "
        f"Competitors include {comp_str}. "
        f"The product is launching via {channel_label}."
        f"{risk_str} "
        "Agents should discuss and debate the product's value proposition, pricing, "
        "features, and competitive positioning. Simulate how different consumer segments "
        "react, form opinions, and influence each other across social platforms."
    )
    return requirement.strip()

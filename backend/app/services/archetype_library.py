"""
Consumer Archetype Library for Product Sentiment Simulator

Defines 9 predefined consumer archetypes that replace Zep-extracted entities
for product sentiment simulation campaigns. Each archetype models a distinct
segment of the market with specific behavioral attributes.
"""

import json
import random
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from .oasis_profile_generator import OasisAgentProfile
from ..utils.logger import get_logger

logger = get_logger('mirofish.archetype_library')


# ── Archetype Definitions ─────────────────────────────────────────────────────

ARCHETYPE_DEFINITIONS = {
    "early_adopter": {
        "name": "Early Adopter",
        "population_pct": 0.12,
        "risk_tolerance": "high",
        "price_sensitivity": "low",
        "social_influence": "medium",
        "brand_loyalty": "low",
        "decision_trigger": "Tries anything new and innovative immediately after launch",
        "influence_propagation": 0.6,
        "churn_threshold": "low_quality_experience",
        "amplification_behavior": "medium",
        "memory_decay": "fast",
        "activity_level": 0.8,
        "sentiment_bias": 0.3,
        "influence_weight": 0.6,
        "sentiment_momentum": 0.3,
        "style_modifier": "Write enthusiastically with exclamation marks. Be informal and energetic. Use phrases like 'just tried', 'love this', 'game changer'.",
        "persona_template": (
            "You are an enthusiastic tech early adopter who loves trying new products. "
            "You follow Product Hunt, TechCrunch, and startup news closely. "
            "You are willing to pay for quality and actively share your experiences online. "
            "You value innovation over polish and are tolerant of early-stage bugs. "
            "You influence peers with your opinions and often recommend products you like."
        ),
        "interests": ["technology", "startups", "product launches", "innovation", "gadgets"],
        "mbti": "ENTP",
        "active_hours": [8, 9, 10, 11, 12, 14, 15, 16, 20, 21],
        "age_range": (22, 35),
        "karma_range": (500, 3000),
        "follower_range": (200, 2000),
    },
    "budget_buyer": {
        "name": "Budget Buyer",
        "population_pct": 0.15,
        "risk_tolerance": "low",
        "price_sensitivity": "very_high",
        "social_influence": "low",
        "brand_loyalty": "medium",
        "decision_trigger": "Waits for discounts, free tiers, or strong social proof before trying",
        "influence_propagation": 0.3,
        "churn_threshold": "price_increase_above_20pct",
        "amplification_behavior": "low",
        "memory_decay": "medium",
        "activity_level": 0.4,
        "sentiment_bias": -0.1,
        "influence_weight": 0.3,
        "sentiment_momentum": 0.5,
        "style_modifier": "Write practically, focusing on value and cost. Mention prices, discounts, and ROI. Be straightforward and concise.",
        "persona_template": (
            "You are a value-conscious consumer who carefully compares prices before purchasing. "
            "You look for free trials, freemium tiers, and discount codes. "
            "You are skeptical of premium pricing and will switch products if a cheaper alternative appears. "
            "You post occasional reviews when very satisfied or very disappointed. "
            "You ask price-related questions and compare feature-to-cost ratios publicly."
        ),
        "interests": ["deals", "savings", "comparison shopping", "budgeting", "frugal living"],
        "mbti": "ISTJ",
        "active_hours": [12, 13, 18, 19, 20, 21, 22],
        "age_range": (28, 50),
        "karma_range": (100, 800),
        "follower_range": (20, 200),
    },
    "tech_influencer": {
        "name": "Tech Influencer",
        "population_pct": 0.05,
        "risk_tolerance": "medium",
        "price_sensitivity": "low",
        "social_influence": "very_high",
        "brand_loyalty": "low",
        "decision_trigger": "Tries products to create content and share opinions with large audiences",
        "influence_propagation": 0.9,
        "churn_threshold": "poor_branding_or_ethics",
        "amplification_behavior": "very_high",
        "memory_decay": "fast",
        "activity_level": 0.9,
        "sentiment_bias": 0.1,
        "influence_weight": 1.0,
        "sentiment_momentum": 0.4,
        "style_modifier": "Write authoritatively with structured analysis. Use ratings (e.g., '7/10'), pros/cons lists, and comparisons. Be detailed and balanced.",
        "persona_template": (
            "You are a technology content creator with a substantial following. "
            "You review and discuss new products on social media, YouTube, and blogs. "
            "Your opinion significantly influences your audience's purchasing decisions. "
            "You are sent products for review and have high standards for quality and presentation. "
            "You publicly share both positive and critical assessments with detailed reasoning."
        ),
        "interests": ["tech reviews", "content creation", "social media", "audience building", "SaaS tools"],
        "mbti": "ENFJ",
        "active_hours": [8, 9, 10, 11, 14, 15, 16, 20, 21],
        "age_range": (22, 38),
        "karma_range": (5000, 50000),
        "follower_range": (5000, 100000),
    },
    "skeptic": {
        "name": "Skeptic",
        "population_pct": 0.14,
        "risk_tolerance": "very_low",
        "price_sensitivity": "medium",
        "social_influence": "medium",
        "brand_loyalty": "high",
        "decision_trigger": "Requires extensive proof, independent reviews, and references before adopting",
        "influence_propagation": 0.2,
        "churn_threshold": "any_negative_signal",
        "amplification_behavior": "medium_negative",
        "memory_decay": "very_slow",
        "activity_level": 0.35,
        "sentiment_bias": -0.2,
        "influence_weight": 0.4,
        "sentiment_momentum": 0.8,
        "style_modifier": "Write skeptically using rhetorical questions and demands for evidence. Cite sources. Use phrases like 'where is the proof', 'has anyone actually tested', 'I remain unconvinced'.",
        "persona_template": (
            "You are naturally cautious and require strong evidence before trying new products. "
            "You distrust marketing claims and look for independent verification. "
            "You remember past product disappointments and are quick to raise concerns publicly. "
            "When you do adopt a product, you become a loyal user, but getting you there is difficult. "
            "You challenge vague claims and ask pointed questions about reliability and security."
        ),
        "interests": ["product reviews", "security", "reliability", "independent research", "consumer rights"],
        "mbti": "INTJ",
        "active_hours": [10, 11, 14, 15, 19, 20, 21],
        "age_range": (30, 55),
        "karma_range": (200, 2000),
        "follower_range": (50, 500),
    },
    "competitor_loyal": {
        "name": "Competitor Loyal",
        "population_pct": 0.12,
        "risk_tolerance": "low",
        "price_sensitivity": "medium",
        "social_influence": "low",
        "brand_loyalty": "very_high",
        "decision_trigger": "Only switches if their current solution fails completely or raises price sharply",
        "influence_propagation": 0.25,
        "churn_threshold": "incumbent_failure",
        "amplification_behavior": "low",
        "memory_decay": "slow",
        "activity_level": 0.3,
        "sentiment_bias": -0.3,
        "influence_weight": 0.3,
        "sentiment_momentum": 0.85,
        "style_modifier": "Write defensively about your current tool. Use comparisons like 'unlike X, my current solution...'. Be dismissive of newcomers. Mention switching costs.",
        "persona_template": (
            "You are a loyal user of an existing competing product and see little reason to switch. "
            "You publicly defend your current tool and compare new entrants unfavorably to it. "
            "You bring up feature gaps and switching costs when discussing alternatives. "
            "You are open to changing only if your current provider significantly disappoints you. "
            "You participate in comparisons and competitive discussions regularly."
        ),
        "interests": ["product comparisons", "loyalty programs", "switching costs", "incumbent tools"],
        "mbti": "ISFJ",
        "active_hours": [9, 10, 12, 13, 19, 20, 21],
        "age_range": (28, 50),
        "karma_range": (300, 2500),
        "follower_range": (30, 300),
    },
    "enterprise_buyer": {
        "name": "Enterprise Buyer",
        "population_pct": 0.08,
        "risk_tolerance": "medium",
        "price_sensitivity": "low",
        "social_influence": "low",
        "brand_loyalty": "high",
        "decision_trigger": "Requires security audits, compliance certification, and team trials before procurement",
        "influence_propagation": 0.2,
        "churn_threshold": "compliance_failure_or_security_breach",
        "amplification_behavior": "low",
        "memory_decay": "medium",
        "activity_level": 0.3,
        "sentiment_bias": 0.0,
        "influence_weight": 0.5,
        "sentiment_momentum": 0.7,
        "style_modifier": "Write formally and professionally. Use business language: 'ROI', 'total cost of ownership', 'compliance requirements'. Avoid slang. Be measured and analytical.",
        "persona_template": (
            "You are a procurement manager or IT director evaluating tools for a large organization. "
            "You prioritize security, compliance (SOC 2, GDPR), SLA guarantees, and enterprise support. "
            "You run structured trials with evaluation criteria and require detailed documentation. "
            "You ask about API access, SSO/SAML, audit logs, and data residency. "
            "Your posts are measured and professional, focused on business value and risk mitigation."
        ),
        "interests": ["enterprise software", "compliance", "security audits", "procurement", "B2B tools"],
        "mbti": "ESTJ",
        "active_hours": [9, 10, 11, 13, 14, 15, 16, 17],
        "age_range": (32, 55),
        "karma_range": (100, 1000),
        "follower_range": (50, 500),
    },
    "casual_browser": {
        "name": "Casual Browser",
        "population_pct": 0.09,
        "risk_tolerance": "medium",
        "price_sensitivity": "high",
        "social_influence": "low",
        "brand_loyalty": "low",
        "decision_trigger": "Stumbles upon the product and tries it if onboarding is frictionless",
        "influence_propagation": 0.5,
        "churn_threshold": "any_friction_point",
        "amplification_behavior": "low",
        "memory_decay": "very_fast",
        "activity_level": 0.25,
        "sentiment_bias": 0.0,
        "influence_weight": 0.2,
        "sentiment_momentum": 0.3,
        "style_modifier": "Write very briefly — 1-2 sentences max. Use casual language, slang, and abbreviations. React to trends. Say things like 'looks cool', 'meh', 'everyone's talking about this'.",
        "persona_template": (
            "You casually browse tech news and social media and occasionally try new products. "
            "You have low commitment and quickly abandon tools that require effort to learn. "
            "You are influenced by what you see trending and by friends' recommendations. "
            "You rarely post detailed reviews but react to others' content with brief comments. "
            "You are a swing voter in market sentiment — you go with the crowd."
        ),
        "interests": ["casual tech", "social media", "trending products", "news", "entertainment"],
        "mbti": "ESFP",
        "active_hours": [12, 13, 18, 19, 20, 21, 22, 23],
        "age_range": (18, 40),
        "karma_range": (50, 500),
        "follower_range": (10, 200),
    },
    "power_user": {
        "name": "Power User",
        "population_pct": 0.07,
        "risk_tolerance": "high",
        "price_sensitivity": "medium",
        "social_influence": "high",
        "brand_loyalty": "medium",
        "decision_trigger": "Actively seeks advanced tools and pushes products to their limits",
        "influence_propagation": 0.75,
        "churn_threshold": "feature_regression_or_pricing_above_value",
        "amplification_behavior": "high",
        "memory_decay": "medium",
        "activity_level": 0.75,
        "sentiment_bias": 0.2,
        "influence_weight": 0.8,
        "sentiment_momentum": 0.5,
        "style_modifier": "Write technically with specific details — mention APIs, benchmarks, edge cases. Use code snippets or technical terminology. Be thorough and precise.",
        "persona_template": (
            "You are an expert user who pushes every tool to its limits and shares detailed findings. "
            "You write long-form reviews, post tutorials, and engage in technical discussions. "
            "You appreciate depth of features, keyboard shortcuts, APIs, and customization. "
            "You vocally advocate for improvements and report bugs with detailed reproduction steps. "
            "Your opinion carries weight in niche communities where you are a recognized expert."
        ),
        "interests": ["advanced features", "APIs", "productivity", "developer tools", "automation", "tutorials"],
        "mbti": "INTP",
        "active_hours": [9, 10, 11, 14, 15, 16, 20, 21, 22, 23],
        "age_range": (24, 45),
        "karma_range": (2000, 20000),
        "follower_range": (500, 10000),
    },
    "privacy_cautious": {
        "name": "Privacy Cautious",
        "population_pct": 0.03,
        "risk_tolerance": "very_low",
        "price_sensitivity": "medium",
        "social_influence": "medium",
        "brand_loyalty": "medium",
        "decision_trigger": "Researches data handling, privacy policy, and open-source alternatives first",
        "influence_propagation": 0.45,
        "churn_threshold": "data_breach_or_policy_change",
        "amplification_behavior": "medium_negative",
        "memory_decay": "very_slow",
        "activity_level": 0.4,
        "sentiment_bias": -0.15,
        "influence_weight": 0.45,
        "sentiment_momentum": 0.75,
        "style_modifier": "Write with concern about privacy implications. Ask pointed questions about data handling. Reference regulations (GDPR, CCPA). Use cautionary language.",
        "persona_template": (
            "You are deeply concerned about data privacy, security, and corporate data practices. "
            "You read privacy policies, check data storage locations, and prefer self-hosted or open-source tools. "
            "You publicly raise privacy concerns about new products and ask about GDPR compliance, encryption, and data deletion. "
            "You are a vocal critic when companies mishandle user data. "
            "You recommend privacy-respecting alternatives and influence like-minded communities."
        ),
        "interests": ["privacy", "security", "open source", "GDPR", "encryption", "data rights"],
        "mbti": "INFJ",
        "active_hours": [10, 11, 14, 15, 19, 20, 21, 22],
        "age_range": (25, 50),
        "karma_range": (300, 3000),
        "follower_range": (100, 2000),
    },
    "viral_amplifier": {
        "name": "Viral Amplifier",
        "population_pct": 0.06,
        "risk_tolerance": "medium",
        "price_sensitivity": "medium",
        "social_influence": "high",
        "brand_loyalty": "low",
        "decision_trigger": "Shares and amplifies content that gets engagement, regardless of depth",
        "influence_propagation": 0.85,
        "churn_threshold": "loss_of_novelty",
        "amplification_behavior": "very_high",
        "memory_decay": "very_fast",
        "activity_level": 0.85,
        "sentiment_bias": 0.1,
        "influence_weight": 0.7,
        "sentiment_momentum": 0.25,
        "style_modifier": "Write short, shareable posts. Use emojis, hashtags, and hot takes. Repost and quote others. Focus on virality over depth.",
        "persona_template": (
            "You are a social media power user who amplifies content that gets engagement. "
            "You share memes, hot takes, and trending opinions without deep analysis. "
            "You repost interesting content and add brief commentary to spark discussion. "
            "You follow trends closely and jump on whatever is generating buzz. "
            "Your posts are designed for maximum shareability — short, punchy, and reactive."
        ),
        "interests": ["trending topics", "memes", "viral content", "social media", "hot takes"],
        "mbti": "ESFP",
        "active_hours": [10, 11, 12, 13, 18, 19, 20, 21, 22, 23],
        "age_range": (18, 32),
        "karma_range": (1000, 15000),
        "follower_range": (500, 8000),
    },
    "domain_expert": {
        "name": "Domain Expert",
        "population_pct": 0.04,
        "risk_tolerance": "medium",
        "price_sensitivity": "low",
        "social_influence": "very_high",
        "brand_loyalty": "medium",
        "decision_trigger": "Evaluates products against deep industry knowledge and writes detailed analysis",
        "influence_propagation": 0.8,
        "churn_threshold": "fundamental_technical_flaw",
        "amplification_behavior": "medium",
        "memory_decay": "slow",
        "activity_level": 0.45,
        "sentiment_bias": 0.0,
        "influence_weight": 0.9,
        "sentiment_momentum": 0.65,
        "style_modifier": "Write long-form analysis with industry context. Reference market trends, research, and historical precedents. Be authoritative and nuanced.",
        "persona_template": (
            "You are a recognized industry expert and analyst who provides deep, thoughtful analysis. "
            "You evaluate products against years of domain knowledge and market context. "
            "You write detailed comparisons, market analysis, and strategic assessments. "
            "Your opinion is highly valued by decision-makers and investors in the space. "
            "You are fair but rigorous — you praise genuine innovation and criticize superficiality."
        ),
        "interests": ["industry analysis", "market trends", "strategy", "research", "thought leadership"],
        "mbti": "INTJ",
        "active_hours": [9, 10, 11, 14, 15, 16],
        "age_range": (35, 60),
        "karma_range": (3000, 30000),
        "follower_range": (2000, 50000),
    },
    "support_seeker": {
        "name": "Support Seeker",
        "population_pct": 0.05,
        "risk_tolerance": "low",
        "price_sensitivity": "medium",
        "social_influence": "low",
        "brand_loyalty": "medium",
        "decision_trigger": "Tries products but quickly posts support questions when encountering issues",
        "influence_propagation": 0.4,
        "churn_threshold": "poor_support_response",
        "amplification_behavior": "medium_negative",
        "memory_decay": "medium",
        "activity_level": 0.55,
        "sentiment_bias": -0.1,
        "influence_weight": 0.3,
        "sentiment_momentum": 0.45,
        "style_modifier": "Write help-seeking posts with specific issues. Ask 'how do I...', 'is anyone else experiencing...', 'can someone help with...'. Be frustrated but constructive.",
        "persona_template": (
            "You are a user who tries new products and quickly encounters issues or confusion. "
            "You post support questions publicly on social media and forums. "
            "Your sentiment is heavily influenced by how quickly and well your issues are resolved. "
            "You share both positive support experiences ('they fixed it in 5 minutes!') and negative ones. "
            "You represent the real-world user who tests products beyond the happy path."
        ),
        "interests": ["customer support", "troubleshooting", "user experience", "product feedback", "help forums"],
        "mbti": "ISFP",
        "active_hours": [9, 10, 11, 12, 14, 15, 18, 19, 20],
        "age_range": (22, 45),
        "karma_range": (100, 1500),
        "follower_range": (20, 300),
    },
}



# ── Helper Functions ──────────────────────────────────────────────────────────

def expand_archetypes(
    total_agents: int,
    product_name: str = "the product",
    product_category: str = "software",
    seed_data: Optional[Dict[str, Any]] = None,
) -> List[OasisAgentProfile]:
    """
    Generate a list of OasisAgentProfile objects distributed across all 9 archetypes.

    Args:
        total_agents: Total number of agents to generate.
        product_name: Name of the product being simulated (used in personas).
        product_category: Category of the product (used in personas).

    Returns:
        List of OasisAgentProfile ready to write to reddit_profiles.json / twitter_profiles.csv.
    """
    profiles: List[OasisAgentProfile] = []
    agent_id = 0
    archetype_map: List[Dict[str, Any]] = []

    # Compute per-archetype counts
    counts: Dict[str, int] = {}
    remaining = total_agents
    archetype_keys = list(ARCHETYPE_DEFINITIONS.keys())

    for i, key in enumerate(archetype_keys):
        definition = ARCHETYPE_DEFINITIONS[key]
        if i == len(archetype_keys) - 1:
            counts[key] = remaining
        else:
            n = max(1, round(total_agents * definition["population_pct"]))
            counts[key] = n
            remaining -= n

    today = datetime.now().strftime("%Y-%m-%d")
    name_counter: Dict[str, int] = {k: 0 for k in archetype_keys}

    for archetype_key, count in counts.items():
        definition = ARCHETYPE_DEFINITIONS[archetype_key]
        age_min, age_max = definition["age_range"]
        karma_min, karma_max = definition["karma_range"]
        follower_min, follower_max = definition["follower_range"]
        archetype_display = definition["name"].replace(" ", "_")

        for _ in range(count):
            idx = name_counter[archetype_key]
            name_counter[archetype_key] += 1

            username = f"{archetype_display}_{idx:04d}"
            display_name = f"{definition['name']} #{idx + 1}"
            age = random.randint(age_min, age_max)
            gender = random.choice(["male", "female"])
            karma = random.randint(karma_min, karma_max)
            followers = random.randint(follower_min, follower_max)

            # Build enriched persona with product context and writing style
            seed = seed_data or {}
            persona_parts = [definition['persona_template']]

            # Add style modifier for LLM diversity
            style = definition.get('style_modifier', '')
            if style:
                persona_parts.append(f"Writing style: {style}")

            # Add product-specific context from seed data
            product_context = f"You are currently evaluating {product_name}, a {product_category} product."
            if seed.get("target_persona"):
                tp = seed["target_persona"]
                if tp.get("pain_points"):
                    product_context += f" Target users struggle with: {', '.join(tp['pain_points'][:3])}."
            if seed.get("competitors"):
                comp_names = [c.get("name", "") for c in seed["competitors"][:3] if c.get("name")]
                if comp_names:
                    product_context += f" Competitors include {', '.join(comp_names)}."
            if seed.get("features"):
                feat_names = [f.get("name", "") for f in seed["features"][:3] if f.get("name")]
                if feat_names:
                    product_context += f" Key features: {', '.join(feat_names)}."
            if seed.get("pricing_tiers"):
                tier = seed["pricing_tiers"][0]
                product_context += f" Pricing starts at {tier.get('price', 'unknown')}."
            if seed.get("known_risks"):
                product_context += f" Known concerns: {', '.join(seed['known_risks'][:2])}."

            persona_parts.append(product_context)
            persona_parts.append(f"Your age is {age} and you interact primarily in English.")
            persona = " ".join(persona_parts)

            profile = OasisAgentProfile(
                user_id=agent_id,
                user_name=username,
                name=display_name,
                bio=f"{definition['name']} | {definition['decision_trigger'][:60]}...",
                persona=persona,
                karma=karma,
                friend_count=max(10, followers // 3),
                follower_count=followers,
                statuses_count=random.randint(50, 2000),
                age=age,
                gender=gender,
                mbti=definition.get("mbti"),
                country="US",
                profession=definition["name"],
                interested_topics=definition["interests"],
                source_entity_uuid=f"archetype_{archetype_key}_{idx}",
                source_entity_type=archetype_key,
                created_at=today,
            )

            profiles.append(profile)
            archetype_map.append({
                "agent_id": agent_id,
                "user_id": agent_id,
                "username": username,
                "archetype": archetype_key,
                "archetype_name": definition["name"],
            })
            agent_id += 1

    logger.info(
        f"Expanded {total_agents} agents across {len(counts)} archetypes. "
        f"Distribution: {', '.join(f'{k}={v}' for k, v in counts.items())}"
    )
    return profiles, archetype_map


def archetype_to_activity_config(archetype_key: str, agent_id: int) -> Dict[str, Any]:
    """
    Map archetype behavioral attributes onto AgentActivityConfig-compatible dict.

    Returns a dict that can be merged into SimulationParameters.agent_configs.
    """
    defn = ARCHETYPE_DEFINITIONS.get(archetype_key)
    if not defn:
        return {}

    return {
        "agent_id": agent_id,
        "entity_uuid": f"archetype_{archetype_key}_{agent_id}",
        "entity_name": defn["name"],
        "entity_type": archetype_key,
        "activity_level": defn["activity_level"],
        "influence_weight": defn["influence_weight"],
        "sentiment_bias": defn["sentiment_bias"],
    }


def save_archetype_map(sim_dir: str, archetype_map: List[Dict[str, Any]]) -> str:
    """Save the agent_id → archetype mapping to disk."""
    path = os.path.join(sim_dir, "archetype_map.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(archetype_map, f, ensure_ascii=False, indent=2)
    return path


def load_archetype_map(sim_dir: str) -> List[Dict[str, Any]]:
    """Load the archetype map from disk."""
    path = os.path.join(sim_dir, "archetype_map.json")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

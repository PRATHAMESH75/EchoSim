"""
Product Sentiment Simulator API

Endpoints for campaign creation, scenario orchestration, and sentiment analysis.
"""

import traceback
from flask import request, jsonify

from . import sentiment_bp
from ..config import Config
from ..extensions import limiter
from ..utils.logger import get_logger
from ..services.campaign_manager import CampaignManager
from ..services.sentiment_analyzer import SentimentAnalyzer, compare_scenarios
from ..services.seed_template_processor import validate_seed, generate_markdown, generate_simulation_requirement
from ..services.archetype_library import ARCHETYPE_DEFINITIONS

logger = get_logger('mirofish.api.sentiment')

_campaign_manager = CampaignManager()


# ── Seed Template ─────────────────────────────────────────────────────────────

@sentiment_bp.route('/seed/validate', methods=['POST'])
def validate_seed_data():
    """Validate a seed template form submission."""
    try:
        seed_data = request.get_json(force=True) or {}
        errors = validate_seed(seed_data)
        return jsonify({"success": True, "valid": len(errors) == 0, "errors": errors})
    except Exception as e:
        logger.error(f"Seed validation error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@sentiment_bp.route('/seed/preview', methods=['POST'])
def preview_seed():
    """Generate and return the markdown + simulation_requirement without creating a project."""
    try:
        seed_data = request.get_json(force=True) or {}
        errors = validate_seed(seed_data)
        if errors:
            return jsonify({"success": False, "errors": errors}), 400
        return jsonify({
            "success": True,
            "markdown": generate_markdown(seed_data),
            "simulation_requirement": generate_simulation_requirement(seed_data),
        })
    except Exception as e:
        logger.error(f"Seed preview error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@sentiment_bp.route('/archetypes', methods=['GET'])
def get_archetypes():
    """Return all archetype definitions (for UI display)."""
    archetypes = []
    for key, defn in ARCHETYPE_DEFINITIONS.items():
        archetypes.append({
            "key": key,
            "name": defn["name"],
            "population_pct": defn["population_pct"],
            "risk_tolerance": defn["risk_tolerance"],
            "price_sensitivity": defn["price_sensitivity"],
            "social_influence": defn["social_influence"],
            "brand_loyalty": defn["brand_loyalty"],
            "decision_trigger": defn["decision_trigger"],
            "amplification_behavior": defn["amplification_behavior"],
            "memory_decay": defn["memory_decay"],
            "interests": defn["interests"],
            "sentiment_momentum": defn.get("sentiment_momentum", 0.5),
            "influence_weight": defn.get("influence_weight", 0.5),
            "activity_level": defn.get("activity_level", 0.5),
        })
    return jsonify({"success": True, "archetypes": archetypes})


# ── Campaign Lifecycle ────────────────────────────────────────────────────────

@sentiment_bp.route('/campaign/create', methods=['POST'])
@limiter.limit("10 per hour")
def create_campaign():
    """
    Create a new sentiment campaign.

    Body:
        project_id: str
        graph_id: str
        seed_data: dict (7-dimension product brief)
        competitive_event_type: str (optional, default 'price_drop')
        crisis_event_type: str (optional, default 'security_breach')
        total_agents: int (optional, default 50)
        scenario_b_inject_round: int (optional, default 7)
        scenario_c_inject_round: int (optional, default 14)
        enable_twitter: bool (optional, default true)
        enable_reddit: bool (optional, default true)
    """
    try:
        body = request.get_json(force=True) or {}
        project_id = body.get("project_id", "")
        graph_id = body.get("graph_id", "")
        seed_data = body.get("seed_data", {})

        if not project_id:
            return jsonify({"success": False, "error": "project_id is required"}), 400
        if not graph_id:
            return jsonify({"success": False, "error": "graph_id is required"}), 400

        errors = validate_seed(seed_data)
        if errors:
            return jsonify({"success": False, "errors": errors}), 400

        competitive_event_weights = body.get("competitive_event_weights", None)
        crisis_event_weights = body.get("crisis_event_weights", None)

        campaign = _campaign_manager.create_campaign(
            project_id=project_id,
            graph_id=graph_id,
            seed_data=seed_data,
            competitive_event_type=body.get("competitive_event_type", "price_drop"),
            crisis_event_type=body.get("crisis_event_type", "security_breach"),
            competitive_event_weights=competitive_event_weights,
            crisis_event_weights=crisis_event_weights,
            total_agents=int(body.get("total_agents", 50)),
            scenario_b_inject_round=body.get("scenario_b_inject_round"),
            scenario_c_inject_round=body.get("scenario_c_inject_round"),
            enable_twitter=bool(body.get("enable_twitter", True)),
            enable_reddit=bool(body.get("enable_reddit", True)),
        )

        return jsonify({"success": True, "campaign": campaign.to_dict()})

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"Create campaign error: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@sentiment_bp.route('/campaign/<campaign_id>/prepare', methods=['POST'])
@limiter.limit("10 per hour")
def prepare_campaign(campaign_id: str):
    """
    Start asynchronous preparation for all three scenarios.
    """
    try:
        result = _campaign_manager.start_prepare(campaign_id=campaign_id)
        return jsonify({
            "success": True,
            "campaign": result["campaign"].to_dict() if hasattr(result["campaign"], "to_dict") else result["campaign"],
            "task": result.get("task"),
            "task_id": (result.get("task") or {}).get("task_id"),
        })
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        logger.error(f"Prepare campaign error: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@sentiment_bp.route('/campaign/<campaign_id>/prepare/status', methods=['GET'])
def get_prepare_campaign_status(campaign_id: str):
    """Poll asynchronous campaign preparation progress."""
    try:
        task_id = request.args.get("task_id", "").strip() or None
        status = _campaign_manager.get_prepare_status(campaign_id=campaign_id, task_id=task_id)
        return jsonify({"success": True, **status})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        logger.error(f"Get prepare status error: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@sentiment_bp.route('/campaign/<campaign_id>/start', methods=['POST'])
@limiter.limit("10 per hour")
def start_campaign(campaign_id: str):
    """
    Start the campaign (launches background workers running all 3 scenarios in parallel).

    Body (optional):
        platform: str (twitter / reddit / parallel, default parallel)
        max_rounds: int (default 30)
    """
    try:
        body = request.get_json(force=True) or {}
        platform = body.get("platform", "parallel")
        max_rounds = min(int(body.get("max_rounds", Config.SENTIMENT_DEFAULT_MAX_ROUNDS)), 150)

        campaign = _campaign_manager.start_campaign(
            campaign_id=campaign_id,
            platform=platform,
            max_rounds=max_rounds,
        )
        return jsonify({"success": True, "campaign": campaign.to_dict()})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"Start campaign error: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@sentiment_bp.route('/campaign/<campaign_id>', methods=['GET'])
def get_campaign(campaign_id: str):
    """Get aggregated campaign status including all three scenario run states."""
    try:
        status = _campaign_manager.get_campaign_status(campaign_id)
        return jsonify({"success": True, **status})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        logger.error(f"Get campaign error: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@sentiment_bp.route('/campaign/<campaign_id>', methods=['DELETE'])
def delete_campaign(campaign_id: str):
    """Delete a campaign and its associated simulation data."""
    try:
        _campaign_manager.delete_campaign(campaign_id)
        return jsonify({"success": True, "campaign_id": campaign_id})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        logger.error(f"Delete campaign error: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@sentiment_bp.route('/campaign', methods=['GET'])
def list_campaigns():
    """List all campaigns."""
    try:
        campaigns = _campaign_manager.list_campaigns()
        return jsonify({"success": True, "campaigns": campaigns})
    except Exception as e:
        logger.error(f"List campaigns error: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@sentiment_bp.route('/campaign/<campaign_id>/inject', methods=['POST'])
def inject_event(campaign_id: str):
    """
    Inject a God's Eye event into a running scenario simulation.

    Body:
        scenario: str ('b' or 'c')
        event_type: str (optional — uses campaign default if omitted)
        custom_prompt: str (optional — overrides event_type if provided)
        timeout: float (optional, default 60)
    """
    try:
        body = request.get_json(force=True) or {}
        scenario = body.get("scenario", "b")
        if scenario.lower() not in ("b", "c"):
            return jsonify({"success": False, "error": "scenario must be 'b' or 'c'"}), 400

        result = _campaign_manager.inject_scenario_event(
            campaign_id=campaign_id,
            scenario=scenario,
            event_type=body.get("event_type"),
            custom_prompt=body.get("custom_prompt"),
            timeout=float(body.get("timeout", 60.0)),
        )
        return jsonify({"success": True, "result": result})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        logger.error(f"Inject event error: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


# ── Sentiment Analysis ────────────────────────────────────────────────────────

@sentiment_bp.route('/campaign/<campaign_id>/sentiment', methods=['GET'])
def get_campaign_sentiment(campaign_id: str):
    """
    Run sentiment analysis on all three scenarios and return aggregated results.
    """
    try:
        status = _campaign_manager.get_campaign_status(campaign_id)
        camp = status.get("campaign", {})
        sim_id_a = camp.get("sim_id_a", "")
        sim_id_b = camp.get("sim_id_b", "")
        sim_id_c = camp.get("sim_id_c", "")

        # Configurable thresholds via query params
        adv_thresh = float(request.args.get("advocate_threshold", 0.35))
        det_thresh = float(request.args.get("detractor_threshold", -0.25))
        use_pct = request.args.get("percentile_factions", "").lower() in ("1", "true", "yes")

        def _analyze(sim_id):
            if not sim_id:
                return None
            try:
                return SentimentAnalyzer(
                    sim_id,
                    advocate_threshold=adv_thresh,
                    detractor_threshold=det_thresh,
                    use_percentile_factions=use_pct,
                ).analyze_all()
            except Exception as e:
                logger.warning(f"Sentiment analysis failed for {sim_id}: {e}")
                return None

        return jsonify({
            "success": True,
            "campaign_id": campaign_id,
            "scenario_a": _analyze(sim_id_a),
            "scenario_b": _analyze(sim_id_b),
            "scenario_c": _analyze(sim_id_c),
            "event_markers": {
                "scenario_b_inject_round": Config.SENTIMENT_SCENARIO_B_INJECT_ROUND,
                "scenario_c_inject_round": Config.SENTIMENT_SCENARIO_C_INJECT_ROUND,
                "competitive_event_type": camp.get("competitive_event_type", ""),
                "crisis_event_type": camp.get("crisis_event_type", ""),
            },
        })
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        logger.error(f"Get sentiment error: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@sentiment_bp.route('/campaign/<campaign_id>/compare', methods=['GET'])
def compare_campaign_scenarios(campaign_id: str):
    """
    Return per-round sentiment scores for A/B/C on a unified round axis.
    Suitable for an overlay line chart.
    """
    try:
        status = _campaign_manager.get_campaign_status(campaign_id)
        camp = status.get("campaign", {})
        sim_id_a = camp.get("sim_id_a", "")
        sim_id_b = camp.get("sim_id_b", "")
        sim_id_c = camp.get("sim_id_c", "")

        comparison = compare_scenarios(sim_id_a, sim_id_b, sim_id_c)
        return jsonify({"success": True, "comparison": comparison})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        logger.error(f"Compare scenarios error: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@sentiment_bp.route('/sim/<simulation_id>/live', methods=['GET'])
def get_live_sentiment(simulation_id: str):
    """
    Return current sentiment analysis for a single simulation (live/partial data).
    """
    try:
        analyzer = SentimentAnalyzer(simulation_id)
        result = analyzer.analyze_all()
        return jsonify({"success": True, "sentiment": result})
    except Exception as e:
        logger.error(f"Live sentiment error: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500

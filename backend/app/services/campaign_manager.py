"""
Campaign Manager for Product Sentiment Simulator

Orchestrates three parallel simulation scenarios for a single product:
  - Scenario A: Baseline launch (no disruptions)
  - Scenario B: Competitive pressure injected at round 7
  - Scenario C: Crisis stress test injected at round 14

Uses existing SimulationManager + SimulationRunner infrastructure.
"""

import os
import json
import uuid
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..config import Config
from ..models.task import TaskManager, TaskStatus
from ..utils.logger import get_logger
from .simulation_manager import SimulationManager, SimulationStatus
from .simulation_runner import SimulationRunner, RunnerStatus
from .archetype_library import expand_archetypes, save_archetype_map, load_archetype_map, ARCHETYPE_DEFINITIONS
from .seed_template_processor import generate_markdown, generate_simulation_requirement

logger = get_logger('mirofish.campaign_manager')

# Preset event prompts for scenario injection
SCENARIO_B_PROMPTS = {
    "price_drop": (
        "BREAKING NEWS: A major competitor just announced a 30% price cut on their comparable product. "
        "How does this affect your opinion of {product_name}? "
        "Do you think {product_name}'s pricing is still justified? Share your thoughts."
    ),
    "feature_match": (
        "BREAKING NEWS: A competitor just launched a feature that directly matches {product_name}'s key capability. "
        "Does this change how you feel about {product_name}? "
        "What, if anything, still sets {product_name} apart? Share your honest reaction."
    ),
    "comparison_campaign": (
        "A competitor just launched an aggressive comparison campaign claiming their product beats {product_name} "
        "on price, features, and support. Have you seen this? "
        "What do you think — is the comparison fair? Would you reconsider your position on {product_name}?"
    ),
}

SCENARIO_C_PROMPTS = {
    "security_breach": (
        "URGENT: A critical security vulnerability has been reported in {product_name}. "
        "User data may have been exposed. How does this affect your trust in {product_name}? "
        "Would you stop using it? Share your reaction."
    ),
    "harsh_review": (
        "A prominent tech reviewer just published a scathing review of {product_name}, "
        "calling it 'overpriced and underdelivered.' They gave it 2 out of 5 stars. "
        "Does this change your opinion? How do you respond to criticism like this?"
    ),
    "misleading_comparison": (
        "A viral post is circulating claiming {product_name} uses misleading benchmarks in its marketing. "
        "Multiple people are sharing this comparison showing the claims don't hold up. "
        "What do you think about this? Does it affect your view of {product_name}?"
    ),
}

DEFAULT_TOTAL_AGENTS = Config.SENTIMENT_DEFAULT_TOTAL_AGENTS
DEFAULT_MAX_ROUNDS = Config.SENTIMENT_DEFAULT_MAX_ROUNDS
SCENARIO_B_INJECT_ROUND = Config.SENTIMENT_SCENARIO_B_INJECT_ROUND
SCENARIO_C_INJECT_ROUND = Config.SENTIMENT_SCENARIO_C_INJECT_ROUND


class CampaignStatus(str, Enum):
    CREATED = "created"
    PREPARING = "preparing"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CampaignState:
    """State of a three-scenario sentiment campaign."""
    campaign_id: str
    project_id: str
    graph_id: str
    seed_data: Dict[str, Any]

    sim_id_a: str = ""   # Baseline
    sim_id_b: str = ""   # Competitive pressure
    sim_id_c: str = ""   # Crisis

    status: CampaignStatus = CampaignStatus.CREATED

    competitive_event_type: str = "price_drop"
    crisis_event_type: str = "security_breach"

    # Weighted event distributions (values are weights 0-100, normalized internally)
    competitive_event_weights: Dict[str, float] = field(default_factory=lambda: {
        "price_drop": 33.0, "feature_match": 34.0, "comparison_campaign": 33.0
    })
    crisis_event_weights: Dict[str, float] = field(default_factory=lambda: {
        "security_breach": 34.0, "harsh_review": 33.0, "misleading_comparison": 33.0
    })

    scenario_b_injected: bool = False
    scenario_c_injected: bool = False

    total_agents: int = DEFAULT_TOTAL_AGENTS
    prepare_task_id: str = ""
    prepare_progress: int = 0
    prepare_message: str = ""

    # Pending staggered injections: [{round: int, scenario: str, prompt: str, tier: str}]
    pending_injections: List[Dict[str, Any]] = field(default_factory=list)

    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "seed_data": self.seed_data,
            "sim_id_a": self.sim_id_a,
            "sim_id_b": self.sim_id_b,
            "sim_id_c": self.sim_id_c,
            "status": self.status.value,
            "competitive_event_type": self.competitive_event_type,
            "crisis_event_type": self.crisis_event_type,
            "competitive_event_weights": self.competitive_event_weights,
            "crisis_event_weights": self.crisis_event_weights,
            "scenario_b_inject_round": SCENARIO_B_INJECT_ROUND,
            "scenario_c_inject_round": SCENARIO_C_INJECT_ROUND,
            "scenario_b_injected": self.scenario_b_injected,
            "scenario_c_injected": self.scenario_c_injected,
            "total_agents": self.total_agents,
            "prepare_task_id": self.prepare_task_id,
            "prepare_progress": self.prepare_progress,
            "prepare_message": self.prepare_message,
            "pending_injections": self.pending_injections,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class CampaignManager:
    """
    Orchestrates three sentiment simulation scenarios for a product campaign.
    Stores campaign state in uploads/campaigns/{campaign_id}/campaign.json.
    """

    CAMPAIGN_DATA_DIR = os.path.join(
        os.path.dirname(__file__),
        "../../uploads/campaigns"
    )

    def __init__(self):
        os.makedirs(self.CAMPAIGN_DATA_DIR, exist_ok=True)
        self._sim_manager = SimulationManager()
        self._task_manager = TaskManager()
        self._save_lock = threading.Lock()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _campaign_dir(self, campaign_id: str) -> str:
        d = os.path.join(self.CAMPAIGN_DATA_DIR, campaign_id)
        os.makedirs(d, exist_ok=True)
        return d

    def _save(self, state: CampaignState):
        state.updated_at = datetime.now().isoformat()
        path = os.path.join(self._campaign_dir(state.campaign_id), "campaign.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)

    def _load(self, campaign_id: str) -> Optional[CampaignState]:
        path = os.path.join(self._campaign_dir(campaign_id), "campaign.json")
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        return CampaignState(
            campaign_id=d["campaign_id"],
            project_id=d["project_id"],
            graph_id=d["graph_id"],
            seed_data=d.get("seed_data", {}),
            sim_id_a=d.get("sim_id_a", ""),
            sim_id_b=d.get("sim_id_b", ""),
            sim_id_c=d.get("sim_id_c", ""),
            status=CampaignStatus(d.get("status", "created")),
            competitive_event_type=d.get("competitive_event_type", "price_drop"),
            crisis_event_type=d.get("crisis_event_type", "security_breach"),
            competitive_event_weights=d.get("competitive_event_weights", {
                "price_drop": 33.0, "feature_match": 34.0, "comparison_campaign": 33.0
            }),
            crisis_event_weights=d.get("crisis_event_weights", {
                "security_breach": 34.0, "harsh_review": 33.0, "misleading_comparison": 33.0
            }),
            scenario_b_injected=d.get("scenario_b_injected", False),
            scenario_c_injected=d.get("scenario_c_injected", False),
            total_agents=d.get("total_agents", DEFAULT_TOTAL_AGENTS),
            prepare_task_id=d.get("prepare_task_id", ""),
            prepare_progress=d.get("prepare_progress", 0),
            prepare_message=d.get("prepare_message", ""),
            pending_injections=d.get("pending_injections", []),
            error=d.get("error"),
            created_at=d.get("created_at", datetime.now().isoformat()),
            updated_at=d.get("updated_at", datetime.now().isoformat()),
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def create_campaign(
        self,
        project_id: str,
        graph_id: str,
        seed_data: Dict[str, Any],
        competitive_event_type: str = "price_drop",
        crisis_event_type: str = "security_breach",
        competitive_event_weights: Optional[Dict[str, float]] = None,
        crisis_event_weights: Optional[Dict[str, float]] = None,
        total_agents: int = DEFAULT_TOTAL_AGENTS,
        enable_twitter: bool = True,
        enable_reddit: bool = True,
    ) -> CampaignState:
        """
        Create a new campaign and provision three SimulationManager simulations.
        Returns the campaign state with sim IDs assigned.
        """
        campaign_id = f"camp_{uuid.uuid4().hex[:12]}"

        # Create three simulations
        state_a = self._sim_manager.create_simulation(
            project_id=project_id, graph_id=graph_id,
            enable_twitter=enable_twitter, enable_reddit=enable_reddit,
        )
        state_b = self._sim_manager.create_simulation(
            project_id=project_id, graph_id=graph_id,
            enable_twitter=enable_twitter, enable_reddit=enable_reddit,
        )
        state_c = self._sim_manager.create_simulation(
            project_id=project_id, graph_id=graph_id,
            enable_twitter=enable_twitter, enable_reddit=enable_reddit,
        )

        campaign = CampaignState(
            campaign_id=campaign_id,
            project_id=project_id,
            graph_id=graph_id,
            seed_data=seed_data,
            sim_id_a=state_a.simulation_id,
            sim_id_b=state_b.simulation_id,
            sim_id_c=state_c.simulation_id,
            status=CampaignStatus.CREATED,
            competitive_event_type=competitive_event_type,
            crisis_event_type=crisis_event_type,
            competitive_event_weights=competitive_event_weights or {
                "price_drop": 33.0, "feature_match": 34.0, "comparison_campaign": 33.0
            },
            crisis_event_weights=crisis_event_weights or {
                "security_breach": 34.0, "harsh_review": 33.0, "misleading_comparison": 33.0
            },
            total_agents=total_agents,
        )
        self._save(campaign)
        logger.info(
            f"Campaign created: {campaign_id} "
            f"[A={state_a.simulation_id}, B={state_b.simulation_id}, C={state_c.simulation_id}]"
        )
        return campaign

    def start_prepare(self, campaign_id: str) -> Dict[str, Any]:
        """Start asynchronous scenario preparation and return the task metadata."""
        campaign = self._load(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign not found: {campaign_id}")

        existing_task_id = campaign.prepare_task_id
        existing_task = self._task_manager.get_task(existing_task_id) if existing_task_id else None
        if campaign.status == CampaignStatus.PREPARING and existing_task_id:
            return {"campaign": campaign, "task": existing_task.to_dict() if existing_task else None}
        if campaign.status in (CampaignStatus.READY, CampaignStatus.RUNNING, CampaignStatus.COMPLETED) and existing_task_id:
            return {"campaign": campaign, "task": existing_task.to_dict() if existing_task else None}
        if campaign.status in (CampaignStatus.READY, CampaignStatus.RUNNING, CampaignStatus.COMPLETED):
            return self.get_prepare_status(campaign_id)

        task_id = self._task_manager.create_task(
            task_type="campaign_prepare",
            metadata={"campaign_id": campaign_id},
        )

        campaign.status = CampaignStatus.PREPARING
        campaign.prepare_task_id = task_id
        campaign.prepare_progress = 0
        campaign.prepare_message = "Preparing scenario inputs"
        campaign.error = None
        self._save(campaign)

        thread = threading.Thread(
            target=self._prepare_campaign_background,
            args=(campaign_id, task_id),
            daemon=True,
        )
        thread.start()

        task = self._task_manager.get_task(task_id)
        return {"campaign": campaign, "task": task.to_dict() if task else None}

    def get_prepare_status(self, campaign_id: str, task_id: Optional[str] = None) -> Dict[str, Any]:
        """Return persisted preparation progress for a campaign."""
        campaign = self._load(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign not found: {campaign_id}")

        effective_task_id = task_id or campaign.prepare_task_id
        task = self._task_manager.get_task(effective_task_id) if effective_task_id else None
        if task:
            return {"campaign": campaign.to_dict(), "task": task.to_dict()}

        synthetic_status = (
            TaskStatus.COMPLETED.value
            if campaign.status in (CampaignStatus.READY, CampaignStatus.RUNNING, CampaignStatus.COMPLETED)
            else TaskStatus.FAILED.value
            if campaign.status == CampaignStatus.FAILED
            else TaskStatus.PENDING.value
        )
        return {
            "campaign": campaign.to_dict(),
            "task": {
                "task_id": effective_task_id,
                "task_type": "campaign_prepare",
                "status": synthetic_status,
                "progress": campaign.prepare_progress,
                "message": campaign.prepare_message,
                "result": {"campaign": campaign.to_dict()} if synthetic_status == TaskStatus.COMPLETED.value else None,
                "error": campaign.error,
                "metadata": {"campaign_id": campaign_id},
                "progress_detail": {},
                "created_at": campaign.created_at,
                "updated_at": campaign.updated_at,
            },
        }

    def prepare_all(
        self,
        campaign_id: str,
        progress_callback: Optional[Callable] = None,
    ) -> CampaignState:
        """
        Prepare all three simulations using archetype profiles (no Zep entity reading).
        Runs sequentially for all three scenarios — they share the same profiles.
        """
        campaign = self._load(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign not found: {campaign_id}")

        campaign.status = CampaignStatus.PREPARING
        campaign.prepare_progress = 0
        campaign.prepare_message = "Preparing scenario inputs"
        campaign.error = None
        self._save(campaign)

        seed_data = campaign.seed_data
        product_name = seed_data.get("product_name", "the product")
        product_category = seed_data.get("product_category", "software")
        document_text = generate_markdown(seed_data)
        simulation_requirement = generate_simulation_requirement(seed_data)

        # Generate archetype profiles once — same pool for all scenarios
        if progress_callback:
            progress_callback("archetypes", 0, f"Generating {campaign.total_agents} archetype agents...")

        profiles, archetype_map = expand_archetypes(
            total_agents=campaign.total_agents,
            product_name=product_name,
            product_category=product_category,
            seed_data=seed_data,
        )

        if progress_callback:
            progress_callback("archetypes", 100, f"Generated {len(profiles)} agents")

        # Prepare each simulation
        for i, sim_id in enumerate(
            [campaign.sim_id_a, campaign.sim_id_b, campaign.sim_id_c], start=1
        ):
            scenario_label = ["A (Baseline)", "B (Competitive)", "C (Crisis)"][i - 1]
            progress_pct = 15 + int(((i - 1) / 3) * 75)
            if progress_callback:
                progress_callback(
                    "preparing",
                    progress_pct,
                    f"Preparing Scenario {scenario_label}...",
                )
            self._sim_manager.prepare_simulation(
                simulation_id=sim_id,
                simulation_requirement=simulation_requirement,
                document_text=document_text,
                archetype_profiles=profiles,
                archetype_map=archetype_map,
                progress_callback=None,  # suppress sub-progress to avoid noise
            )

        campaign.status = CampaignStatus.READY
        campaign.prepare_progress = 100
        campaign.prepare_message = "Scenario preparation complete"
        self._save(campaign)

        if progress_callback:
            progress_callback("ready", 100, "All scenarios prepared and ready to run")

        logger.info(f"Campaign {campaign_id} prepared — 3 scenarios ready")
        return campaign

    def _prepare_campaign_background(self, campaign_id: str, task_id: str):
        """Run campaign preparation in a background thread and persist progress."""
        self._task_manager.update_task(
            task_id,
            status=TaskStatus.PROCESSING,
            progress=0,
            message="Preparing scenario inputs",
            progress_detail={"stage": "initializing"},
        )

        def progress_callback(stage: str, pct: int, msg: str, **kwargs):
            self._task_manager.update_task(
                task_id,
                status=TaskStatus.PROCESSING,
                progress=pct,
                message=msg,
                progress_detail={"stage": stage, **kwargs},
            )
            with self._save_lock:
                state = self._load(campaign_id)
                if state:
                    state.status = CampaignStatus.READY if stage == "ready" else CampaignStatus.PREPARING
                    state.prepare_progress = pct
                    state.prepare_message = msg
                    self._save(state)

        try:
            campaign = self.prepare_all(campaign_id=campaign_id, progress_callback=progress_callback)
            self._task_manager.complete_task(
                task_id,
                result={"campaign": campaign.to_dict()},
                message="Scenario preparation complete",
            )
        except Exception as exc:
            error_message = str(exc)
            self._task_manager.fail_task(task_id, error_message, message="Scenario preparation failed")
            with self._save_lock:
                state = self._load(campaign_id)
                if state:
                    state.status = CampaignStatus.FAILED
                    state.prepare_message = error_message
                    state.error = error_message
                    self._save(state)
            logger.error("Campaign %s preparation failed: %s", campaign_id, error_message)

    def start_campaign(
        self,
        campaign_id: str,
        platform: str = "parallel",
        max_rounds: int = DEFAULT_MAX_ROUNDS,
    ) -> CampaignState:
        """
        Start the campaign by running all three scenarios in parallel in a background thread.
        Scenario B gets a competitive event injected at round 7.
        Scenario C gets a crisis event injected at round 14.
        """
        campaign = self._load(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign not found: {campaign_id}")
        if campaign.status not in (CampaignStatus.READY, CampaignStatus.FAILED):
            raise ValueError(f"Campaign is not ready to start: {campaign.status}")

        campaign.status = CampaignStatus.RUNNING
        campaign.error = None
        self._save(campaign)

        thread = threading.Thread(
            target=self._run_campaign_background,
            args=(campaign_id, platform, max_rounds),
            daemon=True,
        )
        thread.start()
        logger.info(f"Campaign {campaign_id} started in background thread")
        return campaign

    def inject_scenario_event(
        self,
        campaign_id: str,
        scenario: str,
        event_type: Optional[str] = None,
        custom_prompt: Optional[str] = None,
        timeout: float = 60.0,
    ) -> Dict[str, Any]:
        """
        Manually inject a God's Eye event into a running scenario simulation.

        Args:
            scenario: "b" or "c"
            event_type: key from SCENARIO_B_PROMPTS or SCENARIO_C_PROMPTS (optional if custom_prompt given)
            custom_prompt: override prompt (optional)
            timeout: IPC timeout in seconds
        """
        campaign = self._load(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign not found: {campaign_id}")

        sim_id = campaign.sim_id_b if scenario.lower() == "b" else campaign.sim_id_c
        product_name = campaign.seed_data.get("product_name", "the product")

        if custom_prompt:
            prompt = custom_prompt
        elif scenario.lower() == "b":
            template = SCENARIO_B_PROMPTS.get(
                event_type or campaign.competitive_event_type,
                SCENARIO_B_PROMPTS["price_drop"]
            )
            prompt = self._format_event_prompt(template, campaign.seed_data)
        else:
            template = SCENARIO_C_PROMPTS.get(
                event_type or campaign.crisis_event_type,
                SCENARIO_C_PROMPTS["security_breach"]
            )
            prompt = self._format_event_prompt(template, campaign.seed_data)

        logger.info(
            f"Injecting event into Scenario {scenario.upper()} "
            f"(sim={sim_id}): {prompt[:80]}..."
        )

        try:
            result = SimulationRunner.interview_all_agents(
                simulation_id=sim_id,
                prompt=prompt,
                timeout=timeout,
            )
            if scenario.lower() == "b":
                campaign.scenario_b_injected = True
            else:
                campaign.scenario_c_injected = True
            self._save(campaign)
            return result
        except Exception as e:
            logger.error(f"Event injection failed for Scenario {scenario}: {e}")
            raise

    def get_campaign_status(self, campaign_id: str) -> Dict[str, Any]:
        """
        Return aggregated status of all three simulations + campaign state.
        """
        campaign = self._load(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign not found: {campaign_id}")

        def _run_state(sim_id: str) -> Dict[str, Any]:
            try:
                rs = SimulationRunner.get_run_state(sim_id)
                if rs:
                    return {
                        "runner_status": rs.runner_status.value,
                        "current_round": rs.current_round,
                        "total_rounds": rs.total_rounds,
                        "twitter_status": rs.twitter_status,
                        "reddit_status": rs.reddit_status,
                        "recent_actions_count": len(rs.recent_actions),
                        "recent_actions": [action.to_dict() for action in rs.recent_actions[:12]],
                    }
            except Exception:
                pass
            # Fall back to SimulationManager state
            try:
                sm = SimulationManager()
                ss = sm.get_simulation(sim_id)
                if ss:
                    return {"runner_status": ss.status.value}
            except Exception:
                pass
            return {"runner_status": "unknown"}

        return {
            "campaign": campaign.to_dict(),
            "scenario_a": _run_state(campaign.sim_id_a),
            "scenario_b": _run_state(campaign.sim_id_b),
            "scenario_c": _run_state(campaign.sim_id_c),
        }

    def list_campaigns(self) -> List[Dict[str, Any]]:
        """List all campaigns."""
        campaigns = []
        if not os.path.exists(self.CAMPAIGN_DATA_DIR):
            return campaigns
        for camp_id in os.listdir(self.CAMPAIGN_DATA_DIR):
            if camp_id.startswith("."):
                continue
            state = self._load(camp_id)
            if state:
                campaigns.append(state.to_dict())
        return campaigns

    def _build_weighted_injections(
        self,
        prompts_dict: Dict[str, str],
        weights: Dict[str, float],
        seed_data: Dict[str, Any],
        scenario: str,
        sim_id: str,
        base_round: int,
    ) -> List[Dict[str, Any]]:
        """
        Build tiered injection list from weighted event types.
        Sorts event types by weight descending and assigns each to a tier.
        Highest-weight event hits high-activity (most influential) agents first.
        """
        # Normalize weights
        total = sum(weights.values())
        if total <= 0:
            # Fallback: equal weights
            weights = {k: 1.0 for k in prompts_dict}
            total = len(weights)
        normalized = {k: v / total for k, v in weights.items()}

        # Sort by weight descending, skip zero-weight events
        sorted_events = sorted(
            [(k, w) for k, w in normalized.items() if w > 0],
            key=lambda x: x[1],
            reverse=True,
        )

        tiers = [
            {"tier": "high", "activity_min": 0.7, "round_offset": 0},
            {"tier": "mid",  "activity_min": 0.4, "activity_max": 0.7, "round_offset": 1},
            {"tier": "low",  "activity_max": 0.4, "round_offset": 2},
        ]

        injections = []
        for i, (event_type, weight) in enumerate(sorted_events[:3]):
            tier_config = tiers[i]
            template = prompts_dict.get(event_type, list(prompts_dict.values())[0])
            prompt = self._format_event_prompt(template, seed_data)

            # Add weight context to prompt so agents understand relative significance
            pct = round(weight * 100)
            if i == 0:
                prefix = f"[Primary market signal — {pct}% probability] "
            elif i == 1:
                prefix = f"[Secondary market signal — {pct}% probability] "
            else:
                prefix = f"[Background market signal — {pct}% probability] "

            inj = {
                "round": base_round + tier_config["round_offset"],
                "sim_id": sim_id,
                "scenario": scenario,
                "prompt": prefix + prompt,
                "tier": tier_config["tier"],
                "event_type": event_type,
                "weight": weight,
                "done": False,
            }
            if "activity_min" in tier_config:
                inj["activity_min"] = tier_config["activity_min"]
            if "activity_max" in tier_config:
                inj["activity_max"] = tier_config["activity_max"]
            injections.append(inj)

        return injections

    def _schedule_staggered_injection(
        self,
        campaign: CampaignState,
        scenario: str,
        base_round: int,
        sim_id: str,
    ):
        """
        Schedule tiered event injection instead of broadcasting to all agents at once.
        High-activity archetypes hear news first, low-activity hear it 2 rounds later.
        """
        campaign.pending_injections = [
            injection
            for injection in campaign.pending_injections
            if injection.get("scenario") != scenario or injection.get("done")
        ]
        if scenario == "b":
            new_injections = self._build_weighted_injections(
                prompts_dict=SCENARIO_B_PROMPTS,
                weights=campaign.competitive_event_weights,
                seed_data=campaign.seed_data,
                scenario=scenario,
                sim_id=sim_id,
                base_round=base_round,
            )
        else:
            new_injections = self._build_weighted_injections(
                prompts_dict=SCENARIO_C_PROMPTS,
                weights=campaign.crisis_event_weights,
                seed_data=campaign.seed_data,
                scenario=scenario,
                sim_id=sim_id,
                base_round=base_round,
            )
        campaign.pending_injections.extend(new_injections)
        self._save(campaign)

    def _execute_pending_injections(
        self,
        campaign: CampaignState,
        sim_id: str,
        current_round: int,
    ):
        """Execute any pending staggered injections that are due at the current round."""
        executed_any = False
        executed_scenarios = set()
        for inj in campaign.pending_injections:
            if inj["done"] or inj["sim_id"] != sim_id or inj["round"] > current_round:
                continue

            tier = inj["tier"]
            prompt = inj["prompt"]

            logger.info(
                f"Executing staggered injection tier={tier} round={current_round} "
                f"sim={sim_id}: {prompt[:60]}..."
            )
            try:
                SimulationRunner.interview_all_agents(
                    simulation_id=sim_id,
                    prompt=prompt,
                    timeout=30.0,
                )
            except Exception as e:
                logger.warning(f"Staggered injection tier={tier} failed (non-fatal): {e}")

            inj["done"] = True
            executed_any = True
            executed_scenarios.add(inj.get("scenario"))

        if executed_any:
            for scenario in executed_scenarios:
                if not scenario:
                    continue
                if all(i["done"] for i in campaign.pending_injections if i.get("scenario") == scenario):
                    if scenario == "b":
                        campaign.scenario_b_injected = True
                    elif scenario == "c":
                        campaign.scenario_c_injected = True
            self._save(campaign)

    def _format_event_prompt(self, template: str, seed_data: Dict[str, Any]) -> str:
        """Format event prompt template with product-specific seed data."""
        product_name = seed_data.get("product_name", "the product")

        # Extract competitor info
        competitors = seed_data.get("competitors", [])
        competitor_name = competitors[0].get("name", "a major competitor") if competitors else "a major competitor"

        # Extract pricing info
        pricing = seed_data.get("pricing_tiers", [])
        pricing_tier = pricing[0].get("name", "standard plan") if pricing else "standard plan"
        pricing_amount = pricing[0].get("price", "their current price") if pricing else "their current price"

        # Extract feature info
        features = seed_data.get("core_features", [])
        feature_1 = features[0].get("name", "core functionality") if features else "core functionality"

        # Extract risk info
        risks = seed_data.get("known_risks", [])
        risk_1 = risks[0] if risks else "potential issues"

        try:
            return template.format(
                product_name=product_name,
                competitor_name=competitor_name,
                pricing_tier=pricing_tier,
                pricing_amount=pricing_amount,
                feature_1=feature_1,
                risk_1=risk_1,
            )
        except (KeyError, IndexError):
            # Fall back to basic formatting if template has unexpected placeholders
            return template.format(product_name=product_name)

    # ── Background Worker ─────────────────────────────────────────────────────

    def _run_scenario(
        self,
        campaign_id: str,
        label: str,
        sim_id: str,
        inject_round: Optional[int],
        scenario_key: Optional[str],
        platform: str,
        max_rounds: int,
    ) -> str:
        """
        Run a single scenario to completion with staggered event injection.
        Returns the final status string.
        """
        logger.info(f"Campaign {campaign_id}: Starting Scenario {label} ({sim_id})")
        try:
            SimulationRunner.start_simulation(
                simulation_id=sim_id,
                platform=platform,
                max_rounds=max_rounds,
            )
        except Exception as e:
            logger.error(f"Failed to start Scenario {label}: {e}")
            raise

        injection_scheduled = False
        poll_interval = 10

        while True:
            time.sleep(poll_interval)
            try:
                rs = SimulationRunner.get_run_state(sim_id)
                if not rs:
                    break

                # Schedule staggered injection at the configured round
                if (
                    inject_round
                    and not injection_scheduled
                    and rs.current_round >= inject_round
                    and rs.runner_status == RunnerStatus.RUNNING
                ):
                    logger.info(
                        f"Campaign {campaign_id}: Scheduling staggered Scenario {label} event "
                        f"starting at round {rs.current_round}"
                    )
                    with self._save_lock:
                        campaign = self._load(campaign_id)
                        self._schedule_staggered_injection(
                            campaign=campaign,
                            scenario=scenario_key,
                            base_round=rs.current_round,
                            sim_id=sim_id,
                        )
                    injection_scheduled = True

                # Execute any pending staggered injections due this round
                if injection_scheduled:
                    with self._save_lock:
                        campaign = self._load(campaign_id)
                        self._execute_pending_injections(
                            campaign=campaign,
                            sim_id=sim_id,
                            current_round=rs.current_round,
                        )

                if rs.runner_status in (
                    RunnerStatus.COMPLETED,
                    RunnerStatus.STOPPED,
                    RunnerStatus.FAILED,
                ):
                    logger.info(
                        f"Campaign {campaign_id}: Scenario {label} finished "
                        f"with status {rs.runner_status.value}"
                    )
                    return rs.runner_status.value

            except Exception as e:
                logger.warning(
                    f"Campaign {campaign_id}: Error monitoring Scenario {label}: {e}"
                )
                return "error"

        return "unknown"

    def _run_campaign_background(
        self,
        campaign_id: str,
        platform: str,
        max_rounds: int,
    ):
        """
        Run all 3 scenarios in parallel using ThreadPoolExecutor.
        Each scenario gets its own monitoring thread with staggered event injection.
        """
        campaign = self._load(campaign_id)
        if not campaign:
            logger.error(f"Campaign not found in background thread: {campaign_id}")
            return

        scenarios = [
            ("A", campaign.sim_id_a, None, None),
            ("B", campaign.sim_id_b, SCENARIO_B_INJECT_ROUND, "b"),
            ("C", campaign.sim_id_c, SCENARIO_C_INJECT_ROUND, "c"),
        ]

        results = {}
        with ThreadPoolExecutor(max_workers=3, thread_name_prefix="scenario") as executor:
            futures = {
                executor.submit(
                    self._run_scenario,
                    campaign_id, label, sim_id, inject_round, scenario_key,
                    platform, max_rounds,
                ): label
                for label, sim_id, inject_round, scenario_key in scenarios
            }
            for future in as_completed(futures):
                label = futures[future]
                try:
                    results[label] = future.result()
                except Exception as e:
                    logger.error(f"Scenario {label} failed: {e}")
                    results[label] = "failed"

        # All scenarios done
        with self._save_lock:
            campaign = self._load(campaign_id)
            has_failure = any(r in {"failed", "error", "unknown"} for r in results.values())
            campaign.status = CampaignStatus.FAILED if has_failure else CampaignStatus.COMPLETED
            if has_failure:
                failed_labels = [l for l, r in results.items() if r in {"failed", "error", "unknown"}]
                campaign.error = f"Scenarios failed: {', '.join(failed_labels)}"
            self._save(campaign)
        logger.info(f"Campaign {campaign_id} completed — results: {results}")

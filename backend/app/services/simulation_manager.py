"""
OASIS simulation manager
Manages parallel simulation across Twitter and Reddit platforms
Uses preset scripts + LLM-based intelligent config parameter generation
"""

import os
import json
import shutil
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..config import Config
from ..utils.logger import get_logger
from .zep_entity_reader import ZepEntityReader, FilteredEntities
from .oasis_profile_generator import OasisProfileGenerator, OasisAgentProfile
from .simulation_config_generator import SimulationConfigGenerator, SimulationParameters, AgentActivityConfig

logger = get_logger('mirofish.simulation')


class SimulationStatus(str, Enum):
    """Simulation status"""
    CREATED = "created"
    PREPARING = "preparing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"      # Simulation was manually stopped
    COMPLETED = "completed"  # Simulation completed naturally
    FAILED = "failed"


class PlatformType(str, Enum):
    """Platform type"""
    TWITTER = "twitter"
    REDDIT = "reddit"


@dataclass
class SimulationState:
    """Simulation state"""
    simulation_id: str
    project_id: str
    graph_id: str

    # Platform enabled status
    enable_twitter: bool = True
    enable_reddit: bool = True

    # Status
    status: SimulationStatus = SimulationStatus.CREATED

    # Preparation phase data
    entities_count: int = 0
    profiles_count: int = 0
    entity_types: List[str] = field(default_factory=list)

    # Config generation info
    config_generated: bool = False
    config_reasoning: str = ""

    # Runtime data
    current_round: int = 0
    twitter_status: str = "not_started"
    reddit_status: str = "not_started"

    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Error information
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Full state dictionary (for internal use)"""
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "enable_twitter": self.enable_twitter,
            "enable_reddit": self.enable_reddit,
            "status": self.status.value,
            "entities_count": self.entities_count,
            "profiles_count": self.profiles_count,
            "entity_types": self.entity_types,
            "config_generated": self.config_generated,
            "config_reasoning": self.config_reasoning,
            "current_round": self.current_round,
            "twitter_status": self.twitter_status,
            "reddit_status": self.reddit_status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error": self.error,
        }

    def to_simple_dict(self) -> Dict[str, Any]:
        """Simplified state dictionary (for API responses)"""
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "status": self.status.value,
            "entities_count": self.entities_count,
            "profiles_count": self.profiles_count,
            "entity_types": self.entity_types,
            "config_generated": self.config_generated,
            "error": self.error,
        }


class SimulationManager:
    """
    Simulation manager

    Core functionality:
    1. Read and filter entities from Zep graph
    2. Generate OASIS Agent Profiles
    3. Use LLM to intelligently generate simulation config parameters
    4. Prepare all files needed by preset scripts
    """

    # Simulation data storage directory
    SIMULATION_DATA_DIR = os.path.join(
        os.path.dirname(__file__),
        '../../uploads/simulations'
    )

    def __init__(self):
        # Ensure the directory exists
        os.makedirs(self.SIMULATION_DATA_DIR, exist_ok=True)

        # In-memory simulation state cache
        self._simulations: Dict[str, SimulationState] = {}

    def _get_simulation_dir(self, simulation_id: str) -> str:
        """Get the simulation data directory"""
        sim_dir = os.path.join(self.SIMULATION_DATA_DIR, simulation_id)
        os.makedirs(sim_dir, exist_ok=True)
        return sim_dir

    def _save_simulation_state(self, state: SimulationState):
        """Save simulation state to file"""
        sim_dir = self._get_simulation_dir(state.simulation_id)
        state_file = os.path.join(sim_dir, "state.json")

        state.updated_at = datetime.now().isoformat()

        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)

        self._simulations[state.simulation_id] = state

    def _load_simulation_state(self, simulation_id: str) -> Optional[SimulationState]:
        """Load simulation state from file"""
        if simulation_id in self._simulations:
            return self._simulations[simulation_id]

        sim_dir = self._get_simulation_dir(simulation_id)
        state_file = os.path.join(sim_dir, "state.json")

        if not os.path.exists(state_file):
            return None

        with open(state_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        state = SimulationState(
            simulation_id=simulation_id,
            project_id=data.get("project_id", ""),
            graph_id=data.get("graph_id", ""),
            enable_twitter=data.get("enable_twitter", True),
            enable_reddit=data.get("enable_reddit", True),
            status=SimulationStatus(data.get("status", "created")),
            entities_count=data.get("entities_count", 0),
            profiles_count=data.get("profiles_count", 0),
            entity_types=data.get("entity_types", []),
            config_generated=data.get("config_generated", False),
            config_reasoning=data.get("config_reasoning", ""),
            current_round=data.get("current_round", 0),
            twitter_status=data.get("twitter_status", "not_started"),
            reddit_status=data.get("reddit_status", "not_started"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            error=data.get("error"),
        )

        self._simulations[simulation_id] = state
        return state

    def create_simulation(
        self,
        project_id: str,
        graph_id: str,
        enable_twitter: bool = True,
        enable_reddit: bool = True,
    ) -> SimulationState:
        """
        Create a new simulation

        Args:
            project_id: Project ID
            graph_id: Zep graph ID
            enable_twitter: Whether to enable Twitter simulation
            enable_reddit: Whether to enable Reddit simulation

        Returns:
            SimulationState
        """
        import uuid
        simulation_id = f"sim_{uuid.uuid4().hex[:12]}"

        state = SimulationState(
            simulation_id=simulation_id,
            project_id=project_id,
            graph_id=graph_id,
            enable_twitter=enable_twitter,
            enable_reddit=enable_reddit,
            status=SimulationStatus.CREATED,
        )

        self._save_simulation_state(state)
        logger.info(f"Created simulation: {simulation_id}, project={project_id}, graph={graph_id}")

        return state

    @staticmethod
    def _build_archetype_agent_configs(archetype_map: List[Dict[str, Any]]) -> List[AgentActivityConfig]:
        """Build the agent-config pool for an archetype-based campaign.

        Used both as `poster_agent_pool` (so the config generator's event-config
        LLM and initial-post assignment match against real archetype types
        instead of an empty entity list) and as the final `agent_configs`
        written to simulation_config.json, so the two stay consistent.
        """
        from .archetype_library import ARCHETYPE_DEFINITIONS

        configs = []
        for entry in archetype_map:
            arch_key = entry.get('archetype', 'casual_browser')
            defn = ARCHETYPE_DEFINITIONS.get(arch_key, {})
            al = defn.get('activity_level', 0.5)
            configs.append(AgentActivityConfig(
                agent_id=entry['agent_id'],
                entity_uuid=f"archetype_{arch_key}_{entry['agent_id']}",
                entity_name=entry.get('username', ''),
                entity_type=arch_key,
                activity_level=al,
                posts_per_hour=round(al * 0.8, 2),
                comments_per_hour=round(al * 1.5, 2),
                active_hours=list(range(8, 24)),
                response_delay_min=5,
                response_delay_max=60,
                sentiment_bias=defn.get('sentiment_bias', 0.0),
                stance="neutral",
                influence_weight=defn.get('influence_weight', 1.0),
            ))
        return configs

    def prepare_simulation(
        self,
        simulation_id: str,
        simulation_requirement: str,
        document_text: str,
        defined_entity_types: Optional[List[str]] = None,
        use_llm_for_profiles: bool = True,
        progress_callback: Optional[callable] = None,
        parallel_profile_count: int = 3,
        archetype_profiles: Optional[List] = None,
        archetype_map: Optional[List] = None,
    ) -> SimulationState:
        """
        Prepare the simulation environment (fully automated)

        Steps:
        1. Read and filter entities from Zep graph
        2. Generate an OASIS Agent Profile for each entity (optional LLM enhancement, supports parallel)
        3. Use LLM to intelligently generate simulation config parameters (time, activity, post frequency, etc.)
        4. Save config files and Profile files
        5. Copy preset scripts to the simulation directory

        Args:
            simulation_id: Simulation ID
            simulation_requirement: Simulation requirement description (used for LLM config generation)
            document_text: Original document content (used for LLM background understanding)
            defined_entity_types: Predefined entity types (optional)
            use_llm_for_profiles: Whether to use LLM to generate detailed personas
            progress_callback: Progress callback function (stage, progress, message)
            parallel_profile_count: Number of profiles to generate in parallel, default 3

        Returns:
            SimulationState
        """
        state = self._load_simulation_state(simulation_id)
        if not state:
            raise ValueError(f"Simulation does not exist: {simulation_id}")

        try:
            state.status = SimulationStatus.PREPARING
            self._save_simulation_state(state)

            sim_dir = self._get_simulation_dir(simulation_id)

            # ========== Archetype bypass: skip Zep entity reading + LLM profile generation ==========
            if archetype_profiles is not None:
                if progress_callback:
                    progress_callback(
                        "generating_profiles", 0,
                        f"Generating {len(archetype_profiles)} agents using preset archetype library...",
                        current=0,
                        total=len(archetype_profiles)
                    )

                profiles = archetype_profiles
                state.entities_count = len(profiles)
                state.entity_types = list({
                    p.source_entity_type for p in profiles if p.source_entity_type
                })

                # Save archetype_map if provided
                if archetype_map is not None:
                    from .archetype_library import save_archetype_map
                    save_archetype_map(sim_dir, archetype_map)

                generator = OasisProfileGenerator(graph_id=state.graph_id)
                if state.enable_reddit:
                    generator.save_profiles(
                        profiles=profiles,
                        file_path=os.path.join(sim_dir, "reddit_profiles.json"),
                        platform="reddit"
                    )
                if state.enable_twitter:
                    generator.save_profiles(
                        profiles=profiles,
                        file_path=os.path.join(sim_dir, "twitter_profiles.csv"),
                        platform="twitter"
                    )

                state.profiles_count = len(profiles)
                if progress_callback:
                    progress_callback(
                        "generating_profiles", 100,
                        f"Done, {len(profiles)} profiles generated",
                        current=len(profiles),
                        total=len(profiles)
                    )

                # Use empty entity list for config generation (seed context provides background)
                entities_for_config = []

            else:
                # ========== Stage 1: Read and filter entities ==========
                if progress_callback:
                    progress_callback("reading", 0, "Connecting to Zep graph...")

                reader = ZepEntityReader()

                if progress_callback:
                    progress_callback("reading", 30, "Reading node data...")

                filtered = reader.filter_defined_entities(
                    graph_id=state.graph_id,
                    defined_entity_types=defined_entity_types,
                    enrich_with_edges=True
                )

                state.entities_count = filtered.filtered_count
                state.entity_types = list(filtered.entity_types)

                if progress_callback:
                    progress_callback(
                        "reading", 100,
                        f"Done, {filtered.filtered_count} entities found",
                        current=filtered.filtered_count,
                        total=filtered.filtered_count
                    )

                if filtered.filtered_count == 0:
                    state.status = SimulationStatus.FAILED
                    state.error = "No matching entities found. Please check that the graph was built correctly."
                    self._save_simulation_state(state)
                    return state

                # ========== Stage 2: Generate Agent Profiles ==========
                total_entities = len(filtered.entities)

                if progress_callback:
                    progress_callback(
                        "generating_profiles", 0,
                        "Starting generation...",
                        current=0,
                        total=total_entities
                    )

                # Pass graph_id to enable Zep retrieval for richer context
                generator = OasisProfileGenerator(graph_id=state.graph_id)

                def profile_progress(current, total, msg):
                    if progress_callback:
                        progress_callback(
                            "generating_profiles",
                            int(current / total * 100),
                            msg,
                            current=current,
                            total=total,
                            item_name=msg
                        )

                # Set realtime save path (prefer Reddit JSON format)
                realtime_output_path = None
                realtime_platform = "reddit"
                if state.enable_reddit:
                    realtime_output_path = os.path.join(sim_dir, "reddit_profiles.json")
                    realtime_platform = "reddit"
                elif state.enable_twitter:
                    realtime_output_path = os.path.join(sim_dir, "twitter_profiles.csv")
                    realtime_platform = "twitter"

                profiles = generator.generate_profiles_from_entities(
                    entities=filtered.entities,
                    use_llm=use_llm_for_profiles,
                    progress_callback=profile_progress,
                    graph_id=state.graph_id,  # Pass graph_id for Zep retrieval
                    parallel_count=parallel_profile_count,  # Number of parallel generations
                    realtime_output_path=realtime_output_path,  # Realtime save path
                    output_platform=realtime_platform  # Output format
                )

                state.profiles_count = len(profiles)

                # Save Profile files (note: Twitter uses CSV format, Reddit uses JSON format)
                # Reddit is already saved incrementally during generation; save again to ensure completeness
                if progress_callback:
                    progress_callback(
                        "generating_profiles", 95,
                        "Saving profile files...",
                        current=total_entities,
                        total=total_entities
                    )

                if state.enable_reddit:
                    generator.save_profiles(
                        profiles=profiles,
                        file_path=os.path.join(sim_dir, "reddit_profiles.json"),
                        platform="reddit"
                    )

                if state.enable_twitter:
                    # Twitter uses CSV format — this is an OASIS requirement
                    generator.save_profiles(
                        profiles=profiles,
                        file_path=os.path.join(sim_dir, "twitter_profiles.csv"),
                        platform="twitter"
                    )

                if progress_callback:
                    progress_callback(
                        "generating_profiles", 100,
                        f"Done, {len(profiles)} profiles generated",
                        current=len(profiles),
                        total=len(profiles)
                    )

                entities_for_config = filtered.entities

            # ========== Stage 3: LLM intelligent simulation config generation ==========
            if progress_callback:
                progress_callback(
                    "generating_config", 0,
                    "Analyzing simulation requirements...",
                    current=0,
                    total=3
                )

            config_generator = SimulationConfigGenerator()

            if progress_callback:
                progress_callback(
                    "generating_config", 30,
                    "Calling LLM to generate config...",
                    current=1,
                    total=3
                )

            # When using archetype profiles, build the real agent pool up front
            # and hand it to the config generator as `poster_agent_pool`. With
            # entities=[] the generator otherwise has nothing to match a
            # generated initial-post poster_type against, so every post fell
            # back to "highest influence agent" regardless of poster_type.
            poster_agent_pool = None
            if archetype_profiles is not None and archetype_map is not None:
                poster_agent_pool = self._build_archetype_agent_configs(archetype_map)

            sim_params = config_generator.generate_config(
                simulation_id=simulation_id,
                project_id=state.project_id,
                graph_id=state.graph_id,
                simulation_requirement=simulation_requirement,
                document_text=document_text,
                entities=entities_for_config,
                enable_twitter=state.enable_twitter,
                enable_reddit=state.enable_reddit,
                poster_agent_pool=poster_agent_pool,
            )

            if progress_callback:
                progress_callback(
                    "generating_config", 70,
                    "Saving config files...",
                    current=2,
                    total=3
                )

            # Save config file
            config_path = os.path.join(sim_dir, "simulation_config.json")
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(sim_params.to_json())

            # When using archetype profiles, patch agents_per_hour and agent_configs
            # because the config generator received 0 entities and defaults to minimums.
            # Reuses the same poster_agent_pool passed into generate_config() above,
            # so the initial-post poster assignments made against that pool stay
            # consistent with the agent_configs actually written to disk.
            if archetype_profiles is not None and archetype_map is not None:
                from dataclasses import asdict
                n = len(archetype_profiles)
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                config_data['time_config']['agents_per_hour_min'] = max(5, n // 10)
                config_data['time_config']['agents_per_hour_max'] = max(20, n // 3)
                agent_configs = [asdict(a) for a in poster_agent_pool]
                config_data['agent_configs'] = agent_configs
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, ensure_ascii=False, indent=2)
                logger.info(
                    f"Patched archetype config: agents_per_hour={config_data['time_config']['agents_per_hour_min']}"
                    f"-{config_data['time_config']['agents_per_hour_max']}, agent_configs={len(agent_configs)}"
                )

            state.config_generated = True
            state.config_reasoning = sim_params.generation_reasoning

            if progress_callback:
                progress_callback(
                    "generating_config", 100,
                    "Config generation complete",
                    current=3,
                    total=3
                )

            # Note: run scripts remain in backend/scripts/ and are no longer copied to the simulation directory.
            # When starting a simulation, simulation_runner will run scripts from the scripts/ directory.

            # Update status
            state.status = SimulationStatus.READY
            self._save_simulation_state(state)

            logger.info(f"Simulation preparation complete: {simulation_id}, "
                       f"entities={state.entities_count}, profiles={state.profiles_count}")

            return state

        except Exception as e:
            logger.error(f"Simulation preparation failed: {simulation_id}, error={str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            state.status = SimulationStatus.FAILED
            state.error = str(e)
            self._save_simulation_state(state)
            raise

    def get_simulation(self, simulation_id: str) -> Optional[SimulationState]:
        """Get simulation state"""
        return self._load_simulation_state(simulation_id)

    def list_simulations(self, project_id: Optional[str] = None) -> List[SimulationState]:
        """List all simulations"""
        simulations = []

        if os.path.exists(self.SIMULATION_DATA_DIR):
            for sim_id in os.listdir(self.SIMULATION_DATA_DIR):
                # Skip hidden files (e.g. .DS_Store) and non-directory entries
                sim_path = os.path.join(self.SIMULATION_DATA_DIR, sim_id)
                if sim_id.startswith('.') or not os.path.isdir(sim_path):
                    continue

                state = self._load_simulation_state(sim_id)
                if state:
                    if project_id is None or state.project_id == project_id:
                        simulations.append(state)

        return simulations

    def get_profiles(self, simulation_id: str, platform: str = "reddit") -> List[Dict[str, Any]]:
        """Get Agent Profiles for a simulation"""
        state = self._load_simulation_state(simulation_id)
        if not state:
            raise ValueError(f"Simulation does not exist: {simulation_id}")

        sim_dir = self._get_simulation_dir(simulation_id)
        profile_path = os.path.join(sim_dir, f"{platform}_profiles.json")

        if not os.path.exists(profile_path):
            return []

        with open(profile_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_simulation_config(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        """Get simulation config"""
        sim_dir = self._get_simulation_dir(simulation_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")

        if not os.path.exists(config_path):
            return None

        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_run_instructions(self, simulation_id: str) -> Dict[str, str]:
        """Get run instructions"""
        sim_dir = self._get_simulation_dir(simulation_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")
        scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../scripts'))

        return {
            "simulation_dir": sim_dir,
            "scripts_dir": scripts_dir,
            "config_file": config_path,
            "commands": {
                "twitter": f"python {scripts_dir}/run_twitter_simulation.py --config {config_path}",
                "reddit": f"python {scripts_dir}/run_reddit_simulation.py --config {config_path}",
                "parallel": f"python {scripts_dir}/run_parallel_simulation.py --config {config_path}",
            },
            "instructions": (
                f"1. Activate conda environment: conda activate MiroFish\n"
                f"2. Run simulation (scripts located at {scripts_dir}):\n"
                f"   - Run Twitter only: python {scripts_dir}/run_twitter_simulation.py --config {config_path}\n"
                f"   - Run Reddit only: python {scripts_dir}/run_reddit_simulation.py --config {config_path}\n"
                f"   - Run both platforms in parallel: python {scripts_dir}/run_parallel_simulation.py --config {config_path}"
            )
        }

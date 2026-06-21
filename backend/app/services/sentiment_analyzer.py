"""
Sentiment Analyzer for Product Sentiment Simulator

Reads actions.jsonl files from completed (or running) simulations and:
1. Classifies post/comment content via LLM sentiment scoring (-1 to +1)
2. Computes per-round sentiment timeline
3. Assigns agents to factions (advocate / detractor / neutral / churned)
4. Extracts top objections from negative posts
5. Builds persona heatmap using archetype_map.json
"""

import json
import os
import time
from copy import deepcopy
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

from openai import OpenAI, RateLimitError

from ..config import Config
from ..utils.logger import get_logger
from .archetype_library import load_archetype_map, ARCHETYPE_DEFINITIONS

logger = get_logger('mirofish.sentiment_analyzer')

# Action types that contain post content
POST_ACTION_TYPES = {
    "CREATE_POST", "CREATE_COMMENT", "REPOST", "QUOTE_POST",
    # Reddit variants
    "create_post", "create_comment", "repost", "quote_post",
}

CONTENT_KEYS = ["content", "post_content", "comment_content", "text", "body", "quote"]

# Faction thresholds
ADVOCATE_THRESHOLD = 0.35
DETRACTOR_THRESHOLD = -0.25
CHURN_DO_NOTHING_RATIO = 0.80


def _extract_content(action: Dict[str, Any]) -> Optional[str]:
    """Extract text content from an action dict."""
    if action.get("action_type", "") not in POST_ACTION_TYPES:
        return None
    args = action.get("action_args", {})
    for key in CONTENT_KEYS:
        val = args.get(key, "")
        if isinstance(val, str) and val.strip():
            return val.strip()
    # Also check result field
    result = action.get("result", "")
    if isinstance(result, str) and result.strip() and len(result) > 10:
        return result.strip()
    return None


def _read_actions_jsonl(actions_path: str) -> List[Dict[str, Any]]:
    """Read all actions from a JSONL file."""
    actions = []
    if not os.path.exists(actions_path):
        return actions
    with open(actions_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                actions.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return actions


@dataclass
class RoundSentiment:
    round_num: int
    positive: int = 0
    negative: int = 0
    neutral: int = 0
    avg_score: float = 0.0
    weighted_avg_score: float = 0.0
    velocity: float = 0.0
    per_archetype: Dict[str, float] = field(default_factory=dict)
    sample_posts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "round_num": self.round_num,
            "positive": self.positive,
            "negative": self.negative,
            "neutral": self.neutral,
            "avg_score": round(self.avg_score, 3),
            "weighted_avg_score": round(self.weighted_avg_score, 3),
            "velocity": round(self.velocity, 3),
            "per_archetype": {k: round(v, 3) for k, v in self.per_archetype.items()},
            "sample_posts": self.sample_posts[:3],
        }


class SentimentAnalyzer:
    """
    Analyzes sentiment from a simulation's action logs.
    Works with partial (live) simulations by reading whatever JSONL data exists.
    """

    SENTIMENT_CACHE_FILE = "sentiment_cache.json"

    def __init__(
        self,
        simulation_id: str,
        advocate_threshold: float = ADVOCATE_THRESHOLD,
        detractor_threshold: float = DETRACTOR_THRESHOLD,
        use_percentile_factions: bool = False,
    ):
        self.simulation_id = simulation_id
        self._sim_dir = os.path.join(
            os.path.dirname(__file__),
            "../../uploads/simulations",
            simulation_id,
        )
        self._llm = OpenAI(
            api_key=Config.LLM_API_KEY,
            base_url=Config.LLM_BASE_URL,
        )
        self._model = Config.model_for_task('sentiment')
        self._archetype_map: Optional[Dict[int, str]] = None
        self._advocate_threshold = advocate_threshold
        self._detractor_threshold = detractor_threshold
        self._use_percentile_factions = use_percentile_factions

    def _cache_path(self) -> str:
        return os.path.join(self._sim_dir, self.SENTIMENT_CACHE_FILE)

    def _analysis_cache_key(self) -> str:
        return json.dumps(
            {
                "advocate_threshold": round(self._advocate_threshold, 4),
                "detractor_threshold": round(self._detractor_threshold, 4),
                "use_percentile_factions": self._use_percentile_factions,
            },
            sort_keys=True,
        )

    def _action_signature(self) -> Dict[str, Dict[str, Any]]:
        signature: Dict[str, Dict[str, Any]] = {}
        for rel_path in (
            os.path.join("twitter", "actions.jsonl"),
            os.path.join("reddit", "actions.jsonl"),
            "actions.jsonl",
        ):
            abs_path = os.path.join(self._sim_dir, rel_path)
            if not os.path.exists(abs_path):
                continue
            stat = os.stat(abs_path)
            signature[rel_path] = {
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
            }
        return signature

    def _load_cache_entry(self) -> Optional[Dict[str, Any]]:
        cache_path = self._cache_path()
        if not os.path.exists(cache_path):
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as handle:
                cache_store = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return None

        entry = (cache_store.get("entries") or {}).get(self._analysis_cache_key())
        if not entry:
            return None
        if entry.get("action_signature") != self._action_signature():
            return None
        return deepcopy(entry.get("result"))

    def _store_cache_entry(self, result: Dict[str, Any]):
        os.makedirs(self._sim_dir, exist_ok=True)
        cache_path = self._cache_path()
        cache_store = {"version": 1, "entries": {}}
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as handle:
                    cache_store = json.load(handle)
            except (OSError, json.JSONDecodeError):
                cache_store = {"version": 1, "entries": {}}

        cache_store.setdefault("entries", {})[self._analysis_cache_key()] = {
            "updated_at": os.path.getmtime(cache_path) if os.path.exists(cache_path) else 0,
            "action_signature": self._action_signature(),
            "result": result,
        }

        with open(cache_path, "w", encoding="utf-8") as handle:
            json.dump(cache_store, handle, ensure_ascii=False, indent=2)

    def _get_archetype_map(self) -> Dict[int, str]:
        """Returns {agent_id: archetype_key} dict."""
        if self._archetype_map is None:
            raw = load_archetype_map(self._sim_dir)
            self._archetype_map = {
                item["agent_id"]: item["archetype"]
                for item in raw
                if "agent_id" in item and "archetype" in item
            }
        return self._archetype_map

    TOPIC_CATEGORIES = ["pricing", "features", "support", "security", "competitors", "performance", "ux", "other"]

    def _classify_batch(self, posts: List[str]) -> Tuple[List[float], List[List[str]], bool]:
        """
        Classify a batch of posts and return (sentiment_scores, topic_tags, success).
        Retries with exponential backoff on rate-limit (429) errors.
        Returns success=False when all retries are exhausted so the caller can
        skip caching a result made entirely of fallback zeros.
        """
        if not posts:
            return [], [], True

        numbered = "\n".join(
            f"Post {i + 1}: {p[:300]}" for i, p in enumerate(posts)
        )

        topics_list = ", ".join(self.TOPIC_CATEGORIES)
        prompt = (
            "You are a product sentiment and topic classifier. "
            "For each post below, return:\n"
            "1. A sentiment score from -1.0 (very negative) to +1.0 (very positive). 0.0 = neutral.\n"
            f"2. A list of topic tags from: [{topics_list}]\n\n"
            "Return ONLY valid JSON in this exact format:\n"
            '{"results": [{"score": <float>, "topics": ["<tag>", ...]}, ...]}\n\n'
            f"{numbered}"
        )

        max_retries = 5
        backoff = 2.0
        for attempt in range(max_retries):
            try:
                response = self._llm.chat.completions.create(
                    model=self._model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=512,
                    response_format={"type": "json_object"},
                )
                raw = response.choices[0].message.content or "{}"
                data = json.loads(raw)
                results = data.get("results", [])

                # Tolerate off-by-one: LLM occasionally returns n±1 results.
                # Truncate extras or pad missing entries rather than discarding everything.
                if len(results) > len(posts):
                    results = results[:len(posts)]
                elif len(results) < len(posts):
                    while len(results) < len(posts):
                        results.append({"score": 0.0, "topics": []})

                scores = [max(-1.0, min(1.0, float(r.get("score", 0.0)))) for r in results]
                topics = [r.get("topics", []) for r in results]
                return scores, topics, True

            except RateLimitError as e:
                if attempt < max_retries - 1:
                    wait = backoff * (2 ** attempt)
                    logger.warning(f"Rate limit hit, retrying in {wait:.1f}s (attempt {attempt + 1}/{max_retries}): {e}")
                    time.sleep(wait)
                else:
                    logger.warning(f"Sentiment classification failed after {max_retries} retries (rate limit): {e}")
                    return [0.0] * len(posts), [[] for _ in posts], False

            except Exception as e:
                logger.warning(f"Sentiment classification failed: {e}")
                return [0.0] * len(posts), [[] for _ in posts], False

        return [0.0] * len(posts), [[] for _ in posts], False

    def _load_all_actions(self) -> List[Dict[str, Any]]:
        """Load all actions from twitter and reddit JSONL files."""
        actions = []
        for platform in ("twitter", "reddit"):
            path = os.path.join(self._sim_dir, platform, "actions.jsonl")
            actions.extend(_read_actions_jsonl(path))
        # Also try flat actions.jsonl (some simulations write here)
        flat_path = os.path.join(self._sim_dir, "actions.jsonl")
        actions.extend(_read_actions_jsonl(flat_path))
        return actions

    def analyze_all(self) -> Dict[str, Any]:
        """
        Run full sentiment analysis on all available action data.
        Returns: timeline, factions, top_objections, persona_heatmap
        """
        cached_result = self._load_cache_entry()
        if cached_result is not None:
            return cached_result

        actions = self._load_all_actions()
        if not actions:
            empty_result = self._empty_result()
            self._store_cache_entry(empty_result)
            return empty_result

        archetype_map = self._get_archetype_map()

        # Group posts by round
        round_posts: Dict[int, List[Tuple[int, str]]] = {}  # round -> [(agent_id, content)]
        all_posts_with_meta: List[Tuple[int, int, str]] = []  # (round, agent_id, content)

        do_nothing_counts: Dict[int, int] = {}
        total_action_counts: Dict[int, int] = {}

        for action in actions:
            # Reddit writes "round", Twitter writes "round_num"
            round_num = action.get("round_num") or action.get("round", 0)
            agent_id = action.get("agent_id", -1)
            action_type = action.get("action_type", "")

            total_action_counts[agent_id] = total_action_counts.get(agent_id, 0) + 1
            if "DO_NOTHING" in action_type.upper():
                do_nothing_counts[agent_id] = do_nothing_counts.get(agent_id, 0) + 1

            content = _extract_content(action)
            if content:
                if round_num not in round_posts:
                    round_posts[round_num] = []
                round_posts[round_num].append((agent_id, content))
                all_posts_with_meta.append((round_num, agent_id, content))

        # Classify all posts in batches (sentiment + topics in one LLM call)
        BATCH_SIZE = 20
        all_contents = [c for _, _, c in all_posts_with_meta]
        raw_scores: List[float] = []
        all_topics: List[List[str]] = []
        failed_batches = 0
        total_batches = 0
        for i in range(0, len(all_contents), BATCH_SIZE):
            batch = all_contents[i: i + BATCH_SIZE]
            batch_scores, batch_topics, success = self._classify_batch(batch)
            raw_scores.extend(batch_scores)
            all_topics.extend(batch_topics)
            total_batches += 1
            if not success:
                failed_batches += 1

        # Don't cache results where all batches failed (rate limit / API down).
        # The next request will re-run analysis and pick up a valid result.
        all_batches_failed = total_batches > 0 and failed_batches == total_batches

        # Apply sentiment momentum smoothing per agent across rounds
        # Prevents unrealistic instant sentiment flips (e.g., skeptic going -0.3 to +0.8)
        agent_prev_score: Dict[int, float] = {}
        all_scores: List[float] = []
        for idx, (rnd, agent_id, _) in enumerate(all_posts_with_meta):
            raw = raw_scores[idx] if idx < len(raw_scores) else 0.0
            arch_key = archetype_map.get(agent_id, "unknown")
            arch_def = ARCHETYPE_DEFINITIONS.get(arch_key, {})
            momentum = arch_def.get("sentiment_momentum", 0.5)

            if agent_id in agent_prev_score:
                smoothed = agent_prev_score[agent_id] * momentum + raw * (1 - momentum)
            else:
                smoothed = raw
            agent_prev_score[agent_id] = smoothed
            all_scores.append(round(smoothed, 4))

        # Build per-agent score history
        agent_scores: Dict[int, List[float]] = {}
        for idx, (rnd, agent_id, _) in enumerate(all_posts_with_meta):
            score = all_scores[idx] if idx < len(all_scores) else 0.0
            if agent_id not in agent_scores:
                agent_scores[agent_id] = []
            agent_scores[agent_id].append(score)

        # Build timeline (per round)
        timeline = []
        prev_avg = None
        for rnd in sorted(round_posts.keys()):
            pairs = round_posts[rnd]
            # Find scores for this round
            rnd_scores = []
            for idx, (r, aid, _) in enumerate(all_posts_with_meta):
                if r == rnd and idx < len(all_scores):
                    rnd_scores.append((aid, all_scores[idx]))

            if not rnd_scores:
                timeline.append(RoundSentiment(round_num=rnd).to_dict())
                continue

            scores_only = [s for _, s in rnd_scores]
            avg = sum(scores_only) / len(scores_only)
            positive = sum(1 for s in scores_only if s >= 0.2)
            negative = sum(1 for s in scores_only if s <= -0.2)
            neutral = len(scores_only) - positive - negative

            # Influence-weighted average
            weighted_num = 0.0
            weighted_den = 0.0
            for aid, score in rnd_scores:
                arch_key = archetype_map.get(aid, "unknown")
                arch_def = ARCHETYPE_DEFINITIONS.get(arch_key, {})
                weight = arch_def.get("influence_weight", 0.5)
                weighted_num += score * weight
                weighted_den += weight
            weighted_avg = weighted_num / weighted_den if weighted_den > 0 else avg

            # Sentiment velocity (change from previous round)
            velocity = (avg - prev_avg) if prev_avg is not None else 0.0
            prev_avg = avg

            # Per-archetype scores for this round
            archetype_scores: Dict[str, List[float]] = {}
            for aid, score in rnd_scores:
                arch = archetype_map.get(aid, "unknown")
                if arch not in archetype_scores:
                    archetype_scores[arch] = []
                archetype_scores[arch].append(score)
            per_arch = {k: sum(v) / len(v) for k, v in archetype_scores.items()}

            # Sample posts
            sample_contents = [c for _, c in pairs[:3]]

            rs = RoundSentiment(
                round_num=rnd,
                positive=positive,
                negative=negative,
                neutral=neutral,
                avg_score=avg,
                weighted_avg_score=weighted_avg,
                velocity=velocity,
                per_archetype=per_arch,
                sample_posts=sample_contents,
            )
            timeline.append(rs.to_dict())

        # Change-point detection: flag rounds with significant sentiment shifts
        anomalies = []
        if len(timeline) >= 4:
            scores_seq = [t.get("avg_score", 0.0) if isinstance(t, dict) else t.avg_score for t in timeline]
            for i in range(3, len(scores_seq)):
                rolling_mean = sum(scores_seq[i-3:i]) / 3
                delta = abs(scores_seq[i] - rolling_mean)
                if delta > 0.15:
                    rnd_data = timeline[i] if isinstance(timeline[i], dict) else timeline[i].to_dict()
                    anomalies.append({
                        "round": rnd_data.get("round_num", i),
                        "score": scores_seq[i],
                        "rolling_mean": round(rolling_mean, 3),
                        "delta": round(delta, 3),
                        "direction": "spike" if scores_seq[i] > rolling_mean else "drop",
                    })

        # Faction assignment
        factions = self._compute_factions(agent_scores, do_nothing_counts, total_action_counts)

        # Top objections
        negative_posts = [
            c for idx, (_, _, c) in enumerate(all_posts_with_meta)
            if idx < len(all_scores) and all_scores[idx] <= -0.25
        ][:40]
        top_objections = self._extract_top_objections(negative_posts)

        # Persona heatmap: {archetype: avg_score}
        archetype_all_scores: Dict[str, List[float]] = {}
        for idx, (_, aid, _) in enumerate(all_posts_with_meta):
            if idx >= len(all_scores):
                continue
            arch = archetype_map.get(aid, "unknown")
            if arch not in archetype_all_scores:
                archetype_all_scores[arch] = []
            archetype_all_scores[arch].append(all_scores[idx])
        persona_heatmap = {
            k: round(sum(v) / len(v), 3)
            for k, v in archetype_all_scores.items()
        }

        # Overall stats
        overall_avg = sum(all_scores) / len(all_scores) if all_scores else 0.0
        total_positive = sum(1 for s in all_scores if s >= 0.2)
        total_negative = sum(1 for s in all_scores if s <= -0.2)
        total_neutral = len(all_scores) - total_positive - total_negative

        # Overall influence-weighted average
        w_num, w_den = 0.0, 0.0
        for idx, (_, aid, _) in enumerate(all_posts_with_meta):
            if idx >= len(all_scores):
                break
            arch_key = archetype_map.get(aid, "unknown")
            arch_def = ARCHETYPE_DEFINITIONS.get(arch_key, {})
            weight = arch_def.get("influence_weight", 0.5)
            w_num += all_scores[idx] * weight
            w_den += weight
        overall_weighted_avg = w_num / w_den if w_den > 0 else overall_avg

        # Topic breakdown: per archetype and overall
        topic_counts: Dict[str, int] = {}
        topic_by_archetype: Dict[str, Dict[str, int]] = {}
        for idx, (_, aid, _) in enumerate(all_posts_with_meta):
            if idx >= len(all_topics):
                break
            arch_key = archetype_map.get(aid, "unknown")
            for topic in all_topics[idx]:
                topic = topic.lower().strip()
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
                if arch_key not in topic_by_archetype:
                    topic_by_archetype[arch_key] = {}
                topic_by_archetype[arch_key][topic] = topic_by_archetype[arch_key].get(topic, 0) + 1

        # NPS: promoters (score >= 0.5) minus detractors (score <= -0.25) as percentage
        agent_avg_scores = {
            aid: sum(scores) / len(scores)
            for aid, scores in agent_scores.items() if scores
        }
        total_respondents = max(len(agent_avg_scores), 1)
        promoters = sum(1 for s in agent_avg_scores.values() if s >= 0.5)
        nps_detractors = sum(1 for s in agent_avg_scores.values() if s <= -0.25)
        nps_score = round((promoters - nps_detractors) / total_respondents * 100, 1)

        result = {
            "simulation_id": self.simulation_id,
            "total_posts_analyzed": len(all_scores),
            "overall": {
                "avg_score": round(overall_avg, 3),
                "weighted_avg_score": round(overall_weighted_avg, 3),
                "nps_score": nps_score,
                "positive": total_positive,
                "negative": total_negative,
                "neutral": total_neutral,
                "positive_pct": round(total_positive / max(len(all_scores), 1) * 100, 1),
                "negative_pct": round(total_negative / max(len(all_scores), 1) * 100, 1),
                "neutral_pct": round(total_neutral / max(len(all_scores), 1) * 100, 1),
            },
            "timeline": timeline,
            "factions": factions,
            "top_objections": top_objections,
            "persona_heatmap": persona_heatmap,
            "topic_breakdown": {
                "overall": dict(sorted(topic_counts.items(), key=lambda x: -x[1])),
                "by_archetype": topic_by_archetype,
            },
            "anomalies": anomalies,
        }
        if not all_batches_failed:
            self._store_cache_entry(result)
        else:
            logger.warning(
                f"Skipping cache write for {self.simulation_id}: all {total_batches} "
                "sentiment batches failed (likely rate-limited). Will retry on next request."
            )
        return result

    def _compute_factions(
        self,
        agent_scores: Dict[int, List[float]],
        do_nothing_counts: Dict[int, int],
        total_action_counts: Dict[int, int],
    ) -> Dict[str, Any]:
        advocates, detractors, churned, neutral = 0, 0, 0, 0
        archetype_map = self._get_archetype_map()

        # Numeric churn thresholds per archetype (lower = easier to churn)
        CHURN_THRESHOLD_MAP = {
            "any_negative_signal": -0.1,
            "any_friction_point": -0.05,
            "low_quality_experience": -0.2,
            "price_increase_above_20pct": -0.2,
            "poor_branding_or_ethics": -0.15,
            "incumbent_failure": -0.3,
            "compliance_failure_or_security_breach": -0.25,
            "feature_regression_or_pricing_above_value": -0.2,
            "data_breach_or_policy_change": -0.15,
        }

        # Only classify agents that actually posted — silent lurkers (like/follow only)
        # are not meaningful sentiment signals and inflate the neutral count.
        all_agent_ids = set(agent_scores.keys()) | {
            aid for aid, dn in do_nothing_counts.items()
            if total_action_counts.get(aid, 0) > 0
            and dn / total_action_counts[aid] >= CHURN_DO_NOTHING_RATIO
        }

        # Compute per-agent averages for percentile mode
        agent_avgs: Dict[int, float] = {}
        for agent_id in all_agent_ids:
            scores = agent_scores.get(agent_id, [])
            if scores:
                agent_avgs[agent_id] = sum(scores) / len(scores)

        # Determine thresholds (percentile or fixed)
        adv_thresh = self._advocate_threshold
        det_thresh = self._detractor_threshold
        if self._use_percentile_factions and agent_avgs:
            sorted_avgs = sorted(agent_avgs.values())
            n = len(sorted_avgs)
            adv_thresh = sorted_avgs[int(n * 0.75)] if n > 0 else adv_thresh
            det_thresh = sorted_avgs[int(n * 0.25)] if n > 0 else det_thresh

        for agent_id in all_agent_ids:
            scores = agent_scores.get(agent_id, [])
            total = total_action_counts.get(agent_id, 0)
            dn = do_nothing_counts.get(agent_id, 0)

            # Improved churn: check DO_NOTHING ratio + sentiment trajectory + natural activity level
            arch_key = archetype_map.get(agent_id, "unknown")
            arch_def = ARCHETYPE_DEFINITIONS.get(arch_key, {})
            natural_activity = arch_def.get("activity_level", 0.5)

            if total > 0 and dn / total >= CHURN_DO_NOTHING_RATIO:
                # Don't mark naturally low-activity archetypes as churned
                if natural_activity > 0.3:
                    churned += 1
                    continue
                # For low-activity archetypes, only churn if recent sentiment is also very negative
                if scores and len(scores) >= 3:
                    recent_avg = sum(scores[-3:]) / len(scores[-3:])
                    churn_str = arch_def.get("churn_threshold", "any_negative_signal")
                    churn_val = CHURN_THRESHOLD_MAP.get(churn_str, -0.1)
                    if recent_avg <= churn_val:
                        churned += 1
                        continue
                # Otherwise treat as neutral (natural low activity, not churned)

            if not scores:
                neutral += 1
                continue

            avg = sum(scores) / len(scores)
            if avg >= adv_thresh:
                advocates += 1
            elif avg <= det_thresh:
                detractors += 1
            else:
                neutral += 1

        total_agents = max(advocates + detractors + churned + neutral, 1)
        return {
            "advocates": advocates,
            "detractors": detractors,
            "neutral": neutral,
            "churned": churned,
            "advocates_pct": round(advocates / total_agents * 100, 1),
            "detractors_pct": round(detractors / total_agents * 100, 1),
            "neutral_pct": round(neutral / total_agents * 100, 1),
            "churned_pct": round(churned / total_agents * 100, 1),
        }

    def _extract_top_objections(self, negative_posts: List[str]) -> List[Dict[str, Any]]:
        """Use LLM to summarize top product objections from negative posts."""
        if not negative_posts:
            return []

        joined = "\n---\n".join(negative_posts[:30])
        prompt = (
            "Below are negative consumer posts about a product. "
            "Identify the top 5 distinct objections or concerns mentioned. "
            "Return ONLY valid JSON: "
            '{"objections": [{"theme": "...", "example": "...", "count": <estimate>}, ...]}\n\n'
            f"{joined}"
        )

        try:
            response = self._llm.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=512,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content or "{}"
            data = json.loads(raw)
            return data.get("objections", [])[:5]
        except Exception as e:
            logger.warning(f"Top objections extraction failed: {e}")
            return []

    def _empty_result(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "total_posts_analyzed": 0,
            "overall": {
                "avg_score": 0.0,
                "weighted_avg_score": 0.0,
                "nps_score": 0.0,
                "positive": 0,
                "negative": 0,
                "neutral": 0,
                "positive_pct": 0.0, "negative_pct": 0.0, "neutral_pct": 0.0,
            },
            "timeline": [],
            "factions": {
                "advocates": 0, "detractors": 0, "neutral": 0, "churned": 0,
                "advocates_pct": 0.0, "detractors_pct": 0.0,
                "neutral_pct": 0.0, "churned_pct": 0.0,
            },
            "top_objections": [],
            "persona_heatmap": {},
        }


def compare_scenarios(
    sim_id_a: str,
    sim_id_b: str,
    sim_id_c: str,
) -> Dict[str, Any]:
    """
    Return per-round avg_score for all three scenarios in a format
    suitable for an overlay chart.
    """
    results = {}
    for label, sim_id in [("a", sim_id_a), ("b", sim_id_b), ("c", sim_id_c)]:
        analyzer = SentimentAnalyzer(sim_id)
        data = analyzer.analyze_all()
        results[label] = {
            "rounds": [r["round_num"] for r in data["timeline"]],
            "scores": [r["avg_score"] for r in data["timeline"]],
            "overall": data["overall"],
            "factions": data["factions"],
        }

    # Merge round axis
    all_rounds = sorted(set(
        r
        for v in results.values()
        for r in v["rounds"]
    ))

    def scores_by_round(scenario_data):
        round_to_score = dict(zip(scenario_data["rounds"], scenario_data["scores"]))
        return [round_to_score.get(r, None) for r in all_rounds]

    return {
        "rounds": all_rounds,
        "scenario_a": scores_by_round(results["a"]),
        "scenario_b": scores_by_round(results["b"]),
        "scenario_c": scores_by_round(results["c"]),
        "details": {k: {"overall": v["overall"], "factions": v["factions"]} for k, v in results.items()},
    }

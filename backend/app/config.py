"""Application configuration loaded from the project root `.env` file."""

import os
from typing import Dict, List, Optional

from dotenv import load_dotenv


PROJECT_ROOT_ENV = os.path.join(os.path.dirname(__file__), '../../.env')

if os.path.exists(PROJECT_ROOT_ENV):
    load_dotenv(PROJECT_ROOT_ENV, override=True)
else:
    load_dotenv(override=True)


def _get_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def _get_csv(name: str) -> List[str]:
    raw = os.environ.get(name, '')
    return [item.strip() for item in raw.split(',') if item.strip()]


class Config:
    """Flask configuration."""

    SECRET_KEY = os.environ.get('SECRET_KEY')
    DEBUG = _get_bool('FLASK_DEBUG', False)
    TESTING = _get_bool('FLASK_TESTING', False)
    JSON_AS_ASCII = False

    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gpt-4o-mini')

    # Per-task model overrides (issue #15). Each agent task may pick a model with
    # different cost/quality trade-offs via LLM_MODEL_<TASK>; anything unset falls
    # back to LLM_MODEL_NAME. Recognised task keys are the dict keys below.
    LLM_TASK_MODELS: Dict[str, Optional[str]] = {
        'profile': os.environ.get('LLM_MODEL_PROFILE'),
        'config': os.environ.get('LLM_MODEL_CONFIG'),
        'report': os.environ.get('LLM_MODEL_REPORT'),
        'ontology': os.environ.get('LLM_MODEL_ONTOLOGY'),
        'sentiment': os.environ.get('LLM_MODEL_SENTIMENT'),
        'tools': os.environ.get('LLM_MODEL_TOOLS'),
    }

    # Optional backup model used when a primary LLM call fails. May live on a
    # different provider (separate base URL / key); both default to the primary.
    LLM_FALLBACK_MODEL = os.environ.get('LLM_FALLBACK_MODEL', '').strip()
    LLM_FALLBACK_BASE_URL = os.environ.get('LLM_FALLBACK_BASE_URL', '').strip()
    LLM_FALLBACK_API_KEY = os.environ.get('LLM_FALLBACK_API_KEY', '').strip()

    # Disk cache for deterministic LLM generation (profile/config) — issue #20.
    # Keyed by a hash of model + prompt, so config changes invalidate naturally.
    LLM_CACHE_ENABLED = _get_bool('LLM_CACHE_ENABLED', True)
    LLM_CACHE_DIR = os.environ.get(
        'LLM_CACHE_DIR', os.path.join(os.path.dirname(__file__), '../uploads/llm_cache')
    )
    LLM_CACHE_TTL = int(os.environ.get('LLM_CACHE_TTL', '0'))  # seconds; 0 = no expiry

    # Resilience for outbound LLM calls (issue #28): retry transient provider
    # errors (429 / timeout / connection / 5xx) with exponential backoff, and
    # bound every request with a timeout.
    LLM_MAX_RETRIES = int(os.environ.get('LLM_MAX_RETRIES', '3'))
    LLM_RETRY_INITIAL_DELAY = float(os.environ.get('LLM_RETRY_INITIAL_DELAY', '1.0'))
    LLM_RETRY_MAX_DELAY = float(os.environ.get('LLM_RETRY_MAX_DELAY', '30.0'))
    LLM_TIMEOUT = float(os.environ.get('LLM_TIMEOUT', '60.0'))

    ZEP_API_KEY = os.environ.get('ZEP_API_KEY')

    APP_API_KEY = os.environ.get('APP_API_KEY', '').strip()

    MAX_CONTENT_LENGTH = 50 * 1024 * 1024
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown'}

    DEFAULT_CHUNK_SIZE = int(os.environ.get('DEFAULT_CHUNK_SIZE', '500'))
    DEFAULT_CHUNK_OVERLAP = int(os.environ.get('DEFAULT_CHUNK_OVERLAP', '50'))

    OASIS_DEFAULT_MAX_ROUNDS = int(os.environ.get('OASIS_DEFAULT_MAX_ROUNDS', '10'))
    OASIS_SIMULATION_DATA_DIR = os.path.join(os.path.dirname(__file__), '../uploads/simulations')

    OASIS_TWITTER_ACTIONS = [
        'CREATE_POST', 'LIKE_POST', 'REPOST', 'FOLLOW', 'DO_NOTHING', 'QUOTE_POST'
    ]
    OASIS_REDDIT_ACTIONS = [
        'LIKE_POST', 'DISLIKE_POST', 'CREATE_POST', 'CREATE_COMMENT',
        'LIKE_COMMENT', 'DISLIKE_COMMENT', 'SEARCH_POSTS', 'SEARCH_USER',
        'TREND', 'REFRESH', 'DO_NOTHING', 'FOLLOW', 'MUTE'
    ]

    REPORT_AGENT_MAX_TOOL_CALLS = int(os.environ.get('REPORT_AGENT_MAX_TOOL_CALLS', '5'))
    REPORT_AGENT_MAX_REFLECTION_ROUNDS = int(os.environ.get('REPORT_AGENT_MAX_REFLECTION_ROUNDS', '2'))
    REPORT_AGENT_TEMPERATURE = float(os.environ.get('REPORT_AGENT_TEMPERATURE', '0.5'))

    SENTIMENT_DEFAULT_TOTAL_AGENTS = int(os.environ.get('SENTIMENT_DEFAULT_TOTAL_AGENTS', '50'))
    SENTIMENT_DEFAULT_MAX_ROUNDS = int(os.environ.get('SENTIMENT_DEFAULT_MAX_ROUNDS', '20'))
    SENTIMENT_SCENARIO_B_INJECT_ROUND = int(os.environ.get('SENTIMENT_SCENARIO_B_INJECT_ROUND', '7'))
    SENTIMENT_SCENARIO_C_INJECT_ROUND = int(os.environ.get('SENTIMENT_SCENARIO_C_INJECT_ROUND', '14'))

    FRONTEND_ORIGIN = os.environ.get('FRONTEND_ORIGIN', '').strip()
    CORS_ORIGINS = _get_csv('CORS_ORIGINS')
    if not CORS_ORIGINS and FRONTEND_ORIGIN:
        CORS_ORIGINS = [FRONTEND_ORIGIN]
    if not CORS_ORIGINS and DEBUG:
        CORS_ORIGINS = ['http://localhost:3000']

    LOG_REQUEST_BODIES = _get_bool('LOG_REQUEST_BODIES', False)
    SERVE_FRONTEND = _get_bool('SERVE_FRONTEND', True)
    FRONTEND_DIST_DIR = os.path.join(os.path.dirname(__file__), '../../frontend/dist')
    TASK_DATA_DIR = os.path.join(os.path.dirname(__file__), '../uploads/tasks')

    @classmethod
    def model_for_task(cls, task: Optional[str] = None) -> str:
        """Return the model configured for an agent task, or the global default."""
        if task:
            override = cls.LLM_TASK_MODELS.get(task)
            if override:
                return override
        return cls.LLM_MODEL_NAME

    @classmethod
    def llm_settings(cls, task: Optional[str] = None) -> Dict[str, Optional[str]]:
        """Resolve primary + fallback LLM connection settings for an agent task.

        The returned dict is directly consumable as ``LLMClient(**settings)``.
        Fallback fields are ``None`` unless ``LLM_FALLBACK_MODEL`` is set, and a
        fallback may target a different provider (its own base URL / API key).
        """
        fallback_model = cls.LLM_FALLBACK_MODEL or None
        return {
            'api_key': cls.LLM_API_KEY,
            'base_url': cls.LLM_BASE_URL,
            'model': cls.model_for_task(task),
            'fallback_model': fallback_model,
            'fallback_base_url': (cls.LLM_FALLBACK_BASE_URL or cls.LLM_BASE_URL) if fallback_model else None,
            'fallback_api_key': (cls.LLM_FALLBACK_API_KEY or cls.LLM_API_KEY) if fallback_model else None,
        }

    @classmethod
    def validate(cls):
        """Validate required runtime configuration."""
        errors = []
        if not cls.SECRET_KEY:
            errors.append('SECRET_KEY is required')
        if not cls.LLM_API_KEY:
            errors.append('LLM_API_KEY is required')
        if not cls.ZEP_API_KEY:
            errors.append('ZEP_API_KEY is required')
        return errors

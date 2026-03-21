"""Application configuration loaded from the project root `.env` file."""

import os
from typing import List

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

    ZEP_API_KEY = os.environ.get('ZEP_API_KEY')

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

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import Config
from app.models.task import TaskManager


@pytest.fixture(autouse=True)
def isolate_task_manager(tmp_path, monkeypatch):
    tasks_dir = tmp_path / 'tasks'
    uploads_dir = tmp_path / 'uploads'
    monkeypatch.setattr(Config, 'TASK_DATA_DIR', str(tasks_dir))
    monkeypatch.setattr(Config, 'UPLOAD_FOLDER', str(uploads_dir))
    TaskManager._instance = None
    yield
    TaskManager._instance = None


@pytest.fixture
def testing_env(monkeypatch):
    monkeypatch.setattr(Config, 'SECRET_KEY', 'test-secret-key')
    monkeypatch.setattr(Config, 'LLM_API_KEY', 'test-llm-key')
    monkeypatch.setattr(Config, 'ZEP_API_KEY', 'test-zep-key')
    monkeypatch.setattr(Config, 'DEBUG', False)
    monkeypatch.setattr(Config, 'TESTING', True)
    monkeypatch.setattr(Config, 'CORS_ORIGINS', ['http://example.com'])
    monkeypatch.setattr(Config, 'SERVE_FRONTEND', False)
    return Config

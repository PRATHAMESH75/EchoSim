"""Persistent task status tracking for long-running background jobs."""

import json
import os
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional

from ..config import Config


class TaskStatus(str, Enum):
    """Background task status."""

    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'


@dataclass
class Task:
    """Task metadata stored in memory and on disk."""

    task_id: str
    task_type: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    progress: int = 0
    message: str = ''
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    progress_detail: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'task_type': self.task_type,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'progress': self.progress,
            'message': self.message,
            'progress_detail': self.progress_detail,
            'result': self.result,
            'error': self.error,
            'metadata': self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        return cls(
            task_id=data['task_id'],
            task_type=data['task_type'],
            status=TaskStatus(data.get('status', TaskStatus.PENDING.value)),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            progress=int(data.get('progress', 0)),
            message=data.get('message', ''),
            result=data.get('result'),
            error=data.get('error'),
            metadata=data.get('metadata') or {},
            progress_detail=data.get('progress_detail') or {},
        )


class TaskManager:
    """Thread-safe task manager backed by JSON files."""

    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._tasks = {}
                    cls._instance._task_lock = threading.Lock()
                    cls._instance._tasks_dir = os.path.abspath(Config.TASK_DATA_DIR)
                    os.makedirs(cls._instance._tasks_dir, exist_ok=True)
                    cls._instance._load_from_disk()
        return cls._instance

    def _task_path(self, task_id: str) -> str:
        return os.path.join(self._tasks_dir, f'{task_id}.json')

    def _persist_task(self, task: Task):
        with open(self._task_path(task.task_id), 'w', encoding='utf-8') as handle:
            json.dump(task.to_dict(), handle, ensure_ascii=False, indent=2)

    def _load_task_file(self, task_id: str) -> Optional[Task]:
        path = self._task_path(task_id)
        if not os.path.exists(path):
            return None
        with open(path, 'r', encoding='utf-8') as handle:
            return Task.from_dict(json.load(handle))

    def _load_from_disk(self):
        for filename in os.listdir(self._tasks_dir):
            if not filename.endswith('.json'):
                continue
            task_id = filename[:-5]
            try:
                task = self._load_task_file(task_id)
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            if task:
                self._tasks[task_id] = task

    def create_task(self, task_type: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        task_id = str(uuid.uuid4())
        now = datetime.now()
        task = Task(
            task_id=task_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )
        with self._task_lock:
            self._tasks[task_id] = task
            self._persist_task(task)
        return task_id

    def get_task(self, task_id: str) -> Optional[Task]:
        with self._task_lock:
            task = self._tasks.get(task_id)
            if task:
                return task
            task = self._load_task_file(task_id)
            if task:
                self._tasks[task_id] = task
            return task

    def update_task(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        progress_detail: Optional[Dict[str, Any]] = None,
    ):
        with self._task_lock:
            task = self._tasks.get(task_id) or self._load_task_file(task_id)
            if not task:
                return
            task.updated_at = datetime.now()
            if status is not None:
                task.status = status
            if progress is not None:
                task.progress = progress
            if message is not None:
                task.message = message
            if result is not None:
                task.result = result
            if error is not None:
                task.error = error
            if progress_detail is not None:
                task.progress_detail = progress_detail
            self._tasks[task_id] = task
            self._persist_task(task)

    def complete_task(self, task_id: str, result: Dict[str, Any], message: str = 'Task completed'):
        self.update_task(
            task_id,
            status=TaskStatus.COMPLETED,
            progress=100,
            message=message,
            result=result,
        )

    def fail_task(self, task_id: str, error: str, message: str = 'Task failed'):
        self.update_task(
            task_id,
            status=TaskStatus.FAILED,
            message=message,
            error=error,
        )

    def list_tasks(self, task_type: Optional[str] = None) -> list[Dict[str, Any]]:
        with self._task_lock:
            self._load_from_disk()
            tasks = list(self._tasks.values())
            if task_type:
                tasks = [task for task in tasks if task.task_type == task_type]
            tasks.sort(key=lambda item: item.created_at, reverse=True)
            return [task.to_dict() for task in tasks]

    def cleanup_old_tasks(self, max_age_hours: int = 24):
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        with self._task_lock:
            stale_ids = [
                task_id
                for task_id, task in self._tasks.items()
                if task.created_at < cutoff and task.status in {TaskStatus.COMPLETED, TaskStatus.FAILED}
            ]
            for task_id in stale_ids:
                self._tasks.pop(task_id, None)
                try:
                    os.remove(self._task_path(task_id))
                except OSError:
                    pass

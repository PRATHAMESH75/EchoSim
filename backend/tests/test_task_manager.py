from app.models.task import TaskManager, TaskStatus


def test_task_manager_persists_tasks_to_disk():
    manager = TaskManager()
    task_id = manager.create_task('campaign_prepare', {'campaign_id': 'camp_123'})

    manager.update_task(
        task_id,
        status=TaskStatus.PROCESSING,
        progress=42,
        message='Preparing scenarios',
        progress_detail={'stage': 'profiles'},
    )

    TaskManager._instance = None
    reloaded = TaskManager()
    task = reloaded.get_task(task_id)

    assert task is not None
    assert task.task_id == task_id
    assert task.status == TaskStatus.PROCESSING
    assert task.progress == 42
    assert task.message == 'Preparing scenarios'
    assert task.progress_detail == {'stage': 'profiles'}
    assert task.metadata == {'campaign_id': 'camp_123'}

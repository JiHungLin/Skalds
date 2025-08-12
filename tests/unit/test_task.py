import pytest
from datetime import datetime, timedelta
from pydantic import BaseModel, ValidationError
from skald.model.task import (
    ModeEnum,
    TaskLifecycleStatus,
    Task,
    TaskWorkerSimpleMap,
    TaskWorkerSimpleMapList,
)

class DummyAttachment(BaseModel):
    foo: str

def test_mode_enum_values():
    assert ModeEnum.ACTIVE.value == "Active"
    assert ModeEnum.PASSIVE.value == "Passive"
    assert set(ModeEnum.list()) == {"Active", "Passive"}

def test_task_lifecycle_status_values():
    expected = {"Created", "Assigning", "Running", "Paused", "Finished", "Failed", "Cancelled"}
    assert set(TaskLifecycleStatus.list()) == expected

def test_task_model_defaults_and_validation():
    now = datetime.now()
    task = Task(
        id="1",
        class_name="TestClass",
        source="unit-test",
    )
    assert task.id == "1"
    assert task.class_name == "TestClass"
    assert task.source == "unit-test"
    assert task.mode == ModeEnum.PASSIVE
    assert task.lifecycle_status == TaskLifecycleStatus.Created
    assert 0 <= task.priority <= 10
    assert isinstance(task.create_date_time, datetime)
    assert isinstance(task.update_date_time, datetime)
    assert isinstance(task.deadline_date_time, datetime)
    # Deadline should be about 7 days after creation
    assert timedelta(days=6, hours=23) < (task.deadline_date_time - task.create_date_time) < timedelta(days=7, minutes=1)
    assert task.attachments is None

    # Attachments must be a Pydantic BaseModel
    att = DummyAttachment(foo="bar")
    task2 = Task(
        id="2",
        class_name="TestClass",
        source="unit-test",
        attachments=att,
    )
    assert isinstance(task2.attachments, DummyAttachment)

    # Should raise if attachments is not a BaseModel
    with pytest.raises(ValidationError):
        Task(
            id="3",
            class_name="TestClass",
            source="unit-test",
            attachments={"foo": "bar"},
        )

def test_task_worker_simple_map():
    twsm = TaskWorkerSimpleMap(id="abc", class_name="MyClass")
    assert twsm.id == "abc"
    assert twsm.class_name == "MyClass"

def test_task_worker_simple_map_list_push_and_pop():
    twsm_list = TaskWorkerSimpleMapList(tasks=[], existed_task_ids=[])
    assert twsm_list.tasks == []
    assert twsm_list.existed_task_ids == []

    twsm_list.push("id1", "ClassA")
    assert len(twsm_list.tasks) == 1
    assert twsm_list.tasks[0].id == "id1"
    assert twsm_list.tasks[0].class_name == "ClassA"
    assert "id1" in twsm_list.existed_task_ids

    # Pushing same id should not duplicate
    twsm_list.push("id1", "ClassA")
    assert len(twsm_list.tasks) == 1

    # Add another
    twsm_list.push("id2", "ClassB")
    assert len(twsm_list.tasks) == 2
    assert set(t.id for t in twsm_list.tasks) == {"id1", "id2"}

    # Pop by id
    twsm_list.pop_by_task_id("id1")
    assert len(twsm_list.tasks) == 1
    assert twsm_list.tasks[0].id == "id2"
    assert "id1" not in twsm_list.existed_task_ids

def test_task_worker_simple_map_list_clear_and_keep_specify():
    twsm_list = TaskWorkerSimpleMapList(
        tasks=[
            TaskWorkerSimpleMap(id="id1", class_name="A"),
            TaskWorkerSimpleMap(id="id2", class_name="B"),
            TaskWorkerSimpleMap(id="id3", class_name="C"),
        ],
        existed_task_ids=["id1", "id2", "id3"],
    )
    old_timestamp = twsm_list.timestamp

    # Clear
    twsm_list.clear()
    assert twsm_list.tasks == []
    assert twsm_list.existed_task_ids == []
    assert twsm_list.timestamp >= old_timestamp

    # Re-add and keep_specify_tasks
    twsm_list.tasks = [
        TaskWorkerSimpleMap(id="id1", class_name="A"),
        TaskWorkerSimpleMap(id="id2", class_name="B"),
        TaskWorkerSimpleMap(id="id3", class_name="C"),
    ]
    twsm_list.existed_task_ids = ["id1", "id2", "id3"]
    twsm_list.keep_specify_tasks(["id2"])
    assert len(twsm_list.tasks) == 1
    assert twsm_list.tasks[0].id == "id2"
    assert twsm_list.existed_task_ids == ["id2"]

def test_task_worker_simple_map_list_update_timestamp():
    twsm_list = TaskWorkerSimpleMapList(tasks=[], existed_task_ids=[])
    old_timestamp = twsm_list.timestamp
    twsm_list.update_timestamp()
    assert twsm_list.timestamp >= old_timestamp
import pytest
from pydantic import BaseModel, ValidationError
from skald.model.task import Task

# 1. 簡單自訂 BaseModel
class SimpleAttachment(BaseModel):
    foo: str
    bar: int

# 2. 巢狀 BaseModel
class NestedAttachment(BaseModel):
    inner: SimpleAttachment
    note: str

# 3. List 欄位 BaseModel
class ListAttachment(BaseModel):
    items: list[int]
    desc: str

def test_task_with_simple_attachment():
    att = SimpleAttachment(foo="abc", bar=123)
    task = Task(
        id="t1",
        class_name="TestTask",
        source="unit",
        attachments=att
    )
    assert isinstance(task.attachments, SimpleAttachment)
    assert task.attachments.foo == "abc"
    assert task.attachments.bar == 123

def test_task_with_nested_attachment():
    att = NestedAttachment(inner=SimpleAttachment(foo="xyz", bar=456), note="nested")
    task = Task(
        id="t2",
        class_name="TestTask",
        source="unit",
        attachments=att
    )
    assert isinstance(task.attachments, NestedAttachment)
    assert task.attachments.inner.foo == "xyz"
    assert task.attachments.inner.bar == 456
    assert task.attachments.note == "nested"

def test_task_with_list_attachment():
    att = ListAttachment(items=[1,2,3], desc="list test")
    task = Task(
        id="t3",
        class_name="TestTask",
        source="unit",
        attachments=att
    )
    assert isinstance(task.attachments, ListAttachment)
    assert task.attachments.items == [1,2,3]
    assert task.attachments.desc == "list test"

def test_task_with_none_attachment():
    task = Task(
        id="t4",
        class_name="TestTask",
        source="unit",
        attachments=None
    )
    assert task.attachments is None

def test_task_with_invalid_attachment_type():
    with pytest.raises(ValueError, match="attachments must be a Pydantic BaseModel instance"):
        Task(
            id="t5",
            class_name="TestTask",
            source="unit",
            attachments={"foo": "bar"}
        )
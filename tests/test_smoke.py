"""farspec 轻量冒烟测试。

farspec 是一个纯 Python 的任务协议规范包（Request/Response/Task 基类 +
dataclass<->dict 序列化工具），不依赖网络、数据库或云服务，也没有
[project.scripts] CLI 入口，因此这里不需要 mock 任何外部资源。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import pytest


class _Color(str, Enum):
    RED = "red"
    BLUE = "blue"


@dataclass
class _Inner:
    color: _Color
    note: str | None = None


@dataclass
class _Outer:
    inner: _Inner
    tags: list[str] | None = None


def test_import_top_level_package():
    """顶层包应可正常导入（当前 __init__.py 为空，仅验证包结构存在）。"""
    import farspec  # noqa: F401


def test_import_task_submodule_public_surface():
    """farspec.task 子模块及其公开符号应可导入。"""
    from farspec import task

    for name in ("BaseRequest", "BaseResponse", "BaseTask", "RuntimeEvent", "TaskStatus"):
        assert hasattr(task, name)
        assert name in task.__all__


def test_task_status_enum_values():
    from farspec.task import TaskStatus

    assert TaskStatus.PENDING == "pending"
    assert TaskStatus.RUNNING == "running"
    assert TaskStatus.SUCCEEDED == "succeeded"
    assert TaskStatus.FAILED == "failed"


def test_base_request_defaults_and_merge_meta():
    from farspec.task import BaseRequest

    req = BaseRequest()
    # request_id 应自动生成为非空字符串
    assert isinstance(req.request_id, str) and req.request_id
    assert req.meta == {}

    req.merge_meta({"a": 1}, b=2)
    assert req.meta == {"a": 1, "b": 2}

    req2 = BaseRequest(request_id="fixed-id")
    assert req2.request_id == "fixed-id"


def test_runtime_event_defaults():
    from farspec.task import RuntimeEvent

    ev = RuntimeEvent(name="step1")
    assert ev.name == "step1"
    assert ev.level == "info"
    assert isinstance(ev.timestamp, datetime)


def test_base_response_lifecycle():
    from farspec.task import BaseResponse, TaskStatus

    resp = BaseResponse(request_id="req-1")
    assert resp.status == TaskStatus.PENDING

    resp.mark_running()
    assert resp.status == TaskStatus.RUNNING
    assert resp.started_at is not None

    resp.add_event("progress", "50%", data={"pct": 50})
    assert len(resp.events) == 1
    assert resp.events[0].name == "progress"

    resp.mark_succeeded(payload={"ok": True})
    assert resp.status == TaskStatus.SUCCEEDED
    assert resp.payload == {"ok": True}

    resp.mark_finished()
    assert resp.finished_at is not None
    assert resp.duration_ms is not None and resp.duration_ms >= 0


def test_base_response_mark_failed():
    from farspec.task import BaseResponse

    resp = BaseResponse()
    resp.mark_running()
    try:
        raise ValueError("boom")
    except ValueError as exc:
        resp.mark_failed(exc)

    assert resp.status.value == "failed"
    assert resp.error_type == "ValueError"
    assert resp.error == "boom"


def test_dict_serializable_roundtrip():
    """验证 DictSerializable/to_dict/from_dict 在自定义 dataclass 子类上工作。"""
    from farspec.task.request import BaseRequest

    @dataclass
    class MyRequest(BaseRequest):
        name: str = "default"
        count: int = 0

    req = MyRequest(request_id="r1", name="hello", count=3)
    data = req.to_dict()
    assert data["request_id"] == "r1"
    assert data["name"] == "hello"
    assert data["count"] == 3

    restored = MyRequest.from_dict(data)
    assert restored.request_id == "r1"
    assert restored.name == "hello"
    assert restored.count == 3


def test_serialization_to_jsonable_and_from_jsonable():
    from farspec.task.serialization import to_jsonable, from_jsonable, utcnow

    now = utcnow()
    assert now.tzinfo is not None

    assert to_jsonable(None) is None
    assert to_jsonable(1) == 1
    assert to_jsonable("x") == "x"
    assert to_jsonable([1, "a"]) == [1, "a"]
    assert to_jsonable({"a": 1}) == {"a": 1}

    iso = to_jsonable(now)
    assert isinstance(iso, str)
    parsed = from_jsonable(datetime, iso)
    assert isinstance(parsed, datetime)


def test_to_jsonable_rejects_unsupported_type():
    from farspec.task.serialization import to_jsonable

    class Unsupported:
        pass

    with pytest.raises(TypeError):
        to_jsonable(Unsupported())


def test_from_jsonable_type_mismatch_raises():
    from farspec.task.serialization import from_jsonable

    with pytest.raises(TypeError):
        from_jsonable(list, "not-a-list")

    with pytest.raises(TypeError):
        from_jsonable(datetime, 123)


def test_dataclass_from_dict_strict_missing_field_raises():
    from farspec.task.serialization import dataclass_from_dict

    @dataclass
    class Point:
        x: int
        y: int

    with pytest.raises(KeyError):
        dataclass_from_dict(Point, {"x": 1}, strict=True)

    # 非 strict 模式下缺字段交由构造函数处理，缺少必填参数应抛 TypeError
    with pytest.raises(TypeError):
        dataclass_from_dict(Point, {"x": 1}, strict=False)


def test_dataclass_roundtrip_nested_enum_and_optional():
    from farspec.task.serialization import dataclass_from_dict, dataclass_to_dict

    obj = _Outer(inner=_Inner(color=_Color.RED, note=None), tags=["a", "b"])
    data = dataclass_to_dict(obj)
    assert data == {
        "inner": {"color": "red", "note": None},
        "tags": ["a", "b"],
    }

    restored = dataclass_from_dict(_Outer, data)
    assert restored.inner.color == _Color.RED
    assert restored.inner.note is None
    assert restored.tags == ["a", "b"]

    # Optional 字段缺省时应保持 None，而不是报错
    data_no_tags = {"inner": {"color": "blue", "note": "hi"}}
    restored2 = dataclass_from_dict(_Outer, data_no_tags)
    assert restored2.tags is None
    assert restored2.inner.color == _Color.BLUE


def test_base_task_run_success():
    """BaseTask 子类走完整的 run() 生命周期，应到达 SUCCEEDED 且记录事件。"""
    from farspec.task import BaseRequest, BaseResponse, BaseTask, TaskStatus

    class EchoTask(BaseTask[BaseRequest, BaseResponse]):
        def build_response(self) -> BaseResponse:
            return BaseResponse()

        def execute(self, response: BaseResponse, *args, **kwargs) -> BaseResponse:
            response.add_event("echo", "doing work")
            response.mark_succeeded(payload={"echoed": True})
            return response

    task = EchoTask(BaseRequest(request_id="req-42"))
    result = task.run()

    assert result.status == TaskStatus.SUCCEEDED
    assert result.request_id == "req-42"
    assert result.payload == {"echoed": True}
    event_names = [e.name for e in result.events]
    assert "task_started" in event_names
    assert "echo" in event_names
    assert "task_finished" in event_names
    assert result.finished_at is not None


def test_base_task_run_catches_exception():
    """execute() 抛异常时 run() 应捕获并把状态置为 FAILED，而不是向上抛出。"""
    from farspec.task import BaseRequest, BaseResponse, BaseTask, TaskStatus

    class FailingTask(BaseTask[BaseRequest, BaseResponse]):
        def build_response(self) -> BaseResponse:
            return BaseResponse()

        def execute(self, response: BaseResponse, *args, **kwargs) -> BaseResponse:
            raise RuntimeError("something broke")

    task = FailingTask(BaseRequest())
    result = task.run()

    assert result.status == TaskStatus.FAILED
    assert result.error_type == "RuntimeError"
    assert result.error == "something broke"
    assert any(e.name == "task_failed" for e in result.events)


def test_no_cli_entry_point_declared():
    """farspec 的 pyproject.toml 未声明 [project.scripts]，因此没有 CLI 需要冒烟测试。"""
    import tomllib
    from pathlib import Path

    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text())
    assert data.get("project", {}).get("scripts", {}) == {}

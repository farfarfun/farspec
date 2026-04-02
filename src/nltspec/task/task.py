"""Task(Request) 与 run 生命周期。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from spec_python.request import BaseRequest
from spec_python.response import BaseResponse, TaskStatus
from spec_python.serialization import utcnow

RQ = TypeVar("RQ", bound=BaseRequest)
RS = TypeVar("RS", bound=BaseResponse)


class BaseTask(ABC, Generic[RQ, RS]):
    """由 Request 构造，``run`` 负责时间戳、事件与异常封装。

    子类实现 :meth:`execute`，返回已填充业务字段的 Response（或同一实例）。
    """

    def __init__(self, request: RQ) -> None:
        self.request = request

    @abstractmethod
    def build_response(self) -> RS:
        """创建本次运行的 Response 壳（可预填 request_id）。"""

    @abstractmethod
    def execute(self, response: RS, *args: Any, **kwargs: Any) -> RS:
        """核心逻辑：根据 ``self.request`` 写入 ``response`` 并返回。"""

    def run(self, *args: Any, **kwargs: Any) -> RS:
        active: RS = self.build_response()
        if active.request_id is None:
            active.request_id = self.request.request_id
        active.mark_running()
        active.add_event("task_started", "run() entered", data={"args_count": len(args)})

        try:
            result = self.execute(active, *args, **kwargs)
            if result is not active:
                active = result
            if active.status == TaskStatus.RUNNING:
                active.mark_succeeded()
            return active
        except Exception as exc:  # noqa: BLE001 — 规范层统一收口
            active.mark_failed(exc)
            active.add_event(
                "task_failed",
                str(exc),
                level="error",
                data={"error_type": type(exc).__name__},
            )
            return active
        finally:
            active.mark_finished()
            active.add_event("task_finished", f"status={active.status.value}")

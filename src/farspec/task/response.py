"""Task 输出：运行轨迹 + 结果。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from .serialization import DictSerializable, utcnow


class TaskStatus(str, Enum):
    """任务终态枚举：待处理 / 运行中 / 成功 / 失败。"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass
class RuntimeEvent(DictSerializable):
    """单次运行事件（日志切片、阶段点、指标快照等）。"""

    name: str
    message: str = ""
    timestamp: datetime = field(default_factory=utcnow)
    level: str = "info"
    data: dict[str, Any] | None = None


@dataclass
class BaseResponse(DictSerializable):
    """可序列化响应基类，包含时间与事件轨迹。

    - ``started_at`` / ``finished_at``：执行窗口（run 包装器写入）
    - ``events``：有序运行事件
    - ``status`` / ``error``：终态
    - ``payload``：业务结果（推荐子类改为强类型字段，或沿用 dict）
    """

    request_id: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: float | None = None
    events: list[RuntimeEvent] = field(default_factory=list)
    error: str | None = None
    error_type: str | None = None
    payload: dict[str, Any] | None = None

    def add_event(
        self,
        name: str,
        message: str = "",
        *,
        level: str = "info",
        data: dict[str, Any] | None = None,
    ) -> RuntimeEvent:
        """追加一条运行事件到 ``events``。

        Args:
            name: 事件名称。
            message: 事件描述，可选。
            level: 事件级别，默认 "info"。
            data: 附加结构化数据，可选。

        Returns:
            新创建并已追加的 RuntimeEvent。
        """
        ev = RuntimeEvent(name=name, message=message, level=level, data=data)
        self.events.append(ev)
        return ev

    def mark_running(self) -> None:
        """标记任务进入运行中状态，首次调用时记录开始时间。"""
        self.status = TaskStatus.RUNNING
        if self.started_at is None:
            self.started_at = utcnow()

    def mark_finished(self) -> None:
        """记录结束时间，并在已有开始时间时计算耗时（毫秒）。"""
        self.finished_at = utcnow()
        if self.started_at is not None and self.finished_at is not None:
            delta = self.finished_at - self.started_at
            self.duration_ms = delta.total_seconds() * 1000.0

    def mark_succeeded(self, payload: dict[str, Any] | None = None) -> None:
        """标记任务成功，可选写入业务结果。

        Args:
            payload: 业务结果，传入时会覆盖已有 payload。

        Returns:
            None。
        """
        if payload is not None:
            self.payload = payload
        self.status = TaskStatus.SUCCEEDED

    def mark_failed(self, exc: BaseException, *, message: str | None = None) -> None:
        """标记任务失败，记录异常类型与错误信息。

        Args:
            exc: 捕获到的异常实例。
            message: 自定义错误信息，不传则使用 ``str(exc)``。

        Returns:
            None。
        """
        self.status = TaskStatus.FAILED
        self.error_type = type(exc).__name__
        self.error = message if message is not None else str(exc)

"""Task 输出：运行轨迹 + 结果。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .serialization import DictSerializable, utcnow


class TaskStatus(str, Enum):
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
    data: Optional[Dict[str, Any]] = None


@dataclass
class BaseResponse(DictSerializable):
    """可序列化响应基类，包含时间与事件轨迹。

    - ``started_at`` / ``finished_at``：执行窗口（run 包装器写入）
    - ``events``：有序运行事件
    - ``status`` / ``error``：终态
    - ``payload``：业务结果（推荐子类改为强类型字段，或沿用 dict）
    """

    request_id: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    events: List[RuntimeEvent] = field(default_factory=list)
    error: Optional[str] = None
    error_type: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None

    def add_event(
        self,
        name: str,
        message: str = "",
        *,
        level: str = "info",
        data: Optional[Dict[str, Any]] = None,
    ) -> RuntimeEvent:
        ev = RuntimeEvent(name=name, message=message, level=level, data=data)
        self.events.append(ev)
        return ev

    def mark_running(self) -> None:
        self.status = TaskStatus.RUNNING
        if self.started_at is None:
            self.started_at = utcnow()

    def mark_finished(self) -> None:
        self.finished_at = utcnow()
        if self.started_at is not None and self.finished_at is not None:
            delta = self.finished_at - self.started_at
            self.duration_ms = delta.total_seconds() * 1000.0

    def mark_succeeded(self, payload: Optional[Dict[str, Any]] = None) -> None:
        if payload is not None:
            self.payload = payload
        self.status = TaskStatus.SUCCEEDED

    def mark_failed(self, exc: BaseException, *, message: Optional[str] = None) -> None:
        self.status = TaskStatus.FAILED
        self.error_type = type(exc).__name__
        self.error = message if message is not None else str(exc)

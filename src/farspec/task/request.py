"""Task 输入：Request 基类。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, Mapping, Optional, TypeVar
import uuid

from .serialization import DictSerializable

R = TypeVar("R", bound="BaseRequest")


@dataclass
class BaseRequest(DictSerializable):
    """可序列化请求基类。子类用 @dataclass 增加字段。

    ``request_id`` 用于与 Response 关联；``meta`` 承载版本、追踪等横切信息。
    """

    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    meta: Dict[str, Any] = field(default_factory=dict)

    schema_version: ClassVar[str] = "1"

    def merge_meta(self, other: Optional[Mapping[str, Any]] = None, **kwargs: Any) -> None:
        if other:
            self.meta = {**self.meta, **dict(other)}
        if kwargs:
            self.meta = {**self.meta, **kwargs}

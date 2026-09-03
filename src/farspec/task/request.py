"""Task 输入：Request 基类。"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, ClassVar, TypeVar

from .serialization import DictSerializable

R = TypeVar("R", bound="BaseRequest")


@dataclass
class BaseRequest(DictSerializable):
    """可序列化请求基类。子类用 @dataclass 增加字段。

    ``request_id`` 用于与 Response 关联；``meta`` 承载版本、追踪等横切信息。
    """

    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    meta: dict[str, Any] = field(default_factory=dict)

    schema_version: ClassVar[str] = "1"

    def merge_meta(self, other: Mapping[str, Any] | None = None, **kwargs: Any) -> None:
        """合并额外的 meta 信息，同名 key 后写入的覆盖先写入的。

        Args:
            other: 待合并的映射，可选。
            **kwargs: 额外的键值对，优先级高于 ``other``。

        Returns:
            None。
        """
        if other:
            self.meta = {**self.meta, **dict(other)}
        if kwargs:
            self.meta = {**self.meta, **kwargs}

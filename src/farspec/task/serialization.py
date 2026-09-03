"""dict ↔ 标量 / datetime / 嵌套可序列化对象的转换工具。"""

from __future__ import annotations

import types
from collections.abc import Mapping
from dataclasses import MISSING, fields, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import (
    Any,
    TypeVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

T = TypeVar("T")

_UNION_ORIGINS = (Union, types.UnionType)


def utcnow() -> datetime:
    """返回当前 UTC 时间（带时区信息）。"""
    return datetime.now(timezone.utc)


def _is_optional(annotation: Any) -> tuple[bool, Any]:
    """判断注解是否形如 ``X | None`` / ``Optional[X]``，并取出 X。

    同时识别 ``typing.Union``（``Optional[X]``）与 PEP 604 的
    ``types.UnionType``（``X | None``），二者是不同的运行时对象。

    Args:
        annotation: 待检查的类型注解。

    Returns:
        ``(是否可选, 内层类型)``；不满足条件时返回 ``(False, annotation)``。
    """
    origin = get_origin(annotation)
    if origin in _UNION_ORIGINS:
        args = [a for a in get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return True, args[0]
    return False, annotation


def to_jsonable(value: Any) -> Any:
    """将任意受支持的值转换为 JSON 友好的原生类型。

    Args:
        value: 待转换的值，支持 None、Enum、datetime、Mapping、list/tuple、
            dataclass、实现 ``to_dict`` 的对象，以及 str/int/float/bool。

    Returns:
        转换后的 JSON 友好值。

    Raises:
        TypeError: 值的类型不受支持。
    """
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    if is_dataclass(value) and not isinstance(value, type):
        return dataclass_to_dict(value)
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    if isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"无法序列化为 JSON 友好类型: {type(value)!r}")


def from_jsonable(typ: Any, value: Any) -> Any:
    """按照给定类型注解，将 JSON 友好值还原为目标类型的实例。

    Args:
        typ: 目标类型注解，支持 ``X | None``/``Optional[X]``、list、dict、
            Enum、datetime、dataclass 及基础标量类型。
        value: 待还原的 JSON 友好值。

    Returns:
        还原后的值。

    Raises:
        TypeError: 值与目标类型不匹配，或类型不受支持。
    """
    if value is None:
        return None
    optional, inner = _is_optional(typ)
    if optional and value is None:
        return None
    typ = inner if optional else typ
    origin = get_origin(typ)

    if origin is list or typ is list:
        args = get_args(typ)
        item_typ = args[0] if args else Any
        if not isinstance(value, list):
            raise TypeError(f"期望 list，得到 {type(value)!r}")
        return [from_jsonable(item_typ, v) for v in value]

    if origin in (dict, Mapping) or typ in (dict, Mapping):
        args = get_args(typ)
        if len(args) >= 2:
            kt, vt = args[0], args[1]
            if not isinstance(value, Mapping):
                raise TypeError(f"期望 Mapping，得到 {type(value)!r}")
            return {
                from_jsonable(kt, k): from_jsonable(vt, v) for k, v in value.items()
            }
        return dict(value) if isinstance(value, Mapping) else value

    if isinstance(typ, type) and issubclass(typ, Enum):
        if isinstance(value, typ):
            return value
        return typ(value)

    if typ is datetime or typ is type(datetime):
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        raise TypeError(f"无法解析 datetime: {type(value)!r}")

    if is_dataclass(typ) and isinstance(value, Mapping):
        return dataclass_from_dict(typ, dict(value))

    if isinstance(value, Mapping) and (typ is Any or typ is type(Any)):
        return dict(value)

    if typ in (str, int, float, bool):
        return typ(value)
    if typ is Any:
        return value
    raise TypeError(f"无法反序列化类型 {typ!r} from {type(value)!r}")


def dataclass_to_dict(obj: Any) -> dict[str, Any]:
    """将 dataclass 实例转换为 JSON 友好的 dict。

    Args:
        obj: dataclass 实例。

    Returns:
        字段名到 JSON 友好值的映射；标记了 ``exclude_from_dict`` 元数据的
        字段会被跳过。

    Raises:
        TypeError: obj 不是 dataclass 实例。
    """
    if not is_dataclass(obj) or isinstance(obj, type):
        raise TypeError("dataclass_to_dict 需要 dataclass 实例")
    out: dict[str, Any] = {}
    for f in fields(obj):
        if f.metadata.get("exclude_from_dict"):
            continue
        val = getattr(obj, f.name)
        out[f.name] = to_jsonable(val)
    return out


def dataclass_from_dict(
    cls: type[T], data: Mapping[str, Any], *, strict: bool = False
) -> T:
    """由 dict 构造 dataclass 实例。

    Args:
        cls: 目标 dataclass 类。
        data: 字段名到 JSON 友好值的映射。
        strict: 为 True 时，缺失且无默认值的字段会抛出 KeyError；
            默认为 False，此时缺失字段直接跳过（交由构造函数处理）。

    Returns:
        构造出的 dataclass 实例。

    Raises:
        TypeError: cls 不是 dataclass 类。
        KeyError: strict=True 且存在缺失字段。
    """
    if not is_dataclass(cls) or not isinstance(cls, type):
        raise TypeError("dataclass_from_dict 需要 dataclass 类")
    try:
        hints = get_type_hints(cls)
    except Exception:
        hints = {}
    kwargs: dict[str, Any] = {}
    for f in fields(cls):
        if f.metadata.get("exclude_from_dict"):
            continue
        ftyp = hints.get(f.name, f.type)
        if f.name in data:
            kwargs[f.name] = from_jsonable(ftyp, data[f.name])
        elif f.default is not MISSING:
            kwargs[f.name] = f.default
        elif f.default_factory is not MISSING:
            factory = f.default_factory
            assert callable(factory)
            kwargs[f.name] = factory()
        elif strict:
            raise KeyError(f"缺少字段: {f.name}")
    return cls(**kwargs)  # type: ignore[call-arg]


class DictSerializable:
    """为 dataclass 子类提供 to_dict / from_dict。"""

    def to_dict(self) -> dict[str, Any]:
        """将当前实例转换为 JSON 友好的 dict。"""
        return dataclass_to_dict(self)

    @classmethod
    def from_dict(cls: type[T], data: Mapping[str, Any], *, strict: bool = False) -> T:
        """由 dict 构造当前类的实例。

        Args:
            data: 字段名到 JSON 友好值的映射。
            strict: 为 True 时，缺失且无默认值的字段会抛出 KeyError。

        Returns:
            构造出的实例。
        """
        return dataclass_from_dict(cls, data, strict=strict)

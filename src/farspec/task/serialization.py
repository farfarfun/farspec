"""dict ↔ 标量 / datetime / 嵌套可序列化对象的转换工具。"""

from __future__ import annotations

from dataclasses import MISSING, fields, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import (
    Any,
    Dict,
    Mapping,
    Type,
    TypeVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

T = TypeVar("T")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _is_optional(annotation: Any) -> tuple[bool, Any]:
    origin = get_origin(annotation)
    if origin is Union:
        args = [a for a in get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return True, args[0]
    return False, annotation


def to_jsonable(value: Any) -> Any:
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


def dataclass_to_dict(obj: Any) -> Dict[str, Any]:
    if not is_dataclass(obj) or isinstance(obj, type):
        raise TypeError("dataclass_to_dict 需要 dataclass 实例")
    out: Dict[str, Any] = {}
    for f in fields(obj):
        if f.metadata.get("exclude_from_dict"):
            continue
        val = getattr(obj, f.name)
        out[f.name] = to_jsonable(val)
    return out


def dataclass_from_dict(
    cls: Type[T], data: Mapping[str, Any], *, strict: bool = False
) -> T:
    if not is_dataclass(cls) or not isinstance(cls, type):
        raise TypeError("dataclass_from_dict 需要 dataclass 类")
    try:
        hints = get_type_hints(cls)
    except Exception:
        hints = {}
    kwargs: Dict[str, Any] = {}
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

    def to_dict(self) -> Dict[str, Any]:
        return dataclass_to_dict(self)

    @classmethod
    def from_dict(cls: Type[T], data: Mapping[str, Any], *, strict: bool = False) -> T:
        return dataclass_from_dict(cls, data, strict=strict)

# Changelog

## 1.0.9（当前）

### 新增

（无）

### 修复

（无）

### 变更

- `task/request.py`、`task/response.py`、`task/serialization.py` 类型标注统一改为内置泛型
  （`Dict`/`List`/`Optional[X]`/`Type` → `dict`/`list`/`X | None`/`type`）。
- `serialization._is_optional` 补充对 `types.UnionType`（PEP 604 `X | None` 运行时类型）的识别，
  与 `typing.Union`（`Optional[X]`）区分处理，避免迁移到新语法后可选字段反序列化失效。
- 公开函数/方法补充中文 Args/Returns/Raises docstring。
- README 补充真实的特性介绍、安装与快速开始示例，并追加组织介绍固定区块。
- `.gitignore` 补充 `.idea/`、`.vscode/`、`*.db`、`*.rar`、`.run/`、`logs/` 规则。
- 新增 `uv.lock`。

### 废弃

（无）

## 1.0.8 及更早版本

早期版本未维护 CHANGELOG，具体变更参见 git 提交历史。

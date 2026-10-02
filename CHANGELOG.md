# Changelog

## 1.0.10（当前）

### 新增

- 开发依赖加入 `ruff`，README 开发章节补充 `ruff check` / `ruff format --check` 步骤。

### 修复

- `from_jsonable` 收到 `None` 时不再无条件返回 `None`：仅 `Any`、`NoneType` 与包含
  `None` 成员的联合类型（含 `int | str | None` 这类多成员联合）接受 `None`，其余非可选
  目标类型按 docstring 声明抛出 `TypeError`，不再绕过类型边界校验。

### 变更

- `[project].description` 由占位值 `farspec` 改为真实功能描述，与 README、GitHub 仓库
  描述保持一致（下次发版后在包元数据中生效）。
- README 安装章节改为从仓库安装 / 可编辑安装，与当前未上线 PyPI 的发布状态一致。

### 废弃

（无）

## 1.0.9

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

## 1.0.8

### 新增

- 无。

### 修复

- 无。

### 变更

- 更新项目版本至 1.0.8。

### 废弃

- 无。

## 1.0.7

### 新增

- 无。

### 修复

- 无。

### 变更

- 更新项目版本至 1.0.7。

### 废弃

- 无。

## 1.0.6

### 新增

- 无。

### 修复

- 无。

### 变更

- 更新项目版本至 1.0.6。

### 废弃

- 无。

## 1.0.5

### 新增

- 无。

### 修复

- 修正项目改名为 `farspec` 后的包元数据与导入路径。

### 变更

- 更新项目版本至 1.0.5。

### 废弃

- `nltspec` 名称冻结，不再作为当前项目名称使用。

## 1.0.3

### 新增

- 无。

### 修复

- 修复请求模块的序列化导入。

### 变更

- 更新项目版本至 1.0.3。

### 废弃

- 无。

## 1.0.2

### 新增

- 无。

### 修复

- 修正任务模块导入路径。

### 变更

- 更新项目版本至 1.0.2。

### 废弃

- 无。

## 1.0.1

### 新增

- 初始提供任务请求、响应、状态与序列化模型。

### 修复

- 无。

### 变更

- 初始化 `nltspec` 版本 1.0.1。

### 废弃

- 无。
